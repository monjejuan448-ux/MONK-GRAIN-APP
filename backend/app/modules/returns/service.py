"""Devoluciones: retracto, garantía legal y reembolso.

Este módulo traduce a código dos figuras del Estatuto del Consumidor que la
interfaz presenta juntas pero que la ley trata por separado:

- **Retracto** (artículo 47 de la Ley 1480 de 2011). El comprador se arrepiente,
  no tiene que explicar por qué, dispone de cinco días hábiles desde la entrega
  y devuelve el café sellado. El transporte de vuelta corre por su cuenta; el
  reembolso es íntegro y no puede tardar más de treinta días calendario contados
  **desde que ejerció el derecho**, no desde que alguien apruebe la solicitud.
- **Garantía legal** (artículos 7, 8 y 11). Algo salió mal con el producto. El
  plazo es el de la fecha de vencimiento impresa y, a falta de ella, un año
  desde la entrega. El transporte lo paga quien vende y la respuesta escrita
  debe darse dentro de los quince días hábiles siguientes (Decreto 735 de 2013).

Tres decisiones de diseño se derivan de ahí:

1. **Los plazos se calculan al radicar y se guardan.** Un vencimiento que se
   recalculara en cada lectura cambiaría si mañana alguien toca la fórmula, y el
   comprador tiene derecho al plazo que corría cuando presentó su reclamación.
2. **El importe del reembolso no se negocia.** Lo calcula el servidor a partir
   de las líneas devueltas. El artículo 47 prohíbe descuentos y retenciones, así
   que no hay ningún campo por donde quien vende pueda rebajarlo.
3. **Rechazar exige motivar.** La respuesta escrita es el documento que el
   comprador acompaña a su demanda ante la Superintendencia; una casilla de
   «rechazado» sin razones lo dejaría sin ese soporte.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.business_days import add_business_days
from app.core.exceptions import (
    BusinessRuleError,
    ForbiddenError,
    InvalidStateTransitionError,
    NotFoundError,
)
from app.core.files import StoredFile
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate_query
from app.integrations.storage import get_storage
from app.models.catalog import Inventory
from app.models.enums import (
    ALLOWED_RETURN_TRANSITIONS,
    OPEN_RETURN_STATUSES,
    RETURN_REASON_LABELS,
    SELLER_ATTRIBUTABLE_RETURN_REASONS,
    CommissionStatus,
    NotificationType,
    OrderStatus,
    PaymentStatus,
    ReturnReason,
    ReturnStatus,
    RoleCode,
    SubOrderStatus,
)
from app.models.messaging import Notification
from app.models.order import Order, OrderItem, SubOrder
from app.models.payment import Commission, Payment
from app.models.shipment import Return, ReturnEvidence, ReturnItem, return_number_seq
from app.models.user import User
from app.modules.orders.service import derive_order_status
from app.schemas.returns import (
    ReturnableItem,
    ReturnDetail,
    ReturnEligibility,
    ReturnEvidenceResponse,
    ReturnItemResponse,
    ReturnRequestInput,
    ReturnResolutionInput,
    ReturnSummary,
)

logger = get_logger(__name__)

# Artículo 47: cinco días hábiles siguientes a la entrega.
WITHDRAWAL_BUSINESS_DAYS = 5

# Artículo 8: en productos perecederos el término de la garantía es la fecha de
# vencimiento impresa; a falta de ella, un año desde la entrega por tratarse de
# un producto nuevo. Hoy no se captura la fecha de vencimiento del empaque, así
# que rige siempre el año, que es el término más favorable al comprador.
WARRANTY_CALENDAR_DAYS = 365

# Decreto 735 de 2013: quince días hábiles para responder por escrito.
RESPONSE_BUSINESS_DAYS = 15

# Artículo 47: treinta días calendario para devolver el dinero del retracto.
WITHDRAWAL_REFUND_CALENDAR_DAYS = 30

# Artículo 11, numeral 3: quince días hábiles para el reembolso por garantía.
WARRANTY_REFUND_BUSINESS_DAYS = 15

# Las fotos del reclamo se guardan fuera de los prefijos públicos.
EVIDENCE_PREFIX = "returns"
EVIDENCE_LINK_TTL_SECONDS = 300
MAX_EVIDENCES_PER_RETURN = 8

# Estados de la sub-orden desde los que puede reclamarse. El retracto exige
# además que ya se haya entregado, porque su plazo cuenta desde la entrega.
CLAIMABLE_SUB_ORDER_STATUSES = (SubOrderStatus.SHIPPED, SubOrderStatus.DELIVERED)


class ReturnService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.storage = get_storage()

    # ------------------------------------------------------------------
    # Elegibilidad
    # ------------------------------------------------------------------
    def eligibility(self, user: User, sub_order_id: uuid.UUID) -> ReturnEligibility:
        """Qué puede devolverse hoy de esta sub-orden, y bajo qué figura.

        Se consulta antes de pintar el formulario: decide si aparece el botón
        «Solicitar devolución» y qué motivos ofrece.
        """
        sub_order = self._buyer_sub_order(user, sub_order_id)
        delivered_at = self._delivered_at(sub_order)

        withdrawal_deadline = None
        warranty_deadline = None
        if delivered_at is not None:
            delivered_day = delivered_at.astimezone(UTC).date()
            withdrawal_deadline = add_business_days(delivered_day, WITHDRAWAL_BUSINESS_DAYS)
            warranty_deadline = delivered_day + timedelta(days=WARRANTY_CALENDAR_DAYS)

        items = self._returnable_items(sub_order)
        allowed = self._allowed_reasons(sub_order, withdrawal_deadline, warranty_deadline)

        blocked = self._blocked_reason(sub_order, items, allowed)

        return ReturnEligibility(
            sub_order_id=sub_order.id,
            sub_order_number=sub_order.sub_order_number,
            can_request=blocked is None,
            allowed_reasons=allowed,
            withdrawal_deadline=withdrawal_deadline,
            warranty_deadline=warranty_deadline,
            delivered_at=delivered_at,
            items=items,
            blocked_reason=blocked,
        )

    def _allowed_reasons(
        self,
        sub_order: SubOrder,
        withdrawal_deadline: date | None,
        warranty_deadline: date | None,
    ) -> list[ReturnReason]:
        """Motivos que siguen vivos hoy para esta sub-orden."""
        if sub_order.status not in CLAIMABLE_SUB_ORDER_STATUSES:
            return []

        today = datetime.now(UTC).date()
        allowed: list[ReturnReason] = []

        # El retracto necesita una entrega desde la cual contar sus cinco días.
        if withdrawal_deadline is not None and today <= withdrawal_deadline:
            allowed.append(ReturnReason.WITHDRAWAL)

        # La garantía vive mucho más, y un pedido despachado que nunca llegó
        # también da derecho a reclamar aunque no haya fecha de entrega.
        if warranty_deadline is None or today <= warranty_deadline:
            allowed.extend(
                [
                    ReturnReason.DAMAGED,
                    ReturnReason.WRONG_ITEM,
                    ReturnReason.QUALITY,
                    ReturnReason.OTHER,
                ]
            )
        return allowed

    @staticmethod
    def _blocked_reason(
        sub_order: SubOrder,
        items: list[ReturnableItem],
        allowed: list[ReturnReason],
    ) -> str | None:
        """Explicación en lenguaje llano de por qué no puede pedirse."""
        if sub_order.status in (SubOrderStatus.PENDING, SubOrderStatus.CONFIRMED):
            return (
                "Este pedido todavía no ha sido despachado. Puedes cancelarlo sin costo "
                "desde el detalle del pedido."
            )
        if sub_order.status is SubOrderStatus.CANCELLED:
            return "Este pedido está cancelado."
        if sub_order.status is SubOrderStatus.REFUNDED:
            return "Este pedido ya fue reembolsado."
        if not any(item.returnable_qty > 0 for item in items):
            return "Ya solicitaste la devolución de todos los productos de este pedido."
        if not allowed:
            return (
                "El plazo para reclamar por este pedido ya venció. Si crees que "
                "corresponde de todos modos, escríbenos y lo revisamos."
            )
        return None

    def _returnable_items(self, sub_order: SubOrder) -> list[ReturnableItem]:
        """Unidades de cada línea que aún no están comprometidas en otra solicitud."""
        already = self._returned_quantities(sub_order.id)
        return [
            ReturnableItem(
                order_item_id=item.id,
                product_name=item.product_name_snapshot,
                variant_label=item.variant_label_snapshot,
                purchased_qty=item.quantity,
                returnable_qty=max(0, item.quantity - already.get(item.id, 0)),
                unit_price=item.unit_price,
            )
            for item in sub_order.items
        ]

    def _returned_quantities(self, sub_order_id: uuid.UUID) -> dict[uuid.UUID, int]:
        """Unidades ya comprometidas en devoluciones vivas, por línea de pedido.

        Una solicitud rechazada libera sus unidades: el comprador puede volver a
        reclamar la misma línea por otro motivo.
        """
        rows = self.session.execute(
            select(ReturnItem.order_item_id, func.sum(ReturnItem.quantity))
            .join(Return, Return.id == ReturnItem.return_id)
            .where(
                Return.sub_order_id == sub_order_id,
                Return.status.in_(tuple(OPEN_RETURN_STATUSES)),
            )
            .group_by(ReturnItem.order_item_id)
        ).all()
        return {row[0]: int(row[1]) for row in rows}

    # ------------------------------------------------------------------
    # Radicación
    # ------------------------------------------------------------------
    def request_return(self, user: User, payload: ReturnRequestInput) -> ReturnDetail:
        """Radica la solicitud y devuelve la constancia.

        La constancia lleva número y fecha de radicación porque el artículo 58
        de la Ley 1480 obliga a acompañarla a la demanda ante la
        Superintendencia: sin ella el comprador no puede reclamar más adelante.
        """
        sub_order = self._buyer_sub_order(user, payload.sub_order_id)
        eligibility = self.eligibility(user, payload.sub_order_id)

        if not eligibility.can_request:
            raise BusinessRuleError(
                eligibility.blocked_reason or "Este pedido no admite devolución."
            )

        if payload.reason not in eligibility.allowed_reasons:
            raise BusinessRuleError(self._reason_rejected_message(payload.reason, eligibility))

        returnable = {item.order_item_id: item for item in eligibility.items}
        items_refund = Decimal("0")
        lines: list[tuple[OrderItem, int, Decimal]] = []

        for requested in payload.items:
            available = returnable.get(requested.order_item_id)
            if available is None:
                raise BusinessRuleError("Uno de los productos no pertenece a este pedido.")
            if requested.quantity > available.returnable_qty:
                raise BusinessRuleError(
                    f"De «{available.product_name}» solo puedes devolver "
                    f"{available.returnable_qty} de los {available.purchased_qty} kg: "
                    "las demás ya están en otra solicitud."
                )
            order_item = self.session.get(OrderItem, requested.order_item_id)
            assert order_item is not None  # noqa: S101 — validado contra la sub-orden
            line_refund = order_item.unit_price * requested.quantity
            items_refund += line_refund
            lines.append((order_item, requested.quantity, line_refund))

        # El envío original vuelve al comprador solo si devuelve el pedido
        # completo: si se queda con parte, el transporte ya se prestó.
        covers_all = self._covers_whole_sub_order(eligibility.items, payload)
        shipping_refund = sub_order.shipping_cost if covers_all else Decimal("0")

        filed_on = datetime.now(UTC).date()
        seller_pays_return = payload.reason in SELLER_ATTRIBUTABLE_RETURN_REASONS

        return_request = Return(
            return_number=self._generate_return_number(),
            sub_order_id=sub_order.id,
            requested_by=user.id,
            reason=payload.reason,
            description=(payload.description or "").strip() or None,
            declared_unopened=payload.declared_unopened,
            status=ReturnStatus.REQUESTED,
            refund_amount=items_refund + shipping_refund,
            return_shipping_paid_by_seller=seller_pays_return,
            response_due_at=add_business_days(filed_on, RESPONSE_BUSINESS_DAYS),
            refund_due_at=self._refund_deadline(payload.reason, filed_on),
        )
        self.session.add(return_request)
        self.session.flush()

        for order_item, quantity, line_refund in lines:
            self.session.add(
                ReturnItem(
                    return_id=return_request.id,
                    order_item_id=order_item.id,
                    quantity=quantity,
                    line_refund=line_refund,
                )
            )

        self._notify_producer(
            sub_order,
            NotificationType.RETURN_REQUESTED,
            "Nueva solicitud de devolución",
            (
                f"El comprador radicó la devolución {return_request.return_number} "
                f"sobre el pedido {sub_order.sub_order_number}. Tienes hasta el "
                f"{return_request.response_due_at.isoformat()} para responder por escrito."
            ),
            f"/productor/devoluciones/{return_request.id}",
        )

        self.session.commit()

        logger.info(
            "return_requested",
            return_number=return_request.return_number,
            sub_order=sub_order.sub_order_number,
            reason=payload.reason.value,
            amount=str(return_request.refund_amount),
        )
        return self.get_detail(user, return_request.id)

    @staticmethod
    def _reason_rejected_message(reason: ReturnReason, eligibility: ReturnEligibility) -> str:
        if reason is ReturnReason.WITHDRAWAL:
            if eligibility.withdrawal_deadline is None:
                return (
                    "El retracto se cuenta desde la entrega, y este pedido todavía no "
                    "figura como entregado."
                )
            return (
                "El plazo de cinco días hábiles para retractarte venció el "
                f"{eligibility.withdrawal_deadline.isoformat()}. Si el café llegó con "
                "algún problema, la garantía sigue vigente: elige el motivo que "
                "corresponda."
            )
        return "Este motivo ya no admite reclamación para este pedido."

    @staticmethod
    def _covers_whole_sub_order(
        returnable: list[ReturnableItem], payload: ReturnRequestInput
    ) -> bool:
        """¿La solicitud abarca todo lo que quedaba por devolver?"""
        requested = {item.order_item_id: item.quantity for item in payload.items}
        return all(
            requested.get(item.order_item_id, 0) == item.returnable_qty
            and item.returnable_qty == item.purchased_qty
            for item in returnable
        )

    @staticmethod
    def _refund_deadline(reason: ReturnReason, filed_on: date) -> date:
        """Fecha límite para devolver el dinero, según la figura invocada.

        En el retracto los treinta días calendario corren desde que se ejerce el
        derecho —hoy—, no desde que la solicitud se aprueba: condicionarlos a la
        aprobación permitiría alargarlos indefinidamente.
        """
        if reason is ReturnReason.WITHDRAWAL:
            return filed_on + timedelta(days=WITHDRAWAL_REFUND_CALENDAR_DAYS)
        return add_business_days(filed_on, WARRANTY_REFUND_BUSINESS_DAYS)

    def _generate_return_number(self) -> str:
        """Número de radicación legible: DEV-2026-000123."""
        sequence_value = self.session.scalar(return_number_seq.next_value())
        return f"DEV-{datetime.now(UTC).year}-{sequence_value:06d}"

    # ------------------------------------------------------------------
    # Evidencia
    # ------------------------------------------------------------------
    def add_evidence(
        self, user: User, return_id: uuid.UUID, files: list[StoredFile]
    ) -> ReturnDetail:
        """Adjunta fotografías del café y del empaque.

        No son obligatorias. Exigirlas para admitir el reclamo sería poner una
        condición que la ley no impone, y el artículo 43 declara ineficaz de
        pleno derecho lo que dificulte el ejercicio de la garantía.
        """
        return_request = self._visible_return(user, return_id)

        if return_request.status in (ReturnStatus.REJECTED, ReturnStatus.REFUNDED):
            raise BusinessRuleError("Esta solicitud ya está cerrada y no admite más adjuntos.")

        if len(return_request.evidences) + len(files) > MAX_EVIDENCES_PER_RETURN:
            raise BusinessRuleError(
                f"Puedes adjuntar hasta {MAX_EVIDENCES_PER_RETURN} fotografías por solicitud."
            )

        for stored in files:
            key = stored.key_for(f"{EVIDENCE_PREFIX}/{return_request.id}")
            self.storage.put(key, stored.content, stored.content_type)
            self.session.add(
                ReturnEvidence(
                    return_id=return_request.id,
                    file_key=key,
                    content_type=stored.content_type,
                    uploaded_by=user.id,
                )
            )

        self.session.commit()
        logger.info(
            "return_evidence_added",
            return_number=return_request.return_number,
            count=len(files),
        )
        return self.get_detail(user, return_id)

    # ------------------------------------------------------------------
    # Resolución
    # ------------------------------------------------------------------
    def resolve(
        self, user: User, return_id: uuid.UUID, payload: ReturnResolutionInput
    ) -> ReturnDetail:
        """Respuesta escrita de quien vende: aprueba o rechaza, y dice por qué."""
        return_request = self._seller_return(user, return_id)

        target = ReturnStatus.APPROVED if payload.approve else ReturnStatus.REJECTED
        self._transition(return_request, target)

        return_request.resolution_notes = payload.resolution_notes.strip()
        return_request.reviewed_by = user.id
        return_request.reviewed_at = datetime.now(UTC)

        sub_order = return_request.sub_order
        if payload.approve:
            title = "Aprobamos tu devolución"
            body = f"La devolución {return_request.return_number} fue aprobada. " + (
                "Los costos de envío de la devolución corren por cuenta de quien vende."
                if return_request.return_shipping_paid_by_seller
                else "Recuerda que el transporte de la devolución corre por tu cuenta."
            )
        else:
            title = "Respuesta a tu solicitud de devolución"
            body = (
                f"La devolución {return_request.return_number} fue rechazada. "
                "Puedes consultar los motivos en el detalle de la solicitud. Si no "
                "estás de acuerdo, conserva tu número de radicación: lo necesitarás "
                "para acudir a la Superintendencia de Industria y Comercio."
            )

        self._notify_buyer(return_request, title, body)
        self.session.commit()

        logger.info(
            "return_resolved",
            return_number=return_request.return_number,
            approved=payload.approve,
            sub_order=sub_order.sub_order_number,
        )
        return self.get_detail(user, return_id)

    def mark_shipped_back(self, user: User, return_id: uuid.UUID) -> ReturnDetail:
        """El comprador declara que ya envió el café de vuelta."""
        return_request = self._buyer_return(user, return_id)
        self._transition(return_request, ReturnStatus.IN_TRANSIT)

        self._notify_producer(
            return_request.sub_order,
            NotificationType.RETURN_RESOLVED,
            "El comprador envió la devolución",
            f"La devolución {return_request.return_number} va en camino de vuelta.",
            f"/productor/devoluciones/{return_request.id}",
        )
        self.session.commit()
        return self.get_detail(user, return_id)

    def mark_received(self, user: User, return_id: uuid.UUID) -> ReturnDetail:
        """Quien vende confirma que el café volvió."""
        return_request = self._seller_return(user, return_id)
        self._transition(return_request, ReturnStatus.RECEIVED)

        self._notify_buyer(
            return_request,
            "Recibimos tu devolución",
            (
                f"Confirmamos la recepción de la devolución {return_request.return_number}. "
                f"El reembolso debe hacerse a más tardar el "
                f"{return_request.refund_due_at.isoformat()}."
            ),
        )
        self.session.commit()
        return self.get_detail(user, return_id)

    def refund(self, user: User, return_id: uuid.UUID) -> ReturnDetail:
        """Cierra la devolución con el reembolso.

        El importe es el calculado al radicar. No se admite indicar otro: el
        artículo 47 prohíbe descuentos y retenciones sobre el dinero devuelto,
        de modo que el sistema simplemente no ofrece dónde escribirlos.
        """
        return_request = self._seller_return(user, return_id)
        self._transition(return_request, ReturnStatus.REFUNDED)
        return_request.refunded_at = datetime.now(UTC)

        sub_order = return_request.sub_order
        self._restock_if_resellable(return_request)
        items_refund = sum((item.line_refund for item in return_request.items), start=Decimal("0"))
        self._adjust_commission(sub_order, items_refund)
        self._settle_sub_order(sub_order)

        self._notify_buyer(
            return_request,
            "Tu devolución fue reembolsada",
            (
                f"Registramos el reembolso de la devolución {return_request.return_number} "
                f"por ${return_request.refund_amount:,.0f} COP. El proveedor de pago de la "
                "plataforma es simulado: no hay movimiento real de dinero."
            ),
        )
        self.session.commit()

        logger.info(
            "return_refunded",
            return_number=return_request.return_number,
            amount=str(return_request.refund_amount),
        )
        return self.get_detail(user, return_id)

    def _restock_if_resellable(self, return_request: Return) -> None:
        """Devuelve al catálogo el café que puede volver a venderse.

        Solo el retracto repone inventario: la bolsa vuelve sellada y dentro de
        su vida útil. Un café que se devolvió por venir dañado o vencido no
        puede regresar al escaparate.
        """
        if return_request.reason is not ReturnReason.WITHDRAWAL:
            return

        for item in return_request.items:
            order_item = self.session.get(OrderItem, item.order_item_id)
            if order_item is None or order_item.variant_id is None:
                continue
            inventory = self.session.scalar(
                select(Inventory)
                .where(Inventory.variant_id == order_item.variant_id)
                .with_for_update()
            )
            if inventory is not None:
                inventory.stock_qty += item.quantity
        self.session.flush()

    def _adjust_commission(self, sub_order: SubOrder, items_refund: Decimal) -> None:
        """Rebaja la base de comisión en lo que se devolvió.

        Sin esto el vendedor pagaría comisión sobre dinero que ya reintegró. Se
        descuenta solo la parte de producto: el envío nunca formó parte de la
        base. Si la comisión ya se liquidó no se toca —el dinero salió— y queda
        registrado para regularizarlo en el siguiente corte.
        """
        commission = self.session.scalar(
            select(Commission).where(Commission.sub_order_id == sub_order.id)
        )
        if commission is None or items_refund <= 0:
            return

        if commission.status is not CommissionStatus.PENDING:
            logger.warning(
                "commission_already_settled_on_refund",
                sub_order=sub_order.sub_order_number,
                refunded=str(items_refund),
            )
            return

        new_base = max(Decimal("0"), commission.base_amount - items_refund)
        commission.base_amount = new_base
        commission.commission_amount = (new_base * commission.rate_applied).quantize(
            Decimal("0.01")
        )
        if new_base == 0:
            commission.status = CommissionStatus.REVERSED
        self.session.flush()

    def _settle_sub_order(self, sub_order: SubOrder) -> None:
        """Marca la sub-orden como reembolsada cuando ya no queda nada por entregar.

        Una devolución parcial no la cierra: el comprador se quedó con parte de
        lo que compró y esa venta sigue en pie.
        """
        pending = self._returnable_items(sub_order)
        if any(item.returnable_qty > 0 for item in pending):
            return

        sub_order.status = SubOrderStatus.REFUNDED
        self.session.flush()
        self._sync_order_and_payment(sub_order.order_id)

    def _sync_order_and_payment(self, order_id: uuid.UUID) -> None:
        """Cierra el pedido y su pago si ya no queda ninguna sub-orden viva."""
        order = self.session.scalar(
            select(Order).where(Order.id == order_id).options(selectinload(Order.sub_orders))
        )
        if order is None:
            return

        statuses = {sub.status for sub in order.sub_orders}
        order.status = derive_order_status(statuses)

        # El pago solo se marca reembolsado cuando ya no queda nada por
        # entregar: en un pedido con varios vendedores, devolver el café de uno
        # no significa que el comprador haya recuperado todo lo que pagó.
        if order.status is not OrderStatus.REFUNDED:
            self.session.flush()
            return

        payment = self.session.scalar(
            select(Payment)
            .where(Payment.order_id == order.id, Payment.status == PaymentStatus.APPROVED)
            .order_by(Payment.created_at.desc())
        )
        if payment is not None:
            payment.status = PaymentStatus.REFUNDED
        self.session.flush()

    def _transition(self, return_request: Return, target: ReturnStatus) -> None:
        allowed = ALLOWED_RETURN_TRANSITIONS[return_request.status]
        if target not in allowed:
            raise InvalidStateTransitionError(
                f"Una devolución en estado '{return_request.status.value}' no puede pasar "
                f"a '{target.value}'.",
                details={
                    "current": return_request.status.value,
                    "allowed": sorted(status.value for status in allowed),
                },
            )
        return_request.status = target
        self.session.flush()

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def list_for_buyer(self, user: User, params: PageParams) -> Page[ReturnSummary]:
        statement = (
            select(Return)
            .where(Return.requested_by == user.id)
            .order_by(Return.created_at.desc(), Return.id)
        )
        rows, total = paginate_query(self.session, statement, params)
        return Page.create([self._to_summary(row) for row in rows], total, params)

    def list_for_producer(self, user: User, params: PageParams) -> Page[ReturnSummary]:
        profile = user.producer_profile
        if profile is None:
            raise ForbiddenError("Tu cuenta no tiene un perfil de productor.")

        statement = (
            select(Return)
            .join(SubOrder, SubOrder.id == Return.sub_order_id)
            .where(SubOrder.producer_id == profile.id)
            # Lo que vence antes se atiende antes: el orden de la lista es el
            # orden en que hay que responder para no incumplir el plazo.
            .order_by(Return.response_due_at.asc(), Return.created_at.desc(), Return.id)
        )
        rows, total = paginate_query(self.session, statement, params)
        return Page.create([self._to_summary(row) for row in rows], total, params)

    def get_detail(self, user: User, return_id: uuid.UUID) -> ReturnDetail:
        return_request = self._visible_return(user, return_id)
        sub_order = return_request.sub_order
        order = self.session.get(Order, sub_order.order_id)
        assert order is not None  # noqa: S101 — la FK lo garantiza

        return ReturnDetail(
            id=return_request.id,
            return_number=return_request.return_number,
            sub_order_id=sub_order.id,
            sub_order_number=sub_order.sub_order_number,
            order_number=order.order_number,
            producer_name=sub_order.producer.brand_name or sub_order.producer.legal_name,
            reason=return_request.reason,
            reason_label=RETURN_REASON_LABELS[return_request.reason],
            description=return_request.description,
            status=return_request.status,
            declared_unopened=return_request.declared_unopened,
            refund_amount=return_request.refund_amount,
            return_shipping_paid_by_seller=return_request.return_shipping_paid_by_seller,
            response_due_at=return_request.response_due_at,
            refund_due_at=return_request.refund_due_at,
            resolution_notes=return_request.resolution_notes,
            reviewed_at=return_request.reviewed_at,
            refunded_at=return_request.refunded_at,
            items=[
                ReturnItemResponse(
                    id=item.id,
                    order_item_id=item.order_item_id,
                    product_name=item.order_item.product_name_snapshot,
                    variant_label=item.order_item.variant_label_snapshot,
                    quantity=item.quantity,
                    line_refund=item.line_refund,
                )
                for item in return_request.items
            ],
            evidences=[
                ReturnEvidenceResponse(
                    id=evidence.id,
                    content_type=evidence.content_type,
                    url=self.storage.signed_url(evidence.file_key, EVIDENCE_LINK_TTL_SECONDS),
                    created_at=evidence.created_at,
                )
                for evidence in return_request.evidences
            ],
            filed_at=return_request.created_at,
            available_actions=self._available_actions(user, return_request),
        )

    def _available_actions(self, user: User, return_request: Return) -> list[ReturnStatus]:
        """Transiciones que este usuario concreto puede ejecutar ahora.

        Se calcula en el servidor y no en la interfaz: ocultar un botón no es
        control de acceso, pero enviarle al cliente la lista correcta evita
        ofrecerle acciones que el servidor va a rechazar.
        """
        possible = ALLOWED_RETURN_TRANSITIONS[return_request.status]
        is_admin = RoleCode.ADMIN.value in user.role_codes

        # Declarar que el café va de vuelta es lo único que hace el comprador:
        # es el único que sabe si lo entregó al transportador. Lo demás
        # —responder, confirmar la recepción, reembolsar— le toca a quien vende.
        allowed_here: set[ReturnStatus] = set()
        if is_admin or return_request.requested_by == user.id:
            allowed_here.add(ReturnStatus.IN_TRANSIT)
        if is_admin or self._is_seller_of(user, return_request):
            allowed_here |= set(ReturnStatus) - {ReturnStatus.IN_TRANSIT}

        return sorted(possible & allowed_here)

    def _to_summary(self, return_request: Return) -> ReturnSummary:
        sub_order = return_request.sub_order
        order = self.session.get(Order, sub_order.order_id)
        assert order is not None  # noqa: S101 — la FK lo garantiza

        return ReturnSummary(
            id=return_request.id,
            return_number=return_request.return_number,
            order_number=order.order_number,
            sub_order_number=sub_order.sub_order_number,
            producer_name=sub_order.producer.brand_name or sub_order.producer.legal_name,
            reason=return_request.reason,
            reason_label=RETURN_REASON_LABELS[return_request.reason],
            status=return_request.status,
            refund_amount=return_request.refund_amount,
            item_count=sum(item.quantity for item in return_request.items),
            response_due_at=return_request.response_due_at,
            filed_at=return_request.created_at,
        )

    # ------------------------------------------------------------------
    # Acceso
    # ------------------------------------------------------------------
    def _buyer_sub_order(self, user: User, sub_order_id: uuid.UUID) -> SubOrder:
        sub_order = self.session.scalar(
            select(SubOrder)
            .where(SubOrder.id == sub_order_id)
            .options(
                selectinload(SubOrder.items),
                selectinload(SubOrder.shipment),
                selectinload(SubOrder.status_history),
                joinedload(SubOrder.producer),
            )
        )
        if sub_order is None:
            raise NotFoundError("No encontramos este pedido.")

        order = self.session.get(Order, sub_order.order_id)
        if order is None or order.user_id != user.id:
            raise ForbiddenError("Este pedido no te pertenece.")
        return sub_order

    def _load_return(self, return_id: uuid.UUID) -> Return:
        """Carga la solicitud con todo lo que la constancia necesita.

        `populate_existing` no es opcional: si la solicitud ya está en el mapa
        de identidad de la sesión, SQLAlchemy devuelve el objeto que tiene en
        memoria y no vuelve a leer sus colecciones. Adjuntar una fotografía y
        releer la constancia en la misma petición la devolvía sin la fotografía
        recién guardada.
        """
        return_request = self.session.scalar(
            select(Return)
            .where(Return.id == return_id)
            .options(
                selectinload(Return.items).joinedload(ReturnItem.order_item),
                selectinload(Return.evidences),
                joinedload(Return.sub_order).joinedload(SubOrder.producer),
                joinedload(Return.sub_order).selectinload(SubOrder.items),
            )
            .execution_options(populate_existing=True)
        )
        if return_request is None:
            raise NotFoundError("No encontramos esta solicitud de devolución.")
        return return_request

    def _is_seller_of(self, user: User, return_request: Return) -> bool:
        profile = user.producer_profile
        return profile is not None and return_request.sub_order.producer_id == profile.id

    def _visible_return(self, user: User, return_id: uuid.UUID) -> Return:
        """La solicitud la ven su autor, quien vende y un administrador."""
        return_request = self._load_return(return_id)
        if (
            return_request.requested_by == user.id
            or self._is_seller_of(user, return_request)
            or RoleCode.ADMIN.value in user.role_codes
        ):
            return return_request
        raise ForbiddenError("Esta solicitud no te pertenece.")

    def _buyer_return(self, user: User, return_id: uuid.UUID) -> Return:
        return_request = self._load_return(return_id)
        if return_request.requested_by != user.id and RoleCode.ADMIN.value not in user.role_codes:
            raise ForbiddenError("Esta solicitud no te pertenece.")
        return return_request

    def _seller_return(self, user: User, return_id: uuid.UUID) -> Return:
        """Solo quien vende —o un administrador— resuelve una devolución.

        La plataforma conserva la potestad de intervenir porque el artículo 10
        de la Ley 1480 hace solidaria la responsabilidad por la garantía: si
        quien vende no responde dentro del plazo, alguien tiene que hacerlo.
        """
        return_request = self._load_return(return_id)
        if self._is_seller_of(user, return_request) or RoleCode.ADMIN.value in user.role_codes:
            return return_request
        raise ForbiddenError("Esta solicitud no pertenece a tu catálogo.")

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _delivered_at(self, sub_order: SubOrder) -> datetime | None:
        """Momento de la entrega, del que cuelgan todos los plazos.

        Se prefiere la fecha del envío, y si falta se recurre al historial de
        estados: el plazo del comprador no puede depender de que exista una guía
        logística bien diligenciada.
        """
        if sub_order.shipment is not None and sub_order.shipment.delivered_at is not None:
            return sub_order.shipment.delivered_at

        delivered = [
            entry.created_at
            for entry in sub_order.status_history
            if entry.to_status is SubOrderStatus.DELIVERED
        ]
        return min(delivered) if delivered else None

    def _notify_buyer(self, return_request: Return, title: str, body: str) -> None:
        self.session.add(
            Notification(
                user_id=return_request.requested_by,
                type=NotificationType.RETURN_RESOLVED,
                title=title,
                body=body,
                action_url=f"/mi-cuenta/devoluciones/{return_request.id}",
                is_transactional=True,
            )
        )
        self.session.flush()

    def _notify_producer(
        self,
        sub_order: SubOrder,
        notification_type: NotificationType,
        title: str,
        body: str,
        action_url: str,
    ) -> None:
        self.session.add(
            Notification(
                user_id=sub_order.producer.user_id,
                type=notification_type,
                title=title,
                body=body,
                action_url=action_url,
                is_transactional=True,
            )
        )
        self.session.flush()
