"""Pagos, eventos de pago, comisiones y liquidaciones.

Nunca se almacenan datos completos de tarjeta: solo referencias y tokens
devueltos por el proveedor (ADR-03).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import (
    CommissionStatus,
    PaymentMethod,
    PaymentStatus,
    SettlementStatus,
)

if TYPE_CHECKING:
    from app.models.order import Order, SubOrder
    from app.models.producer import ProducerProfile


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Intento de pago de un pedido."""

    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    method: Mapped[PaymentMethod] = mapped_column(
        pg_enum(PaymentMethod, "payment_method"), nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    status: Mapped[PaymentStatus] = mapped_column(
        pg_enum(PaymentStatus, "payment_status"),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship()
    events: Mapped[list["PaymentEvent"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Idempotencia de webhooks: el mismo evento del proveedor no puede
        # procesarse dos veces, garantizado por la base de datos.
        UniqueConstraint("provider", "provider_reference", name="uq_payments_provider_reference"),
        Index("ix_payments_order", "order_id"),
        Index("ix_payments_status", "status"),
        CheckConstraint("amount > 0", name="payment_amount_positive"),
    )


class PaymentEvent(Base, UUIDPrimaryKeyMixin):
    """Traza de cada evento recibido o generado sobre un pago.

    Conserva la carga cruda del proveedor y si la firma resultó válida: es la
    evidencia disponible ante una disputa.
    """

    __tablename__ = "payment_events"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    signature_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    payment: Mapped["Payment"] = relationship(back_populates="events")

    __table_args__ = (Index("ix_payment_events_payment", "payment_id", "created_at"),)


class Commission(Base, UUIDPrimaryKeyMixin):
    """Comisión de la plataforma sobre una sub-orden.

    `rate_applied` guarda la tasa vigente en el momento de confirmar: cambiar la
    comisión no altera pedidos ya calculados (HU-ADM-05, CA2).
    """

    __tablename__ = "commissions"

    sub_order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sub_orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    rate_applied: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    status: Mapped[CommissionStatus] = mapped_column(
        pg_enum(CommissionStatus, "commission_status"),
        default=CommissionStatus.PENDING,
        nullable=False,
    )
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("settlements.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sub_order: Mapped["SubOrder"] = relationship()
    settlement: Mapped["Settlement | None"] = relationship(back_populates="commissions")

    __table_args__ = (
        Index("ix_commissions_settlement", "settlement_id"),
        Index("ix_commissions_status", "status"),
        CheckConstraint("rate_applied >= 0 AND rate_applied <= 1", name="commission_rate_range"),
        CheckConstraint("commission_amount >= 0", name="commission_amount_non_negative"),
    )


class Settlement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Liquidación periódica a un productor.

    En el MVP no hay dispersión real de fondos: la liquidación se calcula y
    registra, quedando marcada como pendiente de pago manual (HU-PRO-11, CA3).
    """

    __tablename__ = "settlements"

    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    commission_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    status: Mapped[SettlementStatus] = mapped_column(
        pg_enum(SettlementStatus, "settlement_status"),
        default=SettlementStatus.DRAFT,
        nullable=False,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    producer: Mapped["ProducerProfile"] = relationship()
    commissions: Mapped[list["Commission"]] = relationship(back_populates="settlement")

    __table_args__ = (
        Index("ix_settlements_producer", "producer_id", "period_start"),
        UniqueConstraint("producer_id", "period_start", "period_end", name="uq_settlements_period"),
        CheckConstraint("period_start <= period_end", name="settlement_period_valid"),
        CheckConstraint(
            "net_amount = gross_amount - commission_total", name="settlement_net_consistent"
        ),
    )
