"""Pedidos, sub-órdenes por vendedor, ítems e historial de estados.

Un pedido agrupa una o más sub-órdenes, una por productor (ADR-02). El comprador
ve un número de pedido único; la operación real —inventario, envío, estado,
comisión y liquidación— ocurre a nivel de sub-orden, porque cada vendedor
despacha, cancela y cobra por separado.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Sequence,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import OrderStatus, SubOrderStatus

if TYPE_CHECKING:
    from app.models.catalog import ProductVariant
    from app.models.producer import ProducerProfile
    from app.models.shipment import Shipment


# Correlativo de `order_number`. Se declara en los metadatos para que exista
# tanto al migrar como al crear el esquema desde cero en las pruebas.
#
# Es una secuencia y no un `SELECT count(*) + 1` porque el conteo no es atómico:
# dos checkouts simultáneos leían el mismo total y generaban el mismo número.
# `nextval` no toma bloqueos ni se revierte con un `ROLLBACK`, así que puede
# dejar huecos si un pedido falla a medias — admisible en un identificador de
# pedido, que no es una numeración fiscal.
order_number_seq = Sequence("order_number_seq", metadata=Base.metadata)


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pedido del comprador. Contenedor de una o más sub-órdenes."""

    __tablename__ = "orders"

    # Identificador legible para comunicación con el usuario, distinto del UUID
    # interno que no se expone en la interfaz (ADR-05).
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    shipping_address_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True
    )

    # Copia inmutable de la dirección al confirmar: si el comprador la edita o
    # la elimina después, el pedido conserva a dónde se envió realmente.
    shipping_address_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    shipping_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True
    )

    # Estado agregado, derivado de las sub-órdenes. La verdad operativa vive en
    # `sub_orders`; este campo existe para listar y filtrar sin agregaciones.
    status: Mapped[OrderStatus] = mapped_column(
        pg_enum(OrderStatus, "order_status"), default=OrderStatus.PENDING, nullable=False
    )

    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sub_orders: Mapped[list["SubOrder"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_orders_user", "user_id", "placed_at"),
        Index("ix_orders_status", "status"),
        CheckConstraint(
            "grand_total = subtotal + shipping_total - discount_total",
            name="order_totals_consistent",
        ),
        CheckConstraint(
            "subtotal >= 0 AND shipping_total >= 0 AND discount_total >= 0",
            name="order_amounts_non_negative",
        ),
    )


class SubOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Parte del pedido correspondiente a un único productor."""

    __tablename__ = "sub_orders"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sub_order_number: Mapped[str] = mapped_column(String(35), unique=True, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    status: Mapped[SubOrderStatus] = mapped_column(
        pg_enum(SubOrderStatus, "sub_order_status"),
        default=SubOrderStatus.PENDING,
        nullable=False,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="sub_orders")
    producer: Mapped["ProducerProfile"] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="sub_order", cascade="all, delete-orphan", lazy="selectin"
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="sub_order", cascade="all, delete-orphan"
    )
    shipment: Mapped["Shipment | None"] = relationship(back_populates="sub_order", uselist=False)

    __table_args__ = (
        # Índice principal del panel del productor: sus pedidos por estado.
        Index("ix_sub_orders_producer", "producer_id", "status", "created_at"),
        Index("ix_sub_orders_order", "order_id"),
        CheckConstraint(
            "net_amount = subtotal - commission_amount", name="sub_order_net_consistent"
        ),
        CheckConstraint("commission_amount >= 0", name="commission_non_negative"),
    )

    @property
    def is_cancellable(self) -> bool:
        """Solo se cancela antes del despacho (HU-CC-14, CA1 y CA2)."""
        return self.status in (SubOrderStatus.PENDING, SubOrderStatus.CONFIRMED)


class OrderItem(Base, UUIDPrimaryKeyMixin):
    """Línea de una sub-orden.

    Los campos `*_snapshot` congelan el nombre y la presentación del producto al
    momento de la compra: si el productor renombra el café o cambia su precio,
    el pedido histórico no muta (HU-PRO-06, CA3).
    """

    __tablename__ = "order_items"

    sub_order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sub_orders.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )

    product_name_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    variant_label_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)

    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sub_order: Mapped["SubOrder"] = relationship(back_populates="items")
    variant: Mapped["ProductVariant | None"] = relationship()

    __table_args__ = (
        Index("ix_order_items_sub_order", "sub_order_id"),
        Index("ix_order_items_product", "product_id"),
        CheckConstraint("quantity > 0", name="order_item_quantity_positive"),
        CheckConstraint("line_total = unit_price * quantity", name="order_item_total_consistent"),
    )


class OrderStatusHistory(Base, UUIDPrimaryKeyMixin):
    """Historial fechado de cambios de estado de una sub-orden (HU-CC-08, CA2)."""

    __tablename__ = "order_status_history"

    sub_order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sub_orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[SubOrderStatus | None] = mapped_column(
        pg_enum(SubOrderStatus, "sub_order_status"), nullable=True
    )
    to_status: Mapped[SubOrderStatus] = mapped_column(
        pg_enum(SubOrderStatus, "sub_order_status"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sub_order: Mapped["SubOrder"] = relationship(back_populates="status_history")

    __table_args__ = (Index("ix_order_status_history_sub_order", "sub_order_id", "created_at"),)
