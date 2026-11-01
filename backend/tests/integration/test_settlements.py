"""Liquidación al vendedor: de la comisión calculada al dinero desembolsado.

Este camino no existía hasta el 1 de noviembre de 2026. La plataforma cobraba al
comprador y calculaba la comisión, pero `settlements` nunca se escribía y no
había dónde registrar una cuenta bancaria: el mercado cobraba y no liquidaba.

Lo que más importa verificar aquí no es que se cree la fila, sino **qué entra y
qué no**: se paga lo entregado, pasado el plazo de retracto y sin reclamaciones
vivas. Pagar de más obliga a pedir dinero de vuelta, que es la situación que
ninguna plataforma quiere tener que resolver.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.catalog import ProductVariant
from app.models.content import AuditLog
from app.models.enums import (
    CommissionStatus,
    ReturnReason,
    ReturnStatus,
    RoleCode,
    SettlementStatus,
    SubOrderStatus,
    UserStatus,
)
from app.models.order import OrderItem, OrderStatusHistory, SubOrder
from app.models.payment import Commission, Settlement
from app.models.producer import ProducerProfile
from app.models.shipment import Return
from app.models.user import Address, Role, User, UserRole
from tests.integration.conftest import TEST_PASSWORD

pytestmark = pytest.mark.integration

API = "/api/v1"
ADMIN_PASSWORD = "AdminMonkGrain2026"  # noqa: S105 — credencial de pruebas

CUENTA = {
    "bank_name": "Bancolombia",
    "account_type": "ahorros",
    "account_number": "123456789012",
    "holder_name": "Juana Caficultora",
    "holder_document": "1098765432",
}


@pytest.fixture
def admin_headers(client: TestClient, session: Session, roles: dict[str, Role]) -> dict[str, str]:
    admin = User(
        email="admin.liquidaciones@prueba.co",
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name="Administradora de Pagos",
        status=UserStatus.ACTIVE,
        data_consent=True,
        data_consent_at=datetime.now(UTC),
    )
    session.add(admin)
    session.flush()
    session.add(UserRole(user_id=admin.id, role_id=roles[RoleCode.ADMIN.value].id))
    session.flush()

    response = client.post(
        f"{API}/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def producer_headers(producer_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {producer_token}"}


def _deliver_an_order(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
    buyer: User,
    variant: ProductVariant,
    delivered_on: date,
    quantity: int = 2,
) -> SubOrder:
    """Pedido entregado, con la fecha de entrega que haga falta para la prueba.

    La fecha se fuerza sobre el historial de estados porque es de ahí de donde
    el cierre la lee —igual que las devoluciones—, y porque esperar cinco días
    hábiles reales no es una opción en una prueba.
    """
    client.post(
        f"{API}/cart/items",
        json={"variant_id": str(variant.id), "quantity": quantity},
        headers=auth_headers,
    )
    address = session.scalar(select(Address).where(Address.user_id == buyer.id))
    assert address is not None
    respuesta = client.post(
        f"{API}/orders",
        json={"shipping_address_id": str(address.id), "accept_terms": True},
        headers=auth_headers,
    )
    assert respuesta.status_code == 201, respuesta.text

    sub_order = session.scalar(
        select(SubOrder)
        .join(OrderItem, OrderItem.sub_order_id == SubOrder.id)
        .where(OrderItem.variant_id == variant.id)
        .order_by(SubOrder.created_at.desc())
        .limit(1)
    )
    assert sub_order is not None, "no se encontró la sub-orden del lote recién pedido"

    sub_order.status = SubOrderStatus.DELIVERED
    session.add(
        OrderStatusHistory(
            sub_order_id=sub_order.id,
            from_status=SubOrderStatus.SHIPPED,
            to_status=SubOrderStatus.DELIVERED,
            created_at=datetime.combine(delivered_on, datetime.min.time(), tzinfo=UTC),
        )
    )
    session.commit()
    return sub_order


def _register_bank_account(client: TestClient, producer_headers: dict[str, str]) -> None:
    respuesta = client.put(f"{API}/producer/bank-account", json=CUENTA, headers=producer_headers)
    assert respuesta.status_code == 200, respuesta.text


def _close(client: TestClient, admin_headers: dict[str, str], desde: date, hasta: date):
    return client.post(
        f"{API}/admin/settlements/close",
        json={"period_start": desde.isoformat(), "period_end": hasta.isoformat()},
        headers=admin_headers,
    )


# ======================================================================
# Cuenta bancaria
# ======================================================================
class TestBankAccount:
    def test_the_number_never_comes_back_whole(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        """Lo que se devuelve basta para reconocer la cuenta y no para usarla."""
        respuesta = client.put(
            f"{API}/producer/bank-account", json=CUENTA, headers=producer_headers
        )

        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["masked_number"] == "••••9012"
        assert CUENTA["account_number"] not in respuesta.text
        assert cuerpo["bank_name"] == "Bancolombia"

    def test_what_lands_in_the_database_is_not_readable(
        self,
        client: TestClient,
        session: Session,
        producer: ProducerProfile,
        producer_headers: dict[str, str],
    ) -> None:
        """Es el punto entero de la columna: quien lea la base no ve la cuenta.

        Los textos legales prometían este cifrado cuando no existía. Ahora
        existe, y esta prueba es lo que impide que la promesa vuelva a vaciarse.
        """
        _register_bank_account(client, producer_headers)
        session.expire_all()

        guardado = session.get(ProducerProfile, producer.id)
        assert guardado is not None
        assert guardado.bank_account_encrypted is not None
        assert CUENTA["account_number"].encode() not in guardado.bank_account_encrypted
        assert b"Bancolombia" not in guardado.bank_account_encrypted

    def test_the_owner_reads_it_back_masked(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        _register_bank_account(client, producer_headers)

        respuesta = client.get(f"{API}/producer/bank-account", headers=producer_headers)

        assert respuesta.status_code == 200
        assert respuesta.json()["masked_number"] == "••••9012"

    def test_without_an_account_there_is_nothing_to_show(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        respuesta = client.get(f"{API}/producer/bank-account", headers=producer_headers)

        assert respuesta.status_code == 200
        assert respuesta.json() is None

    def test_an_account_number_with_letters_is_rejected(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        respuesta = client.put(
            f"{API}/producer/bank-account",
            json={**CUENTA, "account_number": "12AB56789012"},
            headers=producer_headers,
        )

        assert respuesta.status_code == 422

    def test_separators_are_cleaned_so_one_account_is_one_account(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        """En el extracto viene con guiones; dos formas de teclearla no deben
        parecer cuentas distintas."""
        respuesta = client.put(
            f"{API}/producer/bank-account",
            json={**CUENTA, "account_number": "123-456 789-012"},
            headers=producer_headers,
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["masked_number"] == "••••9012"

    def test_a_buyer_has_no_bank_account_to_register(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        respuesta = client.put(f"{API}/producer/bank-account", json=CUENTA, headers=auth_headers)

        assert respuesta.status_code == 403

    def test_removing_it_leaves_nothing_behind(
        self,
        client: TestClient,
        session: Session,
        producer: ProducerProfile,
        producer_headers: dict[str, str],
    ) -> None:
        _register_bank_account(client, producer_headers)

        respuesta = client.delete(f"{API}/producer/bank-account", headers=producer_headers)

        assert respuesta.status_code == 200
        session.expire_all()
        guardado = session.get(ProducerProfile, producer.id)
        assert guardado is not None
        assert guardado.bank_account_encrypted is None


# ======================================================================
# Cierre de periodo
# ======================================================================
class TestWhatGetsSettled:
    def test_a_delivered_order_past_the_withdrawal_window_is_paid(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        _register_bank_account(client, producer_headers)
        hace_un_mes = date.today() - timedelta(days=30)
        sub_order = _deliver_an_order(
            client, session, auth_headers, buyer, product_variant, hace_un_mes
        )

        respuesta = _close(client, admin_headers, hace_un_mes - timedelta(days=5), date.today())

        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["settlements_created"] == 1
        assert cuerpo["sub_orders_settled"] == 1

        liquidacion = session.scalar(select(Settlement))
        assert liquidacion is not None
        assert liquidacion.net_amount == sub_order.net_amount
        assert liquidacion.status is SettlementStatus.PENDING_PAYMENT

    def test_an_order_still_inside_the_withdrawal_window_waits(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Pagar antes de que venza el retracto obliga a pedir el dinero de
        vuelta cuando el comprador desiste."""
        _register_bank_account(client, producer_headers)
        ayer = date.today() - timedelta(days=1)
        _deliver_an_order(client, session, auth_headers, buyer, product_variant, ayer)

        respuesta = _close(client, admin_headers, ayer - timedelta(days=5), date.today())

        assert respuesta.status_code == 201
        assert respuesta.json()["settlements_created"] == 0

    def test_an_order_that_was_never_delivered_is_not_paid(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """No se paga café que no ha llegado."""
        _register_bank_account(client, producer_headers)
        client.post(
            f"{API}/cart/items",
            json={"variant_id": str(product_variant.id), "quantity": 2},
            headers=auth_headers,
        )
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None
        client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )

        respuesta = _close(client, admin_headers, date.today() - timedelta(days=60), date.today())

        assert respuesta.json()["settlements_created"] == 0

    def test_an_order_with_a_live_claim_is_held_back(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Mientras la reclamación viva, ese dinero puede tener que devolverse."""
        _register_bank_account(client, producer_headers)
        hace_un_mes = date.today() - timedelta(days=30)
        sub_order = _deliver_an_order(
            client, session, auth_headers, buyer, product_variant, hace_un_mes
        )
        session.add(
            Return(
                return_number="DEV-2026-000001",
                sub_order_id=sub_order.id,
                requested_by=buyer.id,
                reason=ReturnReason.QUALITY,
                status=ReturnStatus.REQUESTED,
                description="El factor no corresponde a lo publicado.",
                refund_amount=Decimal("0.00"),
                response_due_at=date.today() + timedelta(days=15),
                refund_due_at=date.today() + timedelta(days=30),
            )
        )
        session.commit()

        respuesta = _close(client, admin_headers, hace_un_mes - timedelta(days=5), date.today())

        assert respuesta.json()["settlements_created"] == 0

    def test_a_seller_without_a_bank_account_is_reported_not_silently_skipped(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Crear una liquidación que nadie puede pagar sería peor que omitirla;
        omitirla en silencio, también."""
        hace_un_mes = date.today() - timedelta(days=30)
        _deliver_an_order(client, session, auth_headers, buyer, product_variant, hace_un_mes)

        respuesta = _close(client, admin_headers, hace_un_mes - timedelta(days=5), date.today())

        cuerpo = respuesta.json()
        assert cuerpo["settlements_created"] == 0
        assert cuerpo["skipped_without_bank_account"] == 1

    def test_closing_the_same_period_twice_does_not_pay_twice(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> None:
        """Es el error más caro posible aquí, y el más fácil de cometer: un
        administrador que no está seguro de haber cerrado vuelve a darle."""
        _register_bank_account(client, producer_headers)
        hace_un_mes = date.today() - timedelta(days=30)
        _deliver_an_order(client, session, auth_headers, buyer, product_variant, hace_un_mes)
        desde, hasta = hace_un_mes - timedelta(days=5), date.today()

        primero = _close(client, admin_headers, desde, hasta)
        segundo = _close(client, admin_headers, desde, hasta)

        assert primero.json()["settlements_created"] == 1
        assert segundo.json()["settlements_created"] == 0
        assert len(session.scalars(select(Settlement)).all()) == 1

    def test_each_seller_gets_their_own_settlement(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        second_variant: ProductVariant,
        second_producer: ProducerProfile,
    ) -> None:
        """Un pedido con lotes de dos fincas son dos liquidaciones, no una."""
        _register_bank_account(client, producer_headers)
        otro = session.get(User, second_producer.user_id)
        assert otro is not None
        token = client.post(
            f"{API}/auth/login", json={"email": otro.email, "password": TEST_PASSWORD}
        )
        assert token.status_code == 200, token.text
        _register_bank_account(client, {"Authorization": f"Bearer {token.json()['access_token']}"})

        hace_un_mes = date.today() - timedelta(days=30)
        _deliver_an_order(client, session, auth_headers, buyer, product_variant, hace_un_mes)
        _deliver_an_order(client, session, auth_headers, buyer, second_variant, hace_un_mes)

        respuesta = _close(client, admin_headers, hace_un_mes - timedelta(days=5), date.today())

        assert respuesta.json()["settlements_created"] == 2


# ======================================================================
# Pago y consulta
# ======================================================================
class TestPaying:
    @pytest.fixture
    def liquidacion_lista(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> Settlement:
        _register_bank_account(client, producer_headers)
        hace_un_mes = date.today() - timedelta(days=30)
        _deliver_an_order(client, session, auth_headers, buyer, product_variant, hace_un_mes)
        _close(client, admin_headers, hace_un_mes - timedelta(days=5), date.today())
        liquidacion = session.scalar(select(Settlement))
        assert liquidacion is not None
        return liquidacion

    def test_paying_closes_the_commissions_it_covers(
        self,
        client: TestClient,
        session: Session,
        admin_headers: dict[str, str],
        liquidacion_lista: Settlement,
    ) -> None:
        """Sin esto las comisiones seguirían pendientes y el resumen del
        vendedor diría que se le debe dos veces."""
        respuesta = client.post(
            f"{API}/admin/settlements/{liquidacion_lista.id}/pay",
            json={"payment_reference": "TRF-2026-00412"},
            headers=admin_headers,
        )

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["status"] == SettlementStatus.PAID.value
        session.expire_all()
        comisiones = session.scalars(
            select(Commission).where(Commission.settlement_id == liquidacion_lista.id)
        ).all()
        assert comisiones
        assert all(c.status is CommissionStatus.SETTLED for c in comisiones)

    def test_the_settled_amount_stops_showing_as_pending(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        producer_headers: dict[str, str],
        liquidacion_lista: Settlement,
    ) -> None:
        antes = client.get(f"{API}/producer/settlements/summary", headers=producer_headers).json()
        client.post(
            f"{API}/admin/settlements/{liquidacion_lista.id}/pay",
            json={"payment_reference": "TRF-2026-00413"},
            headers=admin_headers,
        )

        despues = client.get(f"{API}/producer/settlements/summary", headers=producer_headers).json()

        assert Decimal(antes["net_amount"]) > 0
        assert Decimal(despues["net_amount"]) == 0

    def test_paying_twice_is_rejected(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        liquidacion_lista: Settlement,
    ) -> None:
        client.post(
            f"{API}/admin/settlements/{liquidacion_lista.id}/pay",
            json={"payment_reference": "TRF-2026-00414"},
            headers=admin_headers,
        )

        segundo = client.post(
            f"{API}/admin/settlements/{liquidacion_lista.id}/pay",
            json={"payment_reference": "TRF-2026-00415"},
            headers=admin_headers,
        )

        assert segundo.status_code == 422
        assert "TRF-2026-00414" in segundo.json()["error"]["message"]

    def test_a_payment_without_a_reference_is_rejected(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        liquidacion_lista: Settlement,
    ) -> None:
        """Un pago sin constancia de por dónde salió el dinero no es un pago
        registrado, es una casilla marcada."""
        respuesta = client.post(
            f"{API}/admin/settlements/{liquidacion_lista.id}/pay",
            json={"payment_reference": ""},
            headers=admin_headers,
        )

        assert respuesta.status_code == 422

    def test_moving_money_leaves_a_trace_in_the_audit_log(
        self,
        client: TestClient,
        session: Session,
        admin_headers: dict[str, str],
        liquidacion_lista: Settlement,
    ) -> None:
        client.post(
            f"{API}/admin/settlements/{liquidacion_lista.id}/pay",
            json={"payment_reference": "TRF-2026-00416"},
            headers=admin_headers,
        )

        acciones = set(
            session.scalars(
                select(AuditLog.action).where(AuditLog.entity_type == "settlement")
            ).all()
        )

        assert {"settlement.created", "settlement.paid"} <= acciones

    def test_the_audit_entry_never_carries_the_bank_account(
        self,
        client: TestClient,
        session: Session,
        admin_headers: dict[str, str],
        liquidacion_lista: Settlement,
    ) -> None:
        client.post(
            f"{API}/admin/settlements/{liquidacion_lista.id}/pay",
            json={"payment_reference": "TRF-2026-00417"},
            headers=admin_headers,
        )

        registros = session.scalars(
            select(AuditLog).where(AuditLog.entity_type == "settlement")
        ).all()

        for registro in registros:
            assert CUENTA["account_number"] not in str(registro.after_state)


class TestWhoSeesWhat:
    def test_a_seller_only_sees_their_own_settlements(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        second_producer: ProducerProfile,
    ) -> None:
        _register_bank_account(client, producer_headers)
        hace_un_mes = date.today() - timedelta(days=30)
        _deliver_an_order(client, session, auth_headers, buyer, product_variant, hace_un_mes)
        # Una liquidación ajena, que no debe aparecer.
        session.add(
            Settlement(
                producer_id=second_producer.id,
                period_start=hace_un_mes,
                period_end=date.today(),
                gross_amount=Decimal("500000.00"),
                commission_total=Decimal("12500.00"),
                net_amount=Decimal("487500.00"),
                status=SettlementStatus.PENDING_PAYMENT,
            )
        )
        session.commit()
        _close(client, admin_headers, hace_un_mes - timedelta(days=5), date.today())

        respuesta = client.get(f"{API}/producer/settlements", headers=producer_headers)

        assert respuesta.status_code == 200
        assert len(respuesta.json()) == 1

    def test_the_admin_listing_never_carries_a_bank_account(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        liquidacion_lista: Settlement,
    ) -> None:
        """Decisión que viene del diseño original (HU-ADM-02, CA5): el dato
        bancario no se serializa para nadie, ni para el administrador."""
        respuesta = client.get(f"{API}/admin/settlements", headers=admin_headers)

        assert respuesta.status_code == 200
        assert CUENTA["account_number"] not in respuesta.text
        assert respuesta.json()[0]["has_bank_account"] is True

    @pytest.fixture
    def liquidacion_lista(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        producer_headers: dict[str, str],
        admin_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
    ) -> Settlement:
        _register_bank_account(client, producer_headers)
        hace_un_mes = date.today() - timedelta(days=30)
        _deliver_an_order(client, session, auth_headers, buyer, product_variant, hace_un_mes)
        _close(client, admin_headers, hace_un_mes - timedelta(days=5), date.today())
        liquidacion = session.scalar(select(Settlement))
        assert liquidacion is not None
        return liquidacion

    def test_a_seller_cannot_close_a_period(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        respuesta = client.post(
            f"{API}/admin/settlements/close",
            json={"period_start": "2026-01-01", "period_end": "2026-01-31"},
            headers=producer_headers,
        )

        assert respuesta.status_code == 403

    def test_a_buyer_cannot_browse_the_settlements(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        respuesta = client.get(f"{API}/admin/settlements", headers=auth_headers)

        assert respuesta.status_code == 403

    def test_a_period_that_ends_before_it_starts_is_rejected(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        respuesta = client.post(
            f"{API}/admin/settlements/close",
            json={"period_start": "2026-03-01", "period_end": "2026-02-01"},
            headers=admin_headers,
        )

        assert respuesta.status_code == 422

    def test_paying_a_settlement_that_does_not_exist(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        respuesta = client.post(
            f"{API}/admin/settlements/{uuid.uuid4()}/pay",
            json={"payment_reference": "TRF-2026-00418"},
            headers=admin_headers,
        )

        assert respuesta.status_code == 404
