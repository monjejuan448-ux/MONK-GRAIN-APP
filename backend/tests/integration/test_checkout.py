"""Pruebas del flujo de compra.

El checkout es la operación más delicada del sistema: divide el pedido por
vendedor, reserva inventario y calcula comisiones dentro de una sola
transacción. Estas pruebas verifican tanto el camino feliz como los que deben
fallar sin dejar rastro.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Inventory, ProductVariant
from app.models.enums import PaymentStatus, SubOrderStatus
from app.models.geo import Municipality
from app.models.order import Order, SubOrder
from app.models.payment import Commission, Payment
from app.models.user import Address, User

pytestmark = pytest.mark.integration

API = "/api/v1"


def _add_to_cart(
    client: TestClient, headers: dict[str, str], variant_id: str, quantity: int = 1
) -> None:
    response = client.post(
        f"{API}/cart/items",
        json={"variant_id": variant_id, "quantity": quantity},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def _default_address(session: Session, buyer: User) -> Address:
    address = session.scalar(select(Address).where(Address.user_id == buyer.id))
    assert address is not None
    return address


class TestCartOperations:
    def test_add_item_returns_cart_grouped_by_seller(
        self, client: TestClient, auth_headers: dict[str, str], product_variant: ProductVariant
    ) -> None:
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(product_variant.id), "quantity": 2},
            headers=auth_headers,
        )

        assert response.status_code == 201
        cart = response.json()
        assert cart["item_count"] == 2
        assert len(cart["groups"]) == 1
        assert Decimal(cart["subtotal"]) == Decimal("80000")

    def test_cannot_add_more_than_available_stock(
        self, client: TestClient, auth_headers: dict[str, str], product_variant: ProductVariant
    ) -> None:
        """El carrito no admite más unidades de las que hay (HU-CC-05, CA4)."""
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(product_variant.id), "quantity": 99},
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "business_rule_violation"

    def test_adding_same_variant_twice_sums_quantity(
        self, client: TestClient, auth_headers: dict[str, str], product_variant: ProductVariant
    ) -> None:
        """Agregar de nuevo suma a la línea existente en vez de duplicarla."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 2)
        _add_to_cart(client, auth_headers, str(product_variant.id), 3)

        cart = client.get(f"{API}/cart", headers=auth_headers).json()
        assert cart["item_count"] == 5
        assert len(cart["groups"][0]["items"]) == 1

    def test_cart_requires_authentication(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        response = client.post(
            f"{API}/cart/items",
            json={"variant_id": str(product_variant.id), "quantity": 1},
        )
        assert response.status_code == 401


class TestCheckout:
    def test_checkout_creates_order_with_reserved_stock(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """El checkout reserva stock sin descontarlo todavía."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 2)
        address = _default_address(session, buyer)

        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        order = response.json()["order"]
        assert order["status"] == "pending"
        assert len(order["sub_orders"]) == 1

        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        # El stock sigue intacto; lo comprometido son las reservas.
        assert inventory.stock_qty == 10
        assert inventory.reserved_qty == 2
        assert inventory.available_qty == 8

    def test_multi_seller_cart_splits_into_sub_orders(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        second_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """Un carrito con dos vendedores genera dos sub-órdenes (ADR-02)."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 1)
        _add_to_cart(client, auth_headers, str(second_variant.id), 1)
        address = _default_address(session, buyer)

        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )

        assert response.status_code == 201
        order = response.json()["order"]
        assert len(order["sub_orders"]) == 2

        # Cada sub-orden lleva su propio número derivado del pedido principal.
        numbers = {sub["sub_order_number"] for sub in order["sub_orders"]}
        assert numbers == {f"{order['order_number']}-1", f"{order['order_number']}-2"}

        producers = {sub["producer_id"] for sub in order["sub_orders"]}
        assert len(producers) == 2

    def test_checkout_requires_accepting_terms(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """Sin aceptar los términos no se crea el pedido (HU-CC-07, CA4)."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 1)
        address = _default_address(session, buyer)

        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": False},
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert session.scalar(select(Order)) is None

    def test_empty_cart_cannot_checkout(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        session: Session,
    ) -> None:
        address = _default_address(session, buyer)

        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert "carrito está vacío" in response.json()["error"]["message"]

    def test_checkout_with_foreign_address_is_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        producer,  # noqa: ANN001 — fixture que crea otro usuario
        geography: Municipality,
        session: Session,
    ) -> None:
        """No se puede enviar a la dirección de otra persona."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 1)

        other_user = session.get(User, producer.user_id)
        assert other_user is not None
        foreign = Address(
            user_id=other_user.id,
            recipient_name="Otro",
            phone="3009999999",
            department_id=geography.department_id,
            municipality_id=geography.id,
            street_address="Calle ajena 1-1",
        )
        session.add(foreign)
        session.flush()

        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(foreign.id), "accept_terms": True},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_checkout_empties_the_cart(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        _add_to_cart(client, auth_headers, str(product_variant.id), 1)
        address = _default_address(session, buyer)

        client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )

        cart = client.get(f"{API}/cart", headers=auth_headers).json()
        assert cart["item_count"] == 0

    def test_commission_is_calculated_and_frozen(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """La comisión se guarda con la tasa aplicada (HU-ADM-05, CA2)."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 2)
        address = _default_address(session, buyer)

        client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )

        commission = session.scalar(select(Commission))
        assert commission is not None
        assert commission.base_amount == Decimal("80000.00")
        assert commission.commission_amount == commission.base_amount * commission.rate_applied

        sub_order = session.scalar(select(SubOrder))
        assert sub_order is not None
        assert sub_order.net_amount == sub_order.subtotal - sub_order.commission_amount

    def test_address_snapshot_survives_address_deletion(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """El pedido conserva a dónde se envió aunque se borre la dirección."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 1)
        address = _default_address(session, buyer)

        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )
        order_id = response.json()["order"]["id"]

        client.delete(f"{API}/users/me/addresses/{address.id}", headers=auth_headers)

        detail = client.get(f"{API}/orders/{order_id}", headers=auth_headers).json()
        assert detail["shipping_address"]["street_address"] == "Calle 10 # 5-20"


class TestPaymentConfirmation:
    def test_approved_payment_converts_reservation_into_stock_deduction(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        from app.modules.orders.service import OrderService

        _add_to_cart(client, auth_headers, str(product_variant.id), 3)
        address = _default_address(session, buyer)
        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )
        reference = response.json()["payment_reference"]

        OrderService(session).confirm_payment(reference, approved=True)

        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        assert inventory.stock_qty == 7  # descontado de verdad
        assert inventory.reserved_qty == 0

        sub_order = session.scalar(select(SubOrder))
        assert sub_order is not None
        assert sub_order.status == SubOrderStatus.CONFIRMED

    def test_declined_payment_releases_reserved_stock(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """Un pago rechazado devuelve el stock al catálogo."""
        from app.modules.orders.service import OrderService

        _add_to_cart(client, auth_headers, str(product_variant.id), 3)
        address = _default_address(session, buyer)
        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )
        reference = response.json()["payment_reference"]

        OrderService(session).confirm_payment(reference, approved=False)

        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        assert inventory.stock_qty == 10  # intacto
        assert inventory.reserved_qty == 0  # liberado

        sub_order = session.scalar(select(SubOrder))
        assert sub_order is not None
        assert sub_order.status == SubOrderStatus.CANCELLED

    def test_confirming_twice_is_idempotent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """Reprocesar el mismo webhook no descuenta el stock dos veces."""
        from app.modules.orders.service import OrderService

        _add_to_cart(client, auth_headers, str(product_variant.id), 2)
        address = _default_address(session, buyer)
        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )
        reference = response.json()["payment_reference"]

        service = OrderService(session)
        service.confirm_payment(reference, approved=True)
        service.confirm_payment(reference, approved=True)

        inventory = session.get(Inventory, product_variant.id)
        assert inventory is not None
        assert inventory.stock_qty == 8  # descontado una sola vez

        payment = session.scalar(select(Payment))
        assert payment is not None
        assert payment.status == PaymentStatus.APPROVED


