"""Pruebas del catálogo público.

Verifican los filtros, la visibilidad de los productos y —sobre todo— que no se
filtren datos que deben permanecer restringidos: la coordenada exacta de las
fincas y los precios mayoristas.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalog import Product, ProductVariant
from app.models.enums import ProducerStatus, ProductStatus
from app.models.producer import ProducerProfile

pytestmark = pytest.mark.integration

API = "/api/v1"


class TestProductListing:
    def test_lists_published_products(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        response = client.get(f"{API}/products")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Pergamino de Prueba"

    def test_unpublished_products_are_hidden(
        self, client: TestClient, product_variant: ProductVariant, session: Session
    ) -> None:
        product = session.get(Product, product_variant.product_id)
        assert product is not None
        product.status = ProductStatus.DRAFT
        session.flush()

        assert client.get(f"{API}/products").json()["total"] == 0

    def test_suspended_seller_disappears_from_catalog(
        self,
        client: TestClient,
        product_variant: ProductVariant,
        producer: ProducerProfile,
        session: Session,
    ) -> None:
        """Suspender a un vendedor retira su catálogo sin borrar nada."""
        producer.status = ProducerStatus.SUSPENDED
        session.flush()

        assert client.get(f"{API}/products").json()["total"] == 0
        # El producto sigue existiendo en la base de datos.
        assert session.get(Product, product_variant.product_id) is not None

    def test_filter_by_process(self, client: TestClient, product_variant: ProductVariant) -> None:
        assert client.get(f"{API}/products?process=washed").json()["total"] == 1
        assert client.get(f"{API}/products?process=natural").json()["total"] == 0

    def test_filter_by_maximum_yield_factor(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """El factor se acota por arriba: menos es mejor café, así que lo que un
        comprador declara es el techo que acepta. El lote de prueba tiene 92."""
        assert client.get(f"{API}/products?max_yield_factor=94").json()["total"] == 1
        assert client.get(f"{API}/products?max_yield_factor=90").json()["total"] == 0

    def test_filter_by_maximum_moisture(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """Por encima del 12 % el pergamino corre riesgo de hongos. El lote de
        prueba está al 11 %."""
        assert client.get(f"{API}/products?max_moisture_pct=12").json()["total"] == 1
        assert client.get(f"{API}/products?max_moisture_pct=10.5").json()["total"] == 0

    def test_filter_by_minimum_available_kilos(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """Quien necesita media tonelada no quiere ver lotes de 10 kg."""
        assert client.get(f"{API}/products?min_available_kg=10").json()["total"] == 1
        assert client.get(f"{API}/products?min_available_kg=11").json()["total"] == 0

    def test_price_range_filter(self, client: TestClient, product_variant: ProductVariant) -> None:
        assert client.get(f"{API}/products?max_price=50000").json()["total"] == 1
        assert client.get(f"{API}/products?max_price=10000").json()["total"] == 0

    def test_text_search_ignores_accents(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """Buscar "cafe" debe encontrar "Café" (extensión unaccent)."""
        assert client.get(f"{API}/products?q=cafe").json()["total"] == 1

    def test_filters_combine(self, client: TestClient, product_variant: ProductVariant) -> None:
        combined = client.get(f"{API}/products?process=washed&max_yield_factor=94&max_price=50000")
        assert combined.json()["total"] == 1

        # Basta con que un criterio no se cumpla para excluir el lote.
        contradictory = client.get(f"{API}/products?process=washed&max_yield_factor=85")
        assert contradictory.json()["total"] == 0

    def test_sorting_by_price(
        self,
        client: TestClient,
        product_variant: ProductVariant,
        second_variant: ProductVariant,
    ) -> None:
        ascending = client.get(f"{API}/products?sort=price_asc").json()["items"]
        prices = [float(item["base_price"]) for item in ascending]
        assert prices == sorted(prices)

    def test_pagination_metadata(
        self,
        client: TestClient,
        product_variant: ProductVariant,
        second_variant: ProductVariant,
    ) -> None:
        page = client.get(f"{API}/products?page=1&page_size=1").json()

        assert page["total"] == 2
        assert page["total_pages"] == 2
        assert page["has_next"] is True
        assert page["has_previous"] is False
        assert len(page["items"]) == 1


class TestProductDetail:
    def test_detail_includes_traceability(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        response = client.get(f"{API}/products/pergamino-de-prueba")

        assert response.status_code == 200
        body = response.json()
        assert body["attributes"]["variety"] == "Caturra"
        assert body["attributes"]["process"] == "washed"
        assert body["attributes"]["altitude_masl"] == 1750
        # El análisis del pergamino es lo que decide una compra por volumen.
        assert body["attributes"]["yield_factor"] == "92.00"
        assert body["attributes"]["moisture_pct"] == "11.00"
        assert body["attributes"]["screen_sizes"] == [15, 16, 17]
        assert body["attributes"]["lot_code"] == "PR-2026-001"
        assert body["farm"]["name"] == "Finca de Prueba"

    def test_exact_farm_coordinates_are_never_exposed(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """Publicar la coordenada real de una finca rural es un riesgo de
        seguridad física para el productor, no solo de privacidad (ADR-08)."""
        body = client.get(f"{API}/products/pergamino-de-prueba").json()

        farm = body["farm"]
        assert "exact_lat" not in farm
        assert "exact_lng" not in farm
        assert farm["approx_lat"] is not None

        # Ni siquiera en el cuerpo completo de la respuesta.
        assert "1.860000" not in client.get(f"{API}/products/pergamino-de-prueba").text

    def test_wholesale_price_hidden_from_anonymous_visitors(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """El precio mayorista solo lo ve un comprador empresarial verificado."""
        body = client.get(f"{API}/products/pergamino-de-prueba").json()

        assert body["variants"][0]["wholesale_price"] is None
        assert "35000" not in client.get(f"{API}/products/pergamino-de-prueba").text

    def test_wholesale_price_hidden_from_regular_buyers(
        self, client: TestClient, product_variant: ProductVariant, buyer_token: str
    ) -> None:
        body = client.get(
            f"{API}/products/pergamino-de-prueba",
            headers={"Authorization": f"Bearer {buyer_token}"},
        ).json()

        assert body["variants"][0]["wholesale_price"] is None

    def test_unknown_slug_returns_not_found(self, client: TestClient) -> None:
        response = client.get(f"{API}/products/este-cafe-no-existe")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestProducerListing:
    def test_lists_approved_producers(self, client: TestClient, producer: ProducerProfile) -> None:
        response = client.get(f"{API}/producers")

        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_pending_producers_are_not_public(
        self, client: TestClient, producer: ProducerProfile, session: Session
    ) -> None:
        producer.status = ProducerStatus.PENDING_APPROVAL
        session.flush()

        assert client.get(f"{API}/producers").json()["total"] == 0

    def test_producer_profile_includes_products(
        self, client: TestClient, producer: ProducerProfile, product_variant: ProductVariant
    ) -> None:
        response = client.get(f"{API}/producers/{producer.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["brand_name"] == "Café de Prueba"
        assert len(body["products"]) == 1
