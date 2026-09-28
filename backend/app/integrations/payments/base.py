"""Contrato común de las pasarelas de pago.

El módulo de pedidos depende de esta interfaz y nunca de un proveedor concreto
(ADR-03). Añadir Wompi, Mercado Pago o PayU consiste en escribir una clase que
la implemente y cambiar `PAYMENT_PROVIDER` en el entorno: el checkout no se
toca.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.models.enums import PaymentStatus


@dataclass(frozen=True)
class PaymentIntent:
    """Intención de cobro creada en el proveedor."""

    reference: str
    status: PaymentStatus
    # URL a la que redirigir para completar el pago, cuando el proveedor la usa.
    redirect_url: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentResult:
    """Resultado de consultar o procesar un pago."""

    reference: str
    status: PaymentStatus
    amount: Decimal | None = None
    failure_reason: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookEvent:
    """Notificación recibida del proveedor."""

    reference: str
    status: PaymentStatus
    signature_valid: bool
    payload: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None


class PaymentProvider(ABC):
    """Interfaz que debe cumplir toda pasarela."""

    name: str

    @abstractmethod
    def create_intent(
        self,
        *,
        order_number: str,
        amount: Decimal,
        currency: str,
        customer_email: str,
        return_url: str | None = None,
    ) -> PaymentIntent:
        """Crea la intención de cobro y devuelve su referencia."""

    @abstractmethod
    def get_status(self, reference: str) -> PaymentResult:
        """Consulta el estado actual de un pago."""

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any], signature: str | None) -> WebhookEvent:
        """Valida la firma del webhook y traduce su contenido.

        La validación de firma es obligatoria: sin ella, cualquiera podría
        notificar un pago aprobado que nunca ocurrió.
        """

    @abstractmethod
    def refund(self, reference: str, amount: Decimal) -> PaymentResult:
        """Solicita el reembolso total o parcial de un pago."""
