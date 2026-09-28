"""Endpoints de reseñas y calificaciones."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.pagination import Page, PageParams
from app.core.permissions import AdminUser, CurrentUser, OptionalUser
from app.db.session import get_session
from app.modules.reviews.service import ReviewService
from app.schemas.common import MessageResponse
from app.schemas.review import (
    PendingReview,
    ReportedReview,
    ReviewDetail,
    ReviewInput,
    ReviewReportInput,
    ReviewSummary,
    ReviewUpdate,
)

router = APIRouter(tags=["reseñas"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "/products/{product_id}/reviews",
    response_model=Page[ReviewDetail],
    summary="Reseñas de un café",
)
def list_product_reviews(
    product_id: uuid.UUID,
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
    viewer: OptionalUser = None,
) -> Page[ReviewDetail]:
    """Público. Si quien consulta tiene sesión, sus propias reseñas vienen marcadas."""
    return ReviewService(session).list_for_product(product_id, params, viewer)


@router.get(
    "/products/{product_id}/reviews/summary",
    response_model=ReviewSummary,
    summary="Promedio y reparto de estrellas",
)
def review_summary(product_id: uuid.UUID, session: SessionDep) -> ReviewSummary:
    return ReviewService(session).summary_for_product(product_id)


@router.post(
    "/reviews",
    response_model=ReviewDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Reseñar un café comprado",
)
def create_review(payload: ReviewInput, user: CurrentUser, session: SessionDep) -> ReviewDetail:
    """Solo se reseña lo que se compró y ya se recibió (HU-CC-10, CA1 y CA2)."""
    return ReviewService(session).create(user, payload)


@router.get(
    "/reviews/pending",
    response_model=list[PendingReview],
    summary="Cafés entregados sin reseñar",
)
def pending_reviews(user: CurrentUser, session: SessionDep) -> list[PendingReview]:
    """Lo que el panel del comprador ofrece reseñar (RF-06.4)."""
    return ReviewService(session).pending_for_user(user)


@router.put("/reviews/{review_id}", response_model=ReviewDetail, summary="Editar mi reseña")
def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> ReviewDetail:
    """Admisible dentro del plazo de edición (HU-CC-10, CA3)."""
    return ReviewService(session).update(user, review_id, payload)


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar mi reseña",
)
def delete_review(review_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    ReviewService(session).delete(user, review_id)


@router.post(
    "/reviews/{review_id}/report",
    response_model=MessageResponse,
    summary="Reportar una reseña",
)
def report_review(
    review_id: uuid.UUID,
    payload: ReviewReportInput,
    user: CurrentUser,
    session: SessionDep,
) -> MessageResponse:
    """La envía a la cola de moderación sin ocultarla.

    Ocultarla con la sola denuncia convertiría el botón en un interruptor para
    silenciar cualquier opinión incómoda.
    """
    ReviewService(session).report(user, review_id, payload.reason)
    return MessageResponse(message="Gracias. Nuestro equipo revisará esta reseña.")


@router.get(
    "/admin/reviews/reported",
    response_model=Page[ReportedReview],
    summary="Cola de moderación de reseñas",
)
def list_reported_reviews(
    admin: AdminUser, session: SessionDep, params: Annotated[PageParams, Depends()]
) -> Page[ReportedReview]:
    """Reseñas denunciadas, con el motivo de cada denuncia (HU-ADM-06, CA1)."""
    return ReviewService(session).list_reported(params)
