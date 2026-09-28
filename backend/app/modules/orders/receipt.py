"""Comprobante del pedido en PDF (HU-CC-11, RF-05.6).

Este documento **no es una factura**. La factura electrónica la expide cada
vendedor ante la DIAN y es una obligación suya; el comprobante es la constancia
de la relación de consumo que el artículo 50, literal e), de la Ley 1480 de 2011
obliga a poder acreditar. Decirlo en el propio papel evita que alguien lo
presente como soporte tributario.

Dos decisiones de contenido merecen explicación:

- **Identifica a cada vendedor con sus datos del artículo 53**: razón social,
  documento, dirección de notificaciones y teléfono. Esos campos no salen en
  ningún endpoint público, y aquí sí, porque el comprobante lo recibe únicamente
  quien contrató con ese vendedor y necesita saber a quién reclamar. Un
  comprobante que no diga contra quién se reclama no sirve de constancia.
- **Reproduce las cifras tal como se cobraron**, con el envío separado del
  precio de los productos (artículo 26), y el nombre y la presentación
  congelados en el pedido, no los actuales del catálogo.

El PDF se genera al vuelo y no se guarda: los datos de los que sale ya viven en
la base de datos, y almacenar una copia solo añadiría un archivo que puede
quedar desincronizado.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from weasyprint import HTML

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.enums import PaymentMethod, PaymentStatus, SubOrderStatus
from app.models.geo import Department, Municipality
from app.models.order import Order, SubOrder
from app.models.payment import Payment
from app.models.user import User

logger = get_logger(__name__)

PAYMENT_LABELS: dict[PaymentStatus, str] = {
    PaymentStatus.PENDING: "Pendiente de confirmación",
    PaymentStatus.APPROVED: "Aprobado",
    PaymentStatus.DECLINED: "Rechazado",
    PaymentStatus.REFUNDED: "Reembolsado",
    PaymentStatus.FAILED: "Fallido",
}

METHOD_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.CARD: "Tarjeta",
    PaymentMethod.PSE: "PSE",
    PaymentMethod.BANK_TRANSFER: "Transferencia bancaria",
    PaymentMethod.CASH: "Efectivo",
    PaymentMethod.SIMULATED: "Pago simulado",
}

SUB_ORDER_LABELS: dict[SubOrderStatus, str] = {
    SubOrderStatus.PENDING: "Pendiente de pago",
    SubOrderStatus.CONFIRMED: "Confirmado",
    SubOrderStatus.PREPARED: "Preparado",
    SubOrderStatus.SHIPPED: "Enviado",
    SubOrderStatus.DELIVERED: "Entregado",
    SubOrderStatus.CANCELLED: "Cancelado",
    SubOrderStatus.REFUNDED: "Reembolsado",
}


def _money(amount: Decimal | None) -> str:
    """Importe en pesos, con separador de miles y sin decimales.

    El peso no usa decimales en la práctica comercial. Se formatea a mano
    porque `locale` depende de que el sistema tenga instalada la configuración
    regional, y en un contenedor mínimo no la tiene.
    """
    if amount is None:
        return "—"
    entero = f"{int(Decimal(amount).quantize(Decimal('1'))):,}".replace(",", ".")
    return f"$ {entero}"


# El documento vive en `app/templates/receipt.html`, fuera de este módulo: es
# maquetación, y mezclarla con la lógica obliga a tocar código Python para
# mover un margen.
#
# El autoescapado no es opcional. El nombre de un café, una nota de entrega o la
# historia de una finca son texto que escribió un usuario; sin escapar podrían
# alterar la estructura del PDF.
_ENVIRONMENT = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parents[2] / "templates"),
    autoescape=select_autoescape(default=True),
    auto_reload=False,
)
_ENVIRONMENT.filters["money"] = _money

TEMPLATE_NAME = "receipt.html"


class ReceiptService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def render(self, user: User, order_id: uuid.UUID) -> tuple[bytes, str]:
        """Devuelve el PDF y el nombre de archivo sugerido."""
        order = self._authorized_order(user, order_id)
        context = self._build_context(order)

        document = _ENVIRONMENT.get_template(TEMPLATE_NAME).render(**context)
        pdf = HTML(string=document).write_pdf()
        assert pdf is not None  # noqa: S101 — `write_pdf` sin destino siempre devuelve bytes

        logger.info(
            "order_receipt_generated",
            order_number=order.order_number,
            user_id=str(user.id),
            bytes=len(pdf),
        )
        return pdf, f"MONK-GRAIN-{order.order_number}.pdf"

    def _authorized_order(self, user: User, order_id: uuid.UUID) -> Order:
        """El comprobante lo descarga su comprador, o un administrador (HU-CC-11, CA2)."""
        order = self.session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.sub_orders).selectinload(SubOrder.items),
                selectinload(Order.sub_orders).joinedload(SubOrder.producer),
            )
        )
        if order is None:
            raise NotFoundError("No encontramos este pedido.")

        if order.user_id != user.id and "admin" not in user.role_codes:
            raise ForbiddenError("Este pedido no te pertenece.")
        return order

    def _build_context(self, order: Order) -> dict:
        buyer = self.session.get(User, order.user_id)
        payment = self.session.scalar(
            select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
        )

        return {
            "order": order,
            "placed_at": order.placed_at.astimezone(UTC).strftime("%d/%m/%Y"),
            "issued_at": datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC"),
            "buyer_name": buyer.full_name if buyer else "—",
            "buyer_email": buyer.email if buyer else "—",
            "address": self._address(order),
            "payment_status": (
                PAYMENT_LABELS.get(payment.status, payment.status.value)
                if payment
                else "Sin registro de pago"
            ),
            "payment_method": (
                METHOD_LABELS.get(payment.method, payment.method.value) if payment else None
            ),
            "payment_reference": payment.provider_reference if payment else None,
            # El proveedor simulado se declara en el papel: un comprobante que
            # no lo dijera sugeriría un cobro que no ocurrió.
            "simulated_payment": bool(payment and payment.provider == "simulated"),
            "sellers": [self._seller(sub_order) for sub_order in order.sub_orders],
        }

    def _address(self, order: Order) -> dict:
        """Dirección tal como quedó congelada al confirmar la compra.

        El municipio y el departamento se guardan por identificador, así que sus
        nombres se resuelven al imprimir. Si alguno desapareció del catálogo
        geográfico, el resto de la dirección sigue siendo legible.
        """
        snapshot: dict = dict(order.shipping_address_snapshot or {})

        place = None
        municipality = (
            self.session.get(Municipality, snapshot["municipality_id"])
            if snapshot.get("municipality_id")
            else None
        )
        if municipality is not None:
            department = self.session.get(Department, municipality.department_id)
            place = (
                f"{municipality.name}, {department.name}"
                if department is not None
                else municipality.name
            )

        return {
            "recipient_name": snapshot.get("recipient_name") or "—",
            "phone": snapshot.get("phone") or "—",
            "street_address": snapshot.get("street_address") or "—",
            "neighborhood": snapshot.get("neighborhood"),
            "notes": snapshot.get("notes"),
            "place": place,
        }

    @staticmethod
    def _seller(sub_order: SubOrder) -> dict:
        """Datos del vendedor exigidos por el artículo 53 de la Ley 1480.

        El comprador tiene derecho a saber contra quién reclama. Estos campos no
        se publican en ningún endpoint abierto; aquí figuran porque el
        comprobante solo lo recibe quien contrató con este vendedor.
        """
        producer = sub_order.producer
        return {
            "display_name": producer.brand_name or producer.legal_name,
            "legal_name": producer.legal_name,
            "document_number": producer.document_number,
            "notification_address": producer.notification_address,
            "contact_phone": producer.contact_phone,
            "number": sub_order.sub_order_number,
            "status": SUB_ORDER_LABELS.get(sub_order.status, sub_order.status.value),
            "subtotal": sub_order.subtotal,
            "shipping_cost": sub_order.shipping_cost,
            # La clave se llama `lines` y no `items`: en una plantilla Jinja,
            # `seller.items` resuelve al método `.items()` del diccionario en
            # lugar de a la clave, y el bucle falla sin decir por qué.
            "lines": [
                {
                    "name": item.product_name_snapshot,
                    "variant": item.variant_label_snapshot,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total,
                }
                for item in sub_order.items
            ],
        }
