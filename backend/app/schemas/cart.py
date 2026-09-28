"""Schemas del carrito y los cupones."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

# Tope de kilos por línea. El pergamino se comercia en cientos o miles de kilos,
# de modo que el límite anterior de 999 —pensado para bolsas— habría impedido
# comprar una tonelada. Cien toneladas es holgado y sigue acotando una cantidad
# absurda escrita por error.
MAX_KG_PER_LINE = 100_000


class CartItemAdd(BaseModel):
    variant_id: uuid.UUID
    # Cantidad en kilogramos.
    quantity: int = Field(ge=1, le=MAX_KG_PER_LINE)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=MAX_KG_PER_LINE)


class CartItemResponse(BaseModel):
    """Línea del carrito con el estado actual del producto."""

    id: uuid.UUID
    variant_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_slug: str
    producer_name: str
    image_url: str | None
    presentation: str
    # Mínimo de compra del lote, en kilos. Va en la respuesta para que el
    # carrito pueda impedir bajar de ahí sin tener que preguntar al catálogo.
    min_qty_kg: int
    # Cantidad y existencias, en kilogramos.
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
