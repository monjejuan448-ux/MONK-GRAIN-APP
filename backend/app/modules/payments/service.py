"""Liquidación al vendedor: de la comisión calculada al dinero desembolsado.

Hasta el 1 de noviembre de 2026 este camino no existía. La plataforma cobraba al
comprador y calculaba la comisión, pero `settlements` nunca se escribía, no había
dónde registrar una cuenta bancaria y no había cifrado en el proyecto: el
mercado cobraba y no liquidaba. El esquema sí estaba preparado —`Settlement` y
`Commission.settlement_id` existían desde el primer día—, de modo que esto lo usa
en vez de inventar tablas nuevas.

**El flujo del dinero es recaudo centralizado**, decidido junto al dueño del
negocio: comprador → MONK GRAIN → vendedor. Implica recaudo a nombre de terceros
y la revisión jurídica sigue pendiente (decisión D-7 de `docs/10`), que es cosa
distinta de que el software sepa hacerlo.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.business_days import add_business_days
from app.core.crypto import DecryptionError, decrypt_json, encrypt_json
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging import get_logger
from app.models.content import AuditLog
from app.models.enums import CommissionStatus, SettlementStatus, SubOrderStatus
from app.models.order import OrderStatusHistory, SubOrder
from app.models.payment import Commission, Settlement
from app.models.producer import ProducerProfile
from app.models.shipment import Return
from app.models.user import User
from app.schemas.settlement import (
    AdminSettlementItem,
    BankAccountInput,
    BankAccountView,
    ClosePeriodResult,
    ProducerSettlementItem,
)

logger = get_logger(__name__)

# Días hábiles que se espera tras la entrega antes de liquidar. Es el plazo de
# retracto del artículo 47: pagarle al vendedor antes de que venza obligaría a
# pedirle el dinero de vuelta cuando un comprador desiste, que es justo la
# situación que la facultad de retención de la decisión D-6 intenta resolver y
# que todavía no tiene respaldo contractual. Esperar cinco días hábiles la evita
# sin necesidad de retener nada.
SETTLEMENT_HOLD_BUSINESS_DAYS = 5


class SettlementService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _audit(
        self,
        actor: User,
        action: str,
        entity_id: str,
        after: dict[str, object] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Deja constancia de lo que mueve dinero.

        La auditoría es de solo inserción —no hay endpoint que la edite y el rol
        de aplicación en PostgreSQL tampoco puede—, que es justo lo que se le
        pide a un registro de pagos.
        """
        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                entity_type="settlement",
                entity_id=entity_id,
                before_state=None,
                after_state=after,
                ip_address=ip_address,
            )
        )
        self.session.flush()

    # ------------------------------------------------------------------
    # Cuenta bancaria del vendedor
    # ------------------------------------------------------------------
    def _profile(self, user: User) -> ProducerProfile:
        profile = self.session.scalar(
            select(ProducerProfile).where(ProducerProfile.user_id == user.id)
        )
        if profile is None:
            raise NotFoundError("No encontramos tu perfil de vendedor.")
        return profile

    def save_bank_account(self, user: User, payload: BankAccountInput) -> BankAccountView:
        """Guarda la cuenta cifrada y devuelve solo lo que puede mostrarse."""
        profile = self._profile(user)

        profile.bank_account_encrypted = encrypt_json(
            {
                "bank_name": payload.bank_name,
                "account_type": payload.account_type,
                "account_number": payload.account_number,
                "holder_name": payload.holder_name,
                "holder_document": payload.holder_document,
                "saved_at": datetime.now(UTC).isoformat(),
            }
        )
        self.session.commit()

        # Nunca el número, ni en el registro de actividad.
        logger.info("bank_account_saved", producer_id=str(profile.id))
        return self._mask(payload.model_dump(), profile.updated_at)

    def get_bank_account(self, user: User) -> BankAccountView | None:
        profile = self._profile(user)
        if profile.bank_account_encrypted is None:
            return None

        try:
            data = decrypt_json(profile.bank_account_encrypted)
        except DecryptionError as exc:
            raise BusinessRuleError(
                "No pudimos leer la cuenta bancaria guardada. Vuelve a registrarla."
            ) from exc

        return self._mask(data, profile.updated_at)

    def delete_bank_account(self, user: User) -> None:
        profile = self._profile(user)
        profile.bank_account_encrypted = None
        self.session.commit()
        logger.info("bank_account_deleted", producer_id=str(profile.id))

    @staticmethod
    def _mask(data: dict[str, object], updated_at: datetime | None) -> BankAccountView:
        """Deja ver los últimos cuatro dígitos y nada más.

        Es lo justo para que el vendedor reconozca cuál registró y note si se
        equivocó de cuenta, sin que el número completo viaje de vuelta en cada
        carga de la página.
        """
        numero = str(data.get("account_number", ""))
        visibles = numero[-4:] if len(numero) >= 4 else numero
        return BankAccountView(
            bank_name=str(data.get("bank_name", "")),
            account_type=str(data.get("account_type", "")),
            holder_name=str(data.get("holder_name", "")),
            masked_number=f"••••{visibles}",
            updated_at=updated_at,
        )

    # ------------------------------------------------------------------
    # Cierre de periodo
    # ------------------------------------------------------------------
    def _delivered_days(self, sub_order_ids: list[uuid.UUID]) -> dict[uuid.UUID, date]:
        """Cuándo se entregó cada sub-orden, en una sola consulta.

        Se toma del historial de estados y no de la guía logística, por la misma
        razón que en devoluciones: el plazo no puede depender de que exista un
        envío bien diligenciado.
        """
        if not sub_order_ids:
            return {}

        filas = self.session.execute(
            select(
                OrderStatusHistory.sub_order_id,
                func.min(OrderStatusHistory.created_at),
            )
            .where(
                OrderStatusHistory.sub_order_id.in_(sub_order_ids),
                OrderStatusHistory.to_status == SubOrderStatus.DELIVERED,
            )
            .group_by(OrderStatusHistory.sub_order_id)
        ).all()
        return {fila[0]: fila[1].astimezone(UTC).date() for fila in filas}

    def _sub_orders_with_open_returns(self, sub_order_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """Las que tienen una reclamación viva: su dinero no se liquida todavía."""
        if not sub_order_ids:
            return set()

        from app.models.enums import OPEN_RETURN_STATUSES

        filas = self.session.scalars(
            select(Return.sub_order_id).where(
                Return.sub_order_id.in_(sub_order_ids),
                Return.status.in_(OPEN_RETURN_STATUSES),
            )
        ).all()
        return set(filas)

    def close_period(
        self,
        actor: User,
        period_start: date,
        period_end: date,
        today: date | None = None,
        ip_address: str | None = None,
    ) -> ClosePeriodResult:
        """Agrupa en una liquidación por vendedor lo que ya puede pagarse.

        Entra una comisión si cumple todo esto:

        - está pendiente y no pertenece ya a otra liquidación;
        - su sub-orden está **entregada**, no solo confirmada: no se paga café
          que no ha llegado;
        - la entrega cae dentro del periodo que se cierra;
        - han pasado los cinco días hábiles del retracto;
        - y la sub-orden no tiene ninguna devolución viva.

        Es idempotente por construcción: al marcar las comisiones con su
        `settlement_id`, cerrar dos veces el mismo periodo no las duplica.
        """
        hoy = today or datetime.now(UTC).date()

        candidatas = self.session.scalars(
            select(Commission)
            .join(SubOrder, SubOrder.id == Commission.sub_order_id)
            .where(
                Commission.status == CommissionStatus.PENDING,
                Commission.settlement_id.is_(None),
                SubOrder.status == SubOrderStatus.DELIVERED,
            )
            .options(selectinload(Commission.sub_order))
        ).all()

        ids = [c.sub_order_id for c in candidatas]
        entregadas = self._delivered_days(ids)
        con_reclamacion = self._sub_orders_with_open_returns(ids)

        por_vendedor: dict[uuid.UUID, list[Commission]] = {}
        for comision in candidatas:
            entrega = entregadas.get(comision.sub_order_id)
            if entrega is None:
                continue
            if not (period_start <= entrega <= period_end):
                continue
            if add_business_days(entrega, SETTLEMENT_HOLD_BUSINESS_DAYS) > hoy:
                continue
            if comision.sub_order_id in con_reclamacion:
                continue
            por_vendedor.setdefault(comision.sub_order.producer_id, []).append(comision)

        creadas = 0
        sin_cuenta = 0
        sub_ordenes = 0
        neto_total = Decimal("0.00")

        for producer_id, comisiones in por_vendedor.items():
            perfil = self.session.get(ProducerProfile, producer_id)
            if perfil is None:
                continue
            # Sin cuenta bancaria no hay a dónde mandar el dinero. Se omite y se
            # informa, en vez de crear una liquidación que nadie podrá pagar.
            if perfil.bank_account_encrypted is None:
                sin_cuenta += 1
                continue

            bruto = sum((c.base_amount for c in comisiones), Decimal("0.00"))
            comision_total = sum((c.commission_amount for c in comisiones), Decimal("0.00"))

            liquidacion = Settlement(
                producer_id=producer_id,
                period_start=period_start,
                period_end=period_end,
                gross_amount=bruto,
                commission_total=comision_total,
                net_amount=bruto - comision_total,
                status=SettlementStatus.PENDING_PAYMENT,
            )
            self.session.add(liquidacion)
            self.session.flush()

            for comision in comisiones:
                comision.settlement_id = liquidacion.id

            self._audit(
                actor,
                "settlement.created",
                str(liquidacion.id),
                {
                    "producer_id": str(producer_id),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "gross_amount": str(liquidacion.gross_amount),
                    "commission_total": str(liquidacion.commission_total),
                    "net_amount": str(liquidacion.net_amount),
                    "sub_orders": len(comisiones),
                },
                ip_address,
            )

            creadas += 1
            sub_ordenes += len(comisiones)
            neto_total += liquidacion.net_amount

        self.session.commit()
        logger.info(
            "settlement_period_closed",
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            settlements=creadas,
            sub_orders=sub_ordenes,
            skipped_without_bank_account=sin_cuenta,
        )

        return ClosePeriodResult(
            settlements_created=creadas,
            producers_settled=creadas,
            sub_orders_settled=sub_ordenes,
            net_total=neto_total,
            skipped_without_bank_account=sin_cuenta,
        )

    # ------------------------------------------------------------------
    # Consulta y pago
    # ------------------------------------------------------------------
    @staticmethod
    def _base_fields(liquidacion: Settlement) -> dict[str, object]:
        """Los campos que comparten las dos vistas de una liquidación.

        Se enumeran a mano en lugar de recorrer `Settlement.__table__`: el
        recorrido metía `producer_id` por su cuenta y chocaba con el que añade
        la vista del administrador.
        """
        return {
            "id": liquidacion.id,
            "period_start": liquidacion.period_start,
            "period_end": liquidacion.period_end,
            "gross_amount": liquidacion.gross_amount,
            "commission_total": liquidacion.commission_total,
            "net_amount": liquidacion.net_amount,
            "status": liquidacion.status,
            "paid_at": liquidacion.paid_at,
            "payment_reference": liquidacion.payment_reference,
            "created_at": liquidacion.created_at,
        }

    def _count_sub_orders(self, settlement_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Cuántas sub-órdenes hay en cada liquidación, de una sola vez."""
        if not settlement_ids:
            return {}
        filas = self.session.execute(
            select(Commission.settlement_id, func.count(Commission.id))
            .where(Commission.settlement_id.in_(settlement_ids))
            .group_by(Commission.settlement_id)
        ).all()
        # El `is not None` es para el tipado: la consulta ya filtra por
        # `settlement_id IN (...)`, así que ninguna fila puede traerlo nulo.
        return {fila[0]: fila[1] for fila in filas if fila[0] is not None}

    def list_for_producer(self, user: User) -> list[ProducerSettlementItem]:
        perfil = self._profile(user)
        filas = self.session.scalars(
            select(Settlement)
            .where(Settlement.producer_id == perfil.id)
            .order_by(Settlement.period_end.desc(), Settlement.created_at.desc())
        ).all()

        conteos = self._count_sub_orders([f.id for f in filas])
        return [
            ProducerSettlementItem(
                **self._base_fields(fila),  # type: ignore[arg-type]
                sub_orders_count=conteos.get(fila.id, 0),
            )
            for fila in filas
        ]

    def list_for_admin(self, status: SettlementStatus | None = None) -> list[AdminSettlementItem]:
        consulta = (
            select(Settlement, ProducerProfile)
            .join(ProducerProfile, ProducerProfile.id == Settlement.producer_id)
            .order_by(Settlement.status, Settlement.period_end.desc())
        )
        if status is not None:
            consulta = consulta.where(Settlement.status == status)

        filas = self.session.execute(consulta).all()
        conteos = self._count_sub_orders([fila[0].id for fila in filas])

        return [
            AdminSettlementItem(
                **self._base_fields(liquidacion),  # type: ignore[arg-type]
                producer_id=perfil.id,
                producer_name=perfil.brand_name or perfil.legal_name,
                sub_orders_count=conteos.get(liquidacion.id, 0),
                has_bank_account=perfil.bank_account_encrypted is not None,
            )
            for liquidacion, perfil in filas
        ]

    def mark_paid(
        self,
        actor: User,
        settlement_id: uuid.UUID,
        payment_reference: str,
        notes: str | None,
        ip_address: str | None = None,
    ) -> AdminSettlementItem:
        """Deja constancia del desembolso y cierra las comisiones que cubre."""
        liquidacion = self.session.get(Settlement, settlement_id)
        if liquidacion is None:
            raise NotFoundError("No encontramos esta liquidación.")

        if liquidacion.status is SettlementStatus.PAID:
            raise BusinessRuleError(
                f"Esta liquidación ya figura pagada, con la referencia "
                f"«{liquidacion.payment_reference}»."
            )
        if liquidacion.status is SettlementStatus.CANCELLED:
            raise BusinessRuleError("Esta liquidación está anulada y no puede pagarse.")

        liquidacion.status = SettlementStatus.PAID
        liquidacion.paid_at = datetime.now(UTC)
        liquidacion.payment_reference = payment_reference
        liquidacion.notes = notes

        # Las comisiones dejan de estar pendientes: ya se descontaron de un pago
        # realizado. Sin esto seguirían sumando en el resumen del vendedor y
        # parecería que se le debe dos veces.
        comisiones = self.session.scalars(
            select(Commission).where(Commission.settlement_id == liquidacion.id)
        ).all()
        for comision in comisiones:
            comision.status = CommissionStatus.SETTLED

        self._audit(
            actor,
            "settlement.paid",
            str(liquidacion.id),
            {
                "producer_id": str(liquidacion.producer_id),
                "net_amount": str(liquidacion.net_amount),
                "payment_reference": payment_reference,
                "commissions_settled": len(comisiones),
            },
            ip_address,
        )

        self.session.commit()
        logger.info(
            "settlement_paid",
            settlement_id=str(liquidacion.id),
            commissions=len(comisiones),
        )

        perfil = self.session.get(ProducerProfile, liquidacion.producer_id)
        assert perfil is not None  # noqa: S101 — FK con RESTRICT
        return AdminSettlementItem(
            **self._base_fields(liquidacion),  # type: ignore[arg-type]
            producer_id=perfil.id,
            producer_name=perfil.brand_name or perfil.legal_name,
            sub_orders_count=len(comisiones),
            has_bank_account=perfil.bank_account_encrypted is not None,
        )
