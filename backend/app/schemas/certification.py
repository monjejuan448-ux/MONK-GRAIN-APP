"""Esquemas de las certificaciones del vendedor.

Un certificado respalda lo que el café afirma ser: orgánico, de comercio justo,
de denominación de origen. Por eso lleva vigencia y documento — y por eso el
documento no es público.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.models.enums import CertStatus
from app.schemas.common import ORMModel


class CertificationCatalogItem(ORMModel):
    """Certificación disponible para asociar."""

    id: int
    code: str
    name: str
    issuing_body: str | None
    description: str | None


class ProducerCertificationInput(BaseModel):
    certification_id: int
    certificate_number: str | None = Field(default=None, max_length=100)
    issued_at: date | None = None
    expires_at: date | None = None

    @model_validator(mode="after")
    def dates_are_coherent(self) -> ProducerCertificationInput:
        """La emisión no puede ser posterior al vencimiento.

        La base de datos ya lo impide con un `CHECK`, pero llegar hasta allí
        devolvería un 409 genérico en vez de decir cuál de las dos fechas está
        mal.
        """
        if self.issued_at and self.expires_at and self.issued_at > self.expires_at:
            raise ValueError("La fecha de emisión no puede ser posterior a la de vencimiento.")
        return self


class ProducerCertificationResponse(ORMModel):
    id: uuid.UUID
    certification_id: int
    certification_code: str
    certification_name: str
    issuing_body: str | None
    certificate_number: str | None
    issued_at: date | None
    expires_at: date | None
    status: CertStatus
    has_document: bool
    # Días que faltan para vencer. Negativo si ya venció, nulo si no caduca.
    days_to_expiry: int | None


class CertificateDocumentLink(BaseModel):
    """Enlace temporal al documento.

    No se devuelve una URL permanente: el certificado lleva datos del productor
    y un enlace que no caduca sigue funcionando para quien lo reenvíe.
    """

    url: str
    expires_in_seconds: int
