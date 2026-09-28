"""Pruebas de las reseñas.

Una reseña vale por lo que acredita. Lo que se verifica aquí es precisamente
eso: que nadie reseñe un café que no compró, que no lo reseñe dos veces por la
misma compra, que el promedio del café y el del productor sigan al día, y que
reportar una reseña no sirva para silenciarla.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Product, ProductVariant, Review, ReviewReport
from app.models.enums import ReviewStatus, RoleCode, UserStatus
from app.models.order import OrderItem, SubOrder
from app.models.producer import ProducerProfile
from app.models.user import Address, Role, User, UserRole

pytestmark = pytest.mark.integration

API = "/api/v1"


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _deliver(
    client: TestClient,
    session: Session,
    buyer_headers: dict[str, str],
    producer_headers: dict[str, str],
    buyer: User,
    variant: ProductVariant,
    quantity: int = 1,
) -> SubOrder:
    """Lleva un pedido hasta la entrega, que es cuando se puede reseñar."""
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
def delivered_item(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
    producer_headers: dict[str, str],
    buyer: User,
    product_variant: ProductVariant,
) -> OrderItem:
    sub_order = _deliver(client, session, auth_headers, producer_headers, buyer, product_variant)
    return sub_order.items[0]


def _login_new_user(
    client: TestClient,
    session: Session,
    roles: dict[str, Role],
    *,
    email: str,
    full_name: str,
    role: RoleCode,
) -> dict[str, str]:
    """Crea una cuenta con un rol y devuelve su cabecera de autorización.

    Se crea un usuario nuevo en vez de añadirle un rol al comprador existente:
    ese usuario ya está en el mapa de identidad de la sesión con su colección de
    roles cargada, y añadirle uno no la refresca, así que el endpoint seguiría
    viéndolo sin el rol.
    """
    from app.core.security import hash_password
    from tests.integration.conftest import TEST_PASSWORD

    user = User(
        email=email,
        password_hash=hash_password(TEST_PASSWORD),
        full_name=full_name,
        status=UserStatus.ACTIVE,
        data_consent=True,
        data_consent_at=datetime.now(UTC),
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[role.value].id))
    session.flush()

    response = client.post(f"{API}/auth/login", json={"email": email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def other_buyer_headers(
    client: TestClient, session: Session, roles: dict[str, Role]
) -> dict[str, str]:
    """Segundo comprador, para probar el reporte de una reseña ajena."""
    return _login_new_user(
        client,
        session,
        roles,
        email="otro.comprador@prueba.co",
        full_name="Otro Comprador",
        role=RoleCode.CONSUMER,
    )


@pytest.fixture
def admin_headers(client: TestClient, session: Session, roles: dict[str, Role]) -> dict[str, str]:
    return _login_new_user(
        client,
        session,
        roles,
        email="moderador@prueba.co",
        full_name="Moderador de Prueba",
        role=RoleCode.ADMIN,
    )


def _write(
    client: TestClient,
    headers: dict[str, str],
    item: OrderItem,
    *,
    rating: int = 5,
    comment: str | None = "Dulce, con acidez cítrica. Tal cual lo describe la ficha.",
) -> dict:
    response = client.post(
        f"{API}/reviews",
        json={"order_item_id": str(item.id), "rating": rating, "comment": comment},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


# ----------------------------------------------------------------------
# Compra verificada
# ----------------------------------------------------------------------
class TestVerifiedPurchase:
    def test_a_delivered_purchase_can_be_reviewed(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        body = _write(client, auth_headers, delivered_item, rating=5)

        assert body["rating"] == 5
        assert body["is_verified_purchase"] is True
        assert body["is_mine"] is True
        assert body["can_edit"] is True

    def test_the_author_name_is_abbreviated(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        """La ficha es pública: el apellido completo no aporta nada a la reseña."""
        body = _write(client, auth_headers, delivered_item)
        assert body["author_name"] == "Comprador D."

    def test_an_undelivered_order_cannot_be_reviewed(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Hasta que el café no llega, no hay nada que opinar (HU-CC-10, CA1)."""
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
        item = session.scalar(select(OrderItem))
        assert item is not None

        response = client.post(
            f"{API}/reviews",
            json={"order_item_id": str(item.id), "rating": 5},
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert "entregado" in response.json()["error"]["message"]

    def test_someone_elses_purchase_cannot_be_reviewed(
        self,
        client: TestClient,
        other_buyer_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """Reseñar la compra de otro es la vía para opinar sin comprar (CA2).

        Responde 404 y no 403: distinguirlos permitiría averiguar qué
        identificadores de línea existen de verdad.
        """
        response = client.post(
            f"{API}/reviews",
            json={"order_item_id": str(delivered_item.id), "rating": 1},
            headers=other_buyer_headers,
        )

        assert response.status_code == 404

    def test_reviewing_requires_a_session(
        self, client: TestClient, delivered_item: OrderItem
    ) -> None:
        response = client.post(
            f"{API}/reviews", json={"order_item_id": str(delivered_item.id), "rating": 5}
        )
        assert response.status_code == 401

    def test_the_same_purchase_cannot_be_reviewed_twice(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        """CA3: no se duplica la reseña, se edita."""
        _write(client, auth_headers, delivered_item)

        response = client.post(
            f"{API}/reviews",
            json={"order_item_id": str(delivered_item.id), "rating": 1},
            headers=auth_headers,
        )

        assert response.status_code == 409
        assert "editar" in response.json()["error"]["message"]

    def test_the_unique_constraint_is_what_really_prevents_it(
        self, session: Session, delivered_item: OrderItem, buyer: User
    ) -> None:
        """La comprobación previa da el mensaje; la base de datos da la garantía.

        Dos peticiones simultáneas superarían el `SELECT` y solo la restricción
        única frena a la segunda.
        """
        from sqlalchemy.exc import IntegrityError

        assert delivered_item.product_id is not None

        # Dentro de un punto de guardado: al revertirlo se deshace solo esta
        # inserción y la transacción de la prueba sigue viva.
        savepoint = session.begin_nested()
        for _ in range(2):
            session.add(
                Review(
                    product_id=delivered_item.product_id,
                    user_id=buyer.id,
                    order_item_id=delivered_item.id,
                    rating=5,
                )
            )

        with pytest.raises(IntegrityError):
            session.flush()
        savepoint.rollback()


# ----------------------------------------------------------------------
# Promedios
# ----------------------------------------------------------------------
class TestRatings:
    def test_publishing_updates_the_product_and_producer_averages(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        delivered_item: OrderItem,
        producer: ProducerProfile,
    ) -> None:
        """CA4: el promedio del café y el del productor se recalculan solos."""
        _write(client, auth_headers, delivered_item, rating=4)

        session.expire_all()
        product = session.get(Product, delivered_item.product_id)
        assert product is not None
        assert product.rating_avg == Decimal("4.00")
        assert product.rating_count == 1

        session.refresh(producer)
        assert producer.rating_avg == Decimal("4.00")

    def test_deleting_a_review_puts_the_average_back(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        body = _write(client, auth_headers, delivered_item, rating=2)

        response = client.delete(f"{API}/reviews/{body['id']}", headers=auth_headers)

        assert response.status_code == 204
        session.expire_all()
        product = session.get(Product, delivered_item.product_id)
        assert product is not None
        assert product.rating_count == 0
        assert product.rating_avg == Decimal("0.00")

    def test_the_summary_reports_the_star_distribution(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        _write(client, auth_headers, delivered_item, rating=3)

        response = client.get(f"{API}/products/{delivered_item.product_id}/reviews/summary")

        assert response.status_code == 200
        body = response.json()
        assert body["rating_count"] == 1
        assert body["rating_avg"] == 3.0
        assert body["distribution"]["3"] == 1
        assert body["distribution"]["5"] == 0


# ----------------------------------------------------------------------
# Edición
# ----------------------------------------------------------------------
class TestEditing:
    def test_the_author_can_correct_their_review(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        body = _write(client, auth_headers, delivered_item, rating=2)

        response = client.put(
            f"{API}/reviews/{body['id']}",
            json={"rating": 4, "comment": "Lo probé con otro método y mejoró mucho."},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["rating"] == 4

    def test_editing_is_closed_after_the_window(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """Pasado el plazo la reseña queda como está: otros ya compraron leyéndola."""
        from app.modules.reviews.service import EDIT_WINDOW_DAYS

        body = _write(client, auth_headers, delivered_item)
        stored = session.get(Review, body["id"])
        assert stored is not None
        stored.created_at = datetime.now(UTC) - timedelta(days=EDIT_WINDOW_DAYS + 1)
        session.flush()

        response = client.put(
            f"{API}/reviews/{body['id']}", json={"rating": 1}, headers=auth_headers
        )

        assert response.status_code == 422
        assert "plazo" in response.json()["error"]["message"]

    def test_nobody_edits_someone_elses_review(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_buyer_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        body = _write(client, auth_headers, delivered_item)

        assert (
            client.put(
                f"{API}/reviews/{body['id']}", json={"rating": 1}, headers=other_buyer_headers
            ).status_code
            == 403
        )
        assert (
            client.delete(f"{API}/reviews/{body['id']}", headers=other_buyer_headers).status_code
            == 403
        )

    def test_a_rating_outside_one_to_five_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        response = client.post(
            f"{API}/reviews",
            json={"order_item_id": str(delivered_item.id), "rating": 9},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ----------------------------------------------------------------------
# Reporte y moderación
# ----------------------------------------------------------------------
class TestReporting:
    def test_reporting_queues_it_without_hiding_it(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        other_buyer_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """Denunciar no puede ser un interruptor para silenciar una opinión."""
        body = _write(client, auth_headers, delivered_item, rating=1)

        response = client.post(
            f"{API}/reviews/{body['id']}/report",
            json={"reason": "Contiene datos personales de otra persona."},
            headers=other_buyer_headers,
        )

        assert response.status_code == 200
        session.expire_all()
        stored = session.get(Review, body["id"])
        assert stored is not None
        assert stored.status is ReviewStatus.REPORTED

        # Sigue visible en la ficha mientras se revisa.
        listing = client.get(f"{API}/products/{delivered_item.product_id}/reviews")
        assert listing.json()["total"] == 1

    def test_reporting_does_not_remove_the_review_from_the_average(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        other_buyer_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """Si denunciar bastara para dejar de contar, sería un silenciador a medias."""
        body = _write(client, auth_headers, delivered_item, rating=1)
        client.post(
            f"{API}/reviews/{body['id']}/report",
            json={"reason": "No me gusta lo que dice de este café."},
            headers=other_buyer_headers,
        )

        # El recálculo se dispara con cualquier operación posterior sobre el café.
        client.put(
            f"{API}/reviews/{body['id']}",
            json={"rating": 1, "comment": "Mantengo lo dicho."},
            headers=auth_headers,
        )

        session.expire_all()
        product = session.get(Product, delivered_item.product_id)
        assert product is not None
        assert product.rating_count == 1
        assert product.rating_avg == Decimal("1.00")

    def test_you_cannot_report_your_own_review(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        body = _write(client, auth_headers, delivered_item)

        response = client.post(
            f"{API}/reviews/{body['id']}/report",
            json={"reason": "Quiero que desaparezca de la ficha."},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_the_same_person_cannot_report_twice(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_buyer_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """Reportar en bucle inflaría el recuento de la cola de moderación."""
        body = _write(client, auth_headers, delivered_item)
        payload = {"reason": "Lenguaje ofensivo hacia el productor."}

        client.post(f"{API}/reviews/{body['id']}/report", json=payload, headers=other_buyer_headers)
        second = client.post(
            f"{API}/reviews/{body['id']}/report", json=payload, headers=other_buyer_headers
        )

        assert second.status_code == 409

    def test_the_moderation_queue_shows_the_report_reason(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_buyer_headers: dict[str, str],
        admin_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """HU-ADM-06, CA1: la cola muestra por qué se denunció."""
        body = _write(client, auth_headers, delivered_item)
        client.post(
            f"{API}/reviews/{body['id']}/report",
            json={"reason": "Publica el teléfono del productor."},
            headers=other_buyer_headers,
        )

        response = client.get(f"{API}/admin/reviews/reported", headers=admin_headers)

        assert response.status_code == 200
        queued = response.json()["items"]
        assert len(queued) == 1
        assert queued[0]["report_count"] == 1
        assert queued[0]["report_reasons"] == ["Publica el teléfono del productor."]

    def test_the_queue_is_only_for_admins(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        assert client.get(f"{API}/admin/reviews/reported", headers=auth_headers).status_code == 403
        assert client.get(f"{API}/admin/reviews/reported").status_code == 401

    def test_hiding_a_review_excludes_it_from_the_average(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        admin_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """HU-ADM-06, CA3."""
        body = _write(client, auth_headers, delivered_item, rating=1)

        moderated = client.post(
            f"{API}/admin/reviews/{body['id']}/moderate",
            json={"hide": True, "reason": "Incumple las normas de convivencia."},
            headers=admin_headers,
        )
        assert moderated.status_code == 200, moderated.text

        session.expire_all()
        product = session.get(Product, delivered_item.product_id)
        assert product is not None
        assert product.rating_count == 0

        listing = client.get(f"{API}/products/{delivered_item.product_id}/reviews")
        assert listing.json()["total"] == 0

    def test_reports_disappear_with_the_review(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        other_buyer_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """La denuncia no tiene sentido sin la reseña que la motivó."""
        body = _write(client, auth_headers, delivered_item)
        client.post(
            f"{API}/reviews/{body['id']}/report",
            json={"reason": "Contiene lenguaje ofensivo."},
            headers=other_buyer_headers,
        )

        stored = session.get(Review, body["id"])
        assert stored is not None
        session.delete(stored)
        session.flush()

        assert session.scalar(select(ReviewReport)) is None


# ----------------------------------------------------------------------
# Panel del comprador
# ----------------------------------------------------------------------
class TestPendingReviews:
    def test_a_delivered_purchase_appears_as_pending(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        """RF-06.4."""
        response = client.get(f"{API}/reviews/pending", headers=auth_headers)

        assert response.status_code == 200
        pending = response.json()
        assert len(pending) == 1
        assert pending[0]["order_item_id"] == str(delivered_item.id)
        assert pending[0]["product_slug"]

    def test_it_disappears_once_reviewed(
        self, client: TestClient, auth_headers: dict[str, str], delivered_item: OrderItem
    ) -> None:
        _write(client, auth_headers, delivered_item)

        response = client.get(f"{API}/reviews/pending", headers=auth_headers)
        assert response.json() == []

    def test_the_order_detail_marks_what_is_already_reviewed(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        delivered_item: OrderItem,
    ) -> None:
        """`has_review` salía siempre en falso y la ficha ofrecía reseñar dos veces."""
        sub_order = session.get(SubOrder, delivered_item.sub_order_id)
        assert sub_order is not None

        before = client.get(f"{API}/orders/{sub_order.order_id}", headers=auth_headers).json()
        assert before["sub_orders"][0]["items"][0]["can_review"] is True
        assert before["sub_orders"][0]["items"][0]["has_review"] is False

        _write(client, auth_headers, delivered_item)

        after = client.get(f"{API}/orders/{sub_order.order_id}", headers=auth_headers).json()
        assert after["sub_orders"][0]["items"][0]["has_review"] is True
        assert after["sub_orders"][0]["items"][0]["can_review"] is False
