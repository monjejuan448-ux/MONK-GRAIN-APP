"""Reseñas y calificaciones.

Una reseña vale por lo que acredita: que quien la escribe compró ese café y lo
recibió. Esa garantía no descansa en una comprobación del código sino en la
forma de la tabla —`order_item_id` es único y apunta a una línea de pedido
concreta—, de modo que ni un error de validación ni una petición malintencionada
pueden colar una opinión sobre un café que nunca se compró.

De ahí salen las tres reglas del módulo:

- **Solo se reseña lo entregado.** No basta con haber pagado: hasta que el café
  no llega, no hay nada que opinar.
- **Una reseña por línea de pedido.** Quien compra el mismo café dos veces puede
  reseñarlo dos veces, y es correcto: son dos experiencias distintas. Lo que no
  puede es reseñar dos veces la misma compra.
- **Se corrige, no se reescribe indefinidamente.** La edición está abierta un
  plazo acotado. Después la reseña queda como está: otros compradores ya
  decidieron con ella a la vista.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate_query
from app.models.catalog import Product, Review, ReviewReport
from app.models.enums import NotificationType, ReviewStatus, SubOrderStatus
from app.models.messaging import Notification
from app.models.order import Order, OrderItem, SubOrder
from app.models.user import User
from app.modules.catalog.repository import VISIBLE_REVIEW_STATUSES
from app.schemas.review import (
    PendingReview,
    ReportedReview,
    ReviewDetail,
    ReviewInput,
    ReviewSummary,
    ReviewUpdate,
)

logger = get_logger(__name__)

# Plazo para corregir una reseña propia (HU-CC-10, CA3). Treinta días bastan
# para arreglar una nota escrita en caliente sin que la ficha se vuelva un
# terreno movedizo: pasado ese tiempo otros ya compraron leyéndola.
EDIT_WINDOW_DAYS = 30


class ReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    def create(self, user: User, payload: ReviewInput) -> ReviewDetail:
        """Publica la reseña de un café entregado."""
        order_item, sub_order = self._reviewable_item(user, payload.order_item_id)

        if order_item.product_id is None:
            raise BusinessRuleError("Este café ya no está disponible para reseñar.")

        # Comprobación previa solo para dar un mensaje entendible. Quien impide
        # de verdad la reseña duplicada es la restricción única sobre
        # `order_item_id`: dos peticiones simultáneas superarían este `SELECT` y
        # solo la base de datos frena a la segunda, con un 409.
        existing = self.session.scalar(
            select(Review.id).where(
                Review.order_item_id == order_item.id, Review.deleted_at.is_(None)
            )
        )
        if existing is not None:
            raise ConflictError("Ya reseñaste este café en este pedido. Puedes editar tu reseña.")

        review = Review(
            product_id=order_item.product_id,
            user_id=user.id,
            order_item_id=order_item.id,
            rating=payload.rating,
            comment=payload.comment,
            status=ReviewStatus.PUBLISHED,
        )
        self.session.add(review)
        self.session.flush()

        self._recalculate(order_item.product_id)
        self._notify_producer(sub_order, review, order_item)
        self.session.commit()

        logger.info(
            "review_created",
            review_id=str(review.id),
            product_id=str(order_item.product_id),
            rating=payload.rating,
        )
        return self._to_detail(review, user)

    def update(self, user: User, review_id: uuid.UUID, payload: ReviewUpdate) -> ReviewDetail:
        """Corrige una reseña propia dentro del plazo de edición."""
        review = self._own_review(user, review_id)

        if not self._can_edit(review):
            raise BusinessRuleError(
                f"El plazo de {EDIT_WINDOW_DAYS} días para editar esta reseña ya pasó."
            )

        review.rating = payload.rating
        review.comment = payload.comment

        # Editar una reseña oculta no la devuelve al escaparate ni al promedio:
        # eso lo decide la moderación, no su autor. Una denunciada sí cuenta,
        # porque una denuncia sin resolver no retira nada.
        if review.status in VISIBLE_REVIEW_STATUSES:
            self._recalculate(review.product_id)

        self.session.commit()
        logger.info("review_updated", review_id=str(review.id), rating=payload.rating)
        return self._to_detail(review, user)

    def delete(self, user: User, review_id: uuid.UUID) -> None:
        """Retira una reseña propia.

        Se admite en cualquier momento, no solo dentro del plazo de edición: la
        reseña lleva el nombre de quien la escribió y la política de datos le
        reconoce el derecho a suprimir lo que publicó sobre sí mismo.
        """
        review = self._own_review(user, review_id)
        review.deleted_at = datetime.now(UTC)

        self._recalculate(review.product_id)
        self.session.commit()
        logger.info("review_deleted", review_id=str(review.id))

    def report(self, user: User, review_id: uuid.UUID, reason: str) -> None:
        """Denuncia una reseña ajena y la envía a la cola de moderación."""
        review = self._published_review(review_id)

        if review.user_id == user.id:
            raise BusinessRuleError("Esta reseña es tuya. Si quieres retirarla, puedes eliminarla.")

        already = self.session.scalar(
            select(ReviewReport.id).where(
                ReviewReport.review_id == review.id, ReviewReport.reported_by == user.id
            )
        )
        if already is not None:
            raise ConflictError("Ya reportaste esta reseña.")

        self.session.add(
            ReviewReport(review_id=review.id, reported_by=user.id, reason=reason.strip())
        )

        # La reseña sigue visible mientras se revisa. Ocultarla con la sola
        # denuncia convertiría el botón de reportar en un interruptor para
        # silenciar cualquier opinión incómoda; el promedio, por tanto, no
        # cambia aquí.
        if review.status is ReviewStatus.PUBLISHED:
            review.status = ReviewStatus.REPORTED

        self.session.commit()
        logger.info("review_reported", review_id=str(review.id), reporter=str(user.id))

    # ------------------------------------------------------------------
    # Lectura pública
    # ------------------------------------------------------------------
    def list_for_product(
        self, product_id: uuid.UUID, params: PageParams, viewer: User | None = None
    ) -> Page[ReviewDetail]:
        """Reseñas visibles de un café, de la más reciente a la más antigua.

        Las reportadas siguen mostrándose: una denuncia sin resolver no es una
        decisión de moderación.
        """
        statement = (
            select(Review)
            .where(
                Review.product_id == product_id,
                Review.status.in_(VISIBLE_REVIEW_STATUSES),
                Review.deleted_at.is_(None),
            )
            .options(joinedload(Review.product))
            .order_by(Review.created_at.desc(), Review.id)
        )
        rows, total = paginate_query(self.session, statement, params)
        return Page.create([self._to_detail(row, viewer) for row in rows], total, params)

    def summary_for_product(self, product_id: uuid.UUID) -> ReviewSummary:
        """Promedio y reparto de estrellas.

        El reparto se calcula aquí y no se guarda: es una lectura del momento y
        una columna más que mantener sincronizada solo añadiría formas de que se
        desincronice.
        """
        rows = self.session.execute(
            select(Review.rating, func.count(Review.id))
            .where(
                Review.product_id == product_id,
                Review.status.in_(VISIBLE_REVIEW_STATUSES),
                Review.deleted_at.is_(None),
            )
            .group_by(Review.rating)
        ).all()

        distribution = dict.fromkeys(range(1, 6), 0)
        total = 0
        weighted = 0
        for rating, count in rows:
            distribution[int(rating)] = int(count)
            total += int(count)
            weighted += int(rating) * int(count)

        return ReviewSummary(
            rating_avg=round(weighted / total, 2) if total else 0.0,
            rating_count=total,
            distribution=distribution,
        )

    # ------------------------------------------------------------------
    # Panel del comprador
    # ------------------------------------------------------------------
    def pending_for_user(self, user: User) -> list[PendingReview]:
        """Cafés entregados que este comprador todavía no ha reseñado (RF-06.4)."""
        rows = self.session.execute(
            select(OrderItem, SubOrder, Order, Product)
            .join(SubOrder, SubOrder.id == OrderItem.sub_order_id)
            .join(Order, Order.id == SubOrder.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .outerjoin(
                Review,
                (Review.order_item_id == OrderItem.id) & (Review.deleted_at.is_(None)),
            )
            .where(
                Order.user_id == user.id,
                SubOrder.status == SubOrderStatus.DELIVERED,
                Review.id.is_(None),
                Product.deleted_at.is_(None),
            )
            .order_by(SubOrder.updated_at.desc())
        ).all()

        return [
            PendingReview(
                order_item_id=item.id,
                product_id=product.id,
                product_slug=product.slug,
                product_name=item.product_name_snapshot,
                variant_label=item.variant_label_snapshot,
                order_number=order.order_number,
                delivered_at=sub_order.shipment.delivered_at if sub_order.shipment else None,
            )
            for item, sub_order, order, product in rows
        ]

    def reviewed_item_ids(self, order: Order) -> set[uuid.UUID]:
        """Líneas de este pedido que ya tienen reseña.

        La usa el detalle del pedido para no ofrecer «escribir una reseña» donde
        ya hay una.
        """
        item_ids = [item.id for sub in order.sub_orders for item in sub.items]
        if not item_ids:
            return set()

        rows = self.session.scalars(
            select(Review.order_item_id).where(
                Review.order_item_id.in_(item_ids), Review.deleted_at.is_(None)
            )
        ).all()
        return set(rows)

    # ------------------------------------------------------------------
    # Moderación
    # ------------------------------------------------------------------
    def list_reported(self, params: PageParams) -> Page[ReportedReview]:
        """Cola de moderación, con el motivo de cada denuncia (HU-ADM-06, CA1)."""
        statement = (
            select(Review)
            .where(Review.status == ReviewStatus.REPORTED, Review.deleted_at.is_(None))
            .options(selectinload(Review.reports), joinedload(Review.product))
            .order_by(Review.created_at.desc(), Review.id)
        )
        rows, total = paginate_query(self.session, statement, params)

        items = [
            ReportedReview(
                id=review.id,
                product_id=review.product_id,
                product_name=review.product.name,
                product_slug=review.product.slug,
                rating=review.rating,
                comment=review.comment,
                author_name=self._author_name(review),
                status=review.status,
                created_at=review.created_at,
                report_count=len(review.reports),
                report_reasons=[
                    report.reason
                    for report in sorted(
                        review.reports, key=lambda item: item.created_at, reverse=True
                    )
                ],
            )
            for review in rows
        ]
        return Page.create(items, total, params)

    # ------------------------------------------------------------------
    # Acceso y utilidades
    # ------------------------------------------------------------------
    def _reviewable_item(self, user: User, order_item_id: uuid.UUID) -> tuple[OrderItem, SubOrder]:
        """Comprueba que la línea es de este comprador y ya se entregó."""
        row = self.session.execute(
            select(OrderItem, SubOrder, Order)
            .join(SubOrder, SubOrder.id == OrderItem.sub_order_id)
            .join(Order, Order.id == SubOrder.order_id)
            .where(OrderItem.id == order_item_id)
        ).first()

        if row is None:
            raise NotFoundError("No encontramos este producto en tus pedidos.")

        order_item, sub_order, order = row
        if order.user_id != user.id:
            # Mismo mensaje que si no existiera: distinguirlos permitiría
            # averiguar qué identificadores de línea son reales.
            raise NotFoundError("No encontramos este producto en tus pedidos.")

        if sub_order.status is not SubOrderStatus.DELIVERED:
            raise BusinessRuleError(
                "Podrás reseñar este café cuando el pedido figure como entregado."
            )
        return order_item, sub_order

    def _own_review(self, user: User, review_id: uuid.UUID) -> Review:
        review = self.session.get(Review, review_id)
        if review is None or review.deleted_at is not None:
            raise NotFoundError("No encontramos esta reseña.")
        if review.user_id != user.id:
            raise ForbiddenError("Esta reseña no es tuya.")
        return review

    def _published_review(self, review_id: uuid.UUID) -> Review:
        review = self.session.get(Review, review_id)
        if review is None or review.deleted_at is not None:
            raise NotFoundError("No encontramos esta reseña.")
        if review.status is ReviewStatus.HIDDEN:
            raise NotFoundError("No encontramos esta reseña.")
        return review

    @staticmethod
    def _can_edit(review: Review) -> bool:
        deadline = review.created_at + timedelta(days=EDIT_WINDOW_DAYS)
        return datetime.now(UTC) <= deadline

    def _author_name(self, review: Review) -> str:
        """Nombre abreviado: «María L.».

        La ficha es pública y aparece en los buscadores. Publicar el nombre
        completo de quien compra no aporta nada a la reseña y sí expone un dato
        personal más de lo necesario.
        """
        author = self.session.get(User, review.user_id)
        if author is None:
            return "Comprador"

        parts = [part for part in author.full_name.split() if part]
        if not parts:
            return "Comprador"
        if len(parts) == 1:
            return parts[0]
        return f"{parts[0]} {parts[1][0].upper()}."

    def _recalculate(self, product_id: uuid.UUID) -> None:
        """Actualiza el promedio del café y el de su productor (HU-CC-10, CA4)."""
        from app.modules.catalog.repository import CatalogRepository

        CatalogRepository(self.session).recalculate_product_rating(product_id)

    def _to_detail(self, review: Review, viewer: User | None) -> ReviewDetail:
        is_mine = viewer is not None and review.user_id == viewer.id
        return ReviewDetail(
            id=review.id,
            product_id=review.product_id,
            rating=review.rating,
            comment=review.comment,
            author_name=self._author_name(review),
            created_at=review.created_at,
            updated_at=review.updated_at,
            can_edit=is_mine and self._can_edit(review),
            is_mine=is_mine,
        )

    def _notify_producer(self, sub_order: SubOrder, review: Review, item: OrderItem) -> None:
        producer = sub_order.producer
        if producer is None:
            return

        self.session.add(
            Notification(
                user_id=producer.user_id,
                type=NotificationType.REVIEW_REMINDER,
                title=f"Nueva reseña de {review.rating} estrellas",
                body=(
                    f"Un comprador reseñó «{item.product_name_snapshot}» con {review.rating} de 5."
                ),
                action_url=f"/productor/catalogo/{item.product_id}",
                is_transactional=False,
            )
        )
        self.session.flush()
