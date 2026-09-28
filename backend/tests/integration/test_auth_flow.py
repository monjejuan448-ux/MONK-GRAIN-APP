"""Pruebas del flujo de autenticación.

Verifican especialmente que ningún endpoint permita averiguar qué correos están
registrados: registro, login y recuperación deben responder igual exista o no
la cuenta.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TokenPurpose, UserStatus
from app.models.user import RefreshToken, Role, User, VerificationToken

from .conftest import TEST_PASSWORD

pytestmark = pytest.mark.integration

API = "/api/v1"

VALID_REGISTRATION = {
    "email": "nuevo@prueba.co",
    "password": "ClaveSeguraDePrueba2026",
    "full_name": "Usuario Nuevo",
    "data_consent": True,
}


class TestRegistration:
    def test_registration_creates_unverified_account(
        self, client: TestClient, roles: dict[str, Role], session: Session
    ) -> None:
        response = client.post(f"{API}/auth/register", json=VALID_REGISTRATION)

        assert response.status_code == 202
        user = session.scalar(select(User).where(User.email == "nuevo@prueba.co"))
        assert user is not None
        assert user.status == UserStatus.PENDING_VERIFICATION
        assert user.data_consent is True
        assert user.data_consent_at is not None

    def test_password_is_never_stored_in_plain_text(
        self, client: TestClient, roles: dict[str, Role], session: Session
    ) -> None:
        client.post(f"{API}/auth/register", json=VALID_REGISTRATION)

        user = session.scalar(select(User).where(User.email == "nuevo@prueba.co"))
        assert user is not None
        assert VALID_REGISTRATION["password"] not in user.password_hash
        assert user.password_hash.startswith("$argon2id$")

    def test_duplicate_email_gives_the_same_response(
        self, client: TestClient, roles: dict[str, Role], session: Session
    ) -> None:
        """El endpoint no debe servir para averiguar si un correo existe."""
        first = client.post(f"{API}/auth/register", json=VALID_REGISTRATION)
        second = client.post(
            f"{API}/auth/register",
            json={**VALID_REGISTRATION, "full_name": "Impostor"},
        )

        assert first.status_code == second.status_code == 202
        assert first.json() == second.json()

        # Y, sobre todo, no se creó una segunda cuenta ni se sobrescribió la primera.
        users = session.scalars(select(User).where(User.email == "nuevo@prueba.co")).all()
        assert len(users) == 1
        assert users[0].full_name == "Usuario Nuevo"

    def test_registration_requires_explicit_data_consent(
        self, client: TestClient, roles: dict[str, Role]
    ) -> None:
        """La Ley 1581 de 2012 no admite un consentimiento tácito."""
        response = client.post(
            f"{API}/auth/register", json={**VALID_REGISTRATION, "data_consent": False}
        )

        assert response.status_code == 422
        fields = response.json()["error"]["details"]["fields"]
        assert any("data_consent" in field["field"] for field in fields)

    @pytest.mark.parametrize(
        "password",
        ["corta", "solamenteletrasaqui", "123456789012345"],
    )
    def test_weak_passwords_are_rejected(
        self, client: TestClient, roles: dict[str, Role], password: str
    ) -> None:
        response = client.post(
            f"{API}/auth/register", json={**VALID_REGISTRATION, "password": password}
        )
        assert response.status_code == 422


class TestEmailVerification:
    def test_login_blocked_until_email_is_verified(
        self, client: TestClient, roles: dict[str, Role]
    ) -> None:
        client.post(f"{API}/auth/register", json=VALID_REGISTRATION)

        response = client.post(
            f"{API}/auth/login",
            json={
                "email": VALID_REGISTRATION["email"],
                "password": VALID_REGISTRATION["password"],
            },
        )

        assert response.status_code == 401
        assert "verificar tu correo" in response.json()["error"]["message"]

    def test_verification_token_is_single_use(
        self, client: TestClient, roles: dict[str, Role], session: Session
    ) -> None:
        """Reutilizar el enlace de verificación no debe funcionar."""
        client.post(f"{API}/auth/register", json=VALID_REGISTRATION)

        # El token en claro solo existe en el correo; para la prueba se genera
        # uno nuevo con el mismo mecanismo y se persiste su hash.
        from app.core.security import generate_one_time_token, hash_token

        raw, token_hash = generate_one_time_token()
        stored = session.scalar(
            select(VerificationToken).where(
                VerificationToken.purpose == TokenPurpose.EMAIL_VERIFICATION
            )
        )
        assert stored is not None
        stored.token_hash = token_hash
        session.flush()
        assert hash_token(raw) == token_hash

        first = client.post(f"{API}/auth/verify-email", json={"token": raw})
        second = client.post(f"{API}/auth/verify-email", json={"token": raw})

        assert first.status_code == 200
        assert second.status_code == 401

    def test_invalid_token_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/auth/verify-email", json={"token": "token-completamente-inventado"}
        )
        assert response.status_code == 401


class TestLogin:
    def test_login_returns_token_pair(self, client: TestClient, buyer: User) -> None:
        response = client.post(
            f"{API}/auth/login", json={"email": buyer.email, "password": TEST_PASSWORD}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"  # noqa: S105 — esquema HTTP, no una credencial
        assert body["access_token"] != body["refresh_token"]

    def test_wrong_password_and_unknown_email_give_identical_errors(
        self, client: TestClient, buyer: User
    ) -> None:
        """El mensaje no debe revelar si el correo está registrado."""
        wrong_password = client.post(
            f"{API}/auth/login",
            json={"email": buyer.email, "password": "ClaveEquivocada2026"},
        )
        unknown_email = client.post(
            f"{API}/auth/login",
            json={"email": "nadie@prueba.co", "password": "ClaveEquivocada2026"},
        )

        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()

    def test_refresh_token_is_stored_hashed(
        self, client: TestClient, buyer: User, session: Session
    ) -> None:
        """Una filtración de la tabla no debe entregar sesiones utilizables."""
        response = client.post(
            f"{API}/auth/login", json={"email": buyer.email, "password": TEST_PASSWORD}
        )
        raw_refresh = response.json()["refresh_token"]

        stored = session.scalar(select(RefreshToken))
        assert stored is not None
        assert stored.token_hash != raw_refresh
        assert len(stored.token_hash) == 64


class TestSessionLifecycle:
    def test_refresh_rotates_and_revokes_the_previous_token(
        self, client: TestClient, buyer: User
    ) -> None:
        login = client.post(
            f"{API}/auth/login", json={"email": buyer.email, "password": TEST_PASSWORD}
        ).json()

        renewed = client.post(f"{API}/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert renewed.status_code == 200

        # El token anterior queda inservible tras la rotación.
        reused = client.post(f"{API}/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert reused.status_code == 401

    def test_logout_revokes_the_session(self, client: TestClient, buyer: User) -> None:
        login = client.post(
            f"{API}/auth/login", json={"email": buyer.email, "password": TEST_PASSWORD}
        ).json()

        client.post(f"{API}/auth/logout", json={"refresh_token": login["refresh_token"]})

        response = client.post(
            f"{API}/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )
        assert response.status_code == 401

    def test_me_returns_roles_and_permissions_without_secrets(
        self, client: TestClient, buyer_token: str
    ) -> None:
        response = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {buyer_token}"})

        assert response.status_code == 200
        body = response.json()
        assert "password_hash" not in body
        assert [role["code"] for role in body["roles"]] == ["consumer"]
        assert "order.create" in body["permissions"]

    def test_me_requires_a_valid_token(self, client: TestClient) -> None:
        assert client.get(f"{API}/auth/me").status_code == 401
        assert (
            client.get(
                f"{API}/auth/me", headers={"Authorization": "Bearer token.no.valido"}
            ).status_code
            == 401
        )


class TestPasswordReset:
    def test_reset_request_response_is_identical_for_unknown_emails(
        self, client: TestClient, buyer: User
    ) -> None:
        existing = client.post(f"{API}/auth/password-reset", json={"email": buyer.email})
        unknown = client.post(f"{API}/auth/password-reset", json={"email": "nadie@prueba.co"})

        assert existing.status_code == unknown.status_code == 202
        assert existing.json() == unknown.json()

    def test_reset_revokes_all_active_sessions(
        self, client: TestClient, buyer: User, session: Session
    ) -> None:
        """Cambiar la contraseña expulsa a quien tuviera acceso indebido."""
        from app.core.security import generate_one_time_token

        login = client.post(
            f"{API}/auth/login", json={"email": buyer.email, "password": TEST_PASSWORD}
        ).json()

        client.post(f"{API}/auth/password-reset", json={"email": buyer.email})
        stored = session.scalar(
            select(VerificationToken).where(
                VerificationToken.purpose == TokenPurpose.PASSWORD_RESET
            )
        )
        assert stored is not None

        raw, token_hash = generate_one_time_token()
        stored.token_hash = token_hash
        session.flush()

        response = client.post(
            f"{API}/auth/password-reset/confirm",
            json={"token": raw, "password": "ClaveNuevaDePrueba2026"},
        )
        assert response.status_code == 200

        # La sesión anterior deja de servir.
        reused = client.post(f"{API}/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert reused.status_code == 401

        # Y la contraseña antigua tampoco.
        old_password = client.post(
            f"{API}/auth/login", json={"email": buyer.email, "password": TEST_PASSWORD}
        )
        assert old_password.status_code == 401
