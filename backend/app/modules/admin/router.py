"""Endpoints del panel administrativo."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.pagination import Page, PageParams
from app.core.permissions import AdminUser
from app.core.rate_limit import client_ip
from app.db.session import get_session
from app.models.enums import RoleCode, UserStatus
from app.modules.admin.service import AdminService
from app.schemas.common import MessageResponse
from app.schemas.dashboard import (
    AdminDashboard,
    AdminUserItem,
    AuditLogEntry,
    PendingProducerItem,
    ProducerReviewDecision,
)

router = APIRouter(prefix="/admin", tags=["administración"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/dashboard", response_model=AdminDashboard, summary="Panel general")
def get_dashboard(
    admin: AdminUser,
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=365, description="Días del periodo")] = 30,
) -> AdminDashboard:
    """Métricas de usuarios, catálogo, pedidos y comisiones (HU-ADM-08)."""
    return AdminService(session).get_dashboard(days)


@router.get(
    "/producers/pending",
    response_model=Page[PendingProducerItem],
    summary="Vendedores pendientes de aprobación",
)
def list_pending_producers(
    admin: AdminUser, session: SessionDep, params: Annotated[PageParams, Depends()]
) -> Page[PendingProducerItem]:
    return AdminService(session).list_pending_producers(params)


@router.post(
    "/producers/{producer_id}/review",
    response_model=PendingProducerItem,
    summary="Aprobar o rechazar un vendedor",
)
def review_producer(
    producer_id: uuid.UUID,
    payload: ProducerReviewDecision,
    admin: AdminUser,
    session: SessionDep,
    request: Request,
) -> PendingProducerItem:
    """Resuelve una solicitud de vendedor.

    La decisión queda registrada en auditoría con su autor y su motivo
    (HU-ADM-01, CA4).
    """
    return AdminService(session).review_producer(
        admin,
        producer_id,
        approve=payload.approve,
        reason=payload.reason,
        ip_address=client_ip(request),
    )


@router.get(
    "/users",
    response_model=Page[AdminUserItem],
    summary="Cuentas de la plataforma",
)
def list_users(
    admin: AdminUser,
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
    q: Annotated[
        str | None, Query(max_length=120, description="Buscar por correo o nombre")
    ] = None,
    status_filter: Annotated[
        UserStatus | None, Query(alias="status", description="Filtrar por estado de la cuenta")
    ] = None,
    role: Annotated[RoleCode | None, Query(description="Filtrar por rol")] = None,
) -> Page[AdminUserItem]:
    """Listado de cuentas para poder encontrar la que se va a suspender.

    Es lo que faltaba para que `/users/{id}/suspend` fuera alcanzable: sin
    listado, había que conocer el identificador de la cuenta de memoria.
    """
    return AdminService(session).list_users(params, q=q, status=status_filter, role=role)


class SuspendRequest(BaseModel):
    suspend: bool
    reason: str | None = Field(default=None, max_length=500)


@router.post(
    "/users/{user_id}/suspend",
    response_model=MessageResponse,
    summary="Suspender o reactivar una cuenta",
)
def suspend_user(
    user_id: uuid.UUID,
    payload: SuspendRequest,
    admin: AdminUser,
    session: SessionDep,
    request: Request,
) -> MessageResponse:
    AdminService(session).suspend_user(
        admin, user_id, payload.suspend, ip_address=client_ip(request)
    )
    return MessageResponse(
        message="Cuenta suspendida." if payload.suspend else "Cuenta reactivada."
    )


class ModerateReviewRequest(BaseModel):
    hide: bool
    reason: str | None = Field(default=None, max_length=500)


@router.post(
    "/reviews/{review_id}/moderate",
    response_model=MessageResponse,
    summary="Moderar una reseña",
)
def moderate_review(
    review_id: uuid.UUID,
    payload: ModerateReviewRequest,
    admin: AdminUser,
    session: SessionDep,
    request: Request,
) -> MessageResponse:
    """Oculta o restablece una reseña y recalcula el promedio del producto."""
    AdminService(session).moderate_review(
        admin, review_id, payload.hide, payload.reason, client_ip(request)
    )
    return MessageResponse(message="Reseña ocultada." if payload.hide else "Reseña restablecida.")


@router.get("/audit-logs", response_model=Page[AuditLogEntry], summary="Registro de auditoría")
def list_audit_logs(
    admin: AdminUser,
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
    action: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> Page[AuditLogEntry]:
    """Consulta el registro inmutable de acciones administrativas (HU-ADM-09)."""
    return AdminService(session).list_audit_logs(params, action, actor_id)
