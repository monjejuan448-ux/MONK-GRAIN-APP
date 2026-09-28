"""Punto de entrada de la API de MONK GRAIN."""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.cart.router import router as cart_router
from app.modules.catalog.router import router as catalog_router
from app.modules.orders.router import router as orders_router
from app.modules.producers.router import router as producers_router
from app.modules.returns.router import router as returns_router
from app.modules.reviews.router import router as reviews_router
from app.modules.users.router import router as users_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Arranque y apagado de la aplicación."""
    configure_logging()
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
    )
    yield
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Construye la aplicación FastAPI."""
    app = FastAPI(
        title=f"{settings.app_name} API",
        description=(
            "API del marketplace de café MONK GRAIN. "
            "Conecta caficultores, fincas y cooperativas con compradores."
        ),
        version="0.1.0",
        lifespan=lifespan,
        # La documentación interactiva queda deshabilitada en producción para
        # no publicar el mapa completo de la API.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language"],
    )

    register_middleware(app)
    register_exception_handlers(app)
    register_routers(app)

    return app


def register_middleware(app: FastAPI) -> None:
    """Registra el middleware propio de la aplicación."""

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Asigna un identificador a cada petición y registra su resultado.

        El identificador viaja en la cabecera `X-Request-ID` para poder
        correlacionar un error reportado por un usuario con sus logs.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        return response

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Añade cabeceras de seguridad a toda respuesta.

        Nginx las aplica en producción; declararlas también aquí evita que un
        despliegue sin proxy quede desprotegido.
        """
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # La API solo devuelve JSON: nada debe cargarse ni ejecutarse desde sus
        # respuestas. `default-src 'none'` convierte en inerte cualquier
        # contenido que llegara a servirse por error.
        #
        # La documentación interactiva se excluye porque Swagger UI carga su
        # propio CSS y JavaScript; en producción no se publica (ver `main`).
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
            )

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def register_routers(app: FastAPI) -> None:
    """Monta los routers de los módulos de dominio.

    Catálogo, carrito y pedidos se incorporan en la fase 8; los paneles
    administrativos, en la fase 9.
    """
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(catalog_router, prefix=settings.api_v1_prefix)
    app.include_router(cart_router, prefix=settings.api_v1_prefix)
    app.include_router(orders_router, prefix=settings.api_v1_prefix)
    app.include_router(returns_router, prefix=settings.api_v1_prefix)
    app.include_router(reviews_router, prefix=settings.api_v1_prefix)
    app.include_router(users_router, prefix=settings.api_v1_prefix)
    app.include_router(producers_router, prefix=settings.api_v1_prefix)
    app.include_router(admin_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["sistema"], summary="Comprobación de estado")
    async def health_check() -> dict[str, str]:
        """Indica que el servicio está en funcionamiento."""
        return {"status": "ok", "environment": settings.app_env}


app = create_app()
