"""Endpoints de devoluciones, retracto y garantía.

Las rutas están separadas por quién las usa —comprador, vendedor— porque la
autorización no es la misma: el comprador radica y declara que envió el café de
vuelta, quien vende responde por escrito, confirma la recepción y reembolsa.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.files import validate_image
from app.core.pagination import Page, PageParams
from app.core.permissions import CurrentUser, ProducerUser
from app.db.session import get_session
from app.modules.returns.service import MAX_EVIDENCES_PER_RETURN, ReturnService
from app.schemas.returns import (
    ReturnDetail,
    ReturnEligibility,
    ReturnRequestInput,
    ReturnResolutionInput,
    ReturnSummary,
)

router = APIRouter(tags=["devoluciones"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "/orders/sub-orders/{sub_order_id}/return-eligibility",
    response_model=ReturnEligibility,
    summary="Qué puede devolverse de este pedido",
)
def check_eligibility(
    sub_order_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ReturnEligibility:
    """Plazos vivos y unidades devolvibles.

    La interfaz la consulta antes de mostrar el formulario: es lo que decide si
    ofrece el retracto, solo la garantía, o ninguno de los dos.
    """
    return ReturnService(session).eligibility(user, sub_order_id)


@router.post(
    "/returns",
    response_model=ReturnDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar una devolución",
)
def request_return(
    payload: ReturnRequestInput, user: CurrentUser, session: SessionDep
) -> ReturnDetail:
    """Radica la solicitud y devuelve la constancia con su número y fecha."""
    return ReturnService(session).request_return(user, payload)


@router.get("/returns", response_model=Page[ReturnSummary], summary="Mis devoluciones")
def list_my_returns(
    user: CurrentUser, session: SessionDep, params: Annotated[PageParams, Depends()]
) -> Page[ReturnSummary]:
    return ReturnService(session).list_for_buyer(user, params)


@router.get(
    "/returns/{return_id}",
    response_model=ReturnDetail,
    summary="Constancia de la devolución",
)
def get_return(return_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> ReturnDetail:
    """La consultan su autor, quien vende y un administrador."""
    return ReturnService(session).get_detail(user, return_id)


@router.post(
    "/returns/{return_id}/evidence",
    response_model=ReturnDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Adjuntar fotografías",
)
async def upload_evidence(
    return_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    files: Annotated[
        list[UploadFile],
        File(description=f"Hasta {MAX_EVIDENCES_PER_RETURN} imágenes de 5 MB cada una"),
    ],
) -> ReturnDetail:
    """Cada archivo se valida por su contenido y se reescribe como JPEG.

    Las fotos no son públicas: se guardan fuera de los prefijos abiertos y solo
    se entregan mediante enlaces firmados de vida corta.
    """
    stored = [await validate_image(upload) for upload in files]
    return ReturnService(session).add_evidence(user, return_id, stored)


@router.post(
    "/returns/{return_id}/shipped",
    response_model=ReturnDetail,
    summary="Declarar que enviaste el café de vuelta",
)
def mark_shipped_back(return_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> ReturnDetail:
    return ReturnService(session).mark_shipped_back(user, return_id)


# ----------------------------------------------------------------------
# Lado del vendedor
# ----------------------------------------------------------------------
@router.get(
    "/producer/returns",
    response_model=Page[ReturnSummary],
    summary="Devoluciones de mis ventas",
)
def list_producer_returns(
    producer: ProducerUser, session: SessionDep, params: Annotated[PageParams, Depends()]
) -> Page[ReturnSummary]:
    """Ordenadas por vencimiento: primero lo que hay que responder antes."""
    return ReturnService(session).list_for_producer(producer, params)


@router.post(
    "/producer/returns/{return_id}/resolution",
    response_model=ReturnDetail,
    summary="Responder por escrito a la reclamación",
)
def resolve_return(
    return_id: uuid.UUID,
    payload: ReturnResolutionInput,
    producer: ProducerUser,
    session: SessionDep,
) -> ReturnDetail:
    """Aprueba o rechaza, siempre con motivos.

    El Decreto 735 de 2013 exige respuesta escrita dentro de los quince días
    hábiles siguientes, y esa respuesta es el documento que el comprador
    acompaña a su reclamación ante la Superintendencia.
    """
    return ReturnService(session).resolve(producer, return_id, payload)


@router.post(
    "/producer/returns/{return_id}/received",
    response_model=ReturnDetail,
    summary="Confirmar que el café volvió",
)
def mark_received(
    return_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> ReturnDetail:
    return ReturnService(session).mark_received(producer, return_id)


@router.post(
    "/producer/returns/{return_id}/refund",
    response_model=ReturnDetail,
    summary="Registrar el reembolso",
)
def refund_return(
    return_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> ReturnDetail:
    """Cierra la devolución por el importe calculado al radicar.

    No admite un importe distinto: el artículo 47 de la Ley 1480 prohíbe
    descuentos y retenciones sobre el dinero que se devuelve.
    """
    return ReturnService(session).refund(producer, return_id)
