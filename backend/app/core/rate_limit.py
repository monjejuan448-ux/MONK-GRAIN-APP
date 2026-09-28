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


def consume(scope: str, identifier: str, limit: int, window_seconds: int) -> bool:
    """Cuenta una petición y dice si el cliente sigue dentro de su cupo.

    Devuelve `False` cuando lo superó. Si Redis no está disponible responde
    `True`: un fallo de la caché no debe dejar la plataforma inoperativa, y el
    incidente queda registrado.

    Está separado de la dependencia para que el middleware que aplica el límite
    general use exactamente el mismo contador y la misma ventana. Dos
    implementaciones del mismo conteo acabarían divergiendo.
    """
    key = f"rl:{scope}:{identifier}"
    try:
        client = get_redis()
        current = client.incr(key)
        if current == 1:
            client.expire(key, window_seconds)
    except redis.RedisError as exc:
        logger.error("rate_limit_unavailable", scope=scope, error=str(exc))
        return True

    if current > limit:
        logger.warning("rate_limit_exceeded", scope=scope, key=key, count=current)
        return False
    return True


def is_internal_caller(request: Request) -> bool:
    """Si la petición viene de nuestro propio servidor y no de un cliente.

    El renderizado del servidor de Next.js llama a la API por la red interna de
    Docker, sin pasar por el proxy. Todas esas peticiones comparten la dirección
    del contenedor, de modo que un límite por cliente las metería **a todas en el
    mismo cupo**: el catálogo de la portada agotaría 120 peticiones por minuto
    entre todos los visitantes del sitio a la vez, y la página dejaría de cargar
    para todo el mundo.

    Se reconocen por dos cosas juntas: no traen `X-Forwarded-For` —que Nginx
    añade a todo lo que entra de fuera— y su dirección es privada. Una petición
    externa no puede cumplir ambas en producción.

    En desarrollo no hay proxy, así que el navegador también cae aquí. Es
    aceptable: sin proxy delante, limitar por dirección no protege de nada, y el
    límite propio de cada endpoint —el de inicio de sesión, el de subidas— sigue
    aplicándose porque no consulta esta función.
    """
    if request.headers.get("X-Forwarded-For"):
        return False

    host = request.client.host if request.client else None
    if host is None:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback


def rate_limit(scope: str, limit: int, window_seconds: int = 60) -> Callable[[Request], None]:
    """Construye una dependencia que limita las peticiones por cliente."""

    def dependency(request: Request) -> None:
        if not consume(scope, client_identifier(request), limit, window_seconds):
            raise RateLimitError(
                "Demasiados intentos. Espera unos minutos antes de volver a intentarlo."
            )

    return dependency
