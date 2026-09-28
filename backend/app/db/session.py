"""Motor de base de datos y gestión de sesiones."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # descarta conexiones caídas antes de usarlas
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    echo=settings.app_debug and not settings.is_production,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_session() -> Generator[Session, None, None]:
    """Dependencia de FastAPI que entrega una sesión por petición.

    La transacción se confirma o revierte en el servicio, no aquí: este
    generador solo garantiza que la sesión se cierre siempre.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
