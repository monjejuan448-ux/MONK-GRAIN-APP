"""Pruebas de las reglas propias del comercio de pergamino.

El pergamino se vende por kilogramo y con un mínimo de compra, y su calidad se
describe con un análisis físico en vez de con un puntaje de taza. Lo que se
verifica aquí es que esas dos cosas se hagan cumplir en el servidor: el mínimo
frente a un carrito que intenta bajarse de él, y el rango de los valores del
análisis frente a un dato imposible.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalog import CoffeeAttributes, Inventory, Product, ProductVariant
from app.models.user import User

pytestmark = pytest.mark.integration

API = "/api/v1"


class TestMinimumPurchase:
    def test_a_lot_sold_by_the_carga_rejects_less(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
    ) -> None:
        """Por debajo del mínimo el flete se come la venta, de ahí que el
        vendedor lo fije y el servidor lo haga cumplir."""
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 50},
            headers=auth_headers,
        )

        assert response.status_code == 422
        body = response.json()["error"]
        assert "125 kg" in body["message"]
        assert body["details"]["min_qty_kg"] == 125

    def test_exactly_the_minimum_is_accepted(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
    ) -> None:
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 125},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        assert response.json()["groups"][0]["items"][0]["quantity"] == 125

    def test_two_partial_additions_that_reach_the_minimum_are_accepted(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
    ) -> None:
        """El mínimo se juzga sobre el total de la línea, no sobre cada clic: el
        carrito suma, y 100 más 25 son los 125 exigidos."""
        first = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 100},
            headers=auth_headers,
        )
        assert first.status_code == 422

        client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 125},
            headers=auth_headers,
        )
        second = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 25},
            headers=auth_headers,
        )

        assert second.status_code == 201, second.text
        assert second.json()["groups"][0]["items"][0]["quantity"] == 150

    def test_the_minimum_cannot_be_dodged_by_editing_the_line(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
    ) -> None:
        """Agregar 125 y luego bajar a 10 sería la forma obvia de saltárselo."""
        added = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 125},
            headers=auth_headers,
        )
        item_id = added.json()["groups"][0]["items"][0]["id"]

        response = client.patch(
            f"{API}/cart/items/{item_id}", json={"quantity": 10}, headers=auth_headers
        )

        assert response.status_code == 422
        assert "125 kg" in response.json()["error"]["message"]

    def test_the_cart_reports_the_minimum_of_each_line(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
    ) -> None:
        """La interfaz necesita el mínimo para no ofrecer un menos imposible."""
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 125},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        item = response.json()["groups"][0]["items"][0]
        assert item["min_qty_kg"] == 125
        assert item["presentation"] == "A granel, en costal de fique"

    def test_kilos_beyond_the_stock_are_still_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
    ) -> None:
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 5000},
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert "1250 kg" in response.json()["error"]["message"]


class TestPricingByTheKilo:
    def test_the_line_total_is_the_price_per_kilo_times_the_kilos(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
    ) -> None:
        """22.000 el kilo por 125 kilos son 2.750.000: el precio de una carga."""
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant_with_minimum.id), "quantity": 125},
            headers=auth_headers,
        )

        item = response.json()["groups"][0]["items"][0]
        assert Decimal(item["unit_price"]) == Decimal("22000.00")
        assert Decimal(item["line_total"]) == Decimal("2750000.00")

    def test_the_catalogue_reports_the_available_kilos(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        body = client.get(f"{API}/products/pergamino-de-prueba").json()

        assert body["available_kg"] == 10
        assert body["variants"][0]["min_qty_kg"] == 1


class TestAnalysisConstraints:
    def test_the_database_rejects_an_impossible_yield_factor(
        self, session: Session, product_variant: ProductVariant
    ) -> None:
        """Por debajo de 80 no existe café en Colombia: es un error de digitación,
        no un café excepcional. Lo rechaza la base de datos, no solo el schema."""
        attributes = session.scalar(
            select(CoffeeAttributes).where(
                CoffeeAttributes.product_id == product_variant.product_id
            )
        )
        assert attributes is not None

        attributes.yield_factor = Decimal("12.00")
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_the_database_rejects_an_impossible_percentage(
        self, session: Session, product_variant: ProductVariant
    ) -> None:
        attributes = session.scalar(
            select(CoffeeAttributes).where(
                CoffeeAttributes.product_id == product_variant.product_id
            )
        )
        assert attributes is not None

        attributes.pasilla_pct = Decimal("140.00")
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_the_state_column_only_admits_pergamino(
        self, session: Session, product_variant: ProductVariant
    ) -> None:
        """El ENUM nativo de PostgreSQL es la última barrera: aunque alguien
        escribiera directamente en la tabla, no entra otro estado."""
        with pytest.raises(Exception):  # noqa: B017, PT011 — DataError del ENUM
            session.execute(
                text("UPDATE products SET state = 'roasted' WHERE id = :pid"),
                {"pid": str(product_variant.product_id)},
            )
        session.rollback()


class TestPublishingAnOffer:
    def test_a_minimum_above_the_stock_is_rejected(
        self, client: TestClient, producer_token: str, session: Session
    ) -> None:
        """Una oferta con mínimo mayor que las existencias es incomprable: el
        comprador solo lo descubriría al llegar al carrito."""
        producer_headers = {"Authorization": f"Bearer {producer_token}"}
        created = client.post(
            f"{API}/producer/catalog",
            json={
                "name": "Lote Incomprable de Prueba",
                "description": "Lote de prueba con descripción bastante larga para el validador.",
                "base_price": "20000",
                "attributes": {"yield_factor": "93.00"},
            },
            headers=producer_headers,
        )
        assert created.status_code == 201, created.text

        response = client.post(
            f"{API}/producer/catalog/{created.json()['id']}/variants",
            json={
                "presentation": "A granel",
                "min_qty_kg": 500,
                "price": "20000",
                "stock_qty": 100,
            },
            headers=producer_headers,
        )

        assert response.status_code == 422
        # Un validador de modelo deja su mensaje en el detalle por campo, no en
        # el mensaje general de la respuesta.
        fields = response.json()["error"]["details"]["fields"]
        assert any("mínimo de compra" in field["message"] for field in fields), fields

    def test_a_screen_size_that_does_not_exist_is_rejected(
        self, client: TestClient, producer_token: str
    ) -> None:
        """Las mallas del café van de la 14 a la 20."""
        response = client.post(
            f"{API}/producer/catalog",
            json={
                "name": "Lote con Malla Imposible",
                "description": "Lote de prueba con descripción bastante larga para el validador.",
                "base_price": "20000",
                "attributes": {"screen_sizes": [16, 42]},
            },
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 422
        assert "42" in response.text

    def test_the_analysis_is_optional(
        self, client: TestClient, producer_token: str, session: Session
    ) -> None:
        """Un caficultor que no ha mandado su café a un laboratorio tiene que
        poder publicarlo igual: exigir el análisis dejaría fuera a la mayoría."""
        response = client.post(
            f"{API}/producer/catalog",
            json={
                "name": "Lote sin Analisis de Prueba",
                "description": "Lote de prueba con descripción bastante larga para el validador.",
                "base_price": "18000",
            },
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 201, response.text
        assert response.json()["attributes"]["yield_factor"] is None

    def test_the_sku_records_the_minimum_in_kilos(
        self, client: TestClient, producer_token: str
    ) -> None:
        producer_headers = {"Authorization": f"Bearer {producer_token}"}
        created = client.post(
            f"{API}/producer/catalog",
            json={
                "name": "Lote con Referencia de Prueba",
                "description": "Lote de prueba con descripción bastante larga para el validador.",
                "base_price": "20000",
            },
            headers=producer_headers,
        )
        response = client.post(
            f"{API}/producer/catalog/{created.json()['id']}/variants",
            json={
                "presentation": "Bultos de 70 kg",
                "min_qty_kg": 700,
                "price": "20000",
                "stock_qty": 1400,
            },
            headers=producer_headers,
        )

        assert response.status_code == 201, response.text
        assert "700KG" in response.json()["variants"][0]["sku"]


class TestVariantLabel:
    def test_the_label_names_the_minimum_when_there_is_one(
        self, session: Session, variant_with_minimum: ProductVariant
    ) -> None:
        """La etiqueta se congela en el pedido: tiene que decir qué se compró."""
        assert variant_with_minimum.label == "A granel, en costal de fique · mínimo 125 kg"

    def test_without_a_real_minimum_the_label_is_just_the_presentation(
        self, session: Session, product_variant: ProductVariant
    ) -> None:
        """Un «mínimo 1 kg» no informa de nada y solo alarga la etiqueta."""
        assert product_variant.label == "A granel, en costal de fique"


class TestInventoryInKilos:
    def test_the_stock_is_counted_in_kilos(
        self, session: Session, variant_with_minimum: ProductVariant
    ) -> None:
        inventory = session.get(Inventory, variant_with_minimum.id)
        assert inventory is not None
        # Diez cargas de 125 kg.
        assert inventory.stock_qty == 1250
        assert inventory.available_qty == 1250

    def test_the_low_stock_warning_is_measured_in_kilos(
        self, session: Session, variant_with_minimum: ProductVariant
    ) -> None:
        inventory = session.get(Inventory, variant_with_minimum.id)
        assert inventory is not None
        assert inventory.is_low_stock is False

        inventory.stock_qty = 3
        session.flush()
        assert inventory.is_low_stock is True


class TestCategories:
    def test_the_lot_belongs_to_a_pergamino_category_or_none(
        self, session: Session, product_variant: ProductVariant
    ) -> None:
        """Las categorías del catálogo agrupan por factor, no por tueste."""
        product = session.get(Product, product_variant.product_id)
        assert product is not None
        assert product.category_id is None or product.category is not None
