"""Base declarativa y mixins compartidos por todos los modelos."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Convención de nombres para que las migraciones generen identificadores
# estables y predecibles en lugar de nombres automáticos de PostgreSQL.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def pg_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    """Construye un ENUM nativo de PostgreSQL a partir de un StrEnum.

    `values_callable` fuerza a que se almacenen los valores del enum y no los
    nombres de sus miembros, que es lo que SQLAlchemy usaría por defecto.
    """
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def to_dict(self) -> dict[str, Any]:
        """Representación en diccionario, útil para registros de auditoría."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class UUIDPrimaryKeyMixin:
    """Clave primaria UUID.

    Se usa en entidades expuestas al exterior para evitar que un identificador
    secuencial permita enumerar pedidos o usuarios ajenos (ADR-05).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Marcas de creación y última actualización."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Eliminación lógica.

    Se aplica solo a entidades con valor histórico o referencial: un pedido debe
    conservar el producto y la dirección con los que fue creado (ADR-06).
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
