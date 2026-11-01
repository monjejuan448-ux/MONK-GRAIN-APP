"""Endpoints de liquidación al vendedor.

Dos lados: el vendedor registra dónde cobrar y consulta lo que se le ha
liquidado; el administrador cierra periodos y deja constancia de los pagos.

La cuenta bancaria **no se expone nunca completa**, ni al propio dueño —solo sus
cuatro últimos dígitos— ni al administrador, que no la ve en absoluto. Es una
decisión que venía del diseño original (HU-ADM-02, CA5) y se mantiene: quien
dispersa los fondos consulta el dato por el canal que corresponda, no a través de
un listado de la API.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.permissions import AdminUser, ProducerUser, require_permissions
from app.core.rate_limit import client_ip
from app.db.session import get_session
from app.models.enums import SettlementStatus
from app.modules.payments.service import SettlementService
from app.schemas.common import MessageResponse
from app.schemas.settlement import (
    AdminSettlementItem,
    BankAccountInput,
    BankAccountView,
    ClosePeriodInput,
    ClosePeriodResult,
    MarkPaidInput,
    ProducerSettlementItem,
)

router = APIRouter(tags=["liquidaciones"])

SessionDep = Annotated[Session, Depends(get_session)]


# ======================================================================
# Vendedor
# ======================================================================
@router.put(
    "/producer/bank-account",
    response_model=BankAccountView,
    summary="Registrar o actualizar la cuenta donde cobrar",
)
def save_bank_account(
    payload: BankAccountInput, producer: ProducerUser, session: SessionDep
) -> BankAccountView:
    """Guarda la cuenta cifrada y devuelve solo lo que puede mostrarse."""
    return SettlementService(session).save_bank_account(producer, payload)


@router.get(
    "/producer/bank-account",
    response_model=BankAccountView | None,
    summary="Cuenta registrada, con el número enmascarado",
)
def get_bank_account(producer: ProducerUser, session: SessionDep) -> BankAccountView | None:
    return SettlementService(session).get_bank_account(producer)


@router.delete(
    "/producer/bank-account",
    response_model=MessageResponse,
    summary="Retirar la cuenta registrada",
)
def delete_bank_account(producer: ProducerUser, session: SessionDep) -> MessageResponse:
    SettlementService(session).delete_bank_account(producer)
    return MessageResponse(
        message="Retiramos tu cuenta bancaria. Sin una cuenta registrada no podemos liquidarte."
    )


@router.get(
    "/producer/settlements",
    response_model=list[ProducerSettlementItem],
    summary="Historial de liquidaciones del vendedor",
)
def list_my_settlements(
    producer: ProducerUser, session: SessionDep
) -> list[ProducerSettlementItem]:
    return SettlementService(session).list_for_producer(producer)


# ======================================================================
# Administración
# ======================================================================
@router.post(
    "/admin/settlements/close",
    response_model=ClosePeriodResult,
    status_code=status.HTTP_201_CREATED,
    summary="Cerrar un periodo y generar las liquidaciones",
    dependencies=[Depends(require_permissions("settlement.manage"))],
)
def close_period(
    payload: ClosePeriodInput,
    admin: AdminUser,
    request: Request,
    session: SessionDep,
) -> ClosePeriodResult:
    """Agrupa por vendedor lo que ya puede pagarse en ese periodo.

    Solo entra lo entregado, pasado el plazo de retracto y sin reclamaciones
    vivas. Es idempotente: volver a cerrar el mismo periodo no duplica nada,
    porque cada comisión queda marcada con la liquidación que la recoge.
    """
    return SettlementService(session).close_period(
        admin,
        payload.period_start,
        payload.period_end,
        ip_address=client_ip(request),
    )


@router.get(
    "/admin/settlements",
    response_model=list[AdminSettlementItem],
    summary="Liquidaciones de todos los vendedores",
    dependencies=[Depends(require_permissions("settlement.manage"))],
)
def list_settlements(
    admin: AdminUser,
    session: SessionDep,
    settlement_status: Annotated[SettlementStatus | None, Query(alias="status")] = None,
) -> list[AdminSettlementItem]:
    return SettlementService(session).list_for_admin(settlement_status)


@router.post(
    "/admin/settlements/{settlement_id}/pay",
    response_model=AdminSettlementItem,
    summary="Dejar constancia del desembolso",
    dependencies=[Depends(require_permissions("settlement.manage"))],
)
def mark_paid(
    settlement_id: uuid.UUID,
    payload: MarkPaidInput,
    admin: AdminUser,
    request: Request,
    session: SessionDep,
) -> AdminSettlementItem:
    """Marca la liquidación pagada y cierra las comisiones que cubre.

    La referencia es obligatoria: un pago sin constancia de por dónde salió el
    dinero no es un pago registrado, es una casilla marcada.
    """
    return SettlementService(session).mark_paid(
        admin,
        settlement_id,
        payload.payment_reference,
        payload.notes,
        ip_address=client_ip(request),
    )
