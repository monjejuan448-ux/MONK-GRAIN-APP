"""Schemas de los paneles de usuario."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ProducerStatus, ProductStatus, SubOrderStatus, UserStatus


class BuyerDashboard(BaseModel):
    """Resumen de actividad del comprador (HU-CC-08, CA1)."""

    total_orders: int
    orders_in_progress: int
    orders_delivered: int
    total_spent: Decimal
    wishlist_count: int
    pending_reviews: int
    unread_notifications: int


class ProducerSalesPoint(BaseModel):
    """Ventas de un periodo, para la serie temporal del panel."""

    period: str
    orders: int
    revenue: Decimal


class TopProduct(BaseModel):
    product_id: uuid.UUID
    name: str
    slug: str
    units_sold: int
    revenue: Decimal


class ProducerDashboard(BaseModel):
    """Panel del productor (HU-PRO-08)."""

    total_sales: Decimal
    commission_paid: Decimal
    net_earnings: Decimal
    pending_orders: int
    orders_to_prepare: int
    active_products: int
    draft_products: int
    low_stock_variants: int
    rating_avg: Decimal
    rating_count: int
    pending_requests: int
    top_products: list[TopProduct]
    sales_by_month: list[ProducerSalesPoint]


class ProducerOrderItem(BaseModel):
    """Pedido en la bandeja del productor (HU-PRO-07, CA1)."""

    sub_order_id: uuid.UUID
    sub_order_number: str
    order_number: str
    buyer_name: str
    status: SubOrderStatus
    subtotal: Decimal
    net_amount: Decimal
    item_count: int
    shipping_city: str | None
    created_at: datetime


class ProducerProductItem(BaseModel):
    """Producto en la vista de gestión del productor."""

    id: uuid.UUID
    slug: str
    name: str
    status: ProductStatus
    base_price: Decimal
    total_stock: int
    variant_count: int
    sales_count: int
    rating_avg: Decimal
    has_low_stock: bool
    primary_image_url: str | None


class InventoryAlert(BaseModel):
    """Variante con existencias por debajo del umbral (HU-PRO-05, CA3)."""

    variant_id: uuid.UUID
    product_name: str
    variant_label: str
    available_qty: int
    low_stock_threshold: int


class AdminDashboard(BaseModel):
    """Panel administrativo (HU-ADM-08, CA1)."""

    total_users: int
    new_users_period: int
    pending_producers: int
    approved_producers: int
    total_products: int
    published_products: int
    orders_period: int
    revenue_period: Decimal
    commission_period: Decimal
    orders_by_status: dict[str, int]
    reported_reviews: int


class PendingProducerItem(BaseModel):
    """Solicitud de vendedor pendiente de aprobación (HU-ADM-01, CA1)."""

    id: uuid.UUID
    legal_name: str
    brand_name: str | None
    type: str
    document_number: str
    contact_email: str
    contact_name: str
    municipality: str | None
    department: str | None
    production_capacity_kg: Decimal | None
    status: ProducerStatus
    created_at: datetime


class ProducerReviewDecision(BaseModel):
    """Decisión sobre una solicitud de vendedor.

    El motivo es obligatorio al rechazar: una negativa sin explicación deja al
    productor sin saber qué corregir (HU-ADM-01, CA3).
    """

    approve: bool
    reason: str | None = None


class AdminUserItem(BaseModel):
    """Cuenta en el listado del administrador.

    No lleva el documento de identidad ni el teléfono: para decidir una
    suspensión no hacen falta, y un listado es justo donde menos conviene tener
    datos personales que nadie va a usar.
    """

    id: uuid.UUID
    email: str
    full_name: str
    status: UserStatus
    roles: list[str]
    is_producer: bool
    producer_status: str | None
    order_count: int
    created_at: datetime
    last_login_at: datetime | None


class AuditLogEntry(BaseModel):
    id: int
    actor_email: str | None
    action: str
    entity_type: str
    entity_id: str | None
    created_at: datetime


class CommissionSettings(BaseModel):
    default_rate: Decimal
