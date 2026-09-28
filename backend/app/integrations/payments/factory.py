"""Selección del proveedor de pago según la configuración."""

from functools import lru_cache

from app.core.config import settings
from app.integrations.payments.base import PaymentProvider
from app.integrations.payments.simulated import SimulatedPaymentProvider


@lru_cache
def get_payment_provider() -> PaymentProvider:
    """Devuelve el proveedor configurado en `PAYMENT_PROVIDER`.

    Wompi, Mercado Pago y PayU se añaden aquí cuando existan credenciales
    reales. Mientras tanto, cualquier valor distinto de `simulated` falla al
    arrancar en lugar de cobrar de forma silenciosa con el proveedor
    equivocado.
    """
    if settings.payment_provider == "simulated":
        return SimulatedPaymentProvider()

    raise NotImplementedError(
        f"El proveedor de pago '{settings.payment_provider}' aún no está implementado. "
        "Usa 'simulated' o añade su implementación en app/integrations/payments/."
    )
