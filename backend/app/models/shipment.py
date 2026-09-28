"""Envíos, eventos de seguimiento y devoluciones.

El envío se asocia a la sub-orden, no al pedido: cada productor despacha por
separado y con su propia guía (ADR-02).
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
    Sequence,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import ReturnReason, ReturnStatus, ShipmentStatus

if TYPE_CHECKING:
    from app.models.order import OrderItem, SubOrder


class Shipment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Despacho de una sub-orden.

    En el MVP el operador es simulado: genera guías y estados de prueba,
    identificados como tales por el valor `simulated` en `carrier`.
    """

    __tablename__ = "shipments"

    sub_order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sub_orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    carrier: Mapped[str] = mapped_column(String(50), nullable=False)
    tracking_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    weight_grams: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    status: Mapped[ShipmentStatus] = mapped_column(
        pg_enum(ShipmentStatus, "shipment_status"),
        default=ShipmentStatus.PENDING,
        nullable=False,
    )
    estimated_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sub_order: Mapped["SubOrder"] = relationship(back_populates="shipment")
    events: Mapped[list["ShipmentEvent"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_shipments_tracking", "tracking_number"),
        Index("ix_shipments_status", "status"),
        CheckConstraint("shipping_cost >= 0", name="shipping_cost_non_negative"),
    )


class ShipmentEvent(Base, UUIDPrimaryKeyMixin):
    """Evento de la línea de tiempo del envío.

    `is_incident` marca las novedades logísticas, que se muestran destacadas al
    comprador (HU-CC-09, CA2).
    """

    __tablename__ = "shipment_events"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False
    )
    event_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_incident: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="events")

    __table_args__ = (Index("ix_shipment_events_shipment", "shipment_id", "occurred_at"),)


# Correlativo de `return_number`, el número de radicación que el comprador usa
# para hacerle seguimiento a su reclamación y que debe acompañar la demanda ante
# la Superintendencia. Es una secuencia por la misma razón que la de pedidos: un
# conteo no es atómico.
return_number_seq = Sequence("return_number_seq", metadata=Base.metadata)


class Return(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Solicitud de devolución sobre una sub-orden ya despachada.

    Una devolución no es un simple «me arrepentí». La Ley 1480 de 2011 distingue
    dos figuras con plazos, costos y consecuencias distintas —el retracto del
    artículo 47 y la garantía legal del artículo 8—, y de esa distinción cuelga
    todo lo demás: hasta cuándo puede pedirse, quién paga el transporte de
    vuelta y en cuánto tiempo hay que devolver el dinero. Por eso el motivo no
    es un texto libre sino un enumerado, y los vencimientos se calculan al
    radicar y se guardan: el plazo del comprador no puede depender de que la
    fórmula siga siendo la misma dentro de un año.

    `created_at` es la fecha y hora de radicación de la constancia.
    """

    __tablename__ = "returns"

    # Número de radicación legible, del estilo DEV-2026-000123.
    return_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    sub_order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sub_orders.id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[ReturnReason] = mapped_column(
        pg_enum(ReturnReason, "return_reason"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Declaración del comprador de que el empaque sigue sellado. Solo tiene
    # sentido en el retracto: la garantía procede aunque el café se haya abierto,
    # y de hecho abrirlo suele ser la única forma de advertir el defecto.
    declared_unopened: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[ReturnStatus] = mapped_column(
        pg_enum(ReturnStatus, "return_status"),
        default=ReturnStatus.REQUESTED,
        nullable=False,
    )

    # Suma de las líneas devueltas. Se calcula al radicar y no se negocia: el
    # artículo 47 prohíbe descuentos y retenciones sobre el reembolso.
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Quién asume el transporte de vuelta, según el motivo (artículos 47 y 11).
    return_shipping_paid_by_seller: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Vencimiento de la respuesta escrita al comprador: quince días hábiles
    # (Decreto 735 de 2013). Se guarda para poder mostrar el reloj y para que
    # quede constancia del plazo que corría cuando se radicó.
    response_due_at: Mapped[date] = mapped_column(Date, nullable=False)
    # Vencimiento del reembolso, distinto según la figura invocada.
    refund_due_at: Mapped[date] = mapped_column(Date, nullable=False)

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sub_order: Mapped["SubOrder"] = relationship()
    items: Mapped[list["ReturnItem"]] = relationship(
        back_populates="return_request", cascade="all, delete-orphan", lazy="selectin"
    )
    evidences: Mapped[list["ReturnEvidence"]] = relationship(
        back_populates="return_request", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_returns_sub_order", "sub_order_id"),
        Index("ix_returns_status", "status"),
        Index("ix_returns_requested_by", "requested_by", "created_at"),
        CheckConstraint(
            "refund_amount IS NULL OR refund_amount >= 0",
            name="refund_amount_non_negative",
        ),
    )


class ReturnItem(Base, UUIDPrimaryKeyMixin):
    """Línea concreta que se devuelve.

    La devolución se pide por producto y no por pedido completo: si llegaron
    tres cafés y solo uno vino dañado, el comprador devuelve ese. Guardar la
    cantidad permite además impedir que se devuelvan más unidades de las que se
    compraron, sumando lo ya devuelto en solicitudes anteriores.
    """

    __tablename__ = "return_items"

    return_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("returns.id", ondelete="CASCADE"), nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    line_refund: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    return_request: Mapped["Return"] = relationship(back_populates="items")
    order_item: Mapped["OrderItem"] = relationship()

    __table_args__ = (
        Index("ix_return_items_return", "return_id"),
        Index("ix_return_items_order_item", "order_item_id"),
        CheckConstraint("quantity > 0", name="return_item_quantity_positive"),
        CheckConstraint("line_refund >= 0", name="return_item_refund_non_negative"),
    )


class ReturnEvidence(Base, UUIDPrimaryKeyMixin):
    """Fotografía que respalda la reclamación.

    Se guarda fuera de los prefijos públicos y se entrega con enlaces de vida
    corta: son fotos tomadas en casa del comprador y no tienen por qué ser
    legibles por cualquiera que adivine una URL.
    """

    __tablename__ = "return_evidences"

    return_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("returns.id", ondelete="CASCADE"), nullable=False
    )
    file_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    return_request: Mapped["Return"] = relationship(back_populates="evidences")

    __table_args__ = (Index("ix_return_evidences_return", "return_id"),)
