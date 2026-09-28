"""Schemas del catálogo."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.models.enums import (
    CoffeeProcess,
    CoffeeState,
    ProductStatus,
)
from app.schemas.common import ORMModel


class CategoryResponse(ORMModel):
    id: int
    slug: str
    name: str
    description: str | None


class CertificationResponse(ORMModel):
    code: str
    name: str


class ProducerSummary(ORMModel):
    """Datos del productor que acompañan a cada producto."""

    id: uuid.UUID
    legal_name: str
    brand_name: str | None
    type: str
    logo_key: str | None
    rating_avg: Decimal


class CoffeeAttributesResponse(ORMModel):
    """Ficha técnica del lote de pergamino."""

    variety: str | None
    process: CoffeeProcess | None
    altitude_masl: int | None
    harvest_date: date | None

    # Análisis
    yield_factor: Decimal | None
    moisture_pct: Decimal | None
    healthy_bean_pct: Decimal | None
    pasilla_pct: Decimal | None
    borer_damage_pct: Decimal | None
    screen_sizes: list[int] | None

    # Trazabilidad
    lot_code: str | None
    sica_code: str | None
    drying_method: str | None
    notes: str | None


class ProductImageResponse(ORMModel):
    id: uuid.UUID
    image_key: str
    alt_text: str | None
    is_primary: bool


class VariantResponse(ORMModel):
    """Oferta comprable de un lote. `price` es el precio de un kilogramo y
    `available_qty` los kilos disponibles.

    `wholesale_price` solo se rellena para compradores empresariales
    verificados; para el resto viaja como `None` (HU-CE-02, CA2).
    """

    id: uuid.UUID
    sku: str
    presentation: str
    min_qty_kg: int
    price: Decimal
    wholesale_price: Decimal | None = None
    available_qty: int
    is_active: bool


class FarmSummary(ORMModel):
    """Origen del café.

    Expone solo la ubicación aproximada. Los campos `exact_lat`/`exact_lng`
    existen en la base de datos pero nunca se declaran aquí: exponer la
    coordenada real de una finca rural es un riesgo de seguridad física para el
    productor (ADR-08).
    """

    name: str
    village: str | None
    altitude_min_masl: int | None
    altitude_max_masl: int | None
    approx_lat: Decimal | None
    approx_lng: Decimal | None
    environmental_practices: str | None


class ProductListItem(BaseModel):
    """Producto tal como aparece en el listado."""

    id: uuid.UUID
    slug: str
    name: str
    state: CoffeeState
    base_price: Decimal
    currency: str
    primary_image_url: str | None
    producer: ProducerSummary
    region: str | None
    municipality: str | None
    department: str | None
    # El factor de rendimiento y la humedad son lo que un comprador de
    # pergamino contrasta con el precio; van en el listado para no obligar a
    # abrir cada ficha para comparar.
    yield_factor: Decimal | None
    moisture_pct: Decimal | None
    available_kg: int
    rating_avg: Decimal
    rating_count: int
    is_available: bool


class ProductDetail(ProductListItem):
    """Ficha completa con toda la trazabilidad (HU-VIS-04)."""

    description: str
    images: list[ProductImageResponse]
    variants: list[VariantResponse]
    attributes: CoffeeAttributesResponse | None
    certifications: list[CertificationResponse]
    farm: FarmSummary | None
    category: CategoryResponse | None
    dispatch_days: int
    storage_conditions: str | None
    allows_samples: bool
    created_at: datetime


class ProductFilters(BaseModel):
    """Filtros combinables del catálogo (HU-VIS-03, CA2)."""

    q: str | None = Field(default=None, max_length=120, description="Búsqueda por texto")
    department: str | None = None
    municipality: str | None = None
    region: str | None = None
    variety: str | None = None
    process: CoffeeProcess | None = None
    certification: str | None = None
    producer_id: uuid.UUID | None = None

    # Precios por kilogramo.
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)

    # Un factor más bajo es mejor café, así que el filtro útil es el máximo que
    # el comprador acepta, no el mínimo.
    max_yield_factor: Decimal | None = Field(default=None, ge=80, le=130)
    max_moisture_pct: Decimal | None = Field(default=None, ge=0, le=100)
    # Kilos mínimos disponibles: quien necesita media tonelada no quiere ver
    # lotes de 50 kg.
    min_available_kg: int | None = Field(default=None, ge=1)

    sort: str = Field(
        default="newest",
        pattern="^(price_asc|price_desc|rating|yield_factor|popular|newest)$",
    )


class ProducerListItem(ORMModel):
    """Productor en el listado público (HU-VIS-05)."""

    id: uuid.UUID
    legal_name: str
    brand_name: str | None
    type: str
    logo_key: str | None
    cover_key: str | None
    story: str | None
    municipality: str | None
    department: str | None
    rating_avg: Decimal
    rating_count: int
    product_count: int = 0


class ProducerDetail(ProducerListItem):
    """Perfil público completo del productor."""

    farms: list[FarmSummary]
    certifications: list[CertificationResponse]
    products: list[ProductListItem]


class ProductVariantInput(BaseModel):
    """Oferta enviada al crear o editar un lote.

    `price` es el precio de un kilogramo y `stock_qty` los kilos disponibles.
    """

    sku: str = Field(min_length=3, max_length=60)
    presentation: str = Field(min_length=3, max_length=80)
    min_qty_kg: int = Field(default=1, ge=1)
    price: Decimal = Field(ge=0)
    wholesale_price: Decimal | None = Field(default=None, ge=0)
    stock_qty: int = Field(ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)

    @model_validator(mode="after")
    def minimum_must_fit_the_stock(self) -> "ProductVariantInput":
        """Un mínimo mayor que las existencias hace la oferta incomprable.

        Se rechaza al publicar en lugar de dejar que el comprador descubra en el
        carrito que no puede llevar ni la cantidad mínima.
        """
        if self.stock_qty and self.min_qty_kg > self.stock_qty:
            raise ValueError(
                "El mínimo de compra no puede superar los kilos disponibles "
                f"({self.min_qty_kg} kg mínimo contra {self.stock_qty} kg en existencia)."
            )
        return self


class ProductCreate(BaseModel):
    """Alta de un producto por parte del productor (HU-PRO-03)."""

    name: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10)
    state: CoffeeState
    category_id: int | None = None
    farm_id: uuid.UUID | None = None
    base_price: Decimal = Field(ge=0)
    wholesale_price: Decimal | None = Field(default=None, ge=0)
    wholesale_min_qty: int | None = Field(default=None, ge=1)
    dispatch_days: int = Field(default=3, ge=1, le=60)
    storage_conditions: str | None = None
    allows_samples: bool = False

    variety: str | None = Field(default=None, max_length=100)
    process: CoffeeProcess | None = None
    altitude_masl: int | None = Field(default=None, ge=0, le=6000)
    harvest_date: date | None = None

    # Análisis del pergamino. Todo opcional: se publica lo que se tenga medido.
    yield_factor: Decimal | None = Field(default=None, ge=80, le=130)
    moisture_pct: Decimal | None = Field(default=None, ge=0, le=100)
    healthy_bean_pct: Decimal | None = Field(default=None, ge=0, le=100)
    pasilla_pct: Decimal | None = Field(default=None, ge=0, le=100)
    borer_damage_pct: Decimal | None = Field(default=None, ge=0, le=100)
    screen_sizes: list[int] | None = None

    lot_code: str | None = Field(default=None, max_length=60)
    sica_code: str | None = Field(default=None, max_length=40)
    drying_method: str | None = Field(default=None, max_length=80)
    notes: str | None = None

    @field_validator("screen_sizes")
    @classmethod
    def screens_must_be_real_sizes(cls, value: list[int] | None) -> list[int] | None:
        """Las mallas de café van de la 14 a la 20; fuera de ahí no existen."""
        if value is None:
            return None
        invalid = sorted({size for size in value if size < 14 or size > 20})
        if invalid:
            raise ValueError(
                "Las mallas válidas van de 14 a 20. No existen: "
                + ", ".join(str(size) for size in invalid)
                + "."
            )
        return sorted(set(value))

    certification_ids: list[int] = []
    variants: list[ProductVariantInput] = Field(min_length=1)


class ProductUpdate(BaseModel):
    """Edición parcial de un producto."""

    name: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, min_length=10)
    base_price: Decimal | None = Field(default=None, ge=0)
    wholesale_price: Decimal | None = Field(default=None, ge=0)
    wholesale_min_qty: int | None = Field(default=None, ge=1)
    dispatch_days: int | None = Field(default=None, ge=1, le=60)
    storage_conditions: str | None = None
    allows_samples: bool | None = None
    status: ProductStatus | None = None


class InventoryUpdate(BaseModel):
    stock_qty: int = Field(ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)


class ReviewCreate(BaseModel):
    order_item_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewResponse(ORMModel):
    id: uuid.UUID
    rating: int
    comment: str | None
    author_name: str
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_verified_purchase(self) -> bool:
        """Toda reseña procede de una compra: el modelo lo garantiza."""
        return True
