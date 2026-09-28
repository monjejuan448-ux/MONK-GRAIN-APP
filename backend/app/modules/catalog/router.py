"""Endpoints públicos del catálogo."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.pagination import Page, PageParams
from app.core.permissions import OptionalUser
from app.db.session import get_session
from app.models.enums import CoffeeProcess, CoffeeState, RoastLevel
from app.modules.catalog.service import CatalogService
from app.schemas.catalog import (
    ProducerDetail,
    ProducerListItem,
    ProductDetail,
    ProductFilters,
    ProductListItem,
)

router = APIRouter(tags=["catálogo"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "/products",
    response_model=Page[ProductListItem],
    summary="Listar cafés con filtros",
)
def list_products(
    session: SessionDep,
    user: OptionalUser,
    params: Annotated[PageParams, Depends()],
    q: Annotated[str | None, Query(max_length=120, description="Buscar por texto")] = None,
    department: Annotated[str | None, Query(description="Código DANE del departamento")] = None,
    municipality: Annotated[str | None, Query(description="Código DANE del municipio")] = None,
    region: Annotated[str | None, Query(description="Código de la región cafetera")] = None,
    variety: str | None = None,
    process: CoffeeProcess | None = None,
    roast: RoastLevel | None = None,
    state: CoffeeState | None = None,
    certification: str | None = None,
    producer_id: uuid.UUID | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_score: float | None = Query(default=None, ge=0, le=100),
    sort: Annotated[
        str,
        Query(pattern="^(price_asc|price_desc|rating|score|popular|newest)$"),
    ] = "newest",
) -> Page[ProductListItem]:
    """Devuelve el catálogo público, paginado y filtrable.

    Los filtros se combinan entre sí y el ordenamiento se aplica sobre el
    conjunto ya filtrado (HU-VIS-03).
    """
    filters = ProductFilters(
        q=q,
        department=department,
        municipality=municipality,
        region=region,
        variety=variety,
        process=process,
        roast=roast,
        state=state,
        certification=certification,
        producer_id=producer_id,
        min_price=min_price,
        max_price=max_price,
        min_score=min_score,
        sort=sort,
    )
    return CatalogService(session).list_products(filters, params, user)


@router.get(
    "/products/{slug}",
    response_model=ProductDetail,
    summary="Ficha completa de un café",
)
def get_product(slug: str, session: SessionDep, user: OptionalUser) -> ProductDetail:
    """Devuelve la ficha con su trazabilidad.

    La ubicación de la finca se entrega solo de forma aproximada (ADR-08).
    """
    return CatalogService(session).get_product_detail(slug, user)


@router.get(
    "/products/{slug}/related",
    response_model=list[ProductListItem],
    summary="Cafés relacionados",
)
def get_related(slug: str, session: SessionDep) -> list[ProductListItem]:
    return CatalogService(session).get_related_products(slug)


@router.get(
    "/producers",
    response_model=Page[ProducerListItem],
    summary="Listar productores",
)
def list_producers(
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
    department: str | None = None,
    region: str | None = None,
    type: Annotated[  # noqa: A002 — el nombre del filtro es parte del contrato público
        str | None, Query(description="farmer | farm | cooperative | roaster")
    ] = None,
) -> Page[ProducerListItem]:
    return CatalogService(session).list_producers(params, department, region, type)


@router.get(
    "/producers/{producer_id}",
    response_model=ProducerDetail,
    summary="Perfil público de un productor",
)
def get_producer(producer_id: uuid.UUID, session: SessionDep) -> ProducerDetail:
    return CatalogService(session).get_producer_detail(producer_id)
