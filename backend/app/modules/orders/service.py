"""Checkout y gestión de pedidos.

El checkout es la operación más delicada del sistema: crea el pedido, lo divide
por vendedor, reserva inventario y registra comisiones. Todo ello ocurre en una
única transacción — si algo falla, no queda ni pedido a medias ni stock
reservado sin dueño (HU-CC-07, CA5).
"""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.core.exceptions import (
    BusinessRuleError,
    ForbiddenError,
    InsufficientStockError,
    InvalidStateTransitionError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate_query
from app.integrations.payments import get_payment_provider
from app.models.cart import CartItem, CouponUsage
from app.models.catalog import Inventory, Product, ProductVariant, Review
from app.models.enums import (
    ALLOWED_SUB_ORDER_TRANSITIONS,
    CommissionStatus,
    NotificationType,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ShipmentStatus,
    SubOrderStatus,
)
from app.models.messaging import Notification
from app.models.order import Order, OrderItem, OrderStatusHistory, SubOrder, order_number_seq
from app.models.payment import Commission, Payment, PaymentEvent
from app.models.producer import ProducerProfile
from app.models.shipment import Shipment, ShipmentEvent
from app.models.user import Address, User
from app.modules.cart.service import CartService
from app.schemas.order import (
    CheckoutRequest,
    CheckoutResponse,
    OrderDetail,
    OrderItemResponse,
    OrderSummary,
    PaymentResponse,
    ShipmentResponse,
    SubOrderResponse,
)

logger = get_logger(__name__)


def derive_order_status(statuses: set[SubOrderStatus]) -> OrderStatus:
    """Estado agregado del pedido a partir del de sus sub-órdenes.

    Vive fuera de `OrderService` porque el módulo de devoluciones también cierra
    pedidos, y dos lecturas distintas de la misma regla acabarían discrepando: un
    pedido reembolsado figuraría como cancelado en un sitio y como completado en
    el otro.
    """
    if not statuses:
        return OrderStatus.PENDING

    closed = {SubOrderStatus.CANCELLED, SubOrderStatus.REFUNDED}
    if statuses <= closed:
        # Cancelado y reembolsado no son lo mismo: uno nunca llegó a entregarse.
        return (
            OrderStatus.REFUNDED if SubOrderStatus.REFUNDED in statuses else OrderStatus.CANCELLED
        )
    if statuses <= closed | {SubOrderStatus.DELIVERED}:
        return OrderStatus.COMPLETED
    if SubOrderStatus.SHIPPED in statuses and len(statuses) > 1:
        return OrderStatus.PARTIALLY_SHIPPED
    if statuses == {SubOrderStatus.PENDING}:
        return OrderStatus.PENDING
    return OrderStatus.PROCESSING


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.cart_service = CartService(session)
        self.payment_provider = get_payment_provider()

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------
    def checkout(self, user: User, payload: CheckoutRequest) -> CheckoutResponse:
        """Convierte el carrito en un pedido.

        Pasos, todos dentro de la misma transacción:
        1. Serializar los checkouts de este comprador (evita el doble clic).
        2. Validar dirección y contenido del carrito.
        3. Revalidar precios y disponibilidad contra la base de datos.
        4. Reservar inventario con bloqueo pesimista.
        5. Crear el pedido y una sub-orden por vendedor.
        6. Calcular la comisión con la tasa vigente.
        7. Crear la intención de pago y vaciar el carrito.
        """
        # Antes de leer el carrito: si otra petición del mismo comprador está a
        # mitad del checkout, esta espera y encontrará el carrito ya vacío.
        self._lock_checkout_for(user)

        address = self._get_address(user, payload.shipping_address_id)
        cart_items = self._load_cart_items(user)
        if not cart_items:
            raise BusinessRuleError("Tu carrito está vacío.")

        # Agrupa por productor: cada uno origina su propia sub-orden (ADR-02).
        by_producer: dict[uuid.UUID, list[tuple[CartItem, ProductVariant]]] = defaultdict(list)
        for item in cart_items:
            variant = item.variant
            self._assert_purchasable(variant)
            by_producer[variant.product.producer_id].append((item, variant))

        subtotal = sum(
            (item.quantity * variant.price for item, variant in cart_items_pairs(by_producer)),
            Decimal("0"),
        )

        discount = Decimal("0")
        coupon = None
        if payload.coupon_code:
            coupon, discount = self.cart_service.validate_coupon(
                user, payload.coupon_code, subtotal
            )

        commission_rate = settings.default_commission_rate
        order_number = self._generate_order_number()

        order = Order(
            order_number=order_number,
            user_id=user.id,
            shipping_address_id=address.id,
            # Copia inmutable: si el comprador edita o borra la dirección
            # después, el pedido conserva a dónde se envió realmente.
            shipping_address_snapshot=self._address_snapshot(address),
            subtotal=Decimal("0"),
            shipping_total=Decimal("0"),
            discount_total=discount,
            grand_total=Decimal("0"),
            currency=settings.default_currency,
            coupon_id=coupon.id if coupon else None,
            status=OrderStatus.PENDING,
            customer_notes=payload.customer_notes,
        )
        self.session.add(order)
        self.session.flush()

        shipping_total = Decimal("0")
        computed_subtotal = Decimal("0")

        for index, (producer_id, pairs) in enumerate(by_producer.items(), start=1):
            sub_order, sub_subtotal, sub_shipping = self._create_sub_order(
                order=order,
                producer_id=producer_id,
                pairs=pairs,
                sequence=index,
                commission_rate=commission_rate,
            )
            computed_subtotal += sub_subtotal
            shipping_total += sub_shipping
            self._notify_producer(producer_id, order, sub_order)

        order.subtotal = computed_subtotal
        order.shipping_total = shipping_total
        order.grand_total = computed_subtotal + shipping_total - discount

        if coupon is not None:
            self.session.add(
                CouponUsage(
                    coupon_id=coupon.id,
                    user_id=user.id,
                    order_id=order.id,
                    discount_applied=discount,
                )
            )
            coupon.used_count += 1

        payment = self._create_payment(order, user, payload.payment_method)

        # El carrito se vacía solo cuando todo lo anterior salió bien.
        for item in cart_items:
            self.session.delete(item)

        self.session.commit()

        logger.info(
            "order_created",
            order_number=order.order_number,
            user_id=str(user.id),
            sub_orders=len(by_producer),
            total=str(order.grand_total),
        )

        self._notify_buyer(
            user,
            NotificationType.ORDER_PLACED,
            "Recibimos tu pedido",
            f"Tu pedido {order.order_number} fue creado. Te avisaremos cuando el pago se confirme.",
            f"/mi-cuenta/pedidos/{order.id}",
        )
        self.session.commit()

        return CheckoutResponse(
            order=self.get_order_detail(user, order.id),
            payment_reference=payment.provider_reference,
            payment_redirect_url=None,
            message=(
                "Tu pedido fue creado. El pago está en proceso con un proveedor "
                "simulado: no se realizó ningún cobro real."
            ),
        )

    def _create_sub_order(
        self,
        *,
        order: Order,
        producer_id: uuid.UUID,
        pairs: list[tuple[CartItem, ProductVariant]],
        sequence: int,
        commission_rate: Decimal,
    ) -> tuple[SubOrder, Decimal, Decimal]:
        """Crea la sub-orden de un vendedor con sus ítems y su comisión."""
        sub_subtotal = Decimal("0")

        sub_order = SubOrder(
            order_id=order.id,
            producer_id=producer_id,
            sub_order_number=f"{order.order_number}-{sequence}",
            subtotal=Decimal("0"),
            shipping_cost=Decimal("0"),
            commission_amount=Decimal("0"),
            net_amount=Decimal("0"),
            status=SubOrderStatus.PENDING,
        )
        self.session.add(sub_order)
        self.session.flush()

        for item, variant in pairs:
            self._reserve_stock(variant.id, item.quantity)
            # El precio efectivo: el negociado si la línea viene de una postura
            # aceptada, y el de catálogo en cualquier otro caso. Tomar aquí el
            # precio de la variante habría cobrado la lista del vendedor sobre un
            # trato ya cerrado, y con ella se habría calculado la comisión.
            unit_price = item.effective_price
            line_total = unit_price * item.quantity
            sub_subtotal += line_total

            self.session.add(
                OrderItem(
                    sub_order_id=sub_order.id,
                    variant_id=variant.id,
                    product_id=variant.product_id,
                    # Congela nombre y presentación: renombrar el producto no
                    # debe alterar un pedido histórico (HU-PRO-06, CA3).
                    product_name_snapshot=variant.product.name,
                    variant_label_snapshot=variant.label,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
            )

        shipping = self._shipping_for(sub_subtotal)
        commission_amount = (sub_subtotal * commission_rate).quantize(Decimal("0.01"))

        sub_order.subtotal = sub_subtotal
        sub_order.shipping_cost = shipping
        sub_order.commission_amount = commission_amount
        sub_order.net_amount = sub_subtotal - commission_amount

        # La tasa se guarda con la comisión: cambiarla después no altera los
        # pedidos ya calculados (HU-ADM-05, CA2).
        self.session.add(
            Commission(
                sub_order_id=sub_order.id,
                rate_applied=commission_rate,
                base_amount=sub_subtotal,
                commission_amount=commission_amount,
                status=CommissionStatus.PENDING,
            )
        )

        self.session.add(
            OrderStatusHistory(
                sub_order_id=sub_order.id,
                from_status=None,
                to_status=SubOrderStatus.PENDING,
                note="Pedido creado",
            )
        )
        self.session.flush()

        return sub_order, sub_subtotal, shipping

    def _reserve_stock(self, variant_id: uuid.UUID, quantity: int) -> None:
        """Reserva kilos bloqueando la fila de inventario.

        `FOR UPDATE` serializa las compras concurrentes de la misma variante: sin
        él, dos checkouts simultáneos podrían leer el mismo stock y venderlo dos
        veces (HU-PRO-05, CA4).

        La reserva no descuenta el stock: lo retiene hasta que el pago se
        confirme. Un pago rechazado lo devuelve al catálogo.
        """
        inventory = self.session.scalar(
            select(Inventory).where(Inventory.variant_id == variant_id).with_for_update()
        )
        if inventory is None:
            raise NotFoundError("Esta presentación ya no está disponible.")

        if inventory.available_qty < quantity:
            raise InsufficientStockError(
                f"Solo quedan {inventory.available_qty} kg disponibles.",
                details={"variant_id": str(variant_id), "available": inventory.available_qty},
            )

        inventory.reserved_qty += quantity
        self.session.flush()

    def _create_payment(self, order: Order, user: User, method: PaymentMethod) -> Payment:
        """Crea la intención de pago en el proveedor configurado."""
        intent = self.payment_provider.create_intent(
            order_number=order.order_number,
            amount=order.grand_total,
            currency=order.currency,
            customer_email=user.email,
        )

        payment = Payment(
            order_id=order.id,
            provider=self.payment_provider.name,
            provider_reference=intent.reference,
            method=method,
            amount=order.grand_total,
            currency=order.currency,
            status=intent.status,
        )
        self.session.add(payment)
        self.session.flush()

        self.session.add(
            PaymentEvent(
                payment_id=payment.id,
                event_type="created",
                payload=intent.raw_response,
                signature_valid=None,
            )
        )
        self.session.flush()
        return payment

    # ------------------------------------------------------------------
    # Confirmación del pago
    # ------------------------------------------------------------------
    def confirm_payment(self, payment_reference: str, approved: bool = True) -> None:
        """Aplica el resultado del pago.

        Aprobado: la reserva pasa a descuento efectivo y las sub-órdenes se
        confirman. Rechazado: el stock reservado vuelve al catálogo.
        """
        payment = self.session.scalar(
            select(Payment)
            .where(Payment.provider_reference == payment_reference)
            .options(selectinload(Payment.order))
        )
        if payment is None:
            raise NotFoundError("No encontramos este pago.")

        # Idempotencia: reprocesar el mismo webhook no debe duplicar efectos.
        if payment.status in (PaymentStatus.APPROVED, PaymentStatus.REFUNDED):
            logger.info("payment_already_processed", reference=payment_reference)
            return

        order = self.session.scalar(
            select(Order)
            .where(Order.id == payment.order_id)
            .options(selectinload(Order.sub_orders).selectinload(SubOrder.items))
        )
        if order is None:
            raise NotFoundError("No encontramos el pedido asociado.")

        if approved:
            payment.status = PaymentStatus.APPROVED
            payment.paid_at = datetime.now(UTC)

            for sub_order in order.sub_orders:
                for item in sub_order.items:
                    if item.variant_id:
                        self._commit_reserved_stock(item.variant_id, item.quantity)
                self._transition(sub_order, SubOrderStatus.CONFIRMED, note="Pago confirmado")

            order.status = OrderStatus.PROCESSING
            self._increment_sales_counters(order)
            notification = (
                NotificationType.PAYMENT_APPROVED,
                "Pago confirmado",
                f"El pago de tu pedido {order.order_number} fue confirmado.",
            )
        else:
            payment.status = PaymentStatus.DECLINED

            for sub_order in order.sub_orders:
                for item in sub_order.items:
                    if item.variant_id:
                        self._release_reserved_stock(item.variant_id, item.quantity)
                self._transition(sub_order, SubOrderStatus.CANCELLED, note="Pago rechazado")

            order.status = OrderStatus.CANCELLED
            notification = (
                NotificationType.PAYMENT_DECLINED,
                "Pago rechazado",
                f"No pudimos procesar el pago de tu pedido {order.order_number}.",
            )

        buyer = self.session.get(User, order.user_id)
        if buyer is not None:
            self._notify_buyer(
                buyer,
                notification[0],
                notification[1],
                notification[2],
                f"/mi-cuenta/pedidos/{order.id}",
            )

        self.session.commit()
        logger.info(
            "payment_processed",
            reference=payment_reference,
            approved=approved,
            order_number=order.order_number,
        )

    def _commit_reserved_stock(self, variant_id: uuid.UUID, quantity: int) -> None:
        """Convierte la reserva en salida efectiva de inventario."""
        inventory = self.session.scalar(
            select(Inventory).where(Inventory.variant_id == variant_id).with_for_update()
        )
        if inventory is None:
            return
        inventory.stock_qty = max(0, inventory.stock_qty - quantity)
        inventory.reserved_qty = max(0, inventory.reserved_qty - quantity)
        self.session.flush()

    def _release_reserved_stock(self, variant_id: uuid.UUID, quantity: int) -> None:
        """Devuelve al catálogo el stock que estaba reservado."""
        inventory = self.session.scalar(
            select(Inventory).where(Inventory.variant_id == variant_id).with_for_update()
        )
        if inventory is None:
            return
        inventory.reserved_qty = max(0, inventory.reserved_qty - quantity)
        self.session.flush()

    def _increment_sales_counters(self, order: Order) -> None:
        """Actualiza el contador de ventas usado para ordenar por popularidad."""
        for sub_order in order.sub_orders:
            for item in sub_order.items:
                if item.product_id:
                    product = self.session.get(Product, item.product_id)
                    if product is not None:
                        product.sales_count += item.quantity
        self.session.flush()

    # ------------------------------------------------------------------
    # Estados
    # ------------------------------------------------------------------
    def update_sub_order_status(
        self,
        producer_user: User,
        sub_order_id: uuid.UUID,
        new_status: SubOrderStatus,
        note: str | None = None,
        carrier: str | None = None,
        tracking_number: str | None = None,
    ) -> SubOrderResponse:
        """Avanza el estado de una sub-orden (HU-PRO-07)."""
        sub_order = self._get_sub_order(sub_order_id)

        if (
            producer_user.producer_profile is None
            or sub_order.producer_id != producer_user.producer_profile.id
        ):
            raise ForbiddenError("Este pedido no pertenece a tu catálogo.")

        self._transition(sub_order, new_status, note=note, actor_id=producer_user.id)

        if new_status == SubOrderStatus.CANCELLED:
            # El inventario retenido vuelve al catálogo, igual que cuando cancela
            # el comprador. Sin esto, una cancelación del vendedor dejaba las
            # unidades reservadas para siempre: invendibles y sin pedido que las
            # justifique.
            sub_order.cancellation_reason = note
            for item in sub_order.items:
                if item.variant_id:
                    self._release_reserved_stock(item.variant_id, item.quantity)

        if new_status == SubOrderStatus.SHIPPED:
            self._register_shipment(sub_order, carrier, tracking_number)

        if new_status == SubOrderStatus.DELIVERED:
            shipment = sub_order.shipment
            if shipment is not None:
                shipment.status = ShipmentStatus.DELIVERED
                shipment.delivered_at = datetime.now(UTC)

        self._sync_order_status(sub_order.order_id)
        self.session.commit()

        return self._to_sub_order_response(sub_order)

    def _transition(
        self,
        sub_order: SubOrder,
        new_status: SubOrderStatus,
        note: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        """Aplica una transición de estado si el grafo la permite.

        El grafo está declarado como dato en `models.enums`, de modo que la
        regla es verificable de un vistazo y no queda repartida en condicionales
        (HU-PRO-07, CA4).
        """
        allowed = ALLOWED_SUB_ORDER_TRANSITIONS[sub_order.status]
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"No se puede pasar de '{sub_order.status.value}' a '{new_status.value}'.",
                details={
                    "current": sub_order.status.value,
                    "allowed": sorted(status.value for status in allowed),
                },
            )

        previous = sub_order.status
        sub_order.status = new_status
        self.session.add(
            OrderStatusHistory(
                sub_order_id=sub_order.id,
                from_status=previous,
                to_status=new_status,
                changed_by=actor_id,
                note=note,
            )
        )
        self.session.flush()

    def _register_shipment(
        self, sub_order: SubOrder, carrier: str | None, tracking_number: str | None
    ) -> None:
        """Registra el despacho. El operador simulado genera una guía de prueba."""
        shipment = sub_order.shipment
        if shipment is None:
            shipment = Shipment(
                sub_order_id=sub_order.id,
                carrier=carrier or settings.shipping_provider,
                shipping_cost=sub_order.shipping_cost,
            )
            self.session.add(shipment)
            self.session.flush()
            # Asignar también la relación, no solo la clave foránea: el objeto
            # ya cargado conserva su `shipment` en None y la respuesta saldría
            # sin la guía recién generada.
            sub_order.shipment = shipment

        shipment.carrier = carrier or settings.shipping_provider
        shipment.tracking_number = tracking_number or f"SIM{sub_order.sub_order_number}"
        shipment.status = ShipmentStatus.DISPATCHED
        shipment.dispatched_at = datetime.now(UTC)
        shipment.estimated_delivery_date = date.today() + timedelta(days=5)

        self.session.add(
            ShipmentEvent(
                shipment_id=shipment.id,
                event_code="dispatched",
                description="El pedido salió del centro de despacho",
                occurred_at=datetime.now(UTC),
            )
        )
        self.session.flush()

    def _sync_order_status(self, order_id: uuid.UUID) -> None:
        """Deriva el estado del pedido a partir de sus sub-órdenes.

        La verdad operativa vive en las sub-órdenes; este campo existe para
        listar y filtrar sin agregaciones (ADR-02).
        """
        order = self.session.scalar(
            select(Order).where(Order.id == order_id).options(selectinload(Order.sub_orders))
        )
        if order is None:
            return

        order.status = derive_order_status({sub.status for sub in order.sub_orders})
        self.session.flush()

    @staticmethod
    def _not_cancellable_reason(status: SubOrderStatus) -> str:
        """Explica por qué no se puede cancelar, según el estado real.

        Antes se respondía siempre «ya fue despachado», lo que confundía a quien
        intentaba cancelar un pedido que en realidad ya estaba cancelado o
        entregado.
        """
        if status is SubOrderStatus.CANCELLED:
            return "Este pedido ya está cancelado."
        if status is SubOrderStatus.REFUNDED:
            return "Este pedido ya fue reembolsado."
        if status is SubOrderStatus.DELIVERED:
            return (
                "Este pedido ya fue entregado y no puede cancelarse. "
                "Puedes solicitar una devolución desde el detalle del pedido."
            )
        return (
            "Este pedido ya fue despachado y no puede cancelarse. "
            "Puedes solicitar una devolución desde el detalle del pedido."
        )

    def cancel_sub_order(
        self, user: User, sub_order_id: uuid.UUID, reason: str
    ) -> SubOrderResponse:
        """Cancela una sub-orden a petición del comprador (HU-CC-14)."""
        sub_order = self._get_sub_order(sub_order_id)
        order = self.session.get(Order, sub_order.order_id)

        if order is None or order.user_id != user.id:
            raise ForbiddenError("Este pedido no te pertenece.")

        if not sub_order.is_cancellable:
            raise BusinessRuleError(self._not_cancellable_reason(sub_order.status))

        self._transition(sub_order, SubOrderStatus.CANCELLED, note=reason, actor_id=user.id)
        sub_order.cancellation_reason = reason

        # Devuelve el inventario retenido por esta sub-orden.
        for item in sub_order.items:
            if item.variant_id:
                self._release_reserved_stock(item.variant_id, item.quantity)

        self._sync_order_status(sub_order.order_id)
        self.session.commit()

        logger.info("sub_order_cancelled", sub_order=sub_order.sub_order_number)
        return self._to_sub_order_response(sub_order)

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def list_user_orders(self, user: User, params: PageParams) -> Page[OrderSummary]:
        statement = (
            select(Order)
            .where(Order.user_id == user.id)
            .options(selectinload(Order.sub_orders).selectinload(SubOrder.items))
            .order_by(Order.placed_at.desc(), Order.id)
        )
        orders, total = paginate_query(self.session, statement, params)

        items = [
            OrderSummary(
                id=order.id,
                order_number=order.order_number,
                status=order.status,
                grand_total=order.grand_total,
                currency=order.currency,
                item_count=sum(len(sub.items) for sub in order.sub_orders),
                seller_count=len(order.sub_orders),
                placed_at=order.placed_at,
            )
            for order in orders
        ]
        return Page.create(items, total, params)

    def get_order_detail(self, user: User, order_id: uuid.UUID) -> OrderDetail:
        order = self.session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.sub_orders).selectinload(SubOrder.items),
                selectinload(Order.sub_orders).selectinload(SubOrder.shipment),
                selectinload(Order.sub_orders).joinedload(SubOrder.producer),
            )
        )
        if order is None:
            raise NotFoundError("No encontramos este pedido.")

        # Un pedido solo lo consulta su comprador o un administrador.
        is_admin = "admin" in user.role_codes
        if order.user_id != user.id and not is_admin:
            raise ForbiddenError("Este pedido no te pertenece.")

        payment = self.session.scalar(
            select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
        )

        return OrderDetail(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            subtotal=order.subtotal,
            shipping_total=order.shipping_total,
            discount_total=order.discount_total,
            grand_total=order.grand_total,
            currency=order.currency,
            shipping_address=order.shipping_address_snapshot,
            customer_notes=order.customer_notes,
            sub_orders=[self._to_sub_order_response(sub) for sub in order.sub_orders],
            payment=PaymentResponse.model_validate(payment) if payment else None,
            placed_at=order.placed_at,
        )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _get_address(self, user: User, address_id: uuid.UUID) -> Address:
        address = self.session.scalar(
            select(Address).where(
                Address.id == address_id,
                Address.user_id == user.id,
                Address.deleted_at.is_(None),
            )
        )
        if address is None:
            raise NotFoundError("No encontramos esta dirección de entrega.")
        return address

    def _address_snapshot(self, address: Address) -> dict:
        return {
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "street_address": address.street_address,
            "neighborhood": address.neighborhood,
            "municipality_id": address.municipality_id,
            "department_id": address.department_id,
            "notes": address.notes,
        }

    def _load_cart_items(self, user: User) -> list[CartItem]:
        cart = self.cart_service.get_or_create_cart(user)
        return list(
            self.session.scalars(
                select(CartItem)
                .where(CartItem.cart_id == cart.id)
                .options(
                    joinedload(CartItem.variant)
                    .joinedload(ProductVariant.product)
                    .joinedload(Product.producer),
                    joinedload(CartItem.variant).joinedload(ProductVariant.inventory),
                )
            )
            .unique()
            .all()
        )

    def _assert_purchasable(self, variant: ProductVariant) -> None:
        if not variant.is_active or variant.deleted_at is not None:
            raise BusinessRuleError(f"La presentación '{variant.label}' ya no está disponible.")
        if not variant.product.is_purchasable:
            raise BusinessRuleError(f"'{variant.product.name}' ya no está a la venta.")

    def _shipping_for(self, subtotal: Decimal) -> Decimal:
        from app.modules.cart.service import (
            FLAT_SHIPPING_PER_SELLER,
            FREE_SHIPPING_THRESHOLD,
        )

        return Decimal("0") if subtotal >= FREE_SHIPPING_THRESHOLD else FLAT_SHIPPING_PER_SELLER

    def _generate_order_number(self) -> str:
        """Número legible del pedido: MG-2026-000123.

        El correlativo sale de una secuencia de PostgreSQL. Antes se calculaba
        con `SELECT count(*) + 1`, que no es atómico: dos checkouts simultáneos
        leían el mismo total, generaban el mismo número y la restricción
        `UNIQUE` hacía fallar a uno de los dos. Dos compradores sin relación
        entre sí chocaban por pagar en el mismo instante.

        `nextval` no toma bloqueos ni se revierte con un `ROLLBACK`, así que la
        numeración puede saltarse algún valor si un pedido falla a medias. Es
        preferible a serializar todas las compras: `order_number` identifica un
        pedido, no es una numeración fiscal.
        """
        sequence_value = self.session.scalar(order_number_seq.next_value())
        year = datetime.now(UTC).year
        return f"MG-{year}-{sequence_value:06d}"

    def _lock_checkout_for(self, user: User) -> None:
        """Impide que un mismo comprador ejecute dos checkouts a la vez.

        Sin esto, un doble clic en «Pagar» lanza dos peticiones que leen el
        mismo carrito antes de que ninguna lo vacíe, y el comprador termina con
        dos pedidos idénticos.

        El bloqueo es por usuario, no global: dos compradores distintos siguen
        pagando en paralelo. `pg_advisory_xact_lock` se libera solo al cerrar la
        transacción, incluso si esta falla, así que no puede quedar retenido.
        """
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"checkout:{user.id}"},
        )

    def _get_sub_order(self, sub_order_id: uuid.UUID) -> SubOrder:
        sub_order = self.session.scalar(
            select(SubOrder)
            .where(SubOrder.id == sub_order_id)
            .options(
                selectinload(SubOrder.items),
                selectinload(SubOrder.shipment),
                joinedload(SubOrder.producer),
            )
        )
        if sub_order is None:
            raise NotFoundError("No encontramos este pedido.")
        return sub_order

    def _reviewed_items(self, sub_order: SubOrder) -> set[uuid.UUID]:
        """Líneas de esta sub-orden que ya tienen reseña.

        Sin esto, `has_review` salía siempre en falso y el detalle del pedido
        seguía ofreciendo «escribir una reseña» sobre un café ya reseñado, que
        al enviarse acababa en un 409.
        """
        item_ids = [item.id for item in sub_order.items]
        if not item_ids:
            return set()
        return set(
            self.session.scalars(
                select(Review.order_item_id).where(
                    Review.order_item_id.in_(item_ids), Review.deleted_at.is_(None)
                )
            ).all()
        )

    def _to_sub_order_response(self, sub_order: SubOrder) -> SubOrderResponse:
        producer = sub_order.producer
        reviewed = self._reviewed_items(sub_order)
        return SubOrderResponse(
            id=sub_order.id,
            sub_order_number=sub_order.sub_order_number,
            producer_id=sub_order.producer_id,
            producer_name=producer.brand_name or producer.legal_name,
            status=sub_order.status,
            subtotal=sub_order.subtotal,
            shipping_cost=sub_order.shipping_cost,
            items=[
                OrderItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    product_name_snapshot=item.product_name_snapshot,
                    variant_label_snapshot=item.variant_label_snapshot,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    # Solo se reseña lo entregado, y una sola vez por compra
                    # (HU-CC-10, CA1 y CA3).
                    can_review=(
                        sub_order.status == SubOrderStatus.DELIVERED and item.id not in reviewed
                    ),
                    has_review=item.id in reviewed,
                )
                for item in sub_order.items
            ],
            shipment=(
                ShipmentResponse.model_validate(sub_order.shipment) if sub_order.shipment else None
            ),
            cancellation_reason=sub_order.cancellation_reason,
            is_cancellable=sub_order.is_cancellable,
            created_at=sub_order.created_at,
        )

    def _notify_buyer(
        self,
        user: User,
        notification_type: NotificationType,
        title: str,
        body: str,
        action_url: str,
    ) -> None:
        self.session.add(
            Notification(
                user_id=user.id,
                type=notification_type,
                title=title,
                body=body,
                action_url=action_url,
                is_transactional=True,
            )
        )
        self.session.flush()

    def _notify_producer(self, producer_id: uuid.UUID, order: Order, sub_order: SubOrder) -> None:
        producer = self.session.get(ProducerProfile, producer_id)
        if producer is None:
            return

        self.session.add(
            Notification(
                user_id=producer.user_id,
                type=NotificationType.NEW_ORDER_RECEIVED,
                title="Nuevo pedido recibido",
                body=f"Recibiste el pedido {sub_order.sub_order_number}.",
                action_url=f"/productor/pedidos/{sub_order.id}",
                is_transactional=True,
            )
        )
        self.session.flush()


def cart_items_pairs(
    grouped: dict[uuid.UUID, list[tuple[CartItem, ProductVariant]]],
) -> list[tuple[CartItem, ProductVariant]]:
    """Aplana la agrupación por productor en una lista de pares."""
    return [pair for pairs in grouped.values() for pair in pairs]
