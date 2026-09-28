"""Pruebas del flujo de devoluciones.

Lo que se verifica aquí no es que los endpoints respondan, sino que respeten las
reglas de las que dependen derechos concretos: el plazo del retracto, el importe
íntegro del reembolso, la obligación de motivar el rechazo y la imposibilidad de
que un vendedor lea o resuelva la reclamación de otro.
"""

import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_days import add_business_days
from app.models.catalog import Inventory, ProductVariant
from app.models.enums import (
    CommissionStatus,
    OrderStatus,
    PaymentStatus,
    SubOrderStatus,
)
from app.models.order import Order, SubOrder
from app.models.payment import Commission, Payment
from app.models.producer import ProducerProfile
from app.models.shipment import Return
from app.models.user import Address, User

pytestmark = pytest.mark.integration

API = "/api/v1"


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _deliver_order(
    client: TestClient,
    session: Session,
    buyer_headers: dict[str, str],
    producer_headers: dict[str, str],
    buyer: User,
    variant: ProductVariant,
    quantity: int = 2,
) -> SubOrder:
    """Lleva un pedido hasta la entrega, que es donde empiezan los plazos."""
    from app.modules.orders.service import OrderService

    client.post(
        f"{API}/cart/items",
        json={"variant_id": str(variant.id), "quantity": quantity},
        headers=buyer_headers,
    )
    address = session.scalar(select(Address).where(Address.user_id == buyer.id))
    assert address is not None

    checkout = client.post(
        f"{API}/orders",
        json={"shipping_address_id": str(address.id), "accept_terms": True},
        headers=buyer_headers,
    )
    assert checkout.status_code == 201, checkout.text
    OrderService(session).confirm_payment(checkout.json()["payment_reference"], approved=True)

    sub_order = session.scalar(select(SubOrder))
    assert sub_order is not None

    for status in ("prepared", "shipped", "delivered"):
        response = client.patch(
            f"{API}/orders/sub-orders/{sub_order.id}/status",
            json={"status": status},
            headers=producer_headers,
        )
        assert response.status_code == 200, response.text

    session.refresh(sub_order)
    return sub_order


