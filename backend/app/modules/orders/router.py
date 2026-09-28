"""Endpoints de pedidos y pagos."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.core.pagination import Page, PageParams
from app.core.permissions import CurrentUser, ProducerUser
from app.db.session import get_session
from app.integrations.payments import get_payment_provider
from app.models.enums import PaymentStatus
from app.modules.orders.receipt import ReceiptService
from app.modules.orders.service import OrderService
from app.schemas.common import MessageResponse
from app.schemas.order import (
    CheckoutRequest,
    CheckoutResponse,
    OrderCancelRequest,
    OrderDetail,
    OrderSummary,
    SubOrderResponse,
    SubOrderStatusUpdate,
)

router = APIRouter(tags=["pedidos"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/orders",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirmar la compra",
)
def checkout(payload: CheckoutRequest, user: CurrentUser, session: SessionDep) -> CheckoutResponse:
    """Convierte el carrito en un pedido.

    El pedido se divide en una sub-orden por vendedor y la operación es
    atómica: ante cualquier error no queda pedido a medias ni inventario
    reservado (HU-CC-07).
    """
    return OrderService(session).checkout(user, payload)


@router.get("/orders", response_model=Page[OrderSummary], summary="Mis pedidos")
def list_orders(
    user: CurrentUser, session: SessionDep, params: Annotated[PageParams, Depends()]
) -> Page[OrderSummary]:
    return OrderService(session).list_user_orders(user, params)


@router.get("/orders/{order_id}", response_model=OrderDetail, summary="Detalle del pedido")
def get_order(order_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> OrderDetail:
    return OrderService(session).get_order_detail(user, order_id)


@router.get(
    "/orders/{order_id}/receipt",
    summary="Descargar el comprobante en PDF",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "Comprobante del pedido"}},
)
def download_receipt(order_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Response:
    """Comprobante del pedido (HU-CC-11).

    Lo descarga su comprador o un administrador; a cualquier otro se le responde
    403. No es una factura: la factura electrónica la expide cada vendedor ante
    la DIAN, y el propio documento lo dice para que nadie lo presente como
    soporte tributario.
    """
    pdf, filename = ReceiptService(session).render(user, order_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            # `attachment` fuerza la descarga en vez de abrirlo dentro de la
            # página, que es lo que evita servir contenido activo desde el
            # dominio de la API.
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post(
    "/orders/sub-orders/{sub_order_id}/cancel",
    response_model=SubOrderResponse,
    summary="Cancelar un pedido no despachado",
)
def cancel_sub_order(
    sub_order_id: uuid.UUID,
    payload: OrderCancelRequest,
    user: CurrentUser,
    session: SessionDep,
) -> SubOrderResponse:
    return OrderService(session).cancel_sub_order(user, sub_order_id, payload.reason)


@router.patch(
    "/orders/sub-orders/{sub_order_id}/status",
    response_model=SubOrderResponse,
    summary="Actualizar el estado (vendedor)",
)
def update_sub_order_status(
    sub_order_id: uuid.UUID,
    payload: SubOrderStatusUpdate,
    producer: ProducerUser,
    session: SessionDep,
) -> SubOrderResponse:
    """Avanza el estado de una sub-orden. Solo el vendedor dueño puede hacerlo."""
    return OrderService(session).update_sub_order_status(
        producer,
        sub_order_id,
        payload.status,
        note=payload.note,
        carrier=payload.carrier,
        tracking_number=payload.tracking_number,
    )


@router.post(
    "/payments/webhook",
    response_model=MessageResponse,
    summary="Webhook de confirmación de pago",
    include_in_schema=False,
)
async def payment_webhook(
    request: Request,
    session: SessionDep,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> MessageResponse:
    """Recibe la confirmación del proveedor de pago.

    La firma se valida antes de actuar: sin esa comprobación, cualquiera podría
    notificar un pago aprobado que nunca ocurrió. Un evento con firma inválida
    se registra y se descarta.
    """
    payload: dict[str, Any] = await request.json()
    event = get_payment_provider().parse_webhook(payload, x_signature)

    if not event.signature_valid:
        # Se responde 200 deliberadamente: informar del rechazo permitiría a un
        # atacante ajustar su intento hasta dar con una firma válida.
        return MessageResponse(message="Evento recibido.")

    OrderService(session).confirm_payment(
        event.reference, approved=event.status == PaymentStatus.APPROVED
    )
    return MessageResponse(message="Evento procesado.")
