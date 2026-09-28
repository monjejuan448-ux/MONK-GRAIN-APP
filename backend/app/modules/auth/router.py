"""Endpoints de autenticación."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import CurrentUser, collect_permissions
from app.core.rate_limit import client_ip, rate_limit
from app.db.session import get_session
from app.modules.auth.service import AuthService
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["autenticación"])

SessionDep = Annotated[Session, Depends(get_session)]

# Mensaje idéntico exista o no la cuenta: el endpoint no debe servir para
# averiguar qué correos están registrados.
NEUTRAL_REGISTER_MESSAGE = (
    "Si el correo no estaba registrado, te enviamos un enlace de verificación. "
    "Revisa tu bandeja de entrada."
)
NEUTRAL_RESET_MESSAGE = (
    "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña."
)


def _frontend_url(request: Request) -> str:
    """Base del frontend para construir los enlaces de los correos."""
    origin = request.headers.get("Origin")
    if origin and origin in settings.cors_origins:
        return origin
    return settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Registrar una cuenta de comprador",
    dependencies=[Depends(rate_limit("register", limit=5, window_seconds=300))],
)
def register(payload: RegisterRequest, request: Request, session: SessionDep) -> MessageResponse:
    """Crea la cuenta en estado pendiente y envía el correo de verificación."""
    AuthService(session).register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        phone=payload.phone,
        data_consent=payload.data_consent,
        frontend_url=_frontend_url(request),
    )
    return MessageResponse(message=NEUTRAL_REGISTER_MESSAGE)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verificar el correo electrónico",
    dependencies=[Depends(rate_limit("verify", limit=10, window_seconds=300))],
)
def verify_email(payload: VerifyEmailRequest, session: SessionDep) -> MessageResponse:
    AuthService(session).verify_email(payload.token)
    return MessageResponse(message="Tu correo fue verificado. Ya puedes iniciar sesión.")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reenviar el correo de verificación",
    dependencies=[Depends(rate_limit("resend", limit=3, window_seconds=600))],
)
def resend_verification(
    payload: ResendVerificationRequest, request: Request, session: SessionDep
) -> MessageResponse:
    AuthService(session).resend_verification(payload.email, _frontend_url(request))
    return MessageResponse(
        message="Si la cuenta existe y está pendiente de verificación, enviamos un nuevo enlace."
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    dependencies=[
        Depends(
            rate_limit(
                "login",
                limit=settings.rate_limit_login_per_minute,
                window_seconds=60,
            )
        )
    ],
)
def login(payload: LoginRequest, request: Request, session: SessionDep) -> TokenResponse:
    """Autentica y devuelve el par de tokens."""
    tokens, _ = AuthService(session).login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("User-Agent"),
        ip_address=client_ip(request),
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse, summary="Renovar la sesión")
def refresh(payload: RefreshRequest, request: Request, session: SessionDep) -> TokenResponse:
    """Rota el refresh token y emite un nuevo par."""
    return AuthService(session).refresh(
        payload.refresh_token,
        user_agent=request.headers.get("User-Agent"),
        ip_address=client_ip(request),
    )


@router.post("/logout", response_model=MessageResponse, summary="Cerrar sesión")
def logout(payload: RefreshRequest, session: SessionDep) -> MessageResponse:
    """Revoca el refresh token de la sesión actual."""
    AuthService(session).logout(payload.refresh_token)
    return MessageResponse(message="Sesión cerrada.")


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar el restablecimiento de la contraseña",
    dependencies=[Depends(rate_limit("password_reset", limit=3, window_seconds=600))],
)
def request_password_reset(
    payload: PasswordResetRequest, request: Request, session: SessionDep
) -> MessageResponse:
    AuthService(session).request_password_reset(payload.email, _frontend_url(request))
    return MessageResponse(message=NEUTRAL_RESET_MESSAGE)


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirmar la nueva contraseña",
    dependencies=[Depends(rate_limit("password_reset_confirm", limit=5, window_seconds=600))],
)
def confirm_password_reset(payload: PasswordResetConfirm, session: SessionDep) -> MessageResponse:
    AuthService(session).confirm_password_reset(payload.token, payload.password)
    return MessageResponse(
        message="Tu contraseña fue actualizada y se cerraron tus sesiones activas."
    )


@router.post("/change-password", response_model=MessageResponse, summary="Cambiar la contraseña")
def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, session: SessionDep
) -> MessageResponse:
    AuthService(session).change_password(user, payload.current_password, payload.password)
    return MessageResponse(
        message="Tu contraseña fue actualizada y se cerraron tus sesiones activas."
    )


@router.get("/me", response_model=CurrentUserResponse, summary="Perfil del usuario actual")
def get_me(user: CurrentUser) -> CurrentUserResponse:
    """Devuelve el perfil autenticado con sus roles y permisos efectivos."""
    response = CurrentUserResponse.model_validate(user)
    response.permissions = sorted(collect_permissions(user))
    return response
