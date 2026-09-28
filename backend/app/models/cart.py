"""Carrito, lista de deseos y cupones."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import CouponScope, DiscountType

if TYPE_CHECKING:
    from app.models.catalog import Product, ProductVariant


class Cart(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Carrito persistente del usuario.

    El carrito anónimo previo al login vive en Redis (ADR-07) y se fusiona con
    este al autenticarse, sin duplicar ítems (HU-CC-05, CA3).
    """

    __tablename__ = "carts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan", lazy="selectin"
    )


class CartItem(Base, UUIDPrimaryKeyMixin):
    """Línea del carrito, en kilogramos de pergamino."""

    __tablename__ = "cart_items"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(nullable=False)

    # Precio vigente al agregar el ítem. Comparado contra el precio actual,
    # permite avisar al comprador si cambió antes del checkout (HU-CC-05, CA6).
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Precio acordado en una negociación, si la línea viene de una postura que el
    # comprador aceptó. Cuando está presente manda sobre el precio del catálogo:
    # lo acordado es lo acordado, y que el vendedor suba su lista después no
    # altera un trato cerrado.
    negotiated_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Postura de la que sale el precio negociado. Se guarda para poder rastrear
    # de dónde vino un precio distinto del de catálogo, que es justo lo que
    # alguien preguntaría al auditar un pedido.
    demand_offer_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("demand_offers.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    cart: Mapped["Cart"] = relationship(back_populates="items")
    variant: Mapped["ProductVariant"] = relationship(lazy="joined")

    __table_args__ = (
        # Una sola línea por variante: agregar de nuevo suma cantidad.
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_items_cart_variant"),
        CheckConstraint("quantity > 0", name="cart_quantity_positive"),
        CheckConstraint(
            "negotiated_price IS NULL OR negotiated_price > 0",
            name="negotiated_price_positive",
        ),
        # Un precio negociado sin la postura que lo respalda sería un precio
        # arbitrario sin rastro de dónde salió.
        CheckConstraint(
            "(negotiated_price IS NULL) = (demand_offer_id IS NULL)",
            name="negotiated_price_requires_offer",
        ),
    )

    @property
    def effective_price(self) -> Decimal:
        """Precio que se cobra por kilo.

        Lo acordado manda sobre la lista: si esta línea viene de una postura
        aceptada, el precio es el de la postura aunque el vendedor haya cambiado
        el de su catálogo después.
        """
        return self.negotiated_price if self.negotiated_price is not None else self.variant.price


class Wishlist(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Lista de deseos del comprador."""

    __tablename__ = "wishlists"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), default="Favoritos", nullable=False)

    items: Mapped[list["WishlistItem"]] = relationship(
        back_populates="wishlist", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (Index("ix_wishlists_user", "user_id"),)


class WishlistItem(Base):
    """Producto guardado en una lista de deseos."""

    __tablename__ = "wishlist_items"

    wishlist_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("wishlists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    wishlist: Mapped["Wishlist"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(lazy="joined")


class Coupon(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Cupón de descuento."""

    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[DiscountType] = mapped_column(
        pg_enum(DiscountType, "discount_type"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    usage_limit: Mapped[int | None] = mapped_column(nullable=True)
    usage_limit_per_user: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(default=0, nullable=False)

    scope: Mapped[CouponScope] = mapped_column(
        pg_enum(CouponScope, "coupon_scope"), default=CouponScope.GLOBAL, nullable=False
    )
    # Referencia a categoría o productor según el alcance. Es polimórfica por
    # diseño: una clave foránea condicional no aportaría integridad real.
    scope_ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    usages: Mapped[list["CouponUsage"]] = relationship(back_populates="coupon")

    __table_args__ = (
        CheckConstraint("value > 0", name="coupon_value_positive"),
        CheckConstraint("type <> 'percentage' OR value <= 100", name="coupon_percentage_max"),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR starts_at < ends_at",
            name="coupon_dates_valid",
        ),
        Index("ix_coupons_active", "is_active", "ends_at"),
    )


class CouponUsage(Base, UUIDPrimaryKeyMixin):
    """Uso efectivo de un cupón en un pedido."""

    __tablename__ = "coupon_usages"

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    discount_applied: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    coupon: Mapped["Coupon"] = relationship(back_populates="usages")

    __table_args__ = (
        UniqueConstraint("coupon_id", "order_id", name="uq_coupon_usages_coupon_order"),
        Index("ix_coupon_usages_user", "coupon_id", "user_id"),
    )
