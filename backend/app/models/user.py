"""Identidad, control de acceso, sesiones y direcciones.

`users` es la única tabla de identidad. Ser productor o empresa es un perfil
asociado, no una tabla de usuario paralela: un tostador compra y vende con una
sola cuenta.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import TokenPurpose, UserStatus

if TYPE_CHECKING:
    from app.models.producer import BusinessProfile, ProducerProfile


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Cuenta de usuario."""

    __tablename__ = "users"

    # CITEXT hace la comparación insensible a mayúsculas: dos cuentas no pueden
    # diferenciarse solo por el uso de mayúsculas en el correo.
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    avatar_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[UserStatus] = mapped_column(
        pg_enum(UserStatus, "user_status"),
        default=UserStatus.PENDING_VERIFICATION,
        nullable=False,
    )

    # Consentimiento de tratamiento de datos (Ley 1581 de 2012).
    data_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    locale: Mapped[str] = mapped_column(String(10), default="es-CO", nullable=False)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # `user_roles` tiene dos claves foráneas hacia `users` (el titular del rol y
    # quién se lo concedió); el join debe declararse explícitamente porque
    # SQLAlchemy no puede deducir cuál de las dos usar.
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id",
        back_populates="users",
        lazy="selectin",
    )
    addresses: Mapped[list["Address"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    producer_profile: Mapped["ProducerProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        foreign_keys="ProducerProfile.user_id",
    )
    business_profile: Mapped["BusinessProfile | None"] = relationship(
        back_populates="user", uselist=False
    )

    __table_args__ = (
        # Índice único parcial: ignora las cuentas eliminadas lógicamente, de
        # modo que un correo dado de baja puede volver a registrarse.
        Index(
            "uq_users_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def has_role(self, role_code: str) -> bool:
        return any(role.code == role_code for role in self.roles)

    @property
    def role_codes(self) -> list[str]:
        return [role.code for role in self.roles]


class Role(Base):
    """Rol del sistema. Agrupa permisos (ADR-09)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship(
        secondary="user_roles",
        primaryjoin="Role.id == UserRole.role_id",
        secondaryjoin="User.id == UserRole.user_id",
        back_populates="roles",
    )
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions", back_populates="roles", lazy="selectin"
    )


class Permission(Base):
    """Permiso granular sobre un recurso.

    Permite al administrador ajustar capacidades sin desplegar código nuevo.
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary="role_permissions", back_populates="permissions"
    )


class UserRole(Base):
    """Asignación de rol a usuario."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class RolePermission(Base):
    """Permiso concedido a un rol."""

    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    """Refresh token revocable.

    Se almacena únicamente el hash: una filtración de esta tabla no entrega
    sesiones utilizables (HU-TRX-02, CA2 y CA3).
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_refresh_tokens_active",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )


class VerificationToken(Base, UUIDPrimaryKeyMixin):
    """Token de un solo uso para verificar el correo o restablecer la contraseña."""

    __tablename__ = "verification_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[TokenPurpose] = mapped_column(
        pg_enum(TokenPurpose, "token_purpose"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Address(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Dirección de entrega.

    Departamento y municipio se seleccionan del catálogo oficial, no como texto
    libre, para que el cálculo de envío sea confiable (HU-CC-03, CA2).
    """

    __tablename__ = "addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recipient_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    department_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    municipality_id: Mapped[int] = mapped_column(
        ForeignKey("municipalities.id", ondelete="RESTRICT"), nullable=False
    )
    street_address: Mapped[str] = mapped_column(String(255), nullable=False)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="addresses")

    __table_args__ = (
        # Una sola dirección predeterminada por usuario, garantizado por la base
        # de datos y no por lógica de aplicación.
        Index(
            "uq_addresses_default_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_default IS TRUE AND deleted_at IS NULL"),
        ),
        Index("ix_addresses_user", "user_id"),
    )
