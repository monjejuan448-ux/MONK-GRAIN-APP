"""Panel del productor: métricas, pedidos recibidos e inventario."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate_query
from app.models.catalog import Inventory, Product, ProductVariant
from app.models.enums import (
    CommissionStatus,
    ProductStatus,
    RequestStatus,
    SubOrderStatus,
)
from app.models.messaging import CommercialRequest
from app.models.order import Order, OrderItem, SubOrder
from app.models.payment import Commission
from app.models.producer import ProducerProfile
from app.models.user import User
from app.modules.catalog.service import build_media_url
from app.schemas.dashboard import (
    InventoryAlert,
    ProducerDashboard,
    ProducerOrderItem,
    ProducerProductItem,
    ProducerSalesPoint,
    TopProduct,
)
from app.schemas.producer_catalog import (
    ProducerProfileResponse,
    ProducerProfileUpdate,
)

# Estados que representan una venta consumada. Un pedido cancelado no es
# ingreso, y contarlo inflaría las métricas del productor.
REALIZED_STATUSES = (
    SubOrderStatus.CONFIRMED,
    SubOrderStatus.PREPARED,
    SubOrderStatus.SHIPPED,
    SubOrderStatus.DELIVERED,
)


logger = get_logger(__name__)


class ProducerService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _profile(self, user: User) -> ProducerProfile:
        if user.producer_profile is None:
            raise ForbiddenError("Tu cuenta no tiene un perfil de productor.")
        return user.producer_profile

    # ------------------------------------------------------------------
    # Panel
    # ------------------------------------------------------------------
    def get_dashboard(self, user: User) -> ProducerDashboard:
        profile = self._profile(user)

        totals = self.session.execute(
            select(
                func.coalesce(func.sum(SubOrder.subtotal), 0),
                func.coalesce(func.sum(SubOrder.commission_amount), 0),
                func.coalesce(func.sum(SubOrder.net_amount), 0),
            ).where(
                SubOrder.producer_id == profile.id,
                SubOrder.status.in_(REALIZED_STATUSES),
            )
        ).one()

        pending_orders = self._count_sub_orders(profile.id, SubOrderStatus.PENDING)
        to_prepare = self._count_sub_orders(profile.id, SubOrderStatus.CONFIRMED)

        active_products = self._count_products(profile.id, ProductStatus.PUBLISHED)
        draft_products = self._count_products(profile.id, ProductStatus.DRAFT)

        low_stock = (
            self.session.scalar(
                select(func.count())
                .select_from(Inventory)
                .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
                .join(Product, Product.id == ProductVariant.product_id)
                .where(
                    Product.producer_id == profile.id,
                    Product.deleted_at.is_(None),
                    (Inventory.stock_qty - Inventory.reserved_qty) <= Inventory.low_stock_threshold,
                )
            )
            or 0
        )

        pending_requests = (
            self.session.scalar(
                select(func.count())
                .select_from(CommercialRequest)
                .where(
                    CommercialRequest.producer_id == profile.id,
                    CommercialRequest.status == RequestStatus.PENDING,
                )
            )
            or 0
        )

        return ProducerDashboard(
            total_sales=Decimal(str(totals[0])),
            commission_paid=Decimal(str(totals[1])),
            net_earnings=Decimal(str(totals[2])),
            pending_orders=pending_orders,
            orders_to_prepare=to_prepare,
            active_products=active_products,
            draft_products=draft_products,
            low_stock_variants=low_stock,
            rating_avg=profile.rating_avg,
            rating_count=profile.rating_count,
            pending_requests=pending_requests,
            top_products=self._top_products(profile.id),
            sales_by_month=self._sales_by_month(profile.id),
        )

    def _count_sub_orders(self, producer_id: uuid.UUID, status: SubOrderStatus) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(SubOrder)
                .where(SubOrder.producer_id == producer_id, SubOrder.status == status)
            )
            or 0
        )

    def _count_products(self, producer_id: uuid.UUID, status: ProductStatus) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(Product)
                .where(
                    Product.producer_id == producer_id,
                    Product.status == status,
                    Product.deleted_at.is_(None),
                )
            )
            or 0
        )

    def _top_products(self, producer_id: uuid.UUID, limit: int = 5) -> list[TopProduct]:
        """Productos más vendidos, contando solo ventas consumadas."""
        rows = self.session.execute(
            select(
                Product.id,
                Product.name,
                Product.slug,
                func.sum(OrderItem.quantity),
                func.sum(OrderItem.line_total),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(SubOrder, SubOrder.id == OrderItem.sub_order_id)
            .where(
                Product.producer_id == producer_id,
                SubOrder.status.in_(REALIZED_STATUSES),
            )
            .group_by(Product.id, Product.name, Product.slug)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        ).all()

        return [
            TopProduct(
                product_id=row[0],
                name=row[1],
                slug=row[2],
                units_sold=int(row[3] or 0),
                revenue=Decimal(str(row[4] or 0)),
            )
            for row in rows
        ]

    def _sales_by_month(self, producer_id: uuid.UUID, months: int = 6) -> list[ProducerSalesPoint]:
        """Serie mensual de ventas de los últimos meses."""
        since = datetime.now(UTC) - timedelta(days=months * 31)

        # La expresión del periodo se define una sola vez y se reutiliza en
        # SELECT, GROUP BY y ORDER BY: repetir la llamada crea objetos distintos
        # y PostgreSQL rechaza el agrupamiento.
        period = func.to_char(SubOrder.created_at, "YYYY-MM").label("period")

        rows = self.session.execute(
            select(
                period,
                func.count(SubOrder.id),
                func.coalesce(func.sum(SubOrder.subtotal), 0),
            )
            .where(
                SubOrder.producer_id == producer_id,
                SubOrder.status.in_(REALIZED_STATUSES),
                SubOrder.created_at >= since,
            )
            .group_by(period)
            .order_by(period)
        ).all()

        return [
            ProducerSalesPoint(period=row[0], orders=int(row[1]), revenue=Decimal(str(row[2])))
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Pedidos recibidos
    # ------------------------------------------------------------------
    def list_orders(
        self, user: User, params: PageParams, status: SubOrderStatus | None = None
    ) -> Page[ProducerOrderItem]:
        profile = self._profile(user)

        statement = (
            select(SubOrder)
            .where(SubOrder.producer_id == profile.id)
            .options(
                selectinload(SubOrder.items),
                joinedload(SubOrder.order).joinedload(Order.sub_orders),
            )
            .order_by(SubOrder.created_at.desc(), SubOrder.id)
        )
        if status is not None:
            statement = statement.where(SubOrder.status == status)

        sub_orders, total = paginate_query(self.session, statement, params)

        items: list[ProducerOrderItem] = []
        for sub_order in sub_orders:
            order = self.session.get(Order, sub_order.order_id)
            buyer = self.session.get(User, order.user_id) if order else None
            snapshot = order.shipping_address_snapshot if order else {}

            items.append(
                ProducerOrderItem(
                    sub_order_id=sub_order.id,
                    sub_order_number=sub_order.sub_order_number,
                    order_number=order.order_number if order else "",
                    buyer_name=buyer.full_name if buyer else "—",
                    status=sub_order.status,
                    subtotal=sub_order.subtotal,
                    net_amount=sub_order.net_amount,
                    item_count=len(sub_order.items),
                    shipping_city=snapshot.get("neighborhood") if snapshot else None,
                    created_at=sub_order.created_at,
                )
            )

        return Page.create(items, total, params)

    # ------------------------------------------------------------------
    # Productos e inventario
    # ------------------------------------------------------------------
    def list_products(self, user: User, params: PageParams) -> Page[ProducerProductItem]:
        profile = self._profile(user)

        statement = (
            select(Product)
            .where(Product.producer_id == profile.id, Product.deleted_at.is_(None))
            .options(
                selectinload(Product.variants).joinedload(ProductVariant.inventory),
                selectinload(Product.images),
            )
            .order_by(Product.created_at.desc(), Product.id)
        )
        products, total = paginate_query(self.session, statement, params)

        items: list[ProducerProductItem] = []
        for product in products:
            active_variants = [
                variant for variant in product.variants if variant.deleted_at is None
            ]
            total_stock = sum(
                variant.inventory.available_qty
                for variant in active_variants
                if variant.inventory is not None
            )
            # `variant.inventory and ...` devolvería el propio objeto cuando el
            # inventario existe, no un booleano: la comparación debe ser explícita.
            has_low_stock = any(
                variant.inventory is not None and variant.inventory.is_low_stock
                for variant in active_variants
            )
            primary = next(
                (image for image in product.images if image.is_primary),
                product.images[0] if product.images else None,
            )

            items.append(
                ProducerProductItem(
                    id=product.id,
                    slug=product.slug,
                    name=product.name,
                    status=product.status,
                    base_price=product.base_price,
                    total_stock=total_stock,
                    variant_count=len(active_variants),
                    sales_count=product.sales_count,
                    rating_avg=product.rating_avg,
                    has_low_stock=has_low_stock,
                    primary_image_url=build_media_url(primary.image_key) if primary else None,
                )
            )

        return Page.create(items, total, params)

    def list_inventory_alerts(self, user: User) -> list[InventoryAlert]:
        """Variantes con existencias bajo el umbral definido por el productor."""
        profile = self._profile(user)

        rows = self.session.execute(
            select(Inventory, ProductVariant, Product)
            .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                Product.producer_id == profile.id,
                Product.deleted_at.is_(None),
                ProductVariant.deleted_at.is_(None),
                (Inventory.stock_qty - Inventory.reserved_qty) <= Inventory.low_stock_threshold,
            )
            .order_by((Inventory.stock_qty - Inventory.reserved_qty).asc())
        ).all()

        return [
            InventoryAlert(
                variant_id=inventory.variant_id,
                product_name=product.name,
                variant_label=variant.label,
                available_qty=inventory.available_qty,
                low_stock_threshold=inventory.low_stock_threshold,
            )
            for inventory, variant, product in rows
        ]

    def update_inventory(
        self,
        user: User,
        variant_id: uuid.UUID,
        stock_qty: int,
        low_stock_threshold: int | None = None,
    ) -> InventoryAlert:
        """Ajusta el stock de una variante propia."""
        profile = self._profile(user)

        row = self.session.execute(
            select(Inventory, ProductVariant, Product)
            .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Inventory.variant_id == variant_id)
        ).one_or_none()

        if row is None:
            raise NotFoundError("No encontramos esta presentación.")

        inventory, variant, product = row
        if product.producer_id != profile.id:
            raise ForbiddenError("Esta presentación no pertenece a tu catálogo.")

        # El stock no puede quedar por debajo de lo ya reservado por pedidos en
        # curso: esas unidades están comprometidas con compradores concretos.
        if stock_qty < inventory.reserved_qty:
            raise ForbiddenError(
                f"No puedes dejar el stock por debajo de las {inventory.reserved_qty} "
                "unidades reservadas por pedidos en curso."
            )

        inventory.stock_qty = stock_qty
        if low_stock_threshold is not None:
            inventory.low_stock_threshold = low_stock_threshold

        self.session.commit()

        return InventoryAlert(
            variant_id=inventory.variant_id,
            product_name=product.name,
            variant_label=variant.label,
            available_qty=inventory.available_qty,
            low_stock_threshold=inventory.low_stock_threshold,
        )

    # ------------------------------------------------------------------
    # Liquidaciones
    # ------------------------------------------------------------------
    def get_settlement_summary(self, user: User) -> dict[str, Decimal | int]:
        """Resumen de lo pendiente de liquidar (HU-PRO-11, CA2)."""
        profile = self._profile(user)

        pending = self.session.execute(
            select(
                func.coalesce(func.sum(Commission.base_amount), 0),
                func.coalesce(func.sum(Commission.commission_amount), 0),
                func.count(Commission.id),
            )
            .join(SubOrder, SubOrder.id == Commission.sub_order_id)
            .where(
                SubOrder.producer_id == profile.id,
                Commission.status == CommissionStatus.PENDING,
                SubOrder.status.in_(REALIZED_STATUSES),
            )
        ).one()

        gross = Decimal(str(pending[0]))
        commission = Decimal(str(pending[1]))

        return {
            "gross_amount": gross,
            "commission_total": commission,
            "net_amount": gross - commission,
            "sub_orders_count": int(pending[2]),
        }

    # ------------------------------------------------------------------
    # Perfil comercial
    # ------------------------------------------------------------------
    def get_profile(self, user: User) -> ProducerProfileResponse:
        """Datos del negocio tal como los ve su titular."""
        profile = self._profile(user)
        return self._profile_response(profile)

    def update_profile(self, user: User, payload: ProducerProfileUpdate) -> ProducerProfileResponse:
        """Actualiza los datos de contacto y presentación del negocio.

        No se admiten aquí la razón social, el documento ni el estado: son los
        datos que el equipo verificó al aprobar la solicitud, y permitir
        cambiarlos sin revisión vaciaría de sentido esa aprobación.
        """
        profile = self._profile(user)

        profile.brand_name = payload.brand_name
        profile.story = payload.story
        profile.notification_address = payload.notification_address
        profile.contact_phone = payload.contact_phone
        profile.production_capacity_kg = payload.production_capacity_kg

        self.session.commit()

        logger.info("producer_profile_updated", producer_id=str(profile.id))
        return self._profile_response(profile)

    def _profile_response(self, profile: ProducerProfile) -> ProducerProfileResponse:
        return ProducerProfileResponse(
            id=profile.id,
            legal_name=profile.legal_name,
            brand_name=profile.brand_name,
            type=profile.type,
            status=profile.status,
            story=profile.story,
            notification_address=profile.notification_address,
            contact_phone=profile.contact_phone,
            production_capacity_kg=profile.production_capacity_kg,
            # Lo que la ley exige tener registrado de cada oferente. Se expone
            # para que el panel pueda avisar antes de que falle la publicación.
            has_notification_data=bool(
                (profile.notification_address or "").strip()
                and (profile.contact_phone or "").strip()
            ),
        )
