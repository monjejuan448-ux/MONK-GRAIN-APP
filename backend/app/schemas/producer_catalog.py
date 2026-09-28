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

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from app.models.enums import CoffeeProcess, CoffeeState, ProductStatus
from app.schemas.common import ORMModel


class CoffeeAttributesInput(BaseModel):
    """Origen, análisis y trazabilidad del lote de pergamino.

    Todo es opcional: un caficultor publica lo que tenga medido. Exigir el
    análisis físico completo dejaría fuera a quien no lo ha mandado a un
    laboratorio, que es la mayoría.
    """

    variety: str | None = Field(default=None, max_length=100)
    process: CoffeeProcess | None = None
    altitude_masl: int | None = Field(default=None, ge=0, le=3000)
    harvest_date: date | None = None

    # Factor de rendimiento: kilos de pergamino que hay que trillar para obtener
    # un saco de 70 kg de excelso. Más bajo es mejor; el estándar es 94.
    yield_factor: Decimal | None = Field(default=None, ge=80, le=130)
    moisture_pct: Decimal | None = Field(default=None, ge=0, le=100)
    healthy_bean_pct: Decimal | None = Field(default=None, ge=0, le=100)
    pasilla_pct: Decimal | None = Field(default=None, ge=0, le=100)
    borer_damage_pct: Decimal | None = Field(default=None, ge=0, le=100)
    screen_sizes: list[int] | None = Field(default=None, max_length=7)

    lot_code: str | None = Field(default=None, max_length=60)
    sica_code: str | None = Field(default=None, max_length=40)
    drying_method: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("screen_sizes")
    @classmethod
    def clean_screens(cls, value: list[int] | None) -> list[int] | None:
        """Las mallas del café van de la 14 a la 20."""
        if value is None:
            return None
        invalid = sorted({size for size in value if size < 14 or size > 20})
        if invalid:
            raise ValueError(
                "Las mallas válidas van de 14 a 20. No existen: "
                + ", ".join(str(size) for size in invalid)
                + "."
            )
        return sorted(set(value)) or None


class ProductInput(BaseModel):
    """Datos con los que el vendedor crea o edita su lote de pergamino.

    `base_price` y `wholesale_price` son precios **por kilogramo**.
    """

    name: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=20, max_length=5000)
    # Se conserva en la entrada aunque hoy solo admita `pergamino`: el día que
    # se habilite un segundo estado, el vendedor ya lo estará declarando.
    state: CoffeeState = CoffeeState.PERGAMINO
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
            raise ValueError(
                "El precio por volumen debe ser menor que el precio por kilo corriente."
            )
        return value


class VariantInput(BaseModel):
    """Oferta concreta del lote: cómo se entrega, mínimo y precio por kilo.

    `price` es el precio de un kilogramo y `stock_qty` los kilos disponibles.
    """

    presentation: str = Field(min_length=3, max_length=80)
    min_qty_kg: int = Field(default=1, ge=1, le=100_000)
    price: Decimal = Field(gt=0, le=Decimal("99999999.99"))
    wholesale_price: Decimal | None = Field(default=None, gt=0)
    stock_qty: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    is_active: bool = True

    @model_validator(mode="after")
    def minimum_must_fit_the_stock(self) -> VariantInput:
        """El mínimo no puede superar las existencias: la oferta sería
        incomprable y el comprador solo lo descubriría en el carrito.

        Se valida sobre el modelo ya construido y no campo por campo: un
        `field_validator` sobre `min_qty_kg` no llega a ver `stock_qty`, porque
        Pydantic valida en el orden en que están declarados los campos y el
        inventario va después. La comprobación no se ejecutaba nunca.
        """
        if self.stock_qty > 0 and self.min_qty_kg > self.stock_qty:
            raise ValueError(
                f"El mínimo de compra ({self.min_qty_kg} kg) no puede superar los "
                f"kilos disponibles ({self.stock_qty} kg)."
            )
        return self


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
    presentation: str
    min_qty_kg: int
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
