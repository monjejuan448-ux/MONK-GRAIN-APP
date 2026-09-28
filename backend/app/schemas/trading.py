"""Schemas de oferta y demanda."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import CoffeeProcess, DemandStatus, OfferStatus
from app.schemas.common import ORMModel

# Vigencia máxima de una solicitud. Más allá de un trimestre el precio ofrecido
# ya no dice nada: la cosecha cambió y el precio de referencia con ella.
MAX_VALIDITY_DAYS = 90


class DemandCreate(BaseModel):
    """Solicitud de compra que publica un comprador."""

    title: str = Field(min_length=5, max_length=180)
    description: str | None = Field(default=None, max_length=2000)

    wanted_kg: int = Field(ge=1, le=1_000_000)

    # Techos de calidad: menos es mejor, así que lo que se declara es el máximo
    # aceptable.
    max_yield_factor: Decimal | None = Field(default=None, ge=80, le=130)
    max_moisture_pct: Decimal | None = Field(default=None, ge=0, le=100)
    variety: str | None = Field(default=None, max_length=100)
    process: CoffeeProcess | None = None

    municipality_id: int | None = None
    offered_price_per_kg: Decimal | None = Field(default=None, gt=0)
    expires_on: date

    @field_validator("expires_on")
    @classmethod
    def validity_must_be_future_and_reasonable(cls, value: date) -> date:
        today = date.today()
        if value < today:
            raise ValueError("La fecha de vigencia no puede estar en el pasado.")
        if (value - today).days > MAX_VALIDITY_DAYS:
            raise ValueError(
                f"La vigencia máxima es de {MAX_VALIDITY_DAYS} días: más allá, el precio "
                "que ofreces ya no corresponde a la cosecha."
            )
        return value


class DemandUpdate(BaseModel):
    """Cambios que el comprador puede hacer sobre su solicitud abierta.

    Los kilos buscados y los techos de calidad quedan fuera: cambiarlos
    invalidaría las posturas que los vendedores ya enviaron respondiendo a otras
    condiciones. Para pedir otra cosa se cierra esta solicitud y se abre otra.
    """

    title: str | None = Field(default=None, min_length=5, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    offered_price_per_kg: Decimal | None = Field(default=None, gt=0)
    expires_on: date | None = None

    @field_validator("expires_on")
    @classmethod
    def validity_must_be_future(cls, value: date | None) -> date | None:
        if value is None:
            return None
        today = date.today()
        if value < today:
            raise ValueError("La fecha de vigencia no puede estar en el pasado.")
        if (value - today).days > MAX_VALIDITY_DAYS:
            raise ValueError(f"La vigencia máxima es de {MAX_VALIDITY_DAYS} días.")
        return value


class DemandSummary(BaseModel):
    """Solicitud en un listado."""

    id: uuid.UUID
    title: str
    buyer_name: str
    wanted_kg: int
    covered_kg: int
    remaining_kg: int
    max_yield_factor: Decimal | None
    max_moisture_pct: Decimal | None
    variety: str | None
    process: CoffeeProcess | None
    municipality: str | None
    department: str | None
    offered_price_per_kg: Decimal | None
    expires_on: date
    status: DemandStatus
    # Si admite posturas nuevas hoy. Se calcula en el servidor para que la
    # interfaz no tenga que replicar la regla del vencimiento.
    is_receiving: bool
    offer_count: int
    created_at: datetime


class OfferSummary(ORMModel):
    """Postura tal como la ve el comprador que la recibió."""

    id: uuid.UUID
    producer_id: uuid.UUID
    producer_name: str
    product_id: uuid.UUID
    product_name: str
    product_slug: str
    variant_id: uuid.UUID
    presentation: str
    offered_kg: int
    price_per_kg: Decimal
    line_total: Decimal
    message: str | None
    status: OfferStatus
    response_note: str | None

    # Análisis del lote respaldado, para poder comparar posturas sin abrir cada
    # ficha.
    yield_factor: Decimal | None
    moisture_pct: Decimal | None
    municipality: str | None
    available_kg: int
    created_at: datetime
    responded_at: datetime | None


class DemandDetail(DemandSummary):
    """Solicitud con sus posturas. Solo la ve su comprador."""

    description: str | None
    offers: list[OfferSummary]


class OfferCreate(BaseModel):
    """Postura que envía un vendedor.

    `variant_id` señala qué oferta de qué lote respalda la postura: de ahí salen
    el análisis que verá el comprador y los kilos que se descontarán si acepta.
    """

    variant_id: uuid.UUID
    offered_kg: int = Field(ge=1, le=1_000_000)
    price_per_kg: Decimal = Field(gt=0)
    message: str | None = Field(default=None, max_length=1000)


class OfferRespond(BaseModel):
    """Respuesta del comprador a una postura."""

    accept: bool
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def rejection_should_explain(self) -> "OfferRespond":
        """Rechazar sin decir por qué deja al caficultor sin saber qué ajustar.

        No se exige el motivo —obligar a escribir algo produce «no» a secas—,
        pero sí se impide mandar una nota vacía que simule una explicación.
        """
        if self.note is not None and not self.note.strip():
            self.note = None
        return self


class MyOfferSummary(ORMModel):
    """Postura tal como la ve el vendedor que la envió."""

    id: uuid.UUID
    demand_id: uuid.UUID
    demand_title: str
    buyer_name: str
    wanted_kg: int
    product_name: str
    presentation: str
    offered_kg: int
    price_per_kg: Decimal
    line_total: Decimal
    status: OfferStatus
    response_note: str | None
    demand_expires_on: date
    created_at: datetime
    responded_at: datetime | None
