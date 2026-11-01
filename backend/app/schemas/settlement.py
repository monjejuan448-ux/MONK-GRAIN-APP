"""Cuenta bancaria del vendedor y liquidaciones.

El flujo decidido el 1 de noviembre de 2026 es **recaudo centralizado**: el
comprador paga a MONK GRAIN, que descuenta su comisión y liquida al vendedor por
periodos. Es lo que la arquitectura ya hacía —los pagos se registran contra el
pedido—, y ahora el dinero tiene salida.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import SettlementStatus
from app.schemas.common import ORMModel


# ----------------------------------------------------------------------
# Cuenta bancaria
# ----------------------------------------------------------------------
class BankAccountInput(BaseModel):
    """Dónde cobrar. Se guarda cifrada y no se devuelve nunca completa."""

    bank_name: str = Field(min_length=2, max_length=80)
    account_type: str = Field(pattern="^(ahorros|corriente)$")
    account_number: str = Field(min_length=6, max_length=34)
    holder_name: str = Field(min_length=3, max_length=150)
    holder_document: str = Field(min_length=5, max_length=30)

    @field_validator("account_number")
    @classmethod
    def only_digits(cls, value: str) -> str:
        """Los números de cuenta colombianos son dígitos.

        Se admiten guiones y espacios al escribirlos —así vienen en el extracto
        del banco— y se guardan limpios, para que dos formas de teclear la misma
        cuenta no parezcan cuentas distintas.
        """
        limpio = value.replace("-", "").replace(" ", "")
        if not limpio.isdigit():
            raise ValueError("El número de cuenta solo puede tener dígitos.")
        return limpio

    @field_validator("holder_document")
    @classmethod
    def clean_document(cls, value: str) -> str:
        return value.replace(".", "").replace("-", "").replace(" ", "").strip()


class BankAccountView(BaseModel):
    """Lo que se devuelve de una cuenta guardada: nunca el número completo.

    Basta para que el vendedor reconozca cuál registró y note si se equivocó de
    cuenta, sin que el número viaje de vuelta en cada carga de la página.
    """

    bank_name: str
    account_type: str
    holder_name: str
    masked_number: str
    updated_at: datetime | None = None


# ----------------------------------------------------------------------
# Liquidaciones
# ----------------------------------------------------------------------
class SettlementItem(ORMModel):
    """Una liquidación tal como la ven el vendedor y el administrador."""

    id: uuid.UUID
    period_start: date
    period_end: date
    gross_amount: Decimal
    commission_total: Decimal
    net_amount: Decimal
    status: SettlementStatus
    paid_at: datetime | None
    payment_reference: str | None
    created_at: datetime


class ProducerSettlementItem(SettlementItem):
    """La del vendedor añade de cuántos pedidos sale."""

    sub_orders_count: int


class AdminSettlementItem(SettlementItem):
    """La del administrador añade de quién es, para poder pagarla.

    **No lleva la cuenta bancaria.** Es una decisión que venía de antes
    (HU-ADM-02, CA5) y se mantiene: el dato bancario no se serializa en ninguna
    respuesta, ni siquiera para el administrador. Quien dispersa los fondos lo
    consulta por el canal que corresponda, no a través de un listado de la API.
    """

    producer_id: uuid.UUID
    producer_name: str
    sub_orders_count: int
    has_bank_account: bool


class ClosePeriodInput(BaseModel):
    """Periodo que se cierra, con sus dos extremos incluidos."""

    period_start: date
    period_end: date

    @field_validator("period_end")
    @classmethod
    def end_after_start(cls, value: date, info) -> date:  # type: ignore[no-untyped-def]
        inicio = info.data.get("period_start")
        if inicio is not None and value < inicio:
            raise ValueError("La fecha final del periodo no puede ser anterior a la inicial.")
        return value


class ClosePeriodResult(BaseModel):
    """Qué produjo el cierre, para poder decirlo sin que el usuario adivine."""

    settlements_created: int
    producers_settled: int
    sub_orders_settled: int
    net_total: Decimal
    skipped_without_bank_account: int


class MarkPaidInput(BaseModel):
    """Constancia del desembolso."""

    payment_reference: str = Field(min_length=3, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
