"""Autenticación y autorización por endpoint.

La verificación ocurre siempre en el servidor. Ocultar una opción en la interfaz
no es control de acceso: cualquiera puede llamar al endpoint directamente
(HU-TRX-02, CA4).
"""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.db.session import get_session
from app.models.enums import RoleCode, UserStatus
from app.models.user import Role, User

# `auto_error=False` permite distinguir "sin credenciales" de "credenciales
# inválidas" y devolver un mensaje propio en lugar del genérico de FastAPI.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Resuelve el usuario autenticado a partir del access token.

    El usuario se recarga desde la base de datos en cada petición en lugar de
    confiar en los datos del token: si un administrador suspende una cuenta o
    revoca un rol, el cambio surte efecto de inmediato y no cuando expire el
    token.
    """
    if credentials is None:
        raise UnauthorizedError("Se requiere autenticación para esta operación.")

    payload = decode_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except ValueError as exc:
        raise UnauthorizedError("Token inválido.") from exc

    user = session.scalar(
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )

    if user is None:
        raise UnauthorizedError("Token inválido.")

    if user.status == UserStatus.SUSPENDED:
        raise ForbiddenError("Esta cuenta está suspendida. Contacta con soporte.")

    if user.status == UserStatus.PENDING_VERIFICATION:
        raise ForbiddenError(
            "Debes verificar tu correo electrónico antes de continuar.",
            details={"code": "email_not_verified"},
        )

    request.state.user_id = str(user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User | None:
    """Devuelve el usuario si hay sesión válida, o `None` si no la hay.

    Se usa en endpoints públicos cuyo contenido varía según quién consulta: el
    catálogo muestra precios mayoristas solo a un comprador empresarial
    verificado (HU-CE-02, CA2).
    """
    if credentials is None:
        return None
    try:
        return get_current_user(request, credentials, session)
    except (UnauthorizedError, ForbiddenError):
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def collect_permissions(user: User) -> set[str]:
    """Reúne los permisos efectivos del usuario a través de sus roles."""
    return {permission.code for role in user.roles for permission in role.permissions}


def require_permissions(*required: str) -> Callable[[User], User]:
    """Exige que el usuario tenga todos los permisos indicados.

    Ejemplo:
        @router.post("/products", dependencies=[Depends(require_permissions("product.create"))])
    """

    def dependency(user: CurrentUser) -> User:
        granted = collect_permissions(user)
        missing = set(required) - granted
        if missing:
            raise ForbiddenError("No tienes permiso para realizar esta acción.")
        return user

    return dependency


def require_roles(*allowed: RoleCode) -> Callable[[User], User]:
    """Exige que el usuario tenga al menos uno de los roles indicados."""
    allowed_codes = {role.value for role in allowed}

    def dependency(user: CurrentUser) -> User:
        if not allowed_codes & set(user.role_codes):
            raise ForbiddenError("No tienes permiso para acceder a esta sección.")
        return user

    return dependency


# Atajos para los casos más frecuentes.
require_admin = require_roles(RoleCode.ADMIN)
require_producer = require_roles(RoleCode.PRODUCER)
require_business = require_roles(RoleCode.BUSINESS)

AdminUser = Annotated[User, Depends(require_admin)]
ProducerUser = Annotated[User, Depends(require_producer)]
