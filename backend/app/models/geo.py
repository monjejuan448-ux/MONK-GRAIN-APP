"""División territorial de Colombia y regiones cafeteras.

Son datos de referencia estáticos y públicos: usan identificadores enteros en
lugar de UUID (ADR-05) y se cargan desde `db/seed.py` con los códigos DANE.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.producer import Farm


class Department(Base):
    """Departamento de Colombia."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    dane_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    municipalities: Mapped[list["Municipality"]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )


class Municipality(Base):
    """Municipio, con el centroide usado para la ubicación aproximada de fincas."""

    __tablename__ = "municipalities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    dane_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Centroide del municipio: base de la ubicación aproximada que se publica
    # en lugar de la coordenada real de la finca (ADR-08).
    centroid_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    centroid_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    department: Mapped["Department"] = relationship(back_populates="municipalities")
    farms: Mapped[list["Farm"]] = relationship(back_populates="municipality")


class Region(Base):
    """Región cafetera (Huila, Nariño, Eje Cafetero, ...)."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    farms: Mapped[list["Farm"]] = relationship(back_populates="region")
