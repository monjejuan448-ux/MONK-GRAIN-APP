"""Límite de peticiones respaldado por Redis.

Protege los endpoints de autenticación contra fuerza bruta (RNF-04). Los
contadores viven en Redis para que el límite sea compartido entre instancias:
un contador en memoria dejaría de servir en cuanto se escale a más de un
proceso.
"""

import ipaddress
from collections.abc import Callable

import redis
from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def client_identifier(request: Request) -> str:
    """Identifica al cliente para contar sus peticiones.

    Detrás del proxy se usa la primera dirección de `X-Forwarded-For`, que es la
    del cliente real. Solo debe confiarse en esa cabecera cuando el proxy es
    propio, como ocurre aquí con Nginx.

    El valor puede no ser una IP válida (un cliente de pruebas, un socket Unix):
    para el contador da igual, pero no sirve para la columna `INET`. Ese caso lo
    resuelve `client_ip`.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def client_ip(request: Request) -> str | None:
    """Devuelve la IP del cliente solo si es una dirección válida.

    Las columnas `INET` de PostgreSQL rechazan cualquier texto que no sea una
    IP, y un valor inválido abortaría la operación completa —por ejemplo, un
    inicio de sesión— por un dato meramente informativo. Ante la duda se guarda
    `NULL`.
    """
    candidate = client_identifier(request)
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        logger.debug("client_ip_not_parseable", value=candidate)
        return None


def rate_limit(scope: str, limit: int, window_seconds: int = 60) -> Callable[[Request], None]:
    """Construye una dependencia que limita las peticiones por cliente.

    Si Redis no está disponible, la petición se deja pasar: un fallo de la
    caché no debe dejar la plataforma inoperativa. El incidente se registra.
    """

    def dependency(request: Request) -> None:
        key = f"rl:{scope}:{client_identifier(request)}"
        try:
            client = get_redis()
            current = client.incr(key)
            if current == 1:
                client.expire(key, window_seconds)
        except redis.RedisError as exc:
            logger.error("rate_limit_unavailable", scope=scope, error=str(exc))
            return

        if current > limit:
            logger.warning("rate_limit_exceeded", scope=scope, key=key, count=current)
            raise RateLimitError(
                "Demasiados intentos. Espera unos minutos antes de volver a intentarlo."
            )

    return dependency
