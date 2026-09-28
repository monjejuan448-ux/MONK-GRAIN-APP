"""Catálogo: categorías, productos, atributos de café, variantes, inventario y reseñas."""

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
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import (
    GRIND_LABELS,
    CoffeeProcess,
    CoffeeState,
    GrindType,
    ProductStatus,
    ReviewStatus,
    RoastLevel,
)

if TYPE_CHECKING:
    from app.models.producer import Farm, ProducerProfile


class Category(Base, SoftDeleteMixin):
    """Categoría del catálogo, con jerarquía opcional de un nivel."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # En una relación autorreferencial `remote_side` va solo en el lado "muchos
    # a uno": marca cuál columna es la del padre.
    parent: Mapped["Category | None"] = relationship(
        back_populates="children", remote_side="Category.id"
    )
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Café publicado por un productor.

    El precio real vive en las variantes: un mismo lote en 250 g y en 1 kg son
    precios distintos. `base_price` es solo la referencia de visualización
    ("desde $X") que se muestra en el listado.
    """

    __tablename__ = "products"

    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[CoffeeState] = mapped_column(pg_enum(CoffeeState, "coffee_state"), nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        pg_enum(ProductStatus, "product_status"),
        default=ProductStatus.DRAFT,
        nullable=False,
    )

    base_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    wholesale_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    wholesale_min_qty: Mapped[int | None] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    dispatch_days: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    storage_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    allows_samples: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Desnormalizaciones deliberadas: permiten ordenar el catálogo por
    # calificación y popularidad sin agregaciones costosas en cada consulta.
    rating_avg: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.00"), nullable=False
    )
    rating_count: Mapped[int] = mapped_column(default=0, nullable=False)
    sales_count: Mapped[int] = mapped_column(default=0, nullable=False)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    producer: Mapped["ProducerProfile"] = relationship()
    farm: Mapped["Farm | None"] = relationship()
    category: Mapped["Category | None"] = relationship(back_populates="products")
    attributes: Mapped["CoffeeAttributes"] = relationship(
        back_populates="product", uselist=False, cascade="all, delete-orphan"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(back_populates="product")

    __table_args__ = (
        Index("ix_products_catalog", "status", "published_at"),
        Index("ix_products_category_status", "category_id", "status"),
        Index("ix_products_producer_status", "producer_id", "status"),
        Index("ix_products_sales", "sales_count"),
        CheckConstraint("base_price >= 0", name="base_price_non_negative"),
        # No se acepta precio mayorista sin cantidad mínima: la combinación
        # sería inaplicable al calcular el carrito.
        CheckConstraint(
            "wholesale_price IS NULL OR wholesale_min_qty IS NOT NULL",
            name="wholesale_requires_min_qty",
        ),
        CheckConstraint("rating_avg >= 0 AND rating_avg <= 5", name="product_rating_range"),
    )

    @property
    def is_purchasable(self) -> bool:
        return self.status == ProductStatus.PUBLISHED and self.deleted_at is None


class CoffeeAttributes(Base, TimestampMixin):
    """Ficha técnica del café. Relación uno a uno con el producto."""

    __tablename__ = "coffee_attributes"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    variety: Mapped[str | None] = mapped_column(String(100), nullable=True)
    process: Mapped[CoffeeProcess | None] = mapped_column(
        pg_enum(CoffeeProcess, "coffee_process"), nullable=True
    )
    roast: Mapped[RoastLevel | None] = mapped_column(
        pg_enum(RoastLevel, "roast_level"), nullable=True
    )
    altitude_masl: Mapped[int | None] = mapped_column(nullable=True)
    sensory_profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    tasting_notes: Mapped[list[str] | None] = mapped_column(ARRAY(String(50)), nullable=True)

    # NUMERIC(5,2): el rango de catación llega a 100.00. Un NUMERIC(3,2) solo
    # admitiría hasta 9.99 y haría imposible registrar el puntaje real.
    cupping_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    roast_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    moisture_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="attributes")

    __table_args__ = (
        Index("ix_coffee_attributes_filters", "process", "roast", "altitude_masl"),
        Index("ix_coffee_attributes_score", "cupping_score"),
        CheckConstraint(
            "cupping_score IS NULL OR (cupping_score >= 0 AND cupping_score <= 100)",
            name="cupping_score_range",
        ),
        CheckConstraint(
            "moisture_pct IS NULL OR (moisture_pct >= 0 AND moisture_pct <= 100)",
            name="moisture_range",
        ),
    )


