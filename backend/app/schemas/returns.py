"""Esquemas de las solicitudes de devolución.

El comprador solo aporta el motivo, qué devuelve y por qué. El número de
radicación, los plazos, el importe del reembolso y quién paga el transporte los
determina el servidor: son consecuencias legales del motivo invocado, no algo
que ninguna de las dos partes pueda proponer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ReturnReason, ReturnStatus
from app.schemas.common import ORMModel


class ReturnItemInput(BaseModel):
    """Línea del pedido que se devuelve, con la cantidad."""

    order_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=1000)


class ReturnRequestInput(BaseModel):
    """Solicitud del comprador (HU-CC-15)."""

    sub_order_id: uuid.UUID
    reason: ReturnReason
    description: str | None = Field(default=None, max_length=2000)
    items: list[ReturnItemInput] = Field(min_length=1, max_length=50)
    # Declaración de que el empaque sigue sellado, exigible solo en el retracto.
    declared_unopened: bool = False

    @model_validator(mode="after")
    def check_reason_requirements(self) -> ReturnRequestInput:
        if self.reason is ReturnReason.WITHDRAWAL and not self.declared_unopened:
            raise ValueError(
                "Para retractarte, el café debe volver sellado y sin abrir. "
                "Si el problema es con el producto, elige el motivo que corresponda: "
                "la garantía procede aunque lo hayas abierto."
            )
        if self.reason is not ReturnReason.WITHDRAWAL and not (self.description or "").strip():
            raise ValueError("Cuéntanos qué pasó con el café para poder atender tu reclamación.")

        seen: set[uuid.UUID] = set()
        for item in self.items:
            if item.order_item_id in seen:
                raise ValueError("Hay un producto repetido en la solicitud.")
            seen.add(item.order_item_id)
        return self


class ReturnResolutionInput(BaseModel):
    """Respuesta escrita de quien vende (Decreto 735 de 2013).

    El motivo es obligatorio también cuando se aprueba: la constancia debe
    decir qué se decidió y por qué, y es el documento que el comprador lleva a
    la Superintendencia si después hay desacuerdo.
    """

    approve: bool
    resolution_notes: str = Field(min_length=10, max_length=2000)


class ReturnItemResponse(ORMModel):
    id: uuid.UUID
    order_item_id: uuid.UUID
    product_name: str
    variant_label: str
    quantity: int
    line_refund: Decimal


class ReturnEvidenceResponse(BaseModel):
    id: uuid.UUID
    content_type: str
    # Enlace firmado de vida corta; nunca la clave del archivo.
    url: str
    created_at: datetime


class ReturnDetail(BaseModel):
    """Constancia de la reclamación, tal como la ve quien tiene derecho a verla."""

    id: uuid.UUID
    return_number: str
    sub_order_id: uuid.UUID
    sub_order_number: str
    order_number: str
    producer_name: str
    reason: ReturnReason
    reason_label: str
    description: str | None
    status: ReturnStatus
    declared_unopened: bool
    refund_amount: Decimal | None
    return_shipping_paid_by_seller: bool
    response_due_at: date
    refund_due_at: date
    resolution_notes: str | None
    reviewed_at: datetime | None
    refunded_at: datetime | None
    items: list[ReturnItemResponse]
    evidences: list[ReturnEvidenceResponse]
    # Fecha y hora de radicación de la constancia.
    filed_at: datetime
    # Qué puede hacer ahora quien está consultando.
    available_actions: list[ReturnStatus] = Field(default_factory=list)


class ReturnSummary(BaseModel):
    """Devolución en un listado."""

    id: uuid.UUID
    return_number: str
    order_number: str
    sub_order_number: str
    producer_name: str
    reason: ReturnReason
    reason_label: str
    status: ReturnStatus
    refund_amount: Decimal | None
    item_count: int
    response_due_at: date
    filed_at: datetime


class ReturnableItem(BaseModel):
    """Unidad todavía devolvible de una sub-orden."""

    order_item_id: uuid.UUID
    product_name: str
    variant_label: str
    purchased_qty: int
    returnable_qty: int
    unit_price: Decimal


class ReturnEligibility(BaseModel):
    """Si esta sub-orden admite hoy una devolución, y bajo qué figura.

    Se consulta antes de mostrar el formulario: es lo que decide si el botón
    «Solicitar devolución» aparece y qué motivos ofrece.
    """

    sub_order_id: uuid.UUID
    sub_order_number: str
    can_request: bool
    # Motivos admisibles hoy, con su plazo. El retracto caduca a los cinco días
    # hábiles de la entrega; la garantía sigue viva mucho después.
    allowed_reasons: list[ReturnReason]
    withdrawal_deadline: date | None
    warranty_deadline: date | None
    delivered_at: datetime | None
    items: list[ReturnableItem]
    # Motivo por el que no se puede, cuando `can_request` es falso.
    blocked_reason: str | None = None