class TestOrderVisibility:
    def test_buyer_cannot_read_someone_elses_order(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        producer_token: str,
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """Un pedido solo lo consulta su comprador (o un administrador)."""
        _add_to_cart(client, auth_headers, str(product_variant.id), 1)
        address = _default_address(session, buyer)
        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )
        order_id = response.json()["order"]["id"]

        foreign = client.get(
            f"{API}/orders/{order_id}",
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert foreign.status_code == 403


class TestConcurrentCheckout:
    """Regresión del defecto de numeración concurrente (auditoría, HALLAZGO-01).

    El número de pedido se calculaba con `SELECT count(*) + 1`. Dos checkouts
    simultáneos leían el mismo total y producían el mismo número: la restricción
    `UNIQUE` hacía fallar a uno de los dos, de modo que dos compradores sin
    relación entre sí chocaban por pagar a la vez. Cuando las peticiones se
    escalonaban lo justo para leer conteos distintos, la colisión no ocurría y se
    creaba un pedido duplicado.
    """

    def test_order_numbers_are_unique_without_intermediate_commits(self, session: Session) -> None:
        """Números consecutivos deben diferir aunque no se haya insertado nada.

        Es la prueba directa del defecto: `count(*) + 1` devuelve el mismo valor
        en cada llamada mientras no haya un pedido nuevo confirmado, mientras que
        `nextval` avanza siempre.
        """
        from app.modules.orders.service import OrderService

        service = OrderService(session)
        numbers = [service._generate_order_number() for _ in range(5)]

        assert len(set(numbers)) == 5, (
            f"La numeración repitió valores: {numbers}. "
            "Debe apoyarse en una secuencia, no en un conteo de filas."
        )

    def test_double_submit_does_not_create_two_orders(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        product_variant: ProductVariant,
        buyer: User,
        session: Session,
    ) -> None:
        """El doble clic en «Pagar» debe producir un único pedido.

        La segunda petición encuentra el carrito ya vacío y se rechaza como
        regla de negocio, no como error técnico.

        Alcance real de esta prueba: `TestClient` envía las peticiones una tras
        otra, así que cubre el caso secuencial —la segunda llega cuando la
        primera ya vació el carrito— pero **no** ejercita el bloqueo por usuario,
        que solo entra en juego con peticiones verdaderamente simultáneas. La
        concurrencia se verificó contra el entorno en ejecución: cinco rondas de
        dos checkouts en paralelo produjeron un único pedido cada una.
        """
        _add_to_cart(client, auth_headers, str(product_variant.id), 1)
        address = _default_address(session, buyer)
        payload = {"shipping_address_id": str(address.id), "accept_terms": True}

        first = client.post(f"{API}/orders", json=payload, headers=auth_headers)
        second = client.post(f"{API}/orders", json=payload, headers=auth_headers)

        assert first.status_code == 201
        assert second.status_code == 422
        assert "carrito" in second.json()["error"]["message"].lower()

        orders = session.scalars(select(Order).where(Order.user_id == buyer.id)).all()
        assert len(orders) == 1, "El doble envío creó pedidos duplicados."
