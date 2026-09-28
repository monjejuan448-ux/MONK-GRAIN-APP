"""Schemas del carrito y los cupones."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import GrindType


class CartItemAdd(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(ge=1, le=999)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=999)


class CartItemResponse(BaseModel):
    """Línea del carrito con el estado actual del producto."""

    id: uuid.UUID
    variant_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_slug: str
    producer_name: str
    image_url: str | None
    weight_grams: Decimal
    grind: GrindType | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    available_qty: int

    # Avisos que la interfaz debe mostrar antes de continuar (HU-CC-05, CA6).
    price_changed: bool = False
    previous_price: Decimal | None = None
    is_available: bool = True


class CartSellerGroup(BaseModel):
    """Ítems agrupados por vendedor.

    El carrito se muestra agrupado porque el pedido se dividirá así: el
    comprador ve desde el principio que compra a varios productores (ADR-02).
    """

    producer_id: uuid.UUID
    producer_name: str
    items: list[CartItemResponse]
    subtotal: Decimal
    estimated_shipping: Decimal


class AppliedCoupon(BaseModel):
    code: str
    description: str | None
    discount_amount: Decimal


class CartResponse(BaseModel):
    id: uuid.UUID | None
    groups: list[CartSellerGroup]
    item_count: int
    subtotal: Decimal
    shipping_total: Decimal
    discount_total: Decimal
    grand_total: Decimal
    currency: str = "COP"
    coupon: AppliedCoupon | None = None
    has_warnings: bool = False


class CouponApply(BaseModel):
    code: str = Field(min_length=1, max_length=40)


class WishlistItemAdd(BaseModel):
    product_id: uuid.UUID


class WishlistItemResponse(BaseModel):
    product_id: uuid.UUID
    product_name: str
    product_slug: str
    image_url: str | None
    base_price: Decimal
    is_available: bool
