"""Proveedor de pago simulado para el MVP.

No mueve dinero ni contacta con ningún servicio externo: aprueba los pagos de
inmediato y registra los eventos como lo haría una pasarela real, de modo que el
flujo de pedidos pueda probarse completo.

Se identifica como `simulated` en la base de datos y en la respuesta de la API,
para que ningún pago de prueba pueda confundirse con uno real.
"""

import hashlib
import hmac
import secrets
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.payments.base import (
    PaymentIntent,
    PaymentProvider,
    PaymentResult,
    WebhookEvent,
)
from app.models.enums import PaymentStatus

logger = get_logger(__name__)


class SimulatedPaymentProvider(PaymentProvider):
    name = "simulated"

    def create_intent(
        self,
        *,
        order_number: str,
        amount: Decimal,
        currency: str,
        customer_email: str,
        return_url: str | None = None,
    ) -> PaymentIntent:
        reference = f"SIM-{order_number}-{secrets.token_hex(4).upper()}"
        logger.info(
            "simulated_payment_created",
            reference=reference,
            order_number=order_number,
            amount=str(amount),
        )
        return PaymentIntent(
            reference=reference,
            status=PaymentStatus.PENDING,
            redirect_url=None,
            raw_response={
                "provider": self.name,
                "reference": reference,
                "amount": str(amount),
                "currency": currency,
                "simulated": True,
            },
        )

    def get_status(self, reference: str) -> PaymentResult:
        """En el entorno simulado todo pago creado se considera aprobado."""
        return PaymentResult(
            reference=reference,
            status=PaymentStatus.APPROVED,
            raw_response={"provider": self.name, "simulated": True},
        )

    def parse_webhook(self, payload: dict[str, Any], signature: str | None) -> WebhookEvent:
        """Valida la firma igual que un proveedor real.

        Aunque el proveedor sea simulado, la verificación se ejerce de verdad:
        así el camino que se usará en producción queda probado desde ahora.
        """
        reference = str(payload.get("reference", ""))
        status_value = str(payload.get("status", "approved"))

        signature_valid = self._verify_signature(payload, signature)

        try:
            status = PaymentStatus(status_value)
        except ValueError:
            status = PaymentStatus.FAILED

        return WebhookEvent(
            reference=reference,
            status=status,
            signature_valid=signature_valid,
            payload=payload,
            failure_reason=payload.get("failure_reason"),
        )

    def _verify_signature(self, payload: dict[str, Any], signature: str | None) -> bool:
        if not settings.payment_webhook_secret or signature is None:
            return False

        expected = hmac.new(
            settings.payment_webhook_secret.encode(),
            f"{payload.get('reference')}{payload.get('status')}".encode(),
            hashlib.sha256,
        ).hexdigest()

        # Comparación en tiempo constante: una comparación normal filtraría
        # información sobre la firma esperada a través del tiempo de respuesta.
        return hmac.compare_digest(expected, signature)

    def refund(self, reference: str, amount: Decimal) -> PaymentResult:
        logger.info("simulated_refund", reference=reference, amount=str(amount))
        return PaymentResult(
            reference=reference,
            status=PaymentStatus.REFUNDED,
            amount=amount,
            raw_response={"provider": self.name, "simulated": True},
        )
