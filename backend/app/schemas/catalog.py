"""Schemas del catálogo."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field

from app.models.enums import (
    CoffeeProcess,
    CoffeeState,
    GrindType,
    ProductStatus,
    RoastLevel,
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
    variety: str | None
    process: CoffeeProcess | None
    roast: RoastLevel | None
    altitude_masl: int | None
    sensory_profile: str | None
    tasting_notes: list[str] | None
    cupping_score: Decimal | None
    harvest_date: date | None
    roast_date: date | None


class ProductImageResponse(ORMModel):
    id: uuid.UUID
    image_key: str
    alt_text: str | None
    is_primary: bool


class VariantResponse(ORMModel):
    """Presentación comprable.

    `wholesale_price` solo se rellena para compradores empresariales
    verificados; para el resto viaja como `None` (HU-CE-02, CA2).
    """

    id: uuid.UUID
    sku: str
    weight_grams: Decimal
    grind: GrindType | None
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
    sensory_profile: str | None
    cupping_score: Decimal | None
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
    roast: RoastLevel | None = None
    state: CoffeeState | None = None
    certification: str | None = None
    producer_id: uuid.UUID | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    min_score: Decimal | None = Field(default=None, ge=0, le=100)
    sort: str = Field(
        default="newest", pattern="^(price_asc|price_desc|rating|score|popular|newest)$"
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
    """Variante enviada al crear o editar un producto."""

    sku: str = Field(min_length=3, max_length=60)
    weight_grams: Decimal = Field(gt=0)
    grind: GrindType | None = None
    price: Decimal = Field(ge=0)
    wholesale_price: Decimal | None = Field(default=None, ge=0)
    stock_qty: int = Field(ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)


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
    roast: RoastLevel | None = None
    altitude_masl: int | None = Field(default=None, ge=0, le=6000)
    sensory_profile: str | None = None
    tasting_notes: list[str] | None = None
    cupping_score: Decimal | None = Field(default=None, ge=0, le=100)
    harvest_date: date | None = None
    roast_date: date | None = None

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
