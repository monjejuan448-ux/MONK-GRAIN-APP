"""Reglas de negocio de autenticación.

Principios aplicados en todo el módulo:

- **No revelar qué correos existen.** Registro, login y recuperación responden
  igual exista o no la cuenta. Lo contrario convierte cualquiera de esos
  endpoints en un verificador de correos para un atacante.
- **Un fallo de correo no revierte la operación.** El registro se completa
  aunque el servidor SMTP esté caído; la persona puede pedir el reenvío.
- **Los tokens se guardan hasheados.** Una filtración de la base de datos no
  entrega sesiones ni enlaces utilizables.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_one_time_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.integrations.mail import get_mail_sender
from app.integrations.mail.templates import (
    password_changed_email,
    password_reset_email,
    verification_email,
)
from app.models.enums import RoleCode, TokenPurpose, UserStatus
from app.models.user import User
from app.modules.auth.repository import AuthRepository
from app.schemas.auth import TokenResponse

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AuthRepository(session)
        self.mail = get_mail_sender()

    # ------------------------------------------------------------------
    # Registro y verificación
    # ------------------------------------------------------------------
    def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        phone: str | None,
        data_consent: bool,
        frontend_url: str,
    ) -> None:
        """Registra un comprador y envía el correo de verificación.

        No informa si el correo ya estaba registrado (HU-CC-01, CA2): el router
        devuelve el mismo mensaje en ambos casos.
        """
        normalized_email = email.strip().lower()
        existing = self.repo.get_user_by_email(normalized_email)

        if existing is not None:
            # La cuenta ya existe. Se registra el intento para poder detectar
            # un patrón de sondeo, pero la respuesta al cliente no cambia.
            logger.info("register_attempt_existing_email", user_id=str(existing.id))
            return

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            full_name=full_name,
            phone=phone,
            status=UserStatus.PENDING_VERIFICATION,
            data_consent=data_consent,
            data_consent_at=datetime.now(UTC) if data_consent else None,
        )
        self.repo.create_user(user)
        self.repo.assign_role(user.id, RoleCode.CONSUMER)

        self._send_verification_email(user, frontend_url)
        self.session.commit()
        logger.info("user_registered", user_id=str(user.id))

    def _send_verification_email(self, user: User, frontend_url: str) -> None:
        """Genera el token de verificación y envía el correo."""
        self.repo.invalidate_pending_tokens(user.id, TokenPurpose.EMAIL_VERIFICATION)

        raw_token, token_hash = generate_one_time_token()
        expires_at = datetime.now(UTC) + timedelta(hours=settings.email_verification_expire_hours)
        self.repo.create_verification_token(
            user.id, TokenPurpose.EMAIL_VERIFICATION, token_hash, expires_at
        )

        content = verification_email(
            full_name=user.full_name,
            verification_url=f"{frontend_url}/verificar-correo?token={raw_token}",
            expires_hours=settings.email_verification_expire_hours,
        )
        self.mail.send(
            to=user.email,
            subject=content.subject,
            html_body=content.html_body,
            text_body=content.text_body,
        )

    def verify_email(self, raw_token: str) -> None:
        """Activa la cuenta a partir del enlace de verificación."""
        token = self.repo.get_valid_verification_token(
            hash_token(raw_token), TokenPurpose.EMAIL_VERIFICATION
        )
        if token is None:
            raise UnauthorizedError(
                "El enlace de verificación no es válido o ya venció. "
                "Solicita uno nuevo desde la página de inicio de sesión."
            )

        user = self.repo.get_user_by_id(token.user_id)
        if user is None:
            raise UnauthorizedError("El enlace de verificación no es válido.")

        self.repo.mark_token_used(token)

        # Un usuario ya activo que reutiliza el enlace no debe recibir un error:
        # el resultado buscado (cuenta verificada) ya se cumple.
        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE

        self.session.commit()
        logger.info("email_verified", user_id=str(user.id))

    def resend_verification(self, email: str, frontend_url: str) -> None:
        """Reenvía el correo de verificación si procede.

        No revela si la cuenta existe ni si ya estaba verificada.
        """
        user = self.repo.get_user_by_email(email.strip().lower())
        if user is None or user.status != UserStatus.PENDING_VERIFICATION:
            return

        self._send_verification_email(user, frontend_url)
        self.session.commit()

    # ------------------------------------------------------------------
    # Inicio y cierre de sesión
    # ------------------------------------------------------------------
    def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[TokenResponse, User]:
        """Autentica y emite el par de tokens."""
        user = self.repo.get_user_by_email(email.strip().lower())

        # Se verifica la contraseña incluso si el usuario no existe, contra un
        # hash de descarte, para que el tiempo de respuesta no delate qué
        # correos están registrados.
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise UnauthorizedError("Correo o contraseña incorrectos.")

        if not verify_password(password, user.password_hash):
            logger.info("login_failed", user_id=str(user.id))
            raise UnauthorizedError("Correo o contraseña incorrectos.")

        if user.status == UserStatus.PENDING_VERIFICATION:
            raise UnauthorizedError(
                "Debes verificar tu correo antes de iniciar sesión. "
                "Revisa tu bandeja de entrada o solicita un nuevo enlace."
            )

        if user.status == UserStatus.SUSPENDED:
            raise UnauthorizedError("Esta cuenta está suspendida. Contacta con soporte.")

        # Si los parámetros de Argon2 se endurecieron desde el último acceso,
        # se recalcula el hash aprovechando que la contraseña está disponible.
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        self.repo.touch_last_login(user.id)
        tokens = self._issue_tokens(user, user_agent, ip_address)
        self.session.commit()

        logger.info("login_succeeded", user_id=str(user.id))
        return tokens, user

    def refresh(
        self, raw_refresh_token: str, user_agent: str | None, ip_address: str | None
    ) -> TokenResponse:
        """Renueva la sesión rotando el refresh token.

        El token usado se revoca al emitir el nuevo: si uno filtrado se reutiliza
        después, ya no sirve.
        """
        stored = self.repo.get_active_refresh_token(hash_token(raw_refresh_token))
        if stored is None:
            raise UnauthorizedError("La sesión expiró. Inicia sesión nuevamente.")

        user = self.repo.get_user_by_id(stored.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise UnauthorizedError("La sesión ya no es válida.")

        self.repo.revoke_refresh_token(stored)
        tokens = self._issue_tokens(user, user_agent, ip_address)
        self.session.commit()
        return tokens

    def logout(self, raw_refresh_token: str) -> None:
        """Cierra la sesión revocando su refresh token (HU-TRX-02, CA3)."""
        stored = self.repo.get_active_refresh_token(hash_token(raw_refresh_token))
        if stored is not None:
            self.repo.revoke_refresh_token(stored)
            self.session.commit()

    def _issue_tokens(
        self, user: User, user_agent: str | None, ip_address: str | None
    ) -> TokenResponse:
        access_token, expires_at = create_access_token(user.id, user.role_codes)
        refresh_raw, refresh_expires, refresh_hash = create_refresh_token(user.id)

        self.repo.store_refresh_token(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_expires,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_raw,
            expires_at=expires_at,
        )

    # ------------------------------------------------------------------
    # Contraseñas
    # ------------------------------------------------------------------
    def request_password_reset(self, email: str, frontend_url: str) -> None:
        """Envía el enlace de restablecimiento si la cuenta existe.

        Responde igual exista o no (HU-CC-02, CA4).
        """
        user = self.repo.get_user_by_email(email.strip().lower())
        if user is None or user.status == UserStatus.SUSPENDED:
            return

        self.repo.invalidate_pending_tokens(user.id, TokenPurpose.PASSWORD_RESET)

        raw_token, token_hash = generate_one_time_token()
        expires_at = datetime.now(UTC) + timedelta(hours=settings.password_reset_expire_hours)
        self.repo.create_verification_token(
            user.id, TokenPurpose.PASSWORD_RESET, token_hash, expires_at
        )

        content = password_reset_email(
            full_name=user.full_name,
            reset_url=f"{frontend_url}/restablecer-contrasena?token={raw_token}",
            expires_hours=settings.password_reset_expire_hours,
        )
        self.mail.send(
            to=user.email,
            subject=content.subject,
            html_body=content.html_body,
            text_body=content.text_body,
        )
        self.session.commit()

    def confirm_password_reset(self, raw_token: str, new_password: str) -> None:
        """Fija la nueva contraseña y cierra todas las sesiones."""
        token = self.repo.get_valid_verification_token(
            hash_token(raw_token), TokenPurpose.PASSWORD_RESET
        )
        if token is None:
            raise UnauthorizedError("El enlace no es válido o ya venció. Solicita uno nuevo.")

        user = self.repo.get_user_by_id(token.user_id)
        if user is None:
            raise UnauthorizedError("El enlace no es válido.")

        user.password_hash = hash_password(new_password)
        self.repo.mark_token_used(token)
        revoked = self.repo.revoke_all_user_sessions(user.id)

        # Restablecer la contraseña implica probar el control del correo, así
        # que sirve también para activar una cuenta que quedó sin verificar.
        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE

        self.session.commit()

        content = password_changed_email(user.full_name)
        self.mail.send(
            to=user.email,
            subject=content.subject,
            html_body=content.html_body,
            text_body=content.text_body,
        )
        logger.info("password_reset_completed", user_id=str(user.id), sessions_revoked=revoked)

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Cambia la contraseña de un usuario autenticado."""
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("La contraseña actual no es correcta.")

        if verify_password(new_password, user.password_hash):
            raise ConflictError("La nueva contraseña debe ser distinta de la actual.")

        user.password_hash = hash_password(new_password)
        revoked = self.repo.revoke_all_user_sessions(user.id)
        self.session.commit()

        content = password_changed_email(user.full_name)
        self.mail.send(
            to=user.email,
            subject=content.subject,
            html_body=content.html_body,
            text_body=content.text_body,
        )
        logger.info("password_changed", user_id=str(user.id), sessions_revoked=revoked)


# Hash de descarte con el que se compara cuando el correo no existe, para que
# el tiempo de respuesta del login no revele si la cuenta está registrada.
_DUMMY_HASH = hash_password(f"unused-{uuid.uuid4()}")
