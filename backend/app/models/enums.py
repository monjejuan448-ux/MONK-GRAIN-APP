"""Tipos enumerados del dominio.

Cada estado tiene sus valores explícitos y se materializa como ENUM nativo de
PostgreSQL: la base de datos rechaza cualquier valor fuera del conjunto, sin
depender de que la validación ocurra en la aplicación.
"""

from enum import StrEnum


# ------------------------------------------------------------------
# Identidad y acceso
# ------------------------------------------------------------------
class UserStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class RoleCode(StrEnum):
    VISITOR = "visitor"
    CONSUMER = "consumer"
    BUSINESS = "business"
    PRODUCER = "producer"
    ADMIN = "admin"


class TokenPurpose(StrEnum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"  # noqa: S105 — nombre de propósito, no una credencial


# ------------------------------------------------------------------
# Productores y empresas
# ------------------------------------------------------------------
class ProducerType(StrEnum):
    FARMER = "farmer"
    FARM = "farm"
    COOPERATIVE = "cooperative"
    ROASTER = "roaster"


class ProducerStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class BusinessType(StrEnum):
    ROASTER = "roaster"
    DISTRIBUTOR = "distributor"
    COFFEE_SHOP = "coffee_shop"
    COMPANY = "company"


class BusinessStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class CertStatus(StrEnum):
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    REVOKED = "revoked"


# ------------------------------------------------------------------
# Catálogo
# ------------------------------------------------------------------
class CoffeeState(StrEnum):
    """Estado en que se comercializa el café.

    MONK GRAIN opera un solo estado: **pergamino seco**, el café beneficiado y
    secado que todavía conserva el pergamino y aún no ha pasado por trilla. El
    enum se conserva con un único valor en lugar de eliminar la columna porque
    deja constancia explícita de qué se está vendiendo —un pedido de hace un año
    sigue diciendo qué era— y admite un segundo estado el día que se decida sin
    tocar el esquema.
    """

    PERGAMINO = "pergamino"


class CoffeeProcess(StrEnum):
    WASHED = "washed"
    NATURAL = "natural"
    HONEY = "honey"
    ANAEROBIC = "anaerobic"
    OTHER = "other"


class ProductStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    REJECTED = "rejected"


class ReviewStatus(StrEnum):
    PUBLISHED = "published"
    HIDDEN = "hidden"
    REPORTED = "reported"


# ------------------------------------------------------------------
# Carrito y promociones
# ------------------------------------------------------------------
class DiscountType(StrEnum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_SHIPPING = "free_shipping"


class CouponScope(StrEnum):
    GLOBAL = "global"
    CATEGORY = "category"
    PRODUCER = "producer"


# ------------------------------------------------------------------
# Pedidos
# ------------------------------------------------------------------
class OrderStatus(StrEnum):
    """Estado agregado del pedido, derivado de sus sub-órdenes."""

    PENDING = "pending"
    PROCESSING = "processing"
    PARTIALLY_SHIPPED = "partially_shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    # Un pedido reembolsado no es un pedido cancelado: se entregó y después se
    # devolvió. Mezclarlos borraba esa diferencia en el historial del comprador
    # y en las métricas del vendedor.
    REFUNDED = "refunded"


class SubOrderStatus(StrEnum):
    """Estado operativo real: cada vendedor despacha por separado."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARED = "prepared"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# Transiciones permitidas entre estados de sub-orden (HU-PRO-07, CA4).
# Se declara como dato y no como cadena de condicionales para que la regla sea
# verificable de un vistazo y comprobable con una sola prueba.
ALLOWED_SUB_ORDER_TRANSITIONS: dict[SubOrderStatus, frozenset[SubOrderStatus]] = {
    SubOrderStatus.PENDING: frozenset({SubOrderStatus.CONFIRMED, SubOrderStatus.CANCELLED}),
    SubOrderStatus.CONFIRMED: frozenset({SubOrderStatus.PREPARED, SubOrderStatus.CANCELLED}),
    SubOrderStatus.PREPARED: frozenset({SubOrderStatus.SHIPPED, SubOrderStatus.CANCELLED}),
    SubOrderStatus.SHIPPED: frozenset({SubOrderStatus.DELIVERED, SubOrderStatus.REFUNDED}),
    SubOrderStatus.DELIVERED: frozenset({SubOrderStatus.REFUNDED}),
    SubOrderStatus.CANCELLED: frozenset(),
    SubOrderStatus.REFUNDED: frozenset(),
}


# ------------------------------------------------------------------
# Pagos
# ------------------------------------------------------------------
class PaymentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentMethod(StrEnum):
    CARD = "card"
    PSE = "pse"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    SIMULATED = "simulated"


class CommissionStatus(StrEnum):
    PENDING = "pending"
    SETTLED = "settled"
    REVERSED = "reversed"


class SettlementStatus(StrEnum):
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    CANCELLED = "cancelled"


# ------------------------------------------------------------------
# Logística
# ------------------------------------------------------------------
class ShipmentStatus(StrEnum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    INCIDENT = "incident"
    RETURNED = "returned"


class ReturnReason(StrEnum):
    """Motivo por el que se devuelve un pedido.

    `WITHDRAWAL` es el derecho de retracto del artículo 47 de la Ley 1480 de
    2011: el comprador desiste dentro de los cinco días hábiles siguientes a la
    entrega y no tiene que justificarse. Se distingue de los demás motivos
    porque el plazo, quién asume el transporte y la forma de calcular el
    reembolso son distintos; mezclarlo con «otro» impedía darle ese trato.
    """

    WITHDRAWAL = "withdrawal"
    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    QUALITY = "quality"
    OTHER = "other"


# Motivos imputables al vendedor. En estos el transporte de la devolución corre
# por su cuenta; en el retracto, salvo pacto distinto, lo asume el comprador
# (artículo 47).
SELLER_ATTRIBUTABLE_RETURN_REASONS: frozenset[ReturnReason] = frozenset(
    {ReturnReason.DAMAGED, ReturnReason.WRONG_ITEM, ReturnReason.QUALITY}
)


RETURN_REASON_LABELS: dict[ReturnReason, str] = {
    ReturnReason.WITHDRAWAL: "retracto",
    ReturnReason.DAMAGED: "producto dañado",
    ReturnReason.WRONG_ITEM: "producto equivocado",
    ReturnReason.QUALITY: "no corresponde a lo publicado",
    ReturnReason.OTHER: "otro motivo",
}


class ReturnStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    REFUNDED = "refunded"


# Recorrido de una devolución. Igual que en las sub-órdenes, se declara como
# dato para que la regla sea legible de un vistazo.
#
# `APPROVED` puede saltar directo a `REFUNDED` porque el vendedor puede decidir
# reembolsar sin exigir el retorno físico —ocurre con un café dañado, que no
# tiene sentido devolver—. `REJECTED` es terminal: el comprador que no esté de
# acuerdo no reabre la solicitud, acude a la Superintendencia con la constancia.
ALLOWED_RETURN_TRANSITIONS: dict[ReturnStatus, frozenset[ReturnStatus]] = {
    ReturnStatus.REQUESTED: frozenset({ReturnStatus.APPROVED, ReturnStatus.REJECTED}),
    ReturnStatus.APPROVED: frozenset(
        {ReturnStatus.IN_TRANSIT, ReturnStatus.RECEIVED, ReturnStatus.REFUNDED}
    ),
    ReturnStatus.IN_TRANSIT: frozenset({ReturnStatus.RECEIVED, ReturnStatus.REFUNDED}),
    ReturnStatus.RECEIVED: frozenset({ReturnStatus.REFUNDED}),
    ReturnStatus.REJECTED: frozenset(),
    ReturnStatus.REFUNDED: frozenset(),
}

# Estados en los que la solicitud sigue viva y sus unidades no pueden volver a
# reclamarse en otra devolución.
OPEN_RETURN_STATUSES: frozenset[ReturnStatus] = frozenset(
    {
        ReturnStatus.REQUESTED,
        ReturnStatus.APPROVED,
        ReturnStatus.IN_TRANSIT,
        ReturnStatus.RECEIVED,
        ReturnStatus.REFUNDED,
    }
)


# ------------------------------------------------------------------
# Comunicación y contenido
# ------------------------------------------------------------------
class RequestType(StrEnum):
    SAMPLE = "sample"
    QUOTE = "quote"


class RequestStatus(StrEnum):
    PENDING = "pending"
    ANSWERED = "answered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class NotificationType(StrEnum):
    ORDER_PLACED = "order_placed"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_PREPARED = "order_prepared"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REFUNDED = "order_refunded"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_DECLINED = "payment_declined"
    NEW_ORDER_RECEIVED = "new_order_received"
    PRODUCER_APPROVED = "producer_approved"
    PRODUCER_REJECTED = "producer_rejected"
    NEW_MESSAGE = "new_message"
    COMMERCIAL_REQUEST = "commercial_request"
    COMMERCIAL_REQUEST_ANSWERED = "commercial_request_answered"
    RETURN_REQUESTED = "return_requested"
    RETURN_RESOLVED = "return_resolved"
    LOW_STOCK = "low_stock"
    CERTIFICATE_EXPIRING = "certificate_expiring"
    REVIEW_REMINDER = "review_reminder"


class PostStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
