"""Verificación del mapeo ORM.

Estas pruebas no necesitan base de datos: comprueban que los 51 modelos se
configuran sin ambigüedades. Un error de mapeo (una relación sin join
resoluble, una clave foránea inexistente) haría fallar la aplicación al primer
uso, no al arrancar, y por eso conviene detectarlo aquí.
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers

from app.models import Base
from app.models.enums import ALLOWED_SUB_ORDER_TRANSITIONS, SubOrderStatus

EXPECTED_TABLE_COUNT = 51


@pytest.mark.unit
def test_all_mappers_configure() -> None:
    """Todas las relaciones se resuelven sin ambigüedad."""
    configure_mappers()


@pytest.mark.unit
def test_expected_table_count() -> None:
    """El esquema declara exactamente las tablas previstas en el diseño."""
    assert len(Base.metadata.tables) == EXPECTED_TABLE_COUNT


@pytest.mark.unit
def test_every_foreign_key_targets_an_existing_table() -> None:
    """Ninguna clave foránea apunta a una tabla que no existe."""
    table_names = set(Base.metadata.tables)
    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            target = foreign_key.column.table.name
            assert target in table_names, f"{table.name} referencia la tabla inexistente {target}"


@pytest.mark.unit
def test_business_entities_use_uuid_primary_keys() -> None:
    """Las entidades expuestas al exterior no usan identificadores secuenciales.

    Un identificador secuencial permitiría enumerar pedidos o usuarios ajenos
    (ADR-05).
    """
    for table_name in ("users", "orders", "sub_orders", "products", "payments"):
        table = Base.metadata.tables[table_name]
        primary_key = list(table.primary_key.columns)[0]
        assert primary_key.type.__class__.__name__ == "UUID", (
            f"{table_name}.{primary_key.name} debería ser UUID"
        )


@pytest.mark.unit
def test_money_columns_never_use_floating_point() -> None:
    """Ningún importe se almacena en punto flotante (ADR-04)."""
    money_suffixes = ("_price", "_amount", "_total", "price", "subtotal")
    offenders: list[str] = []

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.name.endswith(money_suffixes):
                type_name = column.type.__class__.__name__
                if type_name in ("Float", "REAL", "DOUBLE_PRECISION"):
                    offenders.append(f"{table.name}.{column.name} ({type_name})")

    assert not offenders, f"Importes en punto flotante: {offenders}"


@pytest.mark.unit
def test_audit_log_has_no_update_timestamp() -> None:
    """`audit_logs` es de solo inserción: no puede tener marca de actualización."""
    columns = {column.name for column in Base.metadata.tables["audit_logs"].columns}
    assert "updated_at" not in columns
    assert "deleted_at" not in columns


@pytest.mark.unit
def test_review_allows_one_per_purchased_item() -> None:
    """`order_item_id` es único: una reseña por compra verificada (HU-CC-10)."""
    column = Base.metadata.tables["reviews"].columns["order_item_id"]
    assert column.unique is True


@pytest.mark.unit
def test_payment_reference_is_unique_per_provider() -> None:
    """Idempotencia de webhooks: el mismo evento no se procesa dos veces."""
    constraints = {constraint.name for constraint in Base.metadata.tables["payments"].constraints}
    assert "uq_payments_provider_reference" in constraints


@pytest.mark.unit
def test_cupping_score_supports_full_range() -> None:
    """El puntaje de catación llega a 100.00 y necesita precisión suficiente."""
    column = Base.metadata.tables["coffee_attributes"].columns["cupping_score"]
    assert column.type.precision is not None
    assert column.type.precision >= 5, (
        "NUMERIC(3,2) solo admite hasta 9.99 y no puede representar el puntaje real"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("from_status", "to_status", "allowed"),
    [
        (SubOrderStatus.PENDING, SubOrderStatus.CONFIRMED, True),
        (SubOrderStatus.CONFIRMED, SubOrderStatus.PREPARED, True),
        (SubOrderStatus.PREPARED, SubOrderStatus.SHIPPED, True),
        (SubOrderStatus.SHIPPED, SubOrderStatus.DELIVERED, True),
        # Saltos inválidos que el servicio debe rechazar (HU-PRO-07, CA4).
        (SubOrderStatus.PENDING, SubOrderStatus.DELIVERED, False),
        (SubOrderStatus.PENDING, SubOrderStatus.SHIPPED, False),
        (SubOrderStatus.SHIPPED, SubOrderStatus.CANCELLED, False),
        (SubOrderStatus.DELIVERED, SubOrderStatus.PENDING, False),
        (SubOrderStatus.CANCELLED, SubOrderStatus.CONFIRMED, False),
    ],
)
def test_sub_order_transitions(
    from_status: SubOrderStatus, to_status: SubOrderStatus, allowed: bool
) -> None:
    """El grafo de transiciones permite lo previsto y nada más."""
    assert (to_status in ALLOWED_SUB_ORDER_TRANSITIONS[from_status]) is allowed


@pytest.mark.unit
def test_terminal_states_have_no_outgoing_transitions() -> None:
    """Un pedido cancelado o reembolsado no vuelve a ningún estado activo."""
    for terminal in (SubOrderStatus.CANCELLED, SubOrderStatus.REFUNDED):
        assert ALLOWED_SUB_ORDER_TRANSITIONS[terminal] == frozenset()


@pytest.mark.unit
def test_every_status_is_present_in_the_transition_graph() -> None:
    """Ningún estado queda fuera del grafo, incluso si se añade uno nuevo."""
    assert set(ALLOWED_SUB_ORDER_TRANSITIONS) == set(SubOrderStatus)


@pytest.mark.unit
def test_soft_deleted_tables_expose_deleted_at() -> None:
    """Las entidades con valor histórico conservan su marca de baja lógica."""
    for table_name in ("users", "products", "addresses", "reviews", "categories"):
        columns = {column.name for column in Base.metadata.tables[table_name].columns}
        assert "deleted_at" in columns, f"{table_name} debería admitir baja lógica"


@pytest.mark.unit
def test_farm_exact_coordinates_are_separate_from_public_ones() -> None:
    """La ubicación exacta existe aparte de la publicable (ADR-08)."""
    columns = {column.name for column in Base.metadata.tables["farms"].columns}
    assert {"approx_lat", "approx_lng", "exact_lat", "exact_lng"} <= columns


@pytest.mark.unit
def test_inspection_exposes_relationships() -> None:
    """Las relaciones declaradas son navegables tras configurar los mappers."""
    from app.models import Order, SubOrder, User

    assert "sub_orders" in inspect(Order).relationships
    assert "items" in inspect(SubOrder).relationships
    assert "roles" in inspect(User).relationships
