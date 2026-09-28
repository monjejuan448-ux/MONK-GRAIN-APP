"""Schemas de pedidos."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ShipmentStatus,
    SubOrderStatus,
)
from app.schemas.common import ORMModel


class CheckoutRequest(BaseModel):
    """Datos para confirmar la compra (HU-CC-07)."""

    shipping_address_id: uuid.UUID
    payment_method: PaymentMethod = PaymentMethod.SIMULATED
    coupon_code: str | None = Field(default=None, max_length=40)
    customer_notes: str | None = Field(default=None, max_length=1000)
    accept_terms: bool

    # La aceptación es explícita: sin ella no se crea el pedido (HU-CC-07, CA4).
    def model_post_init(self, _context: object) -> None:
        if not self.accept_terms:
            raise ValueError("Debes aceptar los términos y condiciones para completar la compra.")


class OrderItemResponse(ORMModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    variant_id: uuid.UUID | None
    product_name_snapshot: str
    variant_label_snapshot: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    can_review: bool = False
    has_review: bool = False


class ShipmentResponse(ORMModel):
    carrier: str
    tracking_number: str | None
    tracking_url: str | None
    status: ShipmentStatus
    estimated_delivery_date: date | None
    dispatched_at: datetime | None
    delivered_at: datetime | None


class StatusHistoryEntry(ORMModel):
    from_status: SubOrderStatus | None
    to_status: SubOrderStatus
    note: str | None
    created_at: datetime


class SubOrderResponse(ORMModel):
    """Parte del pedido correspondiente a un productor."""

    id: uuid.UUID
    sub_order_number: str
    producer_id: uuid.UUID
    producer_name: str
    status: SubOrderStatus
    subtotal: Decimal
    shipping_cost: Decimal
    items: list[OrderItemResponse]
    shipment: ShipmentResponse | None = None
    cancellation_reason: str | None = None
    is_cancellable: bool = False
    created_at: datetime


class PaymentResponse(ORMModel):
    provider: str
    method: PaymentMethod
    status: PaymentStatus
    amount: Decimal
    paid_at: datetime | None
    failure_reason: str | None


class OrderSummary(BaseModel):
    """Pedido en el listado del comprador."""

    id: uuid.UUID
    order_number: str
    status: OrderStatus
    grand_total: Decimal
    currency: str
    item_count: int
    seller_count: int
    placed_at: datetime


class OrderDetail(BaseModel):
    """Pedido completo con sus sub-órdenes (HU-CC-08, CA2)."""

    id: uuid.UUID
    order_number: str
    status: OrderStatus
    subtotal: Decimal
    shipping_total: Decimal
    discount_total: Decimal
    grand_total: Decimal
    currency: str
    shipping_address: dict
    customer_notes: str | None
    sub_orders: list[SubOrderResponse]
    payment: PaymentResponse | None
    placed_at: datetime


class CheckoutResponse(BaseModel):
    """Resultado del checkout."""

    order: OrderDetail
    payment_reference: str | None
    # En el MVP el proveedor es simulado y no hay redirección real a pasarela.
    payment_redirect_url: str | None = None
    message: str


class SubOrderStatusUpdate(BaseModel):
    """Avance de estado por parte del productor (HU-PRO-07)."""

    status: SubOrderStatus
    note: str | None = Field(default=None, max_length=500)
    carrier: str | None = Field(default=None, max_length=50)
    tracking_number: str | None = Field(default=None, max_length=80)


class OrderCancelRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
