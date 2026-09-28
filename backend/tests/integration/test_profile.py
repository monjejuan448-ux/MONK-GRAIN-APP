"""Pruebas del perfil personal (HU-CC-02).

Lo que se verifica aquí es que el titular pueda corregir sus datos y que no
pueda tocar, por esta vía, lo que no le corresponde: el correo —que es la llave
de la recuperación de contraseña— ni el estado de su propia cuenta.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import UserStatus
from app.models.user import User

pytestmark = pytest.mark.integration

API = "/api/v1"


class TestEditing:
    def test_the_holder_corrects_their_name(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.patch(
            f"{API}/users/me",
            json={"full_name": "María Fernanda López"},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["full_name"] == "María Fernanda López"

    def test_what_was_not_sent_is_left_alone(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        client.patch(f"{API}/users/me", json={"phone": "3001234567"}, headers=auth_headers)

        response = client.patch(
            f"{API}/users/me", json={"full_name": "Otro Nombre"}, headers=auth_headers
        )

        assert response.json()["phone"] == "3001234567"

    def test_an_explicit_null_clears_the_phone(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        client.patch(f"{API}/users/me", json={"phone": "3001234567"}, headers=auth_headers)

        response = client.patch(f"{API}/users/me", json={"phone": None}, headers=auth_headers)

        assert response.json()["phone"] is None

    def test_notifications_can_be_turned_off(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.patch(
            f"{API}/users/me",
            json={"email_notifications_enabled": False},
            headers=auth_headers,
        )

        assert response.json()["email_notifications_enabled"] is False

    def test_a_name_too_short_to_be_a_name_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.patch(f"{API}/users/me", json={"full_name": "Jo"}, headers=auth_headers)

        assert response.status_code == 422

    def test_an_empty_body_changes_nothing(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.patch(f"{API}/users/me", json={}, headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["full_name"] == buyer.full_name


class TestWhatCannotBeChangedHere:
    def test_the_email_is_not_editable(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        """Cambiar el correo exige volver a verificarlo: es por donde se
        recupera la contraseña. Un campo colado en el cuerpo se ignora."""
        original = buyer.email

        response = client.patch(
            f"{API}/users/me",
            json={"email": "secuestrada@atacante.co", "full_name": "Nombre Nuevo"},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["email"] == original
        session.expire_all()
        refreshed = session.get(User, buyer.id)
        assert refreshed is not None
        assert refreshed.email == original

    def test_the_account_status_is_not_editable(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        """Nadie se reactiva a sí mismo por este endpoint."""
        client.patch(
            f"{API}/users/me",
            json={"status": UserStatus.SUSPENDED.value},
            headers=auth_headers,
        )

        session.expire_all()
        refreshed = session.get(User, buyer.id)
        assert refreshed is not None
        assert refreshed.status == UserStatus.ACTIVE

    def test_the_data_consent_is_not_editable(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        """El consentimiento de la Ley 1581 se otorga al registrarse y su
        retiro es una solicitud del titular, no un campo de formulario."""
        client.patch(f"{API}/users/me", json={"data_consent": False}, headers=auth_headers)

        session.expire_all()
        refreshed = session.get(User, buyer.id)
        assert refreshed is not None
        assert refreshed.data_consent is True


class TestAuthorization:
    def test_an_anonymous_visitor_cannot_edit_a_profile(self, client: TestClient) -> None:
        response = client.patch(f"{API}/users/me", json={"full_name": "Quien Sea"})

        assert response.status_code == 401

    def test_each_account_edits_only_itself(
        self,
        client: TestClient,
        session: Session,
        buyer: User,
        producer_token: str,
    ) -> None:
        """El endpoint no recibe identificador: actúa sobre el titular del token,
        de modo que no hay forma de apuntar a otra cuenta."""
        original = buyer.full_name

        client.patch(
            f"{API}/users/me",
            json={"full_name": "Nombre Impuesto"},
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        session.expire_all()
        refreshed = session.get(User, buyer.id)
        assert refreshed is not None
        assert refreshed.full_name == original
