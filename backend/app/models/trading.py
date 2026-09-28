"""Oferta y demanda: el lado del mercado que empieza en el comprador.

El catálogo resuelve un solo sentido del negocio —el vendedor publica y el
comprador elige—, y en pergamino falta el otro. Una trilladora que necesita
cinco cargas con factor 92 o menos no quiere recorrer el catálogo cada semana:
publica lo que busca, a qué precio, y espera que los caficultores le respondan.

Dos entidades:

- `DemandRequest` — lo que un comprador busca: kilos, techo de factor y de
  humedad, precio que ofrece y hasta cuándo.
- `DemandOffer` — la postura de un vendedor sobre esa solicitud, siempre
  respaldada por un lote real de su catálogo, con su análisis ya publicado. Sin
  ese respaldo la postura sería una promesa sin ficha técnica detrás.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import (
    RECEIVING_DEMAND_STATUSES,
    CoffeeProcess,
    DemandStatus,
    OfferStatus,
)

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.geo import Department, Municipality
    from app.models.producer import ProducerProfile
    from app.models.user import User


class DemandRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Solicitud de compra publicada por un comprador.

    Los requisitos de calidad son techos y no valores exactos: en el factor de
    rendimiento y en la humedad, menos es mejor, de modo que lo que un comprador
    declara es el máximo que acepta. Un lote con factor 88 satisface una solicitud
    que pide «92 o menos».
    """

    __tablename__ = "demand_requests"

    buyer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Kilos buscados y kilos ya cubiertos por posturas aceptadas. El segundo se
    # mantiene como columna y no se calcula al vuelo porque decide si la
    # solicitud sigue recibiendo posturas, y esa pregunta se hace en cada
    # listado.
    wanted_kg: Mapped[int] = mapped_column(nullable=False)
    covered_kg: Mapped[int] = mapped_column(default=0, nullable=False)

    # Techos de calidad. Nulo significa que el comprador no pone ese límite.
    max_yield_factor: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_moisture_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    variety: Mapped[str | None] = mapped_column(String(100), nullable=True)
    process: Mapped[CoffeeProcess | None] = mapped_column(
        pg_enum(CoffeeProcess, "coffee_process"), nullable=True
    )

    # Origen preferido. Nulo significa cualquier origen.
    department_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    municipality_id: Mapped[int | None] = mapped_column(
        ForeignKey("municipalities.id", ondelete="SET NULL"), nullable=True
    )

    # Precio por kilo que el comprador ofrece. Es una referencia, no un
    # compromiso: la postura del vendedor lleva su propio precio y el comprador
    # decide si lo acepta.
    offered_price_per_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Hasta cuándo tiene sentido responder. Una solicitud sin vigencia seguiría
    # apareciendo un año después, con un precio que ya no significa nada.
    expires_on: Mapped[date] = mapped_column(nullable=False)

    status: Mapped[DemandStatus] = mapped_column(
        pg_enum(DemandStatus, "demand_status"),
        default=DemandStatus.OPEN,
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    buyer: Mapped["User"] = relationship()
    department: Mapped["Department | None"] = relationship()
    municipality: Mapped["Municipality | None"] = relationship()
    offers: Mapped[list["DemandOffer"]] = relationship(
        back_populates="demand", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_demand_requests_buyer", "buyer_id", "created_at"),
        # Índice del listado que ven los vendedores: solicitudes vigentes,
        # ordenadas por vencimiento.
        Index("ix_demand_requests_open", "status", "expires_on"),
        CheckConstraint("wanted_kg > 0", name="wanted_kg_positive"),
        CheckConstraint("covered_kg >= 0", name="covered_kg_non_negative"),
        CheckConstraint(
            "max_yield_factor IS NULL OR (max_yield_factor >= 80 AND max_yield_factor <= 130)",
            name="demand_yield_factor_range",
        ),
        CheckConstraint(
            "max_moisture_pct IS NULL OR (max_moisture_pct >= 0 AND max_moisture_pct <= 100)",
            name="demand_moisture_range",
        ),
        CheckConstraint(
            "offered_price_per_kg IS NULL OR offered_price_per_kg > 0",
            name="demand_offered_price_positive",
        ),
    )

    @property
    def remaining_kg(self) -> int:
        """Kilos que todavía faltan por cubrir."""
        return max(0, self.wanted_kg - self.covered_kg)

    def is_receiving(self, today: date) -> bool:
        """Si admite posturas nuevas.

        El vencimiento se evalúa aquí y no con un estado guardado: mantenerlo al
        día exigiría un proceso que recorra la tabla cada noche, y una solicitud
        vencida se comporta igual si simplemente se deja de considerar vigente.
        """
        return self.status in RECEIVING_DEMAND_STATUSES and self.expires_on >= today


class DemandOffer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Postura de un vendedor sobre una solicitud de compra.

    Va siempre respaldada por un lote publicado: su análisis, su origen y su
    trazabilidad son los del lote, no datos que se escriban aquí de nuevo. Así el
    comprador juzga la postura con la misma ficha que vería en el catálogo.
    """

    __tablename__ = "demand_offers"

    demand_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("demand_requests.id", ondelete="CASCADE"), nullable=False
    )
    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    # Oferta concreta del lote de la que sale el precio y de la que se descontarán
    # los kilos si el comprador acepta.
    variant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )

    offered_kg: Mapped[int] = mapped_column(nullable=False)
    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[OfferStatus] = mapped_column(
        pg_enum(OfferStatus, "offer_status"),
        default=OfferStatus.PENDING,
        nullable=False,
    )
    # Motivo con el que el comprador rechaza. No es obligatorio, pero cuando
    # existe le dice al caficultor qué ajustar en la siguiente postura.
    response_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    demand: Mapped["DemandRequest"] = relationship(back_populates="offers")
    producer: Mapped["ProducerProfile"] = relationship()
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        # Una sola postura viva por vendedor y lote sobre la misma solicitud. Sin
        # esto, un vendedor podría inundar una solicitud con la misma oferta
        # repetida para aparecer primero en la lista.
        UniqueConstraint("demand_id", "producer_id", "variant_id", name="uq_demand_offers_unique"),
        Index("ix_demand_offers_demand", "demand_id", "status", "created_at"),
        Index("ix_demand_offers_producer", "producer_id", "created_at"),
        CheckConstraint("offered_kg > 0", name="offered_kg_positive"),
        CheckConstraint("price_per_kg > 0", name="offer_price_positive"),
    )
