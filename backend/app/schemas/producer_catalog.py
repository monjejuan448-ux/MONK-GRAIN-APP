"""Esquemas de la publicación de cafés por el vendedor.

El productor describe su café; el sistema decide todo lo demás. Aquí no viajan
`slug`, `status`, `producer_id` ni fechas de publicación: son campos que el
servidor calcula o controla, y aceptarlos permitiría publicar sin revisión o
colgar un café del catálogo de otro.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.models.enums import CoffeeProcess, CoffeeState, GrindType, ProductStatus, RoastLevel
from app.schemas.common import ORMModel


class CoffeeAttributesInput(BaseModel):
    """Datos de catación y origen del café."""

    variety: str | None = Field(default=None, max_length=100)
    process: CoffeeProcess | None = None
    roast: RoastLevel | None = None
    altitude_masl: int | None = Field(default=None, ge=0, le=3000)
    sensory_profile: str | None = Field(default=None, max_length=2000)
    tasting_notes: list[str] | None = Field(default=None, max_length=10)
    # La escala SCA llega a 100. El modelo académico usaba DECIMAL(3,2), que no
    # admite un 100.00; la columna es NUMERIC(5,2).
    cupping_score: Decimal | None = Field(default=None, ge=0, le=100)
    harvest_date: date | None = None
    roast_date: date | None = None
    moisture_pct: Decimal | None = Field(default=None, ge=0, le=100)

    @field_validator("tasting_notes")
    @classmethod
    def clean_notes(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        notes = [note.strip() for note in value if note.strip()]
        if any(len(note) > 50 for note in notes):
            raise ValueError("Cada nota de cata admite hasta 50 caracteres.")
        return notes or None


class ProductInput(BaseModel):
    """Datos con los que el vendedor crea o edita su café."""

    name: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=20, max_length=5000)
    state: CoffeeState
    base_price: Decimal = Field(gt=0, le=Decimal("99999999.99"))
    wholesale_price: Decimal | None = Field(default=None, gt=0, le=Decimal("99999999.99"))
    wholesale_min_qty: int | None = Field(default=None, ge=1)
    farm_id: uuid.UUID | None = None
    category_id: int | None = None
    dispatch_days: int = Field(default=3, ge=1, le=30)
    storage_conditions: str | None = Field(default=None, max_length=1000)
    allows_samples: bool = False
    attributes: CoffeeAttributesInput = Field(default_factory=CoffeeAttributesInput)

    @field_validator("wholesale_price")
    @classmethod
    def wholesale_below_retail(cls, value: Decimal | None, info: ValidationInfo) -> Decimal | None:
        base = info.data.get("base_price")
        if value is not None and base is not None and value >= base:
            raise ValueError("El precio mayorista debe ser menor que el precio al detal.")
        return value


class VariantInput(BaseModel):
    """Presentación concreta: peso, molienda y precio propios."""

    weight_grams: Decimal = Field(gt=0, le=Decimal("50000"))
    grind: GrindType | None = None
    price: Decimal = Field(gt=0, le=Decimal("99999999.99"))
    wholesale_price: Decimal | None = Field(default=None, gt=0)
    stock_qty: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    is_active: bool = True


class ProductImageResponse(ORMModel):
    id: uuid.UUID
    image_url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool


class VariantDetail(ORMModel):
    id: uuid.UUID
    sku: str
    label: str
    weight_grams: Decimal
    grind: GrindType | None
    price: Decimal
    wholesale_price: Decimal | None
    is_active: bool
    stock_qty: int
    reserved_qty: int


class ProducerProductDetail(ORMModel):
    """Vista completa del café tal como la ve su dueño.

    A diferencia de la ficha pública, incluye el estado de publicación y el
    inventario: son datos de gestión, no de escaparate.
    """

    id: uuid.UUID
    slug: str
    name: str
    description: str
    state: CoffeeState
    status: ProductStatus
    base_price: Decimal
    wholesale_price: Decimal | None
    wholesale_min_qty: int | None
    currency: str
    dispatch_days: int
    storage_conditions: str | None
    allows_samples: bool
    images: list[ProductImageResponse]
    variants: list[VariantDetail]
    attributes: CoffeeAttributesInput | None
    # Qué le falta para poder publicarse. Vacío significa que ya está listo.
    missing_to_publish: list[str]


class ProducerProfileUpdate(BaseModel):
    """Datos del negocio que el propio vendedor puede modificar.

    La razón social, el documento y el estado de aprobación quedan fuera a
    propósito: son lo que el equipo verificó al habilitar la cuenta.
    """

    brand_name: str | None = Field(default=None, max_length=150)
    story: str | None = Field(default=None, max_length=5000)
    # Exigidos por el artículo 53 de la Ley 1480 de 2011 para poder atender una
    # reclamación contra el oferente.
    notification_address: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=30)
    production_capacity_kg: Decimal | None = Field(default=None, ge=0)


class ProducerProfileResponse(ORMModel):
    id: uuid.UUID
    legal_name: str
    brand_name: str | None
    type: str
    status: str
    story: str | None
    notification_address: str | None
    contact_phone: str | None
    production_capacity_kg: Decimal | None
    # `False` mientras falte la dirección o el teléfono de notificaciones.
    has_notification_data: bool
