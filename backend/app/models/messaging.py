"""Conversaciones, mensajes, notificaciones y solicitudes comerciales."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import NotificationType, RequestStatus, RequestType

if TYPE_CHECKING:
    from app.models.catalog import Product


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Hilo de mensajes entre un comprador y un productor.

    Opcionalmente asociado a un producto o a una sub-orden para dar contexto.
    En el MVP la mensajería es asíncrona: el chat en tiempo real es fase 2
    (HU-CC-13, CA3).
    """

    __tablename__ = "conversations"

    buyer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    sub_order_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sub_orders.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conversations_buyer", "buyer_id", "last_message_at"),
        Index("ix_conversations_producer", "producer_id", "last_message_at"),
    )


class Message(Base, UUIDPrimaryKeyMixin, SoftDeleteMixin):
    """Mensaje dentro de una conversación.

    El cuerpo se sanitiza antes de persistirse, no solo al renderizarse: si un
    consumidor futuro de estos datos no escapa el contenido, no habrá inyección
    almacenada esperando (HU-CC-13, CA4).
    """

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_conversation", "conversation_id", "created_at"),)


class Notification(Base, UUIDPrimaryKeyMixin):
    """Notificación dirigida a un usuario.

    `is_transactional` marca las que no pueden desactivarse: el comprador puede
    silenciar avisos comerciales, nunca el estado de su pedido (HU-CC-12, CA2).
    """

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        pg_enum(NotificationType, "notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notification_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    is_transactional: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Ordena la bandeja poniendo primero las no leídas.
        Index("ix_notifications_inbox", "user_id", "read_at", "created_at"),
    )


class CommercialRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Solicitud de muestra o de cotización de un comprador empresarial.

    Se unifican en una sola entidad porque el productor las atiende desde la
    misma bandeja y comparten ciclo de vida (HU-PRO-10). El tipo las distingue.
    """

    __tablename__ = "commercial_requests"

    type: Mapped[RequestType] = mapped_column(pg_enum(RequestType, "request_type"), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("business_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    producer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("producer_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    quantity_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    presentation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    required_by: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[RequestStatus] = mapped_column(
        pg_enum(RequestStatus, "request_status"),
        default=RequestStatus.PENDING,
        nullable=False,
    )

    # Respuesta del productor. En el MVP es única: el ciclo de contraofertas
    # queda para fase 2 (HU-CE-04, CA3).
    quoted_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    quote_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship()

    __table_args__ = (
        Index("ix_commercial_requests_producer", "producer_id", "status", "created_at"),
        Index("ix_commercial_requests_business", "business_id", "created_at"),
        CheckConstraint("quantity_kg IS NULL OR quantity_kg > 0", name="request_quantity_positive"),
    )
