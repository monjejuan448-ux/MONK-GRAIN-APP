"""Excepciones de dominio y sus manejadores HTTP.

Los servicios lanzan excepciones de dominio sin conocer códigos HTTP; la
traducción a respuesta ocurre en un único lugar. Así una regla de negocio no
queda acoplada al transporte.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger

logger = get_logger(__name__)


class DomainError(Exception):
    """Error de negocio. Base de todas las excepciones de dominio."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    """El recurso solicitado no existe o no es visible para quien consulta."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    """La operación choca con el estado actual del recurso."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class UnauthorizedError(DomainError):
    """Falta autenticación o las credenciales no son válidas."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(DomainError):
    """El usuario está autenticado pero no tiene permiso sobre el recurso."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class BusinessRuleError(DomainError):
    """Se incumple una regla de negocio (stock, transición de estado, cupón...)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "business_rule_violation"


class InsufficientStockError(BusinessRuleError):
    """No hay inventario suficiente para completar la operación."""

    code = "insufficient_stock"


class InvalidStateTransitionError(BusinessRuleError):
    """La transición de estado solicitada no está permitida."""

    code = "invalid_state_transition"


class RateLimitError(DomainError):
    """Se superó el número de peticiones permitido."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_exceeded"


class ExternalServiceError(DomainError):
    """Falló un servicio del que dependemos (almacenamiento, correo, pagos).

    Se responde 503 y no 500 a propósito: el fallo es de una dependencia y la
    operación puede prosperar si se reintenta, algo que un 500 no comunica.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "external_service_unavailable"


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores de excepción de la aplicación."""

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]),
                # Pydantic antepone «Value error, » a los mensajes que lanzan
                # los validadores propios. Es ruido para quien rellena el
                # formulario: el texto que sigue ya está redactado para él.
                "message": error["msg"].removeprefix("Value error, "),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                "validation_error",
                "Algunos datos enviados no son válidos.",
                {"fields": fields},
            ),
        )

    @app.exception_handler(ValidationError)
    async def handle_model_validation_error(
        _request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Valida modelos construidos dentro del endpoint.

        FastAPI solo convierte en 422 lo que valida al recibir la petición. Un
        modelo armado a mano en el cuerpo del endpoint —como ocurre al recomponer
        un formulario multiparte— lanza esta excepción fuera de ese ciclo y, sin
        este manejador, llegaría al cliente como un 500 opaco pese a tratarse de
        un dato mal enviado.
        """
        fields = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": str(error["msg"]).removeprefix("Value error, "),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                "validation_error",
                "Algunos datos enviados no son válidos.",
                {"fields": fields},
            ),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
        # El detalle de la restricción violada revela estructura interna:
        # se registra en el log, no se devuelve al cliente.
        logger.warning("integrity_error", error=str(exc.orig))
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body(
                "conflict",
                "La operación entra en conflicto con datos existentes.",
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "internal_error",
                "Ocurrió un error inesperado. El equipo ha sido notificado.",
            ),
        )
