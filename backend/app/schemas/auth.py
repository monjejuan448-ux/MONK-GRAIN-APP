"""Schemas de autenticación."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Email, ORMModel, PasswordField


class RegisterRequest(PasswordField):
    """Datos de registro de un comprador.

    El consentimiento de tratamiento de datos es obligatorio y explícito: la
    Ley 1581 de 2012 no admite un consentimiento tácito ni preseleccionado.
    """

    email: Email
    full_name: str = Field(min_length=3, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    data_consent: bool

    @field_validator("data_consent")
    @classmethod
    def consent_must_be_granted(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "Debes autorizar el tratamiento de tus datos personales para crear una cuenta."
            )
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class LoginRequest(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    """Par de tokens emitido tras autenticarse."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — esquema HTTP, no una credencial
    expires_at: datetime


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=255)


class ResendVerificationRequest(BaseModel):
    email: Email


class PasswordResetRequest(BaseModel):
    email: Email


class PasswordResetConfirm(PasswordField):
    token: str = Field(min_length=1, max_length=255)


class ChangePasswordRequest(PasswordField):
    current_password: str = Field(min_length=1, max_length=128)


class RoleResponse(ORMModel):
    code: str
    name: str


class CurrentUserResponse(ORMModel):
    """Perfil del usuario autenticado.

    No expone `password_hash` ni ningún dato bancario: los schemas de salida son
    la última barrera antes de que un campo sensible salga del servidor.
    """

    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    avatar_key: str | None
    status: str
    locale: str
    email_notifications_enabled: bool
    roles: list[RoleResponse]
    permissions: list[str] = []
    created_at: datetime
