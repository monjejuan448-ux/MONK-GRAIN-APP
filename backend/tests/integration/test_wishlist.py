"""Pruebas de la lista de deseos (HU-CC-04).

Lo que importa aquí, más allá de guardar y quitar, es que un café agotado se
marque en lugar de desaparecer: quien lo guardó tiene derecho a saber que sigue
ahí y que ahora no tiene existencias.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalog import Inventory, Product, ProductVariant
from app.models.enums import ProductStatus
from app.models.user import User

pytestmark = pytest.mark.integration

API = "/api/v1"


def _product_id(session: Session, variant: ProductVariant) -> str:
    product = session.get(Product, variant.product_id)
    assert product is not None
    return str(product.id)


class TestSavingAndRemoving:
    def test_a_buyer_saves_a_coffee(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        response = client.post(
            f"{API}/wishlist",
            json={"product_id": _product_id(session, product_variant)},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        listed = client.get(f"{API}/wishlist", headers=auth_headers).json()
        assert len(listed) == 1
        assert listed[0]["product_name"] == "Pergamino de Prueba"

    def test_saving_the_same_coffee_twice_is_rejected(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        payload = {"product_id": _product_id(session, product_variant)}
        client.post(f"{API}/wishlist", json=payload, headers=auth_headers)

        response = client.post(f"{API}/wishlist", json=payload, headers=auth_headers)

        assert response.status_code == 409

    def test_removing_takes_it_off_the_list(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        product_id = _product_id(session, product_variant)
        client.post(f"{API}/wishlist", json={"product_id": product_id}, headers=auth_headers)

        response = client.delete(f"{API}/wishlist/{product_id}", headers=auth_headers)

        assert response.status_code == 200
        assert client.get(f"{API}/wishlist", headers=auth_headers).json() == []

    def test_removing_something_that_was_never_saved_is_harmless(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        """Quitar dos veces desde dos pestañas no debe dar error."""
        response = client.delete(f"{API}/wishlist/{uuid.uuid4()}", headers=auth_headers)

        assert response.status_code == 200

    def test_a_coffee_that_does_not_exist_cannot_be_saved(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.post(
            f"{API}/wishlist", json={"product_id": str(uuid.uuid4())}, headers=auth_headers
        )

        assert response.status_code == 404


class TestAvailability:
    def test_a_coffee_with_stock_is_marked_available(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        client.post(
            f"{API}/wishlist",
            json={"product_id": _product_id(session, product_variant)},
            headers=auth_headers,
        )

        listed = client.get(f"{API}/wishlist", headers=auth_headers).json()

        assert listed[0]["is_available"] is True

    def test_a_sold_out_coffee_is_marked_not_available(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Regresión: el campo se calculaba con `is_purchasable`, que solo mira
        si el café sigue publicado. Un café agotado salía como disponible, que es
        justo lo que este campo existe para evitar."""
        client.post(
            f"{API}/wishlist",
            json={"product_id": _product_id(session, product_variant)},
            headers=auth_headers,
        )

        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        inventory.stock_qty = 0
        inventory.reserved_qty = 0
        session.flush()

        listed = client.get(f"{API}/wishlist", headers=auth_headers).json()

        assert listed[0]["is_available"] is False
        # Sigue en la lista: se marca, no desaparece (HU-CC-04, CA3).
        assert len(listed) == 1

    def test_a_coffee_whose_stock_is_all_reserved_is_not_available(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Lo reservado por otro pedido no está disponible para nadie más."""
        client.post(
            f"{API}/wishlist",
            json={"product_id": _product_id(session, product_variant)},
            headers=auth_headers,
        )

        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        inventory.reserved_qty = inventory.stock_qty
        session.flush()

        listed = client.get(f"{API}/wishlist", headers=auth_headers).json()

        assert listed[0]["is_available"] is False

    def test_an_unpublished_coffee_is_not_available(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        client.post(
            f"{API}/wishlist",
            json={"product_id": _product_id(session, product_variant)},
            headers=auth_headers,
        )

        product = session.get(Product, product_variant.product_id)
        assert product is not None
        product.status = ProductStatus.UNPUBLISHED
        session.flush()

        listed = client.get(f"{API}/wishlist", headers=auth_headers).json()

        assert listed[0]["is_available"] is False


class TestIsolation:
    def test_each_account_has_its_own_list(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        client.post(
            f"{API}/wishlist",
            json={"product_id": _product_id(session, product_variant)},
            headers=auth_headers,
        )

        response = client.get(
            f"{API}/wishlist", headers={"Authorization": f"Bearer {producer_token}"}
        )

        assert response.json() == []

    def test_an_anonymous_visitor_has_no_list(self, client: TestClient) -> None:
        assert client.get(f"{API}/wishlist").status_code == 401
