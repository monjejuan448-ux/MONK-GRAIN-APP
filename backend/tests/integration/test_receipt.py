"""Pruebas del comprobante del pedido (HU-CC-11).

El comprobante es la constancia de la relación de consumo. Lo que se verifica
aquí es que salga un PDF de verdad, que lleve lo que la ley exige que lleve, y
que solo lo descargue quien tiene derecho a hacerlo.
"""

import re
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import ProductVariant
from app.models.order import Order
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
) -> Order:
    client.post(
        f"{API}/cart/items",
        json={"variant_id": str(variant.id), "quantity": 2},
        headers=headers,
    )
    address = session.scalar(select(Address).where(Address.user_id == buyer.id))
    assert address is not None

    response = client.post(
        f"{API}/orders",
        json={
            "shipping_address_id": str(address.id),
            "accept_terms": True,
            "customer_notes": "Dejar en portería si no hay nadie.",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    order = session.scalar(select(Order))
    assert order is not None
    return order


def _text_of(pdf_bytes: bytes) -> str:
    """Texto plano del PDF, con los espacios normalizados.

    WeasyPrint reparte el texto en fragmentos posicionados, así que comparar
    cadenas literales exige colapsar los saltos de línea.
    """
    reader = PdfReader(__import__("io").BytesIO(pdf_bytes))
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    return re.sub(r"\s+", " ", raw)


@pytest.fixture
def order(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
    buyer: User,
    product_variant: ProductVariant,
) -> Order:
    return _place_order(client, session, auth_headers, buyer, product_variant)


class TestReceipt:
    def test_the_response_is_a_pdf_attachment(
        self, client: TestClient, auth_headers: dict[str, str], order: Order
    ) -> None:
        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        # `attachment` fuerza la descarga: el PDF no se abre dentro del dominio
        # de la API.
        assert "attachment" in response.headers["content-disposition"]
        assert order.order_number in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF-")

    def test_it_carries_everything_the_story_requires(
        self, client: TestClient, auth_headers: dict[str, str], order: Order, buyer: User
    ) -> None:
        """HU-CC-11, CA1: número, fecha, vendedor, ítems, totales y entrega."""
        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)
        text = _text_of(response.content)

        assert order.order_number in text
        assert buyer.full_name in text
        assert "Pergamino de Prueba" in text  # nombre congelado del producto
        # Presentación congelada. El lote de prueba se vende desde 1 kg, así que
        # la etiqueta es solo la presentación, sin la coletilla del mínimo.
        assert "A granel, en costal de fique" in text
        assert "Calle 10 # 5-20" in text  # dirección de entrega
        assert "Pitalito, Huila" in text  # municipio y departamento resueltos
        assert "Total COP" in text
        assert "Dejar en portería" in text  # notas del comprador

    def test_the_amounts_are_the_ones_charged(
        self, client: TestClient, auth_headers: dict[str, str], order: Order
    ) -> None:
        """Dos unidades de 40.000 más el envío."""
        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)
        text = _text_of(response.content)

        assert order.subtotal == Decimal("80000.00")
        assert "$ 80.000" in text
        assert f"$ {int(order.grand_total):,}".replace(",", ".") in text

    def test_it_identifies_the_seller_for_a_future_claim(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        order: Order,
        producer: ProducerProfile,
    ) -> None:
        """Artículo 53 de la Ley 1480: contra quién se reclama.

        Estos datos no salen en ningún endpoint público. Aquí sí, porque el
        comprobante solo lo recibe quien contrató con ese vendedor.
        """
        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)
        text = _text_of(response.content)

        assert producer.legal_name in text
        assert producer.document_number in text
        assert producer.notification_address is not None
        assert producer.notification_address in text
        assert producer.contact_phone is not None
        assert producer.contact_phone in text

    def test_it_says_it_is_not_an_invoice(
        self, client: TestClient, auth_headers: dict[str, str], order: Order
    ) -> None:
        """La factura electrónica la expide el vendedor ante la DIAN.

        Sin esta advertencia alguien podría presentar el comprobante como
        soporte tributario.
        """
        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)
        text = _text_of(response.content)

        assert "no es una factura" in text
        assert "DIAN" in text

    def test_it_declares_the_simulated_payment(
        self, client: TestClient, auth_headers: dict[str, str], order: Order
    ) -> None:
        """Un comprobante que lo callara sugeriría un cobro que no ocurrió."""
        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)
        text = _text_of(response.content)

        assert "simulado" in text
        assert "no se realizó ningún cobro real" in text

    def test_it_states_the_buyer_rights(
        self, client: TestClient, auth_headers: dict[str, str], order: Order
    ) -> None:
        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)
        text = _text_of(response.content)

        assert "retractarte" in text
        assert "garantía legal" in text
        assert "Superintendencia de Industria y Comercio" in text

    def test_user_content_cannot_inject_markup(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        order: Order,
    ) -> None:
        """Las notas del comprador son texto, no marcado.

        El nombre de un café o una nota de entrega los escribe un usuario. Sin
        autoescapado podrían alterar la estructura del documento.
        """
        order.customer_notes = "<style>body{display:none}</style>Entregar en la mañana"
        session.flush()

        response = client.get(f"{API}/orders/{order.id}/receipt", headers=auth_headers)
        text = _text_of(response.content)

        # La etiqueta se imprime como texto y no surte efecto: el resto del
        # documento sigue visible.
        assert "Entregar en la mañana" in text
        assert order.order_number in text
        assert "Total COP" in text


class TestReceiptAuthorization:
    def test_someone_elses_order_is_refused(
        self, client: TestClient, producer_token: str, order: Order
    ) -> None:
        """HU-CC-11, CA2."""
        response = client.get(
            f"{API}/orders/{order.id}/receipt",
            headers={"Authorization": f"Bearer {producer_token}"},
        )
        assert response.status_code == 403

    def test_it_requires_a_session(self, client: TestClient, order: Order) -> None:
        assert client.get(f"{API}/orders/{order.id}/receipt").status_code == 401

    def test_an_unknown_order_is_not_found(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get(
            f"{API}/orders/00000000-0000-0000-0000-000000000000/receipt",
            headers=auth_headers,
        )
        assert response.status_code == 404