@pytest.fixture
def producer_headers(producer_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {producer_token}"}


@pytest.fixture
def delivered_sub_order(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
    producer_headers: dict[str, str],
    buyer: User,
    product_variant: ProductVariant,
) -> SubOrder:
    return _deliver_order(client, session, auth_headers, producer_headers, buyer, product_variant)


def _request_return(
    client: TestClient,
    headers: dict[str, str],
    sub_order: SubOrder,
    *,
    reason: str,
    quantity: int = 2,
    description: str | None = "El café llegó con el empaque roto y mojado.",
    declared_unopened: bool = False,
) -> dict:
    eligibility = client.get(
        f"{API}/orders/sub-orders/{sub_order.id}/return-eligibility", headers=headers
    )
    assert eligibility.status_code == 200, eligibility.text
    item_id = eligibility.json()["items"][0]["order_item_id"]

    response = client.post(
        f"{API}/returns",
        json={
            "sub_order_id": str(sub_order.id),
            "reason": reason,
            "description": description,
            "declared_unopened": declared_unopened,
            "items": [{"order_item_id": item_id, "quantity": quantity}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


# ----------------------------------------------------------------------
# Elegibilidad y plazos
# ----------------------------------------------------------------------
class TestEligibility:
    def test_delivered_order_offers_withdrawal_and_warranty(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """Recién entregado, siguen vivas las dos figuras."""
        response = client.get(
            f"{API}/orders/sub-orders/{delivered_sub_order.id}/return-eligibility",
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["can_request"] is True
        assert "withdrawal" in body["allowed_reasons"]
        assert "damaged" in body["allowed_reasons"]
        assert body["items"][0]["returnable_qty"] == 2

    def test_withdrawal_deadline_counts_business_days_from_delivery(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        delivered_sub_order: SubOrder,
        session: Session,
    ) -> None:
        """El plazo del artículo 47 son cinco días hábiles, no cinco corridos."""
        response = client.get(
            f"{API}/orders/sub-orders/{delivered_sub_order.id}/return-eligibility",
            headers=auth_headers,
        )
        body = response.json()

        delivered_day = datetime.fromisoformat(body["delivered_at"]).astimezone(UTC).date()
        assert body["withdrawal_deadline"] == add_business_days(delivered_day, 5).isoformat()

    def test_undispatched_order_points_to_cancellation_instead(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Antes del despacho no se devuelve: se cancela, y sin costo."""
        client.post(
            f"{API}/cart/items",
            json={"variant_id": str(product_variant.id), "quantity": 1},
            headers=auth_headers,
        )
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None
        client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )
        sub_order = session.scalar(select(SubOrder))
        assert sub_order is not None

        response = client.get(
            f"{API}/orders/sub-orders/{sub_order.id}/return-eligibility", headers=auth_headers
        )

        assert response.json()["can_request"] is False
        assert "cancelarlo sin costo" in response.json()["blocked_reason"]

    def test_another_buyer_cannot_inspect_the_order(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """La elegibilidad la consulta el comprador, no cualquiera con el identificador."""
        response = client.get(
            f"{API}/orders/sub-orders/{delivered_sub_order.id}/return-eligibility",
            headers=producer_headers,
        )
        assert response.status_code == 403


# ----------------------------------------------------------------------
# Radicación
# ----------------------------------------------------------------------
class TestRequest:
    def test_filing_returns_a_receipt_with_number_and_timestamp(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """La constancia es lo que el comprador lleva a la Superintendencia."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        assert body["return_number"].startswith("DEV-")
        assert body["filed_at"] is not None
        assert body["status"] == "requested"
        assert body["reason_label"] == "producto dañado"

    def test_refund_covers_the_full_price_paid(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """Devolver todo el pedido reembolsa producto y envío, sin retenciones."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        expected = delivered_sub_order.subtotal + delivered_sub_order.shipping_cost
        assert Decimal(body["refund_amount"]) == expected

    def test_partial_return_does_not_refund_the_shipping(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """Si el comprador se queda con parte, el transporte ya se prestó."""
        body = _request_return(
            client, auth_headers, delivered_sub_order, reason="damaged", quantity=1
        )

        assert Decimal(body["refund_amount"]) == Decimal("40000")

    def test_seller_pays_return_shipping_when_the_fault_is_theirs(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """Numeral 1 del artículo 11: el defecto lo transporta quien vende."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        assert body["return_shipping_paid_by_seller"] is True

    def test_buyer_pays_return_shipping_on_withdrawal(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """Artículo 47: en el retracto el transporte corre por cuenta del comprador."""
        body = _request_return(
            client,
            auth_headers,
            delivered_sub_order,
            reason="withdrawal",
            description=None,
            declared_unopened=True,
        )
        assert body["return_shipping_paid_by_seller"] is False

    def test_withdrawal_requires_declaring_the_package_sealed(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """Una bolsa de café abierta no puede volver a venderse."""
        eligibility = client.get(
            f"{API}/orders/sub-orders/{delivered_sub_order.id}/return-eligibility",
            headers=auth_headers,
        ).json()

        response = client.post(
            f"{API}/returns",
            json={
                "sub_order_id": str(delivered_sub_order.id),
                "reason": "withdrawal",
                "declared_unopened": False,
                "items": [
                    {"order_item_id": eligibility["items"][0]["order_item_id"], "quantity": 1}
                ],
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert "sellado" in response.text

    def test_warranty_claim_requires_telling_what_happened(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        eligibility = client.get(
            f"{API}/orders/sub-orders/{delivered_sub_order.id}/return-eligibility",
            headers=auth_headers,
        ).json()

        response = client.post(
            f"{API}/returns",
            json={
                "sub_order_id": str(delivered_sub_order.id),
                "reason": "quality",
                "items": [
                    {"order_item_id": eligibility["items"][0]["order_item_id"], "quantity": 1}
                ],
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_the_deadlines_are_recorded_when_filing(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Quince días hábiles para responder; treinta calendario para el retracto."""
        today = datetime.now(UTC).date()
        body = _request_return(
            client,
            auth_headers,
            delivered_sub_order,
            reason="withdrawal",
            description=None,
            declared_unopened=True,
        )

        assert body["response_due_at"] == add_business_days(today, 15).isoformat()
        assert body["refund_due_at"] == (today + timedelta(days=30)).isoformat()

    def test_cannot_return_more_units_than_purchased(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        eligibility = client.get(
            f"{API}/orders/sub-orders/{delivered_sub_order.id}/return-eligibility",
            headers=auth_headers,
        ).json()

        response = client.post(
            f"{API}/returns",
            json={
                "sub_order_id": str(delivered_sub_order.id),
                "reason": "damaged",
                "description": "Llegaron mal las dos bolsas.",
                "items": [
                    {"order_item_id": eligibility["items"][0]["order_item_id"], "quantity": 99}
                ],
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert "solo puedes devolver" in response.text

    def test_units_already_claimed_cannot_be_claimed_again(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """Dos solicitudes sobre la misma unidad duplicarían el reembolso."""
        _request_return(client, auth_headers, delivered_sub_order, reason="damaged", quantity=2)

        eligibility = client.get(
            f"{API}/orders/sub-orders/{delivered_sub_order.id}/return-eligibility",
            headers=auth_headers,
        ).json()

        assert eligibility["can_request"] is False
        assert eligibility["items"][0]["returnable_qty"] == 0


# ----------------------------------------------------------------------
# Resolución y reembolso
# ----------------------------------------------------------------------
class TestResolution:
    def test_rejection_must_be_reasoned(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Sin motivos no hay respuesta escrita que valga (Decreto 735 de 2013)."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        response = client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": False, "resolution_notes": "no"},
            headers=producer_headers,
        )

        assert response.status_code == 422

    def test_full_cycle_refunds_and_closes_the_order(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Aprobar, recibir y reembolsar deja el pedido y el pago cerrados."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        return_id = body["id"]

        approved = client.post(
            f"{API}/producer/returns/{return_id}/resolution",
            json={
                "approve": True,
                "resolution_notes": "Verificamos las fotos: el empaque llegó roto.",
            },
            headers=producer_headers,
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        client.post(f"{API}/returns/{return_id}/shipped", headers=auth_headers)
        client.post(f"{API}/producer/returns/{return_id}/received", headers=producer_headers)
        refunded = client.post(
            f"{API}/producer/returns/{return_id}/refund", headers=producer_headers
        )

        assert refunded.status_code == 200
        assert refunded.json()["status"] == "refunded"
        assert refunded.json()["refunded_at"] is not None

        session.expire_all()
        sub_order = session.get(SubOrder, delivered_sub_order.id)
        assert sub_order is not None
        assert sub_order.status == SubOrderStatus.REFUNDED

        order = session.get(Order, sub_order.order_id)
        assert order is not None
        assert order.status == OrderStatus.REFUNDED

        payment = session.scalar(select(Payment).where(Payment.order_id == order.id))
        assert payment is not None
        assert payment.status == PaymentStatus.REFUNDED

    def test_defective_coffee_does_not_return_to_the_catalogue(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
        product_variant: ProductVariant,
    ) -> None:
        """Un café que llegó dañado no puede volver al escaparate."""
        before = session.get(Inventory, product_variant.id)
        assert before is not None
        stock_before = before.stock_qty

        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": True, "resolution_notes": "Procede la garantía por el empaque."},
            headers=producer_headers,
        )
        client.post(f"{API}/producer/returns/{body['id']}/refund", headers=producer_headers)

        session.expire_all()
        after = session.get(Inventory, product_variant.id)
        assert after is not None
        assert after.stock_qty == stock_before

    def test_withdrawn_coffee_goes_back_to_stock(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
        product_variant: ProductVariant,
    ) -> None:
        """Una bolsa sellada y dentro de su vida útil sí vuelve al inventario."""
        before = session.get(Inventory, product_variant.id)
        assert before is not None
        stock_before = before.stock_qty

        body = _request_return(
            client,
            auth_headers,
            delivered_sub_order,
            reason="withdrawal",
            description=None,
            declared_unopened=True,
        )
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": True, "resolution_notes": "Retracto dentro del plazo legal."},
            headers=producer_headers,
        )
        client.post(f"{API}/producer/returns/{body['id']}/refund", headers=producer_headers)

        session.expire_all()
        after = session.get(Inventory, product_variant.id)
        assert after is not None
        assert after.stock_qty == stock_before + 2

    def test_commission_drops_by_what_was_returned(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Nadie paga comisión sobre dinero que ya reintegró."""
        body = _request_return(
            client, auth_headers, delivered_sub_order, reason="damaged", quantity=1
        )
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": True, "resolution_notes": "Procede: una bolsa llegó rota."},
            headers=producer_headers,
        )
        client.post(f"{API}/producer/returns/{body['id']}/refund", headers=producer_headers)

        session.expire_all()
        commission = session.scalar(
            select(Commission).where(Commission.sub_order_id == delivered_sub_order.id)
        )
        assert commission is not None
        # Se compraron dos bolsas de 40.000 y se devolvió una.
        assert commission.base_amount == Decimal("40000.00")
        assert commission.status == CommissionStatus.PENDING

    def test_full_refund_reverses_the_commission(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": True, "resolution_notes": "Procede la garantía en su totalidad."},
            headers=producer_headers,
        )
        client.post(f"{API}/producer/returns/{body['id']}/refund", headers=producer_headers)

        session.expire_all()
        commission = session.scalar(
            select(Commission).where(Commission.sub_order_id == delivered_sub_order.id)
        )
        assert commission is not None
        assert commission.base_amount == Decimal("0.00")
        assert commission.status == CommissionStatus.REVERSED

    def test_rejected_return_is_terminal(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Rechazada, no se reabre: el camino que queda es la Superintendencia."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="quality")
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={
                "approve": False,
                "resolution_notes": "El café corresponde a la variedad y el proceso publicados.",
            },
            headers=producer_headers,
        )

        response = client.post(
            f"{API}/producer/returns/{body['id']}/refund", headers=producer_headers
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_state_transition"

    def test_cannot_refund_before_resolving(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        response = client.post(
            f"{API}/producer/returns/{body['id']}/refund", headers=producer_headers
        )
        assert response.status_code == 422


# ----------------------------------------------------------------------
# Evidencia
# ----------------------------------------------------------------------
def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (900, 700), "sienna").save(buffer, format="JPEG")
    return buffer.getvalue()


class TestEvidence:
    def test_uploaded_photo_comes_back_in_the_receipt(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """La constancia debe mostrar la fotografía recién adjuntada.

        La solicitud ya está en el mapa de identidad de la sesión, así que sin
        `populate_existing` SQLAlchemy devolvía el objeto en memoria —con su
        colección de evidencias vacía— y la respuesta salía sin la foto que se
        acababa de guardar.
        """
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        response = client.post(
            f"{API}/returns/{body['id']}/evidence",
            files={"files": ("empaque.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        evidences = response.json()["evidences"]
        assert len(evidences) == 1
        # Se reescribe como JPEG: garantiza que lo guardado es una imagen.
        assert evidences[0]["content_type"] == "image/jpeg"
        assert evidences[0]["url"]

    def test_photos_are_stored_outside_the_public_prefixes(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Son fotos tomadas en casa del comprador: no cuelgan del escaparate."""
        from app.integrations.storage.base import is_public
        from app.models.shipment import ReturnEvidence

        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        client.post(
            f"{API}/returns/{body['id']}/evidence",
            files={"files": ("empaque.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=auth_headers,
        )

        stored = session.scalar(select(ReturnEvidence))
        assert stored is not None
        assert not is_public(stored.file_key)
        assert stored.file_key.startswith("returns/")

    def test_a_file_that_is_not_an_image_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        """La extensión y el `Content-Type` los declara quien envía; el contenido no."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        response = client.post(
            f"{API}/returns/{body['id']}/evidence",
            files={"files": ("foto.jpg", b"<?php system($_GET['c']); ?>", "image/jpeg")},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_a_closed_return_takes_no_more_attachments(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        body = _request_return(client, auth_headers, delivered_sub_order, reason="quality")
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": False, "resolution_notes": "El café corresponde a lo publicado."},
            headers=producer_headers,
        )

        response = client.post(
            f"{API}/returns/{body['id']}/evidence",
            files={"files": ("empaque.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=auth_headers,
        )

        assert response.status_code == 422


# ----------------------------------------------------------------------
# Autorización
# ----------------------------------------------------------------------
class TestAccessControl:
    def test_a_different_seller_cannot_read_or_resolve(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
        second_producer: ProducerProfile,
    ) -> None:
        """La reclamación de un vendedor no la ve —ni resuelve— otro."""
        from tests.integration.conftest import TEST_PASSWORD

        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        other_user = session.get(User, second_producer.user_id)
        assert other_user is not None
        token = client.post(
            f"{API}/auth/login", json={"email": other_user.email, "password": TEST_PASSWORD}
        ).json()["access_token"]
        intruder = {"Authorization": f"Bearer {token}"}

        assert client.get(f"{API}/returns/{body['id']}", headers=intruder).status_code == 403
        assert (
            client.post(
                f"{API}/producer/returns/{body['id']}/resolution",
                json={"approve": True, "resolution_notes": "Aprobado sin ser mío."},
                headers=intruder,
            ).status_code
            == 403
        )
        assert (
            client.post(f"{API}/producer/returns/{body['id']}/refund", headers=intruder).status_code
            == 403
        )

    def test_the_seller_cannot_declare_the_return_shipped(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Solo el comprador sabe si entregó el paquete al transportador."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": True, "resolution_notes": "Procede la garantía."},
            headers=producer_headers,
        )

        response = client.post(f"{API}/returns/{body['id']}/shipped", headers=producer_headers)
        assert response.status_code == 403

    def test_anonymous_access_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        assert client.get(f"{API}/returns/{body['id']}").status_code == 401
        assert client.get(f"{API}/returns").status_code == 401

    def test_available_actions_depend_on_who_is_asking(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """El servidor dice qué puede hacer cada uno; la interfaz solo lo pinta."""
        body = _request_return(client, auth_headers, delivered_sub_order, reason="damaged")
        client.post(
            f"{API}/producer/returns/{body['id']}/resolution",
            json={"approve": True, "resolution_notes": "Procede la garantía."},
            headers=producer_headers,
        )

        buyer_view = client.get(f"{API}/returns/{body['id']}", headers=auth_headers).json()
        seller_view = client.get(f"{API}/returns/{body['id']}", headers=producer_headers).json()

        assert buyer_view["available_actions"] == ["in_transit"]
        assert "in_transit" not in seller_view["available_actions"]
        assert "refunded" in seller_view["available_actions"]


# ----------------------------------------------------------------------
# Listados
# ----------------------------------------------------------------------
class TestListing:
    def test_buyer_only_sees_their_own_returns(
        self, client: TestClient, auth_headers: dict[str, str], delivered_sub_order: SubOrder
    ) -> None:
        _request_return(client, auth_headers, delivered_sub_order, reason="damaged")

        response = client.get(f"{API}/returns", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["item_count"] == 2

    def test_seller_list_is_ordered_by_deadline(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        delivered_sub_order: SubOrder,
    ) -> None:
        """Primero lo que vence antes: la lista es el orden en que hay que responder."""
        first = _request_return(
            client, auth_headers, delivered_sub_order, reason="damaged", quantity=1
        )
        stored = session.get(Return, first["id"])
        assert stored is not None
        stored.response_due_at = stored.response_due_at + timedelta(days=10)
        session.flush()

        second = _request_return(
            client, auth_headers, delivered_sub_order, reason="quality", quantity=1
        )

        response = client.get(f"{API}/producer/returns", headers=producer_headers)

        assert response.status_code == 200
        numbers = [item["return_number"] for item in response.json()["items"]]
        assert numbers == [second["return_number"], first["return_number"]]
