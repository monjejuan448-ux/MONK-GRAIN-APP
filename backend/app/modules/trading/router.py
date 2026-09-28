"""Endpoints de oferta y demanda.

Las rutas están separadas por lado del mercado y no por entidad: un comprador
vive en `/demands` y un vendedor en `/producer/demands`. Mezclarlas en un solo
recurso habría obligado a que cada endpoint decidiera, según el rol de quien
llama, qué es lo que devuelve.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.pagination import Page, PageParams
from app.core.permissions import CurrentUser, ProducerUser
from app.db.session import get_session
from app.modules.trading.service import TradingService
from app.schemas.trading import (
    DemandCreate,
    DemandDetail,
    DemandSummary,
    DemandUpdate,
    MyOfferSummary,
    OfferCreate,
    OfferRespond,
)

router = APIRouter(tags=["oferta y demanda"])

SessionDep = Annotated[Session, Depends(get_session)]


# ------------------------------------------------------------------
# Comprador
# ------------------------------------------------------------------
@router.post(
    "/demands",
    response_model=DemandDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar lo que busco comprar",
)
def create_demand(payload: DemandCreate, user: CurrentUser, session: SessionDep) -> DemandDetail:
    """Publica una solicitud de compra de pergamino.

    Los vendedores aprobados la verán y podrán responder con una postura
    respaldada por uno de sus lotes publicados.
    """
    return TradingService(session).create_demand(user, payload)


@router.get("/demands", response_model=Page[DemandSummary], summary="Mis solicitudes")
def list_my_demands(
    user: CurrentUser, session: SessionDep, params: Annotated[PageParams, Depends()]
) -> Page[DemandSummary]:
    return TradingService(session).list_my_demands(user, params)


@router.get(
    "/demands/{demand_id}",
    response_model=DemandDetail,
    summary="Detalle de mi solicitud con sus posturas",
)
def get_demand(demand_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> DemandDetail:
    return TradingService(session).get_demand_detail(user, demand_id)


@router.patch("/demands/{demand_id}", response_model=DemandDetail, summary="Editar mi solicitud")
def update_demand(
    demand_id: uuid.UUID,
    payload: DemandUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> DemandDetail:
    """Ajusta título, descripción, precio ofrecido o vigencia.

    Los kilos y los techos de calidad no se editan: cambiarlos invalidaría las
    posturas que ya se enviaron respondiendo a otras condiciones.
    """
    return TradingService(session).update_demand(user, demand_id, payload)


@router.post(
    "/demands/{demand_id}/close",
    response_model=DemandDetail,
    summary="Cerrar mi solicitud",
)
def close_demand(demand_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> DemandDetail:
    """Cierra la solicitud y rechaza lo que quedara pendiente."""
    return TradingService(session).close_demand(user, demand_id)


@router.post(
    "/demands/offers/{offer_id}/respond",
    response_model=DemandDetail,
    summary="Aceptar o rechazar una postura",
)
def respond_to_offer(
    offer_id: uuid.UUID,
    payload: OfferRespond,
    user: CurrentUser,
    session: SessionDep,
) -> DemandDetail:
    """Responde a una postura recibida.

    Aceptar deja los kilos acordados en tu carrito **al precio acordado**. Desde
    ahí sigues por el checkout de siempre, de modo que puedes armar tu carga con
    varios vendedores y pagar una sola vez.
    """
    return TradingService(session).respond_to_offer(user, offer_id, payload)


# ------------------------------------------------------------------
# Vendedor
# ------------------------------------------------------------------
@router.get(
    "/producer/demands",
    response_model=Page[DemandSummary],
    summary="Solicitudes de compra vigentes",
)
def list_open_demands(
    producer: ProducerUser,
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
    only_matching: Annotated[
        bool,
        Query(description="Solo las que alguno de mis lotes publicados puede satisfacer"),
    ] = False,
) -> Page[DemandSummary]:
    """Solicitudes que todavía admiten posturas.

    No son públicas: contienen lo que un comprador busca y a qué precio, que es
    información comercial suya. Solo las ve un vendedor aprobado.
    """
    return TradingService(session).list_open_demands(producer, params, only_matching=only_matching)


@router.post(
    "/producer/demands/{demand_id}/offers",
    response_model=MyOfferSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Responder con una postura",
)
def create_offer(
    demand_id: uuid.UUID,
    payload: OfferCreate,
    producer: ProducerUser,
    session: SessionDep,
) -> MyOfferSummary:
    """Ofrece kilos de uno de tus lotes publicados al precio que propongas."""
    return TradingService(session).create_offer(producer, demand_id, payload)


@router.get(
    "/producer/offers",
    response_model=Page[MyOfferSummary],
    summary="Mis posturas enviadas",
)
def list_my_offers(
    producer: ProducerUser,
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
) -> Page[MyOfferSummary]:
    return TradingService(session).list_my_offers(producer, params)


@router.post(
    "/producer/offers/{offer_id}/withdraw",
    response_model=MyOfferSummary,
    summary="Retirar una postura",
)
def withdraw_offer(
    offer_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> MyOfferSummary:
    """Retira una postura que el comprador todavía no respondió."""
    return TradingService(session).withdraw_offer(producer, offer_id)
