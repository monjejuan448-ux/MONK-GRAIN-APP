"""Pruebas del panel administrativo.

Lo que se verifica aquí es lo que el panel puede hacer con cuentas y reseñas
ajenas, que es donde más importa el control de acceso: suspender a alguien,
ocultar lo que escribió y dejar constancia de ambas cosas en un registro que
nadie puede editar.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.catalog import Review
from app.models.content import AuditLog
from app.models.enums import ReviewStatus, RoleCode, UserStatus
from app.models.user import Role, User, UserRole

pytestmark = pytest.mark.integration

API = "/api/v1"
ADMIN_PASSWORD = "AdminMonkGrain2026"  # noqa: S105 — credencial de pruebas


@pytest.fixture
def admin_token(client: TestClient, session: Session, roles: dict[str, Role]) -> str:
    """Administrador autenticado por el endpoint real de login."""
    admin = User(
        email="admin@prueba.co",
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name="Administradora de Prueba",
        status=UserStatus.ACTIVE,
        data_consent=True,
        data_consent_at=datetime.now(UTC),
    )
    session.add(admin)
    session.flush()
    session.add(UserRole(user_id=admin.id, role_id=roles[RoleCode.ADMIN.value].id))
    session.flush()

    response = client.post(
        f"{API}/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


class TestUserListing:
    def test_the_accounts_are_listed(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        buyer: User,
        producer: object,
    ) -> None:
        response = client.get(f"{API}/admin/users", headers=admin_headers)

        assert response.status_code == 200, response.text
        emails = {item["email"] for item in response.json()["items"]}
        assert "comprador@prueba.co" in emails
        assert "productor@prueba.co" in emails

    def test_searching_by_email_finds_the_account(
        self, client: TestClient, admin_headers: dict[str, str], buyer: User
    ) -> None:
        """Es lo que hace alcanzable la suspensión: sin búsqueda había que
        conocer el identificador de la cuenta de memoria."""
        response = client.get(
            f"{API}/admin/users", params={"q": "comprador@"}, headers=admin_headers
        )

        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["email"] == "comprador@prueba.co"

    def test_searching_by_name_ignores_accents(
        self, client: TestClient, session: Session, admin_headers: dict[str, str]
    ) -> None:
        """Buscar «Nunez» debe encontrar a «Núñez»."""
        session.add(
            User(
                email="acentos@prueba.co",
                password_hash=hash_password(ADMIN_PASSWORD),
                full_name="María Núñez",
                status=UserStatus.ACTIVE,
                data_consent=True,
            )
        )
        session.flush()

        response = client.get(f"{API}/admin/users", params={"q": "Nunez"}, headers=admin_headers)

        assert [item["email"] for item in response.json()["items"]] == ["acentos@prueba.co"]

    def test_filtering_by_status(
        self, client: TestClient, session: Session, admin_headers: dict[str, str], buyer: User
    ) -> None:
        buyer.status = UserStatus.SUSPENDED
        session.flush()

        suspended = client.get(
            f"{API}/admin/users", params={"status": "suspended"}, headers=admin_headers
        ).json()

        assert [item["email"] for item in suspended["items"]] == ["comprador@prueba.co"]

    def test_filtering_by_role(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        buyer: User,
        producer: object,
    ) -> None:
        response = client.get(
            f"{API}/admin/users", params={"role": "producer"}, headers=admin_headers
        )

        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["is_producer"] is True
        assert items[0]["producer_status"] == "approved"

    def test_the_listing_does_not_carry_personal_data_nobody_uses(
        self, client: TestClient, admin_headers: dict[str, str], buyer: User
    ) -> None:
        """Para decidir una suspensión no hace falta el teléfono ni el documento,
        y un listado es donde menos conviene tenerlos."""
        item = client.get(f"{API}/admin/users", headers=admin_headers).json()["items"][0]

        assert "phone" not in item
        assert "document_number" not in item
        assert "password_hash" not in item

    def test_only_an_admin_reaches_the_listing(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        assert client.get(f"{API}/admin/users", headers=auth_headers).status_code == 403

    def test_an_anonymous_visitor_is_rejected(self, client: TestClient) -> None:
        assert client.get(f"{API}/admin/users").status_code == 401


class TestSuspension:
    def test_suspending_an_account_blocks_it_immediately(
        self, client: TestClient, admin_headers: dict[str, str], buyer: User, buyer_token: str
    ) -> None:
        """El usuario se recarga en cada petición, así que la suspensión surte
        efecto sin esperar a que expire su token."""
        response = client.post(
            f"{API}/admin/users/{buyer.id}/suspend",
            json={"suspend": True, "reason": "Actividad fraudulenta."},
            headers=admin_headers,
        )

        assert response.status_code == 200, response.text
        blocked = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {buyer_token}"})
        assert blocked.status_code == 403
        assert "suspendida" in blocked.json()["error"]["message"]

    def test_reactivating_lets_them_back_in(
        self, client: TestClient, admin_headers: dict[str, str], buyer: User, buyer_token: str
    ) -> None:
        client.post(
            f"{API}/admin/users/{buyer.id}/suspend",
            json={"suspend": True},
            headers=admin_headers,
        )

        client.post(
            f"{API}/admin/users/{buyer.id}/suspend",
            json={"suspend": False},
            headers=admin_headers,
        )

        back = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {buyer_token}"})
        assert back.status_code == 200

    def test_suspending_leaves_a_trace_in_the_audit_log(
        self, client: TestClient, session: Session, admin_headers: dict[str, str], buyer: User
    ) -> None:
        client.post(
            f"{API}/admin/users/{buyer.id}/suspend",
            json={"suspend": True, "reason": "Actividad fraudulenta."},
            headers=admin_headers,
        )

        entries = session.scalars(select(AuditLog)).all()
        assert any(str(buyer.id) in (entry.entity_id or "") for entry in entries)

    def test_a_buyer_cannot_suspend_anyone(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.post(
            f"{API}/admin/users/{buyer.id}/suspend",
            json={"suspend": True},
            headers=auth_headers,
        )

        assert response.status_code == 403

    def test_suspending_an_account_that_does_not_exist_gives_404(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.post(
            f"{API}/admin/users/{uuid.uuid4()}/suspend",
            json={"suspend": True},
            headers=admin_headers,
        )

        assert response.status_code == 404


class TestReviewModeration:
    def _review(self, client: TestClient, session: Session, buyer: User, variant: object) -> Review:
        """Deja una reseña real: comprar, entregar y reseñar."""
        from app.models.enums import SubOrderStatus
        from app.models.order import OrderItem, SubOrder
        from app.models.user import Address

        client.post(
            f"{API}/cart/items",
            json={"variant_id": str(variant.id), "quantity": 2},  # type: ignore[attr-defined]
            headers={"Authorization": f"Bearer {self.buyer_token}"},
        )
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None
        client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers={"Authorization": f"Bearer {self.buyer_token}"},
        )
        sub_order = session.scalar(select(SubOrder))
        assert sub_order is not None
        sub_order.status = SubOrderStatus.DELIVERED
        session.flush()

        item = session.scalar(select(OrderItem))
        assert item is not None
        response = client.post(
            f"{API}/reviews",
            json={"order_item_id": str(item.id), "rating": 1, "comment": "Reseña de prueba."},
            headers={"Authorization": f"Bearer {self.buyer_token}"},
        )
        assert response.status_code == 201, response.text
        review = session.scalar(select(Review))
        assert review is not None
        return review

    @pytest.fixture(autouse=True)
    def _tokens(self, buyer_token: str) -> None:
        self.buyer_token = buyer_token

    def test_hiding_a_review_takes_it_out_of_the_average(
        self,
        client: TestClient,
        session: Session,
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: object,
    ) -> None:
        review = self._review(client, session, buyer, product_variant)
        product_id = review.product_id

        response = client.post(
            f"{API}/admin/reviews/{review.id}/moderate",
            json={"hide": True, "reason": "Lenguaje ofensivo."},
            headers=admin_headers,
        )

        assert response.status_code == 200, response.text
        session.expire_all()
        refreshed = session.get(Review, review.id)
        assert refreshed is not None
        assert refreshed.status == ReviewStatus.HIDDEN
        assert refreshed.moderation_reason == "Lenguaje ofensivo."

        from app.models.catalog import Product

        product = session.get(Product, product_id)
        assert product is not None
        assert product.rating_count == 0
        assert product.rating_avg == Decimal("0.00")

    def test_restoring_it_brings_it_back(
        self,
        client: TestClient,
        session: Session,
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: object,
    ) -> None:
        review = self._review(client, session, buyer, product_variant)
        client.post(
            f"{API}/admin/reviews/{review.id}/moderate",
            json={"hide": True},
            headers=admin_headers,
        )

        client.post(
            f"{API}/admin/reviews/{review.id}/moderate",
            json={"hide": False},
            headers=admin_headers,
        )

        session.expire_all()
        refreshed = session.get(Review, review.id)
        assert refreshed is not None
        assert refreshed.status == ReviewStatus.PUBLISHED

    def test_the_queue_carries_the_slug_to_reach_the_lot(
        self,
        client: TestClient,
        session: Session,
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: object,
        producer_token: str,
    ) -> None:
        """La ruta pública del lote usa el slug, no el identificador: sin él, el
        enlace de la cola de moderación llevaría a un 404.

        Denuncia el vendedor y no el comprador: nadie puede denunciar su propia
        reseña, y es justo el vendedor quien suele hacerlo."""
        review = self._review(client, session, buyer, product_variant)
        reported = client.post(
            f"{API}/reviews/{review.id}/report",
            json={"reason": "Contiene datos personales de un tercero."},
            headers={"Authorization": f"Bearer {producer_token}"},
        )
        assert reported.status_code in (200, 201), reported.text
        # La prueba comparte sesión con la aplicación, así que la reseña sigue en
        # el mapa de identidad con su colección de denuncias tal como se cargó
        # antes —vacía—. En producción cada petición abre su propia sesión y no
        # ocurre; aquí hay que caducarla a mano.
        session.expire_all()

        queue = client.get(f"{API}/admin/reviews/reported", headers=admin_headers).json()

        assert queue["total"] == 1
        assert queue["items"][0]["product_slug"] == "pergamino-de-prueba"
        assert queue["items"][0]["report_reasons"] == ["Contiene datos personales de un tercero."]

    def test_a_buyer_cannot_moderate(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: object,
    ) -> None:
        review = self._review(client, session, buyer, product_variant)

        response = client.post(
            f"{API}/admin/reviews/{review.id}/moderate",
            json={"hide": True},
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestAuditLog:
    def test_the_log_is_readable_by_an_admin(
        self, client: TestClient, admin_headers: dict[str, str], buyer: User
    ) -> None:
        client.post(
            f"{API}/admin/users/{buyer.id}/suspend",
            json={"suspend": True},
            headers=admin_headers,
        )

        response = client.get(f"{API}/admin/audit-logs", headers=admin_headers)

        assert response.status_code == 200, response.text
        assert response.json()["total"] >= 1
        entry = response.json()["items"][0]
        assert entry["actor_email"] == "admin@prueba.co"
        assert entry["action"]

    def test_the_log_can_be_filtered_by_action(
        self, client: TestClient, admin_headers: dict[str, str], buyer: User
    ) -> None:
        client.post(
            f"{API}/admin/users/{buyer.id}/suspend",
            json={"suspend": True},
            headers=admin_headers,
        )
        action = client.get(f"{API}/admin/audit-logs", headers=admin_headers).json()["items"][0][
            "action"
        ]

        filtered = client.get(
            f"{API}/admin/audit-logs", params={"action": action}, headers=admin_headers
        ).json()

        assert filtered["total"] >= 1
        assert all(item["action"] == action for item in filtered["items"])

    def test_there_is_no_endpoint_to_alter_the_log(self, client: TestClient) -> None:
        """La auditoría es inmutable: no hay por dónde editarla ni borrarla.

        Se comprueba contra las rutas declaradas y no por inspección del código,
        de modo que añadir un endpoint de escritura sobre la auditoría rompa esta
        prueba.
        """
        from app.main import app

        for route in app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            if "audit" in path:
                assert methods <= {"GET", "HEAD", "OPTIONS"}, f"{path}: {methods}"

    def test_a_buyer_cannot_read_the_log(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        assert client.get(f"{API}/admin/audit-logs", headers=auth_headers).status_code == 403
