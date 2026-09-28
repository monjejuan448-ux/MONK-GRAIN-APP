"""Panel administrativo: aprobaciones, métricas y auditoría."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate_query
from app.models.catalog import Product, Review
from app.models.content import AuditLog
from app.models.enums import (
    NotificationType,
    ProducerStatus,
    ProductStatus,
    ReviewStatus,
    RoleCode,
    SubOrderStatus,
    UserStatus,
)
from app.models.geo import Department, Municipality
from app.models.messaging import Notification
from app.models.order import Order, SubOrder
from app.models.producer import ProducerProfile
from app.models.user import Role, User, UserRole
from app.schemas.dashboard import (
    AdminDashboard,
    AdminUserItem,
    AuditLogEntry,
    PendingProducerItem,
)

logger = get_logger(__name__)


class AdminService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Auditoría
    # ------------------------------------------------------------------
    def _audit(
        self,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: str | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Registra una acción administrativa sensible.

        La tabla es de solo inserción: no hay endpoint para editarla ni
        borrarla, de modo que el registro no puede reescribirse a posteriori
        (HU-ADM-09, CA3).
        """
        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before,
                after_state=after,
                ip_address=ip_address,
            )
        )
        self.session.flush()

    # ------------------------------------------------------------------
    # Panel
    # ------------------------------------------------------------------
    def get_dashboard(self, days: int = 30) -> AdminDashboard:
        since = datetime.now(UTC) - timedelta(days=days)

        total_users = (
            self.session.scalar(
                select(func.count()).select_from(User).where(User.deleted_at.is_(None))
            )
            or 0
        )
        new_users = (
            self.session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.deleted_at.is_(None), User.created_at >= since)
            )
            or 0
        )

        pending_producers = self._count_producers(ProducerStatus.PENDING_APPROVAL)
        approved_producers = self._count_producers(ProducerStatus.APPROVED)

        total_products = (
            self.session.scalar(
                select(func.count()).select_from(Product).where(Product.deleted_at.is_(None))
            )
            or 0
        )
        published_products = (
            self.session.scalar(
                select(func.count())
                .select_from(Product)
                .where(Product.deleted_at.is_(None), Product.status == ProductStatus.PUBLISHED)
            )
            or 0
        )

        orders_period = (
            self.session.scalar(
                select(func.count()).select_from(Order).where(Order.placed_at >= since)
            )
            or 0
        )

        # Los ingresos cuentan solo ventas consumadas; un pedido cancelado no
        # es facturación y contarlo daría una lectura falsa del negocio.
        realized = (
            SubOrderStatus.CONFIRMED,
            SubOrderStatus.PREPARED,
            SubOrderStatus.SHIPPED,
            SubOrderStatus.DELIVERED,
        )
        revenue = self.session.execute(
            select(
                func.coalesce(func.sum(SubOrder.subtotal), 0),
                func.coalesce(func.sum(SubOrder.commission_amount), 0),
            ).where(SubOrder.created_at >= since, SubOrder.status.in_(realized))
        ).one()

        status_rows = self.session.execute(
            select(SubOrder.status, func.count(SubOrder.id))
            .where(SubOrder.created_at >= since)
            .group_by(SubOrder.status)
        ).all()

        reported_reviews = (
            self.session.scalar(
                select(func.count())
                .select_from(Review)
                .where(Review.status == ReviewStatus.REPORTED)
            )
            or 0
        )

        return AdminDashboard(
            total_users=total_users,
            new_users_period=new_users,
            pending_producers=pending_producers,
            approved_producers=approved_producers,
            total_products=total_products,
            published_products=published_products,
            orders_period=orders_period,
            revenue_period=Decimal(str(revenue[0])),
            commission_period=Decimal(str(revenue[1])),
            orders_by_status={row[0].value: int(row[1]) for row in status_rows},
            reported_reviews=reported_reviews,
        )

    def _count_producers(self, status: ProducerStatus) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(ProducerProfile)
                .where(
                    ProducerProfile.status == status,
                    ProducerProfile.deleted_at.is_(None),
                )
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Aprobación de vendedores
    # ------------------------------------------------------------------
    def list_users(
        self,
        params: PageParams,
        *,
        q: str | None = None,
        status: UserStatus | None = None,
        role: RoleCode | None = None,
    ) -> Page[AdminUserItem]:
        """Cuentas de la plataforma, con búsqueda por correo o nombre.

        Existía el endpoint para suspender una cuenta pero no había forma de
        encontrarla: había que conocer su identificador de memoria. Sin este
        listado, la suspensión era inalcanzable en la práctica.
        """
        statement = (
            select(User)
            .where(User.deleted_at.is_(None))
            .options(joinedload(User.producer_profile))
            .order_by(User.created_at.desc(), User.id)
        )

        if q:
            pattern = f"%{q.strip()}%"
            statement = statement.where(
                or_(
                    User.email.ilike(pattern),
                    func.unaccent(User.full_name).ilike(func.unaccent(pattern)),
                )
            )
        if status is not None:
            statement = statement.where(User.status == status)
        if role is not None:
            statement = statement.where(
                User.id.in_(
                    select(UserRole.user_id)
                    .join(Role, Role.id == UserRole.role_id)
                    .where(Role.code == role.value)
                )
            )

        users, total = paginate_query(self.session, statement, params)

        # Los pedidos de toda la página en una sola consulta, no uno por fila.
        order_counts: dict[uuid.UUID, int] = {}
        if users:
            rows = self.session.execute(
                select(Order.user_id, func.count(Order.id))
                .where(Order.user_id.in_([user.id for user in users]))
                .group_by(Order.user_id)
            ).all()
            order_counts = {row[0]: row[1] for row in rows}

        items = [
            AdminUserItem(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                status=user.status,
                roles=sorted(role.code for role in user.roles),
                is_producer=user.producer_profile is not None,
                producer_status=(
                    user.producer_profile.status.value if user.producer_profile else None
                ),
                order_count=order_counts.get(user.id, 0),
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            )
            for user in users
        ]
        return Page.create(items, total, params)

    def list_pending_producers(self, params: PageParams) -> Page[PendingProducerItem]:
        statement = (
            select(ProducerProfile)
            .where(
                ProducerProfile.status == ProducerStatus.PENDING_APPROVAL,
                ProducerProfile.deleted_at.is_(None),
            )
            .options(joinedload(ProducerProfile.user, innerjoin=False))
            .order_by(ProducerProfile.created_at.asc(), ProducerProfile.id)
        )
        profiles, total = paginate_query(self.session, statement, params)

        items: list[PendingProducerItem] = []
        for profile in profiles:
            owner = self.session.get(User, profile.user_id)
            municipality = self.session.get(Municipality, profile.municipality_id)
            department = self.session.get(Department, profile.department_id)

            items.append(
                PendingProducerItem(
                    id=profile.id,
                    legal_name=profile.legal_name,
                    brand_name=profile.brand_name,
                    type=profile.type.value,
                    document_number=profile.document_number,
                    contact_email=owner.email if owner else "—",
                    contact_name=owner.full_name if owner else "—",
                    municipality=municipality.name if municipality else None,
                    department=department.name if department else None,
                    production_capacity_kg=profile.production_capacity_kg,
                    status=profile.status,
                    created_at=profile.created_at,
                )
            )

        return Page.create(items, total, params)

    def review_producer(
        self,
        admin: User,
        producer_id: uuid.UUID,
        approve: bool,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> PendingProducerItem:
        """Aprueba o rechaza una solicitud de vendedor (HU-ADM-01)."""
        profile = self.session.scalar(
            select(ProducerProfile).where(ProducerProfile.id == producer_id)
        )
        if profile is None:
            raise NotFoundError("No encontramos este productor.")

        if profile.status != ProducerStatus.PENDING_APPROVAL:
            raise BusinessRuleError(
                f"Esta solicitud ya fue revisada (estado actual: {profile.status.value})."
            )

        # El motivo es obligatorio al rechazar: sin él, el productor no sabe qué
        # corregir para volver a intentarlo (HU-ADM-01, CA3).
        if not approve and not reason:
            raise BusinessRuleError("Debes indicar el motivo del rechazo.")

        before = {"status": profile.status.value}

        profile.status = ProducerStatus.APPROVED if approve else ProducerStatus.REJECTED
        profile.rejection_reason = None if approve else reason
        profile.reviewed_by = admin.id
        profile.reviewed_at = datetime.now(UTC)

        owner = self.session.get(User, profile.user_id)
        if approve and owner is not None:
            self._grant_producer_role(owner)

        if owner is not None:
            self.session.add(
                Notification(
                    user_id=owner.id,
                    type=(
                        NotificationType.PRODUCER_APPROVED
                        if approve
                        else NotificationType.PRODUCER_REJECTED
                    ),
                    title="Solicitud aprobada" if approve else "Solicitud rechazada",
                    body=(
                        "Tu perfil de productor fue aprobado. Ya puedes publicar tus cafés."
                        if approve
                        else f"Tu solicitud fue rechazada. Motivo: {reason}"
                    ),
                    action_url="/productor",
                    is_transactional=True,
                )
            )

        self._audit(
            actor=admin,
            action="producer.approve" if approve else "producer.reject",
            entity_type="producer_profile",
            entity_id=str(profile.id),
            before=before,
            after={"status": profile.status.value, "reason": reason},
            ip_address=ip_address,
        )

        self.session.commit()
        logger.info(
            "producer_reviewed",
            producer_id=str(profile.id),
            approved=approve,
            admin_id=str(admin.id),
        )

        municipality = self.session.get(Municipality, profile.municipality_id)
        department = self.session.get(Department, profile.department_id)

        return PendingProducerItem(
            id=profile.id,
            legal_name=profile.legal_name,
            brand_name=profile.brand_name,
            type=profile.type.value,
            document_number=profile.document_number,
            contact_email=owner.email if owner else "—",
            contact_name=owner.full_name if owner else "—",
            municipality=municipality.name if municipality else None,
            department=department.name if department else None,
            production_capacity_kg=profile.production_capacity_kg,
            status=profile.status,
            created_at=profile.created_at,
        )

    def _grant_producer_role(self, user: User) -> None:
        """Concede el rol de productor si aún no lo tiene."""
        if RoleCode.PRODUCER.value in user.role_codes:
            return

        role = self.session.scalar(select(Role).where(Role.code == RoleCode.PRODUCER.value))
        if role is not None:
            self.session.add(UserRole(user_id=user.id, role_id=role.id))
            self.session.flush()

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------
    def suspend_user(
        self, admin: User, user_id: uuid.UUID, suspend: bool, ip_address: str | None = None
    ) -> None:
        """Suspende o reactiva una cuenta (HU-ADM-02, CA2 y CA3)."""
        target = self.session.get(User, user_id)
        if target is None or target.deleted_at is not None:
            raise NotFoundError("No encontramos este usuario.")

        if target.id == admin.id:
            raise BusinessRuleError("No puedes suspender tu propia cuenta.")

        before = {"status": target.status.value}
        target.status = UserStatus.SUSPENDED if suspend else UserStatus.ACTIVE

        # Suspender a un vendedor retira su catálogo de la vista pública sin
        # borrar nada: el filtro del catálogo excluye a los no aprobados.
        if suspend and target.producer_profile is not None:
            target.producer_profile.status = ProducerStatus.SUSPENDED

        self._audit(
            actor=admin,
            action="user.suspend" if suspend else "user.reactivate",
            entity_type="user",
            entity_id=str(target.id),
            before=before,
            after={"status": target.status.value},
            ip_address=ip_address,
        )
        self.session.commit()

    # ------------------------------------------------------------------
    # Moderación de reseñas
    # ------------------------------------------------------------------
    def moderate_review(
        self,
        admin: User,
        review_id: uuid.UUID,
        hide: bool,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Oculta o restablece una reseña reportada (HU-ADM-06)."""
        review = self.session.get(Review, review_id)
        if review is None or review.deleted_at is not None:
            raise NotFoundError("No encontramos esta reseña.")

        before = {"status": review.status.value}
        review.status = ReviewStatus.HIDDEN if hide else ReviewStatus.PUBLISHED
        review.moderation_reason = reason
        review.moderated_by = admin.id

        # El promedio debe excluir las reseñas ocultas (HU-ADM-06, CA3).
        from app.modules.catalog.repository import CatalogRepository

        CatalogRepository(self.session).recalculate_product_rating(review.product_id)

        self._audit(
            actor=admin,
            action="review.hide" if hide else "review.restore",
            entity_type="review",
            entity_id=str(review.id),
            before=before,
            after={"status": review.status.value, "reason": reason},
            ip_address=ip_address,
        )
        self.session.commit()

    # ------------------------------------------------------------------
    # Auditoría
    # ------------------------------------------------------------------
    def list_audit_logs(
        self,
        params: PageParams,
        action: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Page[AuditLogEntry]:
        statement = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())

        if action:
            statement = statement.where(AuditLog.action == action)
        if actor_id:
            statement = statement.where(AuditLog.actor_id == actor_id)

        logs, total = paginate_query(self.session, statement, params)

        items = []
        for log in logs:
            actor = self.session.get(User, log.actor_id) if log.actor_id else None
            items.append(
                AuditLogEntry(
                    id=log.id,
                    actor_email=actor.email if actor else None,
                    action=log.action,
                    entity_type=log.entity_type,
                    entity_id=log.entity_id,
                    created_at=log.created_at,
                )
            )

        return Page.create(items, total, params)
