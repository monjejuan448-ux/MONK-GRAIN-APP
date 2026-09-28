"""Pruebas del despacho por parte del vendedor (HU-PRO-07).

Es la otra mitad del pedido: el comprador paga y el vendedor tiene que poder
confirmarlo, prepararlo, despacharlo con su guía y, si no puede cumplir,
cancelarlo. El grafo de transiciones está declarado como dato en
`models.enums`; aquí se comprueba que el endpoint lo respete y que cada paso
deje la consecuencia que le corresponde en inventario y en envío.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Inventory, ProductVariant
from app.models.enums import ShipmentStatus, SubOrderStatus
from app.models.order import SubOrder
from app.models.producer import ProducerProfile
from app.models.user import Address, User

pytestmark = pytest.mark.integration

API = "/api/v1"


def _place_order(
    client: TestClient,
    session: Session,
    headers: dict[str, str],
    buyer: User,
    variant: ProductVariant,
    quantity: int = 2,
) -> SubOrder:
    """Deja un pedido pagado a medias: creado y con el stock reservado."""
    client.post(
        f"{API}/cart/items",
        json={"variant_id": str(variant.id), "quantity": quantity},
        headers=headers,
    )
    address = session.scalar(select(Address).where(Address.user_id == buyer.id))
    assert address is not None

    response = client.post(
        f"{API}/orders",
        json={"shipping_address_id": str(address.id), "accept_terms": True},
        headers=headers,
    )
    assert response.status_code == 201, response.text

    sub_order = session.scalar(select(SubOrder))
    assert sub_order is not None
    return sub_order


def _advance(
    client: TestClient,
    producer_token: str,
    sub_order_id: uuid.UUID,
    status: str,
    **extra: str,
):
    return client.patch(
        f"{API}/orders/sub-orders/{sub_order_id}/status",
        json={"status": status, **extra},
        headers={"Authorization": f"Bearer {producer_token}"},
    )


class TestInbox:
    def test_the_seller_sees_the_order_just_placed(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        _place_order(client, session, auth_headers, buyer, product_variant)

        response = client.get(
            f"{API}/producer/orders", headers={"Authorization": f"Bearer {producer_token}"}
        )

        assert response.status_code == 200, response.text
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == SubOrderStatus.PENDING.value
        assert items[0]["item_count"] == 1

    def test_the_inbox_can_be_filtered_by_status(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        _place_order(client, session, auth_headers, buyer, product_variant)

        pending = client.get(
            f"{API}/producer/orders",
            params={"status": SubOrderStatus.PENDING.value},
            headers={"Authorization": f"Bearer {producer_token}"},
        )
        shipped = client.get(
            f"{API}/producer/orders",
            params={"status": SubOrderStatus.SHIPPED.value},
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert len(pending.json()["items"]) == 1
        assert shipped.json()["items"] == []

    def test_the_inbox_shows_the_destination_municipality(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """Regresión: se mostraba el barrio, que es opcional y llegaba vacío en
        la mayoría de los pedidos. El vendedor necesita el municipio para
        cotizar el envío."""
        _place_order(client, session, auth_headers, buyer, product_variant)

        response = client.get(
            f"{API}/producer/orders", headers={"Authorization": f"Bearer {producer_token}"}
        )

        assert response.json()["items"][0]["shipping_city"] == "Pitalito"

    def test_a_seller_does_not_see_another_sellers_orders(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        second_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """El pedido es del segundo vendedor; el primero no debe verlo."""
        _place_order(client, session, auth_headers, buyer, second_variant)

        response = client.get(
            f"{API}/producer/orders", headers={"Authorization": f"Bearer {producer_token}"}
        )

        assert response.json()["items"] == []


class TestTransitions:
    def test_the_seller_confirms_a_pending_order(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)

        response = _advance(client, producer_token, sub_order.id, SubOrderStatus.CONFIRMED.value)

        assert response.status_code == 200, response.text
        assert response.json()["status"] == SubOrderStatus.CONFIRMED.value

    def test_the_whole_path_up_to_delivered(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)

        for status in (
            SubOrderStatus.CONFIRMED,
            SubOrderStatus.PREPARED,
            SubOrderStatus.SHIPPED,
            SubOrderStatus.DELIVERED,
        ):
            response = _advance(client, producer_token, sub_order.id, status.value)
            assert response.status_code == 200, f"{status.value}: {response.text}"

        assert response.json()["status"] == SubOrderStatus.DELIVERED.value

    def test_skipping_a_step_is_rejected_and_says_what_is_allowed(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """No se puede despachar lo que aún no se ha confirmado. El error enumera
        las transiciones válidas para que la interfaz no tenga que adivinarlas."""
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)

        response = _advance(client, producer_token, sub_order.id, SubOrderStatus.SHIPPED.value)

        assert response.status_code == 422
        details = response.json()["error"]["details"]
        assert details["current"] == SubOrderStatus.PENDING.value
        assert sorted(details["allowed"]) == [
            SubOrderStatus.CANCELLED.value,
            SubOrderStatus.CONFIRMED.value,
        ]

    def test_a_cancelled_order_is_terminal(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)
        _advance(
            client,
            producer_token,
            sub_order.id,
            SubOrderStatus.CANCELLED.value,
            note="Se perdió el lote en el secado.",
        )

        response = _advance(client, producer_token, sub_order.id, SubOrderStatus.CONFIRMED.value)

        assert response.status_code == 422

    def test_an_invalid_status_value_is_rejected_by_the_schema(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)

        response = _advance(client, producer_token, sub_order.id, "despachadisimo")

        assert response.status_code == 422


class TestShipment:
    def test_shipping_registers_the_carrier_and_the_tracking_number(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)
        _advance(client, producer_token, sub_order.id, SubOrderStatus.CONFIRMED.value)
        _advance(client, producer_token, sub_order.id, SubOrderStatus.PREPARED.value)

        response = _advance(
            client,
            producer_token,
            sub_order.id,
            SubOrderStatus.SHIPPED.value,
            carrier="Servientrega",
            tracking_number="SE-998877",
        )

        assert response.status_code == 200, response.text
        shipment = response.json()["shipment"]
        assert shipment["carrier"] == "Servientrega"
        assert shipment["tracking_number"] == "SE-998877"

    def test_shipping_without_a_guide_falls_back_to_the_simulated_one(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """El operador logístico del MVP es simulado: el vendedor puede despachar
        sin guía real y el sistema genera una de prueba."""
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)
        _advance(client, producer_token, sub_order.id, SubOrderStatus.CONFIRMED.value)
        _advance(client, producer_token, sub_order.id, SubOrderStatus.PREPARED.value)

        response = _advance(client, producer_token, sub_order.id, SubOrderStatus.SHIPPED.value)

        assert response.status_code == 200, response.text
        assert response.json()["shipment"]["tracking_number"].startswith("SIM")

    def test_delivering_closes_the_shipment(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)
        for status in (
            SubOrderStatus.CONFIRMED,
            SubOrderStatus.PREPARED,
            SubOrderStatus.SHIPPED,
            SubOrderStatus.DELIVERED,
        ):
            _advance(client, producer_token, sub_order.id, status.value)

        session.expire_all()
        refreshed = session.get(SubOrder, sub_order.id)
        assert refreshed is not None
        assert refreshed.shipment is not None
        assert refreshed.shipment.status == ShipmentStatus.DELIVERED
        assert refreshed.shipment.delivered_at is not None


class TestSellerCancellation:
    def test_cancelling_returns_the_reserved_stock_to_the_catalogue(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """Regresión: la cancelación del vendedor no liberaba la reserva.

        El stock quedaba retenido para siempre —invendible y sin pedido que lo
        justificara— porque solo la cancelación del comprador lo devolvía. El
        camino era inalcanzable desde la interfaz, así que el defecto no se veía.
        """
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant, quantity=3)

        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        session.refresh(inventory)
        assert inventory.reserved_qty == 3

        response = _advance(
            client,
            producer_token,
            sub_order.id,
            SubOrderStatus.CANCELLED.value,
            note="No alcanza el lote para completar el pedido.",
        )

        assert response.status_code == 200, response.text
        session.expire_all()
        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        assert inventory.reserved_qty == 0
        # El stock nunca se había descontado: solo estaba retenido.
        assert inventory.stock_qty == 10
        assert inventory.available_qty == 10

    def test_the_reason_is_recorded_on_the_sub_order(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """Quien recibe la cancelación tiene derecho a saber por qué."""
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)
        reason = "El lote no pasó el control de humedad."

        _advance(
            client,
            producer_token,
            sub_order.id,
            SubOrderStatus.CANCELLED.value,
            note=reason,
        )

        session.expire_all()
        refreshed = session.get(SubOrder, sub_order.id)
        assert refreshed is not None
        assert refreshed.cancellation_reason == reason

    def test_cancelling_an_already_shipped_order_is_not_allowed(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """Lo despachado no se cancela: se devuelve, que es otro procedimiento
        con sus propios plazos y su propio reembolso."""
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)
        _advance(client, producer_token, sub_order.id, SubOrderStatus.CONFIRMED.value)
        _advance(client, producer_token, sub_order.id, SubOrderStatus.PREPARED.value)
        _advance(client, producer_token, sub_order.id, SubOrderStatus.SHIPPED.value)

        response = _advance(client, producer_token, sub_order.id, SubOrderStatus.CANCELLED.value)

        assert response.status_code == 422


class TestAuthorization:
    def test_a_seller_cannot_touch_another_sellers_order(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        second_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, second_variant)

        response = _advance(client, producer_token, sub_order.id, SubOrderStatus.CONFIRMED.value)

        assert response.status_code == 403

    def test_a_buyer_cannot_advance_the_status(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        buyer_token: str,
    ) -> None:
        """Ocultar el botón no es control de acceso: el endpoint mismo rechaza."""
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)

        response = _advance(client, buyer_token, sub_order.id, SubOrderStatus.CONFIRMED.value)

        assert response.status_code == 403

    def test_an_anonymous_visitor_is_rejected(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        sub_order = _place_order(client, session, auth_headers, buyer, product_variant)

        response = client.patch(
            f"{API}/orders/sub-orders/{sub_order.id}/status",
            json={"status": SubOrderStatus.CONFIRMED.value},
        )

        assert response.status_code == 401

    def test_advancing_an_order_that_does_not_exist_gives_404(
        self, client: TestClient, producer: ProducerProfile, producer_token: str
    ) -> None:
        response = _advance(client, producer_token, uuid.uuid4(), SubOrderStatus.CONFIRMED.value)

        assert response.status_code == 404
