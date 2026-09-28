"""Acceso a datos del módulo de autenticación."""

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.enums import RoleCode, TokenPurpose
from app.models.user import RefreshToken, Role, User, UserRole, VerificationToken


class AuthRepository:
    """Consultas y escrituras sobre identidad y sesiones."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ---------------- Usuarios ----------------
    def get_user_by_email(self, email: str) -> User | None:
        """Busca por correo. La columna es CITEXT: la comparación ignora mayúsculas."""
        return self.session.scalar(
            select(User)
            .where(User.email == email, User.deleted_at.is_(None))
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )

    def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.scalar(
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )

    def create_user(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def assign_role(self, user_id: uuid.UUID, role_code: RoleCode) -> None:
        role = self.session.scalar(select(Role).where(Role.code == role_code.value))
        if role is None:
            raise RuntimeError(
                f"El rol '{role_code.value}' no existe. Ejecuta la carga de datos iniciales."
            )
        self.session.add(UserRole(user_id=user_id, role_id=role.id))
        self.session.flush()

    def touch_last_login(self, user_id: uuid.UUID) -> None:
        self.session.execute(
            update(User).where(User.id == user_id).values(last_login_at=datetime.now(UTC))
        )

    # ---------------- Tokens de un solo uso ----------------
    def create_verification_token(
        self,
        user_id: uuid.UUID,
        purpose: TokenPurpose,
        token_hash: str,
        expires_at: datetime,
    ) -> VerificationToken:
        token = VerificationToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        self.session.flush()
        return token

    def get_valid_verification_token(
        self, token_hash: str, purpose: TokenPurpose
    ) -> VerificationToken | None:
        """Recupera un token vigente: no usado y no vencido."""
        return self.session.scalar(
            select(VerificationToken).where(
                VerificationToken.token_hash == token_hash,
                VerificationToken.purpose == purpose,
                VerificationToken.used_at.is_(None),
                VerificationToken.expires_at > datetime.now(UTC),
            )
        )

    def mark_token_used(self, token: VerificationToken) -> None:
        token.used_at = datetime.now(UTC)
        self.session.flush()

    def invalidate_pending_tokens(self, user_id: uuid.UUID, purpose: TokenPurpose) -> None:
        """Anula los tokens anteriores del mismo propósito.

        Al pedir un nuevo enlace, los previos dejan de servir: un enlace antiguo
        filtrado por correo no debe seguir siendo utilizable.
        """
        self.session.execute(
            update(VerificationToken)
            .where(
                VerificationToken.user_id == user_id,
                VerificationToken.purpose == purpose,
                VerificationToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )

    # ---------------- Sesiones ----------------
    def store_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address,
        )
        self.session.add(token)
        self.session.flush()
        return token

    def get_active_refresh_token(self, token_hash: str) -> RefreshToken | None:
        return self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )

    def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        self.session.flush()

    def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """Cierra todas las sesiones activas del usuario.

        Se invoca al cambiar o restablecer la contraseña: si alguien tenía
        acceso indebido, el cambio debe expulsarlo (HU-CC-02, CA3).
        """
        result = self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        # `rowcount` lo expone el CursorResult que devuelve un UPDATE, pero la
        # firma genérica de `execute` no lo declara.
        return cast("CursorResult[Any]", result).rowcount or 0
