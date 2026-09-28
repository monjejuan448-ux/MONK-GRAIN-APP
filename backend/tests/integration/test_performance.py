"""Pruebas de regresión de rendimiento.

Un problema N+1 no altera el resultado funcional: la respuesta es correcta y
ninguna prueba de comportamiento falla. Solo se nota en la carga de la base de
datos, y para entonces ya está en producción.

Estas pruebas fijan un techo de consultas por operación. Si alguien introduce
una carga perezosa dentro de un bucle, el número sube y la prueba falla.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from app.core.pagination import PageParams
from app.models.catalog import ProductVariant
from app.models.producer import ProducerProfile
from app.modules.catalog.service import CatalogService
from app.schemas.catalog import ProductFilters

pytestmark = pytest.mark.integration


class QueryCounter:
    """Cuenta las sentencias SQL ejecutadas mientras está activo."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        self.count += 1


@pytest.fixture
def count_queries(engine: Engine) -> Generator[QueryCounter, None, None]:
    counter = QueryCounter()
    event.listen(engine, "before_cursor_execute", counter)
    yield counter
    event.remove(engine, "before_cursor_execute", counter)


# Techos deliberadamente holgados respecto a lo medido: dejan margen para
# cambios razonables, pero un N+1 los supera con creces.
MAX_QUERIES_PRODUCT_LIST = 10
MAX_QUERIES_PRODUCT_DETAIL = 12
MAX_QUERIES_PRODUCER_LIST = 10


class TestQueryCounts:
    def test_product_listing_does_not_scale_with_result_count(
        self,
        session: Session,
        count_queries: QueryCounter,
        product_variant: ProductVariant,
        second_variant: ProductVariant,
    ) -> None:
        """El número de consultas no debe crecer con los productos devueltos."""
        service = CatalogService(session)

        count_queries.count = 0
        page = service.list_products(ProductFilters(), PageParams(page=1, page_size=20))

        assert len(page.items) == 2
        assert count_queries.count <= MAX_QUERIES_PRODUCT_LIST, (
            f"El listado disparó {count_queries.count} consultas. "
            "Probablemente falta carga anticipada en alguna relación."
        )

    def test_product_detail_stays_within_budget(
        self,
        session: Session,
        count_queries: QueryCounter,
        product_variant: ProductVariant,
    ) -> None:
        service = CatalogService(session)

        count_queries.count = 0
        service.get_product_detail("pergamino-de-prueba")

        assert count_queries.count <= MAX_QUERIES_PRODUCT_DETAIL

    def test_producer_listing_uses_a_grouped_count(
        self,
        session: Session,
        count_queries: QueryCounter,
        producer: ProducerProfile,
        second_producer: ProducerProfile,
        product_variant: ProductVariant,
        second_variant: ProductVariant,
    ) -> None:
        """El conteo de productos por productor debe ser una sola consulta.

        Consultarlo uno a uno multiplicaba las consultas por el número de
        productores: con 6 eran 15, con 100 habrían sido más de 200.
        """
        service = CatalogService(session)

        count_queries.count = 0
        page = service.list_producers(PageParams(page=1, page_size=20))

        assert len(page.items) == 2
        assert all(item.product_count == 1 for item in page.items)
        assert count_queries.count <= MAX_QUERIES_PRODUCER_LIST, (
            f"El listado de productores disparó {count_queries.count} consultas. "
            "Comprueba que el conteo de productos sigue siendo agrupado."
        )
