"""Primitivas de seguridad: hash de contraseñas y emisión de tokens JWT.

Decisiones aplicadas:
- Argon2id para contraseñas (RNF-04).
- Los refresh tokens se guardan hasheados con SHA-256 en base de datos: una
  filtración de la tabla no entrega sesiones utilizables.
- El access token es de vida corta y el refresh token es revocable.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"  # noqa: S105 — discriminador de tipo, no una credencial
TOKEN_TYPE_REFRESH = "refresh"  # noqa: S105 — discriminador de tipo, no una credencial

_password_hasher = PasswordHasher()


# ------------------------------------------------------------------
# Contraseñas
# ------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Genera el hash Argon2id de una contraseña."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash sin filtrar el motivo del fallo."""
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Indica si el hash quedó obsoleto tras endurecer los parámetros."""
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def validate_password_strength(password: str) -> list[str]:
    """Devuelve la lista de reglas incumplidas; vacía si la contraseña es válida."""
    problems: list[str] = []
    if len(password) < settings.password_min_length:
        problems.append(f"Debe tener al menos {settings.password_min_length} caracteres.")
    if not any(char.isalpha() for char in password):
        problems.append("Debe incluir al menos una letra.")
    if not any(char.isdigit() for char in password):
        problems.append("Debe incluir al menos un número.")
    return problems


# ------------------------------------------------------------------
# Tokens JWT
# ------------------------------------------------------------------
def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime, str]:
    """Crea un JWT firmado. Devuelve (token, expiración, identificador jti)."""
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    jti = str(uuid.uuid4())

    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, expires_at, jti


def create_access_token(
    user_id: uuid.UUID, roles: list[str], extra_claims: dict[str, Any] | None = None
) -> tuple[str, datetime]:
    """Emite un access token de vida corta con los roles del usuario."""
    claims: dict[str, Any] = {"roles": roles}
    if extra_claims:
        claims.update(extra_claims)

    token, expires_at, _ = _create_token(
        subject=str(user_id),
        token_type=TOKEN_TYPE_ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims=claims,
    )
    return token, expires_at


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, datetime, str]:
    """Emite un refresh token. Devuelve (token, expiración, hash a almacenar)."""
    token, expires_at, _ = _create_token(
        subject=str(user_id),
        token_type=TOKEN_TYPE_REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    return token, expires_at, hash_token(token)


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    """Valida y decodifica un JWT, comprobando que sea del tipo esperado."""
    try:
        payload: dict[str, Any] = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("La sesión expiró. Inicia sesión nuevamente.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Token inválido.") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Token inválido.")

    return payload


# ------------------------------------------------------------------
# Tokens de un solo uso (verificación de correo, recuperación de contraseña)
# ------------------------------------------------------------------
def generate_one_time_token() -> tuple[str, str]:
    """Genera un token aleatorio. Devuelve (token en claro, hash a almacenar).

    El token en claro se envía por correo y no se persiste en ningún momento.
    """
    token = secrets.token_urlsafe(48)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    """Calcula el hash SHA-256 de un token para almacenarlo o compararlo."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(candidate_token: str, stored_hash: str) -> bool:
    """Compara un token contra su hash en tiempo constante."""
    return secrets.compare_digest(hash_token(candidate_token), stored_hash)
