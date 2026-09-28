"""Paginación reutilizable para los listados de la API."""

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

MAX_PAGE_SIZE = 100


class PageParams(BaseModel):
    """Parámetros de paginación recibidos por query string."""

    page: Annotated[int, Query(ge=1, description="Número de página")] = 1
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Elementos por página")] = (
        20
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page[T](BaseModel):
    """Respuesta paginada estándar de la API."""

    items: list[T]
    total: int = Field(description="Total de elementos disponibles")
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def create(cls, items: list[T], total: int, params: PageParams) -> "Page[T]":
        total_pages = (total + params.page_size - 1) // params.page_size if total else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )


def paginate_query[T](
    session: Session, statement: Select[tuple[T]], params: PageParams
) -> tuple[list[T], int]:
    """Ejecuta una consulta paginada y devuelve (elementos, total).

    El conteo se hace sobre una subconsulta de la sentencia original para que
    respete exactamente los mismos filtros aplicados al listado.
    """
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.scalar(count_statement) or 0

    if total == 0:
        return [], 0

    paged_statement = statement.offset(params.offset).limit(params.page_size)
    # `unique()` es obligatorio cuando la consulta trae colecciones con
    # `joinedload`: el JOIN devuelve una fila por elemento de la colección y sin
    # esto la entidad principal aparecería repetida. Es inocuo en los demás
    # casos, así que se aplica siempre en lugar de recordarlo en cada consulta.
    items = list(session.scalars(paged_statement).unique().all())
    return items, total
