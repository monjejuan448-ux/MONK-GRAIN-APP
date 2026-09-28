"""Pruebas de las primitivas de seguridad."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    ALGORITHM,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_one_time_token,
    hash_password,
    hash_token,
    tokens_match,
    validate_password_strength,
    verify_password,
)


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_uses_argon2id(self) -> None:
        """Se exige Argon2id, no un algoritmo más débil (RNF-04)."""
        assert hash_password("ContraseñaSegura123").startswith("$argon2id$")

    def test_hash_is_salted(self) -> None:
        """Dos hashes de la misma contraseña difieren: la sal es aleatoria."""
        assert hash_password("MismaClave12345") != hash_password("MismaClave12345")

    def test_verify_accepts_correct_password(self) -> None:
        assert verify_password("CafeDeHuila2026", hash_password("CafeDeHuila2026"))

    def test_verify_rejects_wrong_password(self) -> None:
        assert not verify_password("Incorrecta123", hash_password("CafeDeHuila2026"))

    def test_verify_rejects_malformed_hash_without_raising(self) -> None:
        """Un hash corrupto devuelve False en vez de propagar una excepción."""
        assert not verify_password("cualquiera", "no-es-un-hash")


@pytest.mark.unit
class TestPasswordStrength:
    def test_accepts_valid_password(self) -> None:
        assert validate_password_strength("CafeDeHuila2026") == []

    def test_rejects_short_password(self) -> None:
        problems = validate_password_strength("Corta1")
        assert any("caracteres" in problem for problem in problems)

    def test_rejects_password_without_digits(self) -> None:
        problems = validate_password_strength("SoloLetrasSinNumeros")
        assert any("número" in problem for problem in problems)

    def test_rejects_password_without_letters(self) -> None:
        problems = validate_password_strength("123456789012345")
        assert any("letra" in problem for problem in problems)


@pytest.mark.unit
class TestJwtTokens:
    def test_access_token_carries_roles(self) -> None:
        user_id = uuid.uuid4()
        token, _ = create_access_token(user_id, ["consumer", "producer"])
        payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)

        assert payload["sub"] == str(user_id)
        assert payload["roles"] == ["consumer", "producer"]

    def test_refresh_token_returns_storable_hash(self) -> None:
        """Solo se almacena el hash: una filtración no entrega sesiones."""
        token, _, stored_hash = create_refresh_token(uuid.uuid4())

        assert stored_hash == hash_token(token)
        assert token not in stored_hash
        assert len(stored_hash) == 64  # SHA-256 en hexadecimal

    def test_access_token_rejected_where_refresh_expected(self) -> None:
        """El tipo del token importa: uno de acceso no sirve para renovar."""
        token, _ = create_access_token(uuid.uuid4(), ["consumer"])

        with pytest.raises(UnauthorizedError):
            decode_token(token, expected_type=TOKEN_TYPE_REFRESH)

    def test_expired_token_is_rejected(self) -> None:
        expired = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "type": TOKEN_TYPE_ACCESS,
                "exp": datetime.now(UTC) - timedelta(minutes=1),
            },
            settings.secret_key,
            algorithm=ALGORITHM,
        )

        with pytest.raises(UnauthorizedError):
            decode_token(expired, expected_type=TOKEN_TYPE_ACCESS)

    def test_token_signed_with_another_key_is_rejected(self) -> None:
        """Un token forjado con otra clave no se acepta."""
        forged = jwt.encode(
            {"sub": str(uuid.uuid4()), "type": TOKEN_TYPE_ACCESS},
            "clave-de-un-atacante-completamente-distinta",
            algorithm=ALGORITHM,
        )

        with pytest.raises(UnauthorizedError):
            decode_token(forged, expected_type=TOKEN_TYPE_ACCESS)

    def test_unsigned_token_is_rejected(self) -> None:
        """Rechaza el algoritmo `none`, ataque clásico contra JWT."""
        unsigned = jwt.encode(
            {"sub": str(uuid.uuid4()), "type": TOKEN_TYPE_ACCESS},
            key="",
            algorithm="none",
        )

        with pytest.raises(UnauthorizedError):
            decode_token(unsigned, expected_type=TOKEN_TYPE_ACCESS)

    def test_each_token_has_a_unique_identifier(self) -> None:
        """El `jti` distingue tokens emitidos en el mismo instante."""
        user_id = uuid.uuid4()
        first, _ = create_access_token(user_id, ["consumer"])
        second, _ = create_access_token(user_id, ["consumer"])

        assert (
            decode_token(first, expected_type=TOKEN_TYPE_ACCESS)["jti"]
            != decode_token(second, expected_type=TOKEN_TYPE_ACCESS)["jti"]
        )


@pytest.mark.unit
class TestOneTimeTokens:
    def test_raw_token_is_never_equal_to_its_hash(self) -> None:
        raw, stored = generate_one_time_token()
        assert raw != stored
        assert len(stored) == 64

    def test_tokens_match_compares_correctly(self) -> None:
        raw, stored = generate_one_time_token()
        assert tokens_match(raw, stored)
        assert not tokens_match("token-inventado", stored)

    def test_generated_tokens_are_unique(self) -> None:
        tokens = {generate_one_time_token()[0] for _ in range(50)}
        assert len(tokens) == 50
