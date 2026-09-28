"""Certificaciones del vendedor y su vigencia.

Un certificado es la prueba de lo que el café afirma ser. Tiene dos
particularidades frente al resto del catálogo:

- **Caduca.** El estado no se guarda y se olvida: se recalcula con la fecha de
  vencimiento cada vez que se consulta, porque un certificado no deja de estar
  vencido porque nadie haya pasado a marcarlo.
- **No es público.** El documento lleva números de registro y datos del
  productor, así que se guarda fuera de los prefijos abiertos y solo se entrega
  mediante un enlace de vida corta.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.files import StoredFile
from app.core.logging import get_logger
from app.integrations.storage import get_storage
from app.integrations.storage.base import CERTIFICATE_PREFIX
from app.models.catalog import Product, ProductCertification
from app.models.enums import CertStatus
from app.models.producer import Certification, ProducerCertification, ProducerProfile
from app.models.user import User
from app.schemas.certification import (
    CertificateDocumentLink,
    CertificationCatalogItem,
    ProducerCertificationInput,
    ProducerCertificationResponse,
)

logger = get_logger(__name__)

# Un certificado a punto de vencer se marca antes de caducar para que el
# productor tenga margen de renovarlo.
EXPIRY_WARNING_DAYS = 60

DOCUMENT_LINK_TTL_SECONDS = 300


class CertificationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.storage = get_storage()

    # ------------------------------------------------------------------
    # Catálogo
    # ------------------------------------------------------------------
    def list_catalog(self) -> list[CertificationCatalogItem]:
        """Certificaciones que el vendedor puede declarar."""
        rows = self.session.scalars(select(Certification).order_by(Certification.name)).all()
        return [CertificationCatalogItem.model_validate(row, from_attributes=True) for row in rows]

    # ------------------------------------------------------------------
    # Certificaciones del vendedor
    # ------------------------------------------------------------------
    def _profile(self, user: User) -> ProducerProfile:
        if user.producer_profile is None:
            raise ForbiddenError("Tu cuenta no tiene un perfil de productor.")
        return user.producer_profile

    def _owned(self, user: User, certification_id: uuid.UUID) -> ProducerCertification:
        profile = self._profile(user)
        row = self.session.get(ProducerCertification, certification_id)
        if row is None:
            raise NotFoundError("No encontramos esta certificación.")
        if row.producer_id != profile.id:
            raise ForbiddenError("Esta certificación no pertenece a tu perfil.")
        return row

    def list_own(self, user: User) -> list[ProducerCertificationResponse]:
        profile = self._profile(user)
        rows = self.session.scalars(
            select(ProducerCertification)
            .where(ProducerCertification.producer_id == profile.id)
            .order_by(ProducerCertification.expires_at.asc().nullslast())
        ).all()
        return [self._to_response(row) for row in rows]

    def add(
        self,
        user: User,
        payload: ProducerCertificationInput,
        document: StoredFile | None,
    ) -> ProducerCertificationResponse:
        profile = self._profile(user)

        certification = self.session.get(Certification, payload.certification_id)
        if certification is None:
            raise NotFoundError("Esta certificación no existe en el catálogo.")

        existing = self.session.scalar(
            select(ProducerCertification).where(
                ProducerCertification.producer_id == profile.id,
                ProducerCertification.certification_id == payload.certification_id,
                ProducerCertification.status != CertStatus.REVOKED,
            )
        )
        if existing is not None:
            raise BusinessRuleError(
                f"Ya declaraste la certificación «{certification.name}». "
                "Edita la existente en vez de añadirla otra vez."
            )

        document_key = None
        if document is not None:
            document_key = document.key_for(f"{CERTIFICATE_PREFIX.rstrip('/')}/{profile.id}")
            self.storage.put(document_key, document.content, document.content_type)

        row = ProducerCertification(
            producer_id=profile.id,
            certification_id=payload.certification_id,
            certificate_number=payload.certificate_number,
            issued_at=payload.issued_at,
            expires_at=payload.expires_at,
            document_key=document_key,
            status=self._status_for(payload.expires_at),
        )
        self.session.add(row)
        self.session.commit()

        logger.info(
            "producer_certification_added",
            producer_id=str(profile.id),
            certification=certification.code,
            with_document=document_key is not None,
        )
        return self._to_response(row)

    def delete(self, user: User, certification_id: uuid.UUID) -> None:
        row = self._owned(user, certification_id)
        document_key = row.document_key

        # Las asociaciones producto–certificación se borran en cascada desde la
        # certificación del catálogo, no desde la del productor: aquí solo
        # desaparece la declaración de este vendedor.
        self.session.delete(row)
        self.session.commit()

        if document_key:
            self.storage.delete(document_key)

        logger.info("producer_certification_deleted", certification_id=str(certification_id))

    def document_link(self, user: User, certification_id: uuid.UUID) -> CertificateDocumentLink:
        """Enlace temporal al documento, solo para su dueño."""
        row = self._owned(user, certification_id)
        if not row.document_key:
            raise NotFoundError("Esta certificación no tiene documento adjunto.")

        return CertificateDocumentLink(
            url=self.storage.signed_url(row.document_key, DOCUMENT_LINK_TTL_SECONDS),
            expires_in_seconds=DOCUMENT_LINK_TTL_SECONDS,
        )

    # ------------------------------------------------------------------
    # Asociación con un café
    # ------------------------------------------------------------------
    def attach_to_product(
        self, user: User, product_id: uuid.UUID, certification_id: int
    ) -> list[CertificationCatalogItem]:
        """Declara que un café concreto ampara esta certificación."""
        profile = self._profile(user)
        product = self._owned_product(profile, product_id)

        # Solo puede declararse en un café lo que el productor tiene acreditado:
        # de lo contrario la ficha mostraría un sello sin respaldo.
        held = self.session.scalar(
            select(ProducerCertification).where(
                ProducerCertification.producer_id == profile.id,
                ProducerCertification.certification_id == certification_id,
            )
        )
        if held is None:
            raise BusinessRuleError(
                "Primero registra esta certificación en tu perfil, con su documento y vigencia."
            )
        if self._status_for(held.expires_at) is CertStatus.EXPIRED:
            raise BusinessRuleError(
                "Esta certificación está vencida. Renuévala antes de asociarla a un café."
            )

        already = self.session.get(ProductCertification, (product.id, certification_id))
        if already is None:
            self.session.add(
                ProductCertification(product_id=product.id, certification_id=certification_id)
            )
            self.session.commit()

        return self.list_product_certifications(user, product_id)

    def detach_from_product(
        self, user: User, product_id: uuid.UUID, certification_id: int
    ) -> list[CertificationCatalogItem]:
        profile = self._profile(user)
        product = self._owned_product(profile, product_id)

        row = self.session.get(ProductCertification, (product.id, certification_id))
        if row is not None:
            self.session.delete(row)
            self.session.commit()

        return self.list_product_certifications(user, product_id)

    def list_product_certifications(
        self, user: User, product_id: uuid.UUID
    ) -> list[CertificationCatalogItem]:
        profile = self._profile(user)
        product = self._owned_product(profile, product_id)

        rows = self.session.scalars(
            select(Certification)
            .join(ProductCertification, ProductCertification.certification_id == Certification.id)
            .where(ProductCertification.product_id == product.id)
            .order_by(Certification.name)
        ).all()
        return [CertificationCatalogItem.model_validate(row, from_attributes=True) for row in rows]

    def _owned_product(self, profile: ProducerProfile, product_id: uuid.UUID) -> Product:
        product = self.session.get(Product, product_id)
        if product is None or product.deleted_at is not None:
            raise NotFoundError("No encontramos este café.")
        if product.producer_id != profile.id:
            raise ForbiddenError("Este café no pertenece a tu catálogo.")
        return product

    # ------------------------------------------------------------------
    # Vigencia
    # ------------------------------------------------------------------
    @staticmethod
    def _days_to_expiry(expires_at: date | None) -> int | None:
        if expires_at is None:
            return None
        return (expires_at - datetime.now(UTC).date()).days

    @classmethod
    def _status_for(cls, expires_at: date | None) -> CertStatus:
        """Deriva el estado de la fecha de vencimiento.

        Se calcula en vez de leerse de la columna porque el paso del tiempo no
        dispara ninguna escritura: un certificado vencido ayer seguiría
        figurando como vigente hasta que alguien lo tocara.
        """
        days = cls._days_to_expiry(expires_at)
        if days is None:
            return CertStatus.ACTIVE
        if days < 0:
            return CertStatus.EXPIRED
        if days <= EXPIRY_WARNING_DAYS:
            return CertStatus.EXPIRING
        return CertStatus.ACTIVE

    def _to_response(self, row: ProducerCertification) -> ProducerCertificationResponse:
        certification = self.session.get(Certification, row.certification_id)
        assert certification is not None  # noqa: S101 — la FK lo garantiza

        # Una certificación revocada lo está por decisión, no por fecha.
        status = (
            CertStatus.REVOKED
            if row.status is CertStatus.REVOKED
            else self._status_for(row.expires_at)
        )

        return ProducerCertificationResponse(
            id=row.id,
            certification_id=row.certification_id,
            certification_code=certification.code,
            certification_name=certification.name,
            issuing_body=certification.issuing_body,
            certificate_number=row.certificate_number,
            issued_at=row.issued_at,
            expires_at=row.expires_at,
            status=status,
            has_document=row.document_key is not None,
            days_to_expiry=self._days_to_expiry(row.expires_at),
        )
