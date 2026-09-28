"""Configuración compartida de las pruebas.

Las pruebas de integración usan una base de datos PostgreSQL real, no SQLite:
el esquema depende de tipos específicos de PostgreSQL (CITEXT, JSONB, ENUM
nativos, índices parciales) que SQLite no reproduce. Una prueba que pase contra
un motor distinto al de producción da una falsa sensación de seguridad.
"""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

TEST_DATABASE_SUFFIX = "_test"


def _test_database_url() -> str:
    """Deriva la URL de la base de datos de pruebas de la configuración real."""
    base_url = os.environ["DATABASE_URL"]
    if base_url.endswith(TEST_DATABASE_SUFFIX):
        return base_url
    return base_url + TEST_DATABASE_SUFFIX


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Crea la base de datos de pruebas y su esquema una vez por sesión."""
    admin_url = os.environ["DATABASE_URL"]
    test_url = _test_database_url()
    test_db_name = test_url.rsplit("/", 1)[-1]

    # La creación de la base de datos no puede ocurrir dentro de una
    # transacción, de ahí el nivel de aislamiento AUTOCOMMIT.
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
        connection.execute(text(f'CREATE DATABASE "{test_db_name}"'))
    admin_engine.dispose()

    test_engine = create_engine(test_url)
    with test_engine.connect() as connection:
        for extension in ("citext", "pg_trgm", "unaccent"):
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
        connection.commit()

    Base.metadata.create_all(test_engine)

    yield test_engine

    test_engine.dispose()
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
    admin_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    """Entrega una sesión aislada por prueba.

    Cada prueba corre dentro de una transacción que se revierte al terminar, de
    modo que ninguna prueba puede contaminar a la siguiente sin importar el
    orden en que se ejecuten.

    `autoflush=False` y `expire_on_commit=False` replican la configuración real
    de `app.db.session.SessionLocal`. No es un detalle: con `autoflush` activado
    —el valor por defecto— cualquier consulta arrastra los cambios pendientes, y
    una prueba pasa aunque el código dependa de un `flush` que en producción
    nunca ocurre. Así se ocultó durante meses que el promedio de calificación
    del productor se calculaba con el del café todavía sin escribir.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    db_session = session_factory()

    try:
        yield db_session
    finally:
        db_session.close()
        transaction.rollback()
        connection.close()