class ProductImage(Base, UUIDPrimaryKeyMixin):
    """Imagen del producto. Se exige al menos una al publicar (HU-PRO-03, CA2)."""

    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="images")

    __table_args__ = (Index("ix_product_images_product", "product_id", "sort_order"),)


class ProductVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Presentación concreta del producto: peso y molienda, con su propio precio."""

    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    weight_grams: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    grind: Mapped[GrindType | None] = mapped_column(pg_enum(GrindType, "grind_type"), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    wholesale_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="variants")
    inventory: Mapped["Inventory"] = relationship(
        back_populates="variant", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_product_variants_product", "product_id"),
        CheckConstraint("price >= 0", name="variant_price_non_negative"),
        CheckConstraint("weight_grams > 0", name="variant_weight_positive"),
    )

    @property
    def label(self) -> str:
        """Etiqueta legible que se congela en el pedido (`variant_label_snapshot`).

        Se usa el nombre en español de la molienda y no el valor del enum: ese
        valor es un identificador técnico, y el texto que se genere aquí queda
        guardado tal cual en el histórico del pedido.
        """
        weight = f"{self.weight_grams:.0f} g"
        return f"{weight} · {GRIND_LABELS[self.grind]}" if self.grind else weight


class Inventory(Base):
    """Existencias de una variante.

    `reserved_qty` retiene el stock de pedidos en curso: se convierte en
    descuento efectivo al confirmarse el pago y se libera si el pago se rechaza.
    """

    __tablename__ = "inventories"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stock_qty: Mapped[int] = mapped_column(default=0, nullable=False)
    reserved_qty: Mapped[int] = mapped_column(default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(default=5, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    variant: Mapped["ProductVariant"] = relationship(back_populates="inventory")

    __table_args__ = (
        CheckConstraint(
            "stock_qty >= 0 AND reserved_qty >= 0 AND reserved_qty <= stock_qty",
            name="inventory_quantities_valid",
        ),
    )

    @property
    def available_qty(self) -> int:
        """Unidades realmente vendibles."""
        return self.stock_qty - self.reserved_qty

    @property
    def is_low_stock(self) -> bool:
        return self.available_qty <= self.low_stock_threshold


class ProductCertification(Base):
    """Certificación asociada a un producto concreto."""

    __tablename__ = "product_certifications"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    certification_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("certifications.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Review(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Reseña de un producto.

    `order_item_id` es único: la base de datos garantiza una sola reseña por
    ítem comprado, de modo que solo reseña quien compró y solo una vez
    (HU-CC-10, CA2 y CA3). No depende de una validación en código.
    """

    __tablename__ = "reviews"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        pg_enum(ReviewStatus, "review_status"),
        default=ReviewStatus.PUBLISHED,
        nullable=False,
    )
    moderation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderated_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    product: Mapped["Product"] = relationship(back_populates="reviews")
    reports: Mapped[list["ReviewReport"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_reviews_product", "product_id", "status", "created_at"),
        Index("ix_reviews_user", "user_id"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
    )


class ReviewReport(Base, UUIDPrimaryKeyMixin):
    """Denuncia de una reseña por parte de un lector.

    El motivo del reporte se guarda aparte de `moderation_reason`, que es la
    razón que da el administrador al decidir. Son cosas distintas: la cola de
    moderación necesita mostrar por qué alguien denunció la reseña
    (HU-ADM-06, CA1), y esa denuncia sobrevive a la decisión que se tome.

    La clave única impide que una misma persona reporte dos veces la misma
    reseña, lo que permitiría inflar el recuento y colar en la cola una reseña
    legítima que simplemente no gustó.
    """

    __tablename__ = "review_reports"

    review_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    reported_by: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review: Mapped["Review"] = relationship(back_populates="reports")

    __table_args__ = (
        UniqueConstraint("review_id", "reported_by", name="uq_review_reports_reviewer"),
        Index("ix_review_reports_review", "review_id", "created_at"),
    )
