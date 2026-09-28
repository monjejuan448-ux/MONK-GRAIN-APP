"""Perfiles de productor y empresa, fincas y certificaciones."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import (
    BusinessStatus,
    BusinessType,
    CertStatus,
    ProducerStatus,
    ProducerType,
)

if TYPE_CHECKING:
    from app.models.geo import Municipality, Region
    from app.models.user import User


class ProducerProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Perfil comercial de un caficultor, finca, cooperativa o tostador."""

    __tablename__ = "producer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    type: Mapped[ProducerType] = mapped_column(
        pg_enum(ProducerType, "producer_type"), nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    document_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    story: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    department_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    municipality_id: Mapped[int] = mapped_column(
        ForeignKey("municipalities.id", ondelete="RESTRICT"), nullable=False
    )
    production_capacity_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Dirección física y teléfono para notificaciones. El artículo 53 de la Ley
    # 1480 de 2011 obliga a los portales de contacto a llevar un registro con
    # estos datos de cada oferente, y a entregarlos a quien tenga un reclamo.
    #
    # Admiten nulo porque hay perfiles anteriores a esta obligación; el momento
    # de exigirlos es la publicación del primer café, junto al resto de
    # requisitos, no una migración que dejaría filas inválidas.
    #
    # No se serializan en ninguna respuesta pública: se entregan a un comprador
    # concreto cuando abre una reclamación, no al catálogo.
    notification_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    status: Mapped[ProducerStatus] = mapped_column(
        pg_enum(ProducerStatus, "producer_status"),
        default=ProducerStatus.PENDING_APPROVAL,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Datos bancarios cifrados en la aplicación. Nunca se serializan en una
    # respuesta de API, ni siquiera para el administrador (HU-ADM-02, CA5).
    bank_account_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    rating_avg: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.00"), nullable=False
    )
    rating_count: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="producer_profile", foreign_keys=[user_id])
    farms: Mapped[list["Farm"]] = relationship(
        back_populates="producer", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["ProducerCertification"]] = relationship(
        back_populates="producer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_producer_profiles_status", "status"),
        Index("ix_producer_profiles_municipality", "municipality_id"),
        CheckConstraint(
            "rating_avg >= 0 AND rating_avg <= 5",
            name="rating_avg_range",
        ),
    )

    @property
    def is_approved(self) -> bool:
        return self.status == ProducerStatus.APPROVED


class BusinessProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Perfil de comprador empresarial (tostador, distribuidor, cafetería)."""

    __tablename__ = "business_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    type: Mapped[BusinessType] = mapped_column(
        pg_enum(BusinessType, "business_type"), nullable=False
    )
    contact_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    department_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    municipality_id: Mapped[int] = mapped_column(
        ForeignKey("municipalities.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[BusinessStatus] = mapped_column(
        pg_enum(BusinessStatus, "business_status"),
        default=BusinessStatus.PENDING,
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="business_profile")

    @property
    def is_verified(self) -> bool:
        """Solo un perfil verificado accede a precios mayoristas (HU-CE-02)."""
        return self.status == BusinessStatus.VERIFIED


class Farm(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Finca productora.

    Guarda dos ubicaciones: la aproximada, que se publica, y la exacta, que
    queda restringida y nunca se serializa en respuestas públicas (ADR-08).
    Exponer la coordenada real de una finca rural es un riesgo de seguridad
    física para el productor, no solo de privacidad.
    """

    __tablename__ = "farms"

    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    region_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True
    )
    municipality_id: Mapped[int] = mapped_column(
        ForeignKey("municipalities.id", ondelete="RESTRICT"), nullable=False
    )
    village: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area_hectares: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    altitude_min_masl: Mapped[int | None] = mapped_column(nullable=True)
    altitude_max_masl: Mapped[int | None] = mapped_column(nullable=True)

    approx_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    approx_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    exact_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    exact_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    environmental_practices: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    producer: Mapped["ProducerProfile"] = relationship(back_populates="farms")
    municipality: Mapped["Municipality"] = relationship(back_populates="farms")
    region: Mapped["Region | None"] = relationship(back_populates="farms")

    __table_args__ = (
        Index("ix_farms_producer", "producer_id"),
        Index("ix_farms_municipality", "municipality_id"),
        Index("ix_farms_region", "region_id"),
        CheckConstraint(
            "altitude_min_masl IS NULL OR altitude_max_masl IS NULL "
            "OR altitude_min_masl <= altitude_max_masl",
            name="altitude_range_valid",
        ),
    )


class Certification(Base):
    """Catálogo de certificaciones disponibles (Orgánico, Fairtrade, ...)."""

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    issuing_body: Mapped[str | None] = mapped_column(String(150), nullable=True)
    logo_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProducerCertification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Certificación concreta obtenida por un productor, con su vigencia."""

    __tablename__ = "producer_certifications"

    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    certification_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("certifications.id", ondelete="RESTRICT"), nullable=False
    )
    certificate_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Documento privado: se sirve mediante URL firmada de expiración corta.
    document_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[CertStatus] = mapped_column(
        pg_enum(CertStatus, "cert_status"), default=CertStatus.ACTIVE, nullable=False
    )

    producer: Mapped["ProducerProfile"] = relationship(back_populates="certifications")

    __table_args__ = (
        Index("ix_producer_certifications_producer", "producer_id"),
        Index("ix_producer_certifications_expiry", "expires_at"),
        CheckConstraint(
            "issued_at IS NULL OR expires_at IS NULL OR issued_at <= expires_at",
            name="certification_dates_valid",
        ),
    )

    def is_valid_on(self, reference_date: date) -> bool:
        """Una certificación vencida deja de mostrarse como vigente (HU-PRO-09)."""
        if self.status in (CertStatus.EXPIRED, CertStatus.REVOKED):
            return False
        return self.expires_at is None or self.expires_at >= reference_date
