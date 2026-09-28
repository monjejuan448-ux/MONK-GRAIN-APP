"""Esquemas de las reseñas.

El autor solo aporta la calificación y el texto. Quién la firma, sobre qué
producto recae y si procede de una compra verificada lo deduce el servidor del
ítem de pedido: aceptarlos del cliente permitiría reseñar un café que nunca se
compró, que es justo lo que la reseña pretende acreditar.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ReviewStatus
from app.schemas.common import ORMModel


class ReviewInput(BaseModel):
    """Calificación y comentario sobre un café comprado (HU-CC-10)."""

    order_item_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def clean_comment(cls, value: str | None) -> str | None:
        cleaned = (value or "").strip()
        return cleaned or None


class ReviewUpdate(BaseModel):
    """Corrección de una reseña propia dentro del plazo de edición."""

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def clean_comment(cls, value: str | None) -> str | None:
        cleaned = (value or "").strip()
        return cleaned or None


class ReviewReportInput(BaseModel):
    """Denuncia de una reseña ajena."""

    reason: str = Field(min_length=10, max_length=500)


class ReviewDetail(BaseModel):
    """Reseña tal como se muestra en la ficha del café."""

    id: uuid.UUID
    product_id: uuid.UUID
    rating: int
    comment: str | None
    # Nombre abreviado: la ficha es pública y no tiene por qué revelar el
    # apellido completo de quien compró.
    author_name: str
    created_at: datetime
    updated_at: datetime
    # Toda reseña procede de una compra: el modelo lo garantiza con la clave
    # única sobre `order_item_id`.
    is_verified_purchase: bool = True
    # Verdadero solo para el autor, y solo mientras el plazo siga abierto.
    can_edit: bool = False
    is_mine: bool = False


class ReviewSummary(BaseModel):
    """Promedio y reparto de estrellas de un café."""

    rating_avg: float
    rating_count: int
    # Cuántas reseñas hay de cada calificación, de 1 a 5.
    distribution: dict[int, int]


class PendingReview(BaseModel):
    """Café entregado que el comprador todavía no ha reseñado (RF-06.4)."""

    order_item_id: uuid.UUID
    product_id: uuid.UUID
    product_slug: str
    product_name: str
    variant_label: str
    order_number: str
    delivered_at: datetime | None


class ReportedReview(ORMModel):
    """Reseña en la cola de moderación (HU-ADM-06, CA1)."""

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    rating: int
    comment: str | None
    author_name: str
    status: ReviewStatus
    created_at: datetime
    report_count: int
    # Motivos que adujeron quienes la denunciaron, del más reciente al primero.
    report_reasons: list[str]
