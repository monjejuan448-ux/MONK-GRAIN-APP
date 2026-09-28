"""Carrito de compras, cupones y lista de deseos."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.cart import Cart, CartItem, Coupon, CouponUsage, Wishlist, WishlistItem
from app.models.catalog import Product, ProductVariant
from app.models.enums import CouponScope, DiscountType
from app.models.user import User
from app.modules.catalog.service import build_media_url
from app.schemas.cart import (
    AppliedCoupon,
    CartItemResponse,
    CartResponse,
    CartSellerGroup,
    WishlistItemResponse,
)

logger = get_logger(__name__)

# Tarifa plana de envío por vendedor mientras no haya integración logística
# real. Cada sub-orden paga su propio envío porque cada productor despacha por
# separado (ADR-02).
FLAT_SHIPPING_PER_SELLER = Decimal("12000")
FREE_SHIPPING_THRESHOLD = Decimal("150000")


class CartService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Acceso al carrito
    # ------------------------------------------------------------------
    def get_or_create_cart(self, user: User) -> Cart:
        cart = self.session.scalar(select(Cart).where(Cart.user_id == user.id))
        if cart is None:
            cart = Cart(user_id=user.id)
            self.session.add(cart)
            self.session.flush()
        return cart

    def _load_items(self, cart: Cart) -> list[CartItem]:
        return list(
            self.session.scalars(
                select(CartItem)
                .where(CartItem.cart_id == cart.id)
                .options(
                    joinedload(CartItem.variant)
                    .joinedload(ProductVariant.product)
                    .joinedload(Product.producer),
                    joinedload(CartItem.variant).joinedload(ProductVariant.inventory),
                    joinedload(CartItem.variant)
                    .joinedload(ProductVariant.product)
                    .joinedload(Product.images),
                )
                .order_by(CartItem.created_at)
            )
            .unique()
            .all()
        )

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    def add_item(self, user: User, variant_id: uuid.UUID, quantity: int) -> CartResponse:
        """Agrega una variante al carrito o suma a la línea existente."""
        cart = self.get_or_create_cart(user)
        variant = self._get_purchasable_variant(variant_id)

        existing = self.session.scalar(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id)
        )
        desired = (existing.quantity if existing else 0) + quantity
        available = variant.inventory.available_qty if variant.inventory else 0

        # No se permite superar el stock disponible (HU-CC-05, CA4).
        if desired > available:
            raise BusinessRuleError(
                f"Solo quedan {available} unidades disponibles de esta presentación.",
                details={"available_qty": available},
            )

        if existing:
            existing.quantity = desired
        else:
            self.session.add(
                CartItem(
                    cart_id=cart.id,
                    variant_id=variant_id,
                    quantity=quantity,
                    unit_price_snapshot=variant.price,
                )
            )

        self.session.commit()
        return self.get_cart(user)

    def update_item(self, user: User, item_id: uuid.UUID, quantity: int) -> CartResponse:
        cart = self.get_or_create_cart(user)
        item = self.session.scalar(
            select(CartItem)
            .where(CartItem.id == item_id, CartItem.cart_id == cart.id)
            .options(joinedload(CartItem.variant).joinedload(ProductVariant.inventory))
        )
        if item is None:
            raise NotFoundError("Este producto no está en tu carrito.")

        available = item.variant.inventory.available_qty if item.variant.inventory else 0
        if quantity > available:
            raise BusinessRuleError(
                f"Solo quedan {available} unidades disponibles de esta presentación.",
                details={"available_qty": available},
            )

        item.quantity = quantity
        self.session.commit()
        return self.get_cart(user)

    def remove_item(self, user: User, item_id: uuid.UUID) -> CartResponse:
        cart = self.get_or_create_cart(user)
        item = self.session.scalar(
            select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        )
        if item is None:
            raise NotFoundError("Este producto no está en tu carrito.")

        self.session.delete(item)
        self.session.commit()
        return self.get_cart(user)

    def clear(self, user: User) -> None:
        cart = self.get_or_create_cart(user)
        for item in self._load_items(cart):
            self.session.delete(item)
        self.session.commit()

    def merge_anonymous_cart(
        self, user: User, anonymous_items: list[tuple[uuid.UUID, int]]
    ) -> CartResponse:
        """Fusiona el carrito anónimo con el del usuario al iniciar sesión.

        Las cantidades se suman en lugar de duplicar la línea, y se recortan al
        stock disponible en vez de fallar: perder el carrito al autenticarse es
        peor experiencia que ajustar una cantidad (HU-CC-05, CA3).
        """
        cart = self.get_or_create_cart(user)

        for variant_id, quantity in anonymous_items:
            variant = self.session.scalar(
                select(ProductVariant)
                .where(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True))
                .options(joinedload(ProductVariant.inventory))
            )
            if variant is None or variant.inventory is None:
                continue

            existing = self.session.scalar(
                select(CartItem).where(
                    CartItem.cart_id == cart.id, CartItem.variant_id == variant_id
                )
            )
            total = (existing.quantity if existing else 0) + quantity
            capped = min(total, variant.inventory.available_qty)
            if capped <= 0:
                continue

            if existing:
                existing.quantity = capped
            else:
                self.session.add(
                    CartItem(
                        cart_id=cart.id,
                        variant_id=variant_id,
                        quantity=capped,
                        unit_price_snapshot=variant.price,
                    )
                )

        self.session.commit()
        return self.get_cart(user)

    # ------------------------------------------------------------------
    # Cálculo del carrito
    # ------------------------------------------------------------------
    def get_cart(self, user: User, coupon_code: str | None = None) -> CartResponse:
        cart = self.get_or_create_cart(user)
        items = self._load_items(cart)

        if not items:
            return CartResponse(
                id=cart.id,
                groups=[],
                item_count=0,
                subtotal=Decimal("0"),
                shipping_total=Decimal("0"),
                discount_total=Decimal("0"),
                grand_total=Decimal("0"),
            )

        grouped: dict[uuid.UUID, list[CartItemResponse]] = defaultdict(list)
        producer_names: dict[uuid.UUID, str] = {}
        has_warnings = False

        for item in items:
            variant = item.variant
            product = variant.product
            producer = product.producer

            available = variant.inventory.available_qty if variant.inventory else 0
            is_available = (
                product.is_purchasable and variant.is_active and available >= item.quantity
            )
            # El precio pudo cambiar desde que se agregó el ítem.
            price_changed = variant.price != item.unit_price_snapshot

            if not is_available or price_changed:
                has_warnings = True

            primary = next(
                (image for image in product.images if image.is_primary),
                product.images[0] if product.images else None,
            )

            grouped[producer.id].append(
                CartItemResponse(
                    id=item.id,
                    variant_id=variant.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_slug=product.slug,
                    producer_name=producer.brand_name or producer.legal_name,
                    image_url=build_media_url(primary.image_key) if primary else None,
                    weight_grams=variant.weight_grams,
                    grind=variant.grind,
                    quantity=item.quantity,
                    unit_price=variant.price,
                    line_total=variant.price * item.quantity,
                    available_qty=available,
                    price_changed=price_changed,
                    previous_price=item.unit_price_snapshot if price_changed else None,
                    is_available=is_available,
                )
            )
            producer_names[producer.id] = producer.brand_name or producer.legal_name

        groups: list[CartSellerGroup] = []
        subtotal = Decimal("0")
        shipping_total = Decimal("0")

        for producer_id, group_items in grouped.items():
            group_subtotal = sum((i.line_total for i in group_items), Decimal("0"))
            shipping = (
                Decimal("0")
                if group_subtotal >= FREE_SHIPPING_THRESHOLD
                else FLAT_SHIPPING_PER_SELLER
            )
            groups.append(
                CartSellerGroup(
                    producer_id=producer_id,
                    producer_name=producer_names[producer_id],
                    items=group_items,
                    subtotal=group_subtotal,
                    estimated_shipping=shipping,
                )
            )
            subtotal += group_subtotal
            shipping_total += shipping

        discount = Decimal("0")
        applied_coupon = None
        if coupon_code:
            coupon, discount = self.validate_coupon(user, coupon_code, subtotal)
            applied_coupon = AppliedCoupon(
                code=coupon.code, description=coupon.description, discount_amount=discount
            )
            if coupon.type == DiscountType.FREE_SHIPPING:
                shipping_total = Decimal("0")

        return CartResponse(
            id=cart.id,
            groups=groups,
            item_count=sum(i.quantity for group in groups for i in group.items),
            subtotal=subtotal,
            shipping_total=shipping_total,
            discount_total=discount,
            grand_total=subtotal + shipping_total - discount,
            coupon=applied_coupon,
            has_warnings=has_warnings,
        )

    # ------------------------------------------------------------------
    # Cupones
    # ------------------------------------------------------------------
    def validate_coupon(self, user: User, code: str, subtotal: Decimal) -> tuple[Coupon, Decimal]:
        """Valida un cupón y calcula su descuento.

        Cada motivo de rechazo tiene su propio mensaje: un "cupón inválido"
        genérico deja al comprador sin saber si expiró, si no alcanza el mínimo
        o si ya lo usó (HU-CC-06, CA2).
        """
        coupon = self.session.scalar(select(Coupon).where(Coupon.code == code.strip().upper()))
        if coupon is None or not coupon.is_active:
            raise BusinessRuleError("Este código promocional no existe.")

        now = datetime.now(UTC)
        if coupon.starts_at and coupon.starts_at > now:
            raise BusinessRuleError("Este cupón aún no está vigente.")
        if coupon.ends_at and coupon.ends_at < now:
            raise BusinessRuleError("Este cupón ya venció.")

        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            raise BusinessRuleError("Este cupón alcanzó su límite de usos.")

        user_uses = (
            self.session.scalar(
                select(func.count())
                .select_from(CouponUsage)
                .where(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == user.id)
            )
            or 0
        )
        if user_uses >= coupon.usage_limit_per_user:
            raise BusinessRuleError("Ya usaste este cupón el máximo de veces permitido.")

        if coupon.min_order_amount and subtotal < coupon.min_order_amount:
            raise BusinessRuleError(
                f"Este cupón aplica en compras desde ${coupon.min_order_amount:,.0f}."
            )

        if coupon.scope != CouponScope.GLOBAL:
            raise BusinessRuleError("Este cupón no aplica a los productos de tu carrito.")

        return coupon, self._calculate_discount(coupon, subtotal)

    def _calculate_discount(self, coupon: Coupon, subtotal: Decimal) -> Decimal:
        if coupon.type == DiscountType.FREE_SHIPPING:
            return Decimal("0")

        if coupon.type == DiscountType.PERCENTAGE:
            discount = (subtotal * coupon.value / Decimal("100")).quantize(Decimal("1"))
        else:
            discount = coupon.value

        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)

        # El descuento nunca puede superar el subtotal: un total negativo sería
        # dinero devuelto por una compra no realizada.
        return min(discount, subtotal)

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _get_purchasable_variant(self, variant_id: uuid.UUID) -> ProductVariant:
        variant = self.session.scalar(
            select(ProductVariant)
            .where(
                ProductVariant.id == variant_id,
                ProductVariant.is_active.is_(True),
                ProductVariant.deleted_at.is_(None),
            )
            .options(
                joinedload(ProductVariant.inventory),
                joinedload(ProductVariant.product),
            )
        )
        if variant is None:
            raise NotFoundError("Esta presentación ya no está disponible.")
        if not variant.product.is_purchasable:
            raise BusinessRuleError("Este café ya no está a la venta.")
        return variant

    # ------------------------------------------------------------------
    # Lista de deseos
    # ------------------------------------------------------------------
    def _get_or_create_wishlist(self, user: User) -> Wishlist:
        wishlist = self.session.scalar(select(Wishlist).where(Wishlist.user_id == user.id))
        if wishlist is None:
            wishlist = Wishlist(user_id=user.id, name="Favoritos")
            self.session.add(wishlist)
            self.session.flush()
        return wishlist

    def add_to_wishlist(self, user: User, product_id: uuid.UUID) -> None:
        wishlist = self._get_or_create_wishlist(user)
        product = self.session.get(Product, product_id)
        if product is None or product.deleted_at is not None:
            raise NotFoundError("No encontramos este café.")

        existing = self.session.get(WishlistItem, (wishlist.id, product_id))
        if existing is not None:
            raise ConflictError("Este café ya está en tus favoritos.")

        self.session.add(WishlistItem(wishlist_id=wishlist.id, product_id=product_id))
        self.session.commit()

    def remove_from_wishlist(self, user: User, product_id: uuid.UUID) -> None:
        wishlist = self._get_or_create_wishlist(user)
        item = self.session.get(WishlistItem, (wishlist.id, product_id))
        if item is not None:
            self.session.delete(item)
            self.session.commit()

    def list_wishlist(self, user: User) -> list[WishlistItemResponse]:
        wishlist = self._get_or_create_wishlist(user)
        items = (
            self.session.scalars(
                select(WishlistItem)
                .where(WishlistItem.wishlist_id == wishlist.id)
                .options(
                    joinedload(WishlistItem.product).joinedload(Product.images),
                    # El inventario entra en la misma carga: comprobar las
                    # existencias variante por variante sería una consulta por
                    # cada una.
                    joinedload(WishlistItem.product)
                    .joinedload(Product.variants)
                    .joinedload(ProductVariant.inventory),
                )
                .order_by(WishlistItem.created_at.desc())
            )
            .unique()
            .all()
        )

        result: list[WishlistItemResponse] = []
        for item in items:
            product = item.product
            primary = next(
                (image for image in product.images if image.is_primary),
                product.images[0] if product.images else None,
            )
            # Un favorito que dejó de estar disponible se marca, no desaparece
            # sin explicación (HU-CC-04, CA3).
            result.append(
                WishlistItemResponse(
                    product_id=product.id,
                    product_name=product.name,
                    product_slug=product.slug,
                    image_url=build_media_url(primary.image_key) if primary else None,
                    base_price=product.base_price,
                    # Disponible si alguna variante activa tiene existencias
                    # reales, con el mismo criterio que el catálogo. Antes se
                    # usaba `is_purchasable`, que solo mira si el café sigue
                    # publicado: un café agotado aparecía como disponible, que
                    # es exactamente lo que este campo existe para evitar.
                    is_available=product.is_purchasable
                    and any(
                        variant.is_active
                        and variant.deleted_at is None
                        and variant.inventory is not None
                        and variant.inventory.available_qty > 0
                        for variant in product.variants
                    ),
                )
            )
        return result
