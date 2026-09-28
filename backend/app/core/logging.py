"""Logs estructurados en JSON.

Se emiten a stdout para que el orquestador los recolecte. Nunca se registran
contraseñas, tokens, datos bancarios ni cargas completas de webhooks de pago.
"""

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings

# Claves cuyo valor se enmascara siempre que aparezcan en un evento de log.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "token_hash",
        "secret",
        "secret_key",
        "authorization",
        "bank_account",
        "bank_account_encrypted",
        "card_number",
        "cvv",
    }
)


def mask_sensitive(
    _logger: Any, _method_name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Reemplaza el valor de cualquier clave sensible por un marcador."""
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "***"
    return event_dict


def configure_logging() -> None:
    """Configura structlog y la librería estándar de logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.app_debug else logging.INFO,
    )

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        mask_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # En desarrollo se prioriza la legibilidad; en producción, el formato JSON.
    if settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.app_debug else logging.INFO
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Reduce el ruido de librerías de terceros.
    for noisy in ("uvicorn.access", "botocore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Devuelve un logger con nombre para el módulo indicado."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
