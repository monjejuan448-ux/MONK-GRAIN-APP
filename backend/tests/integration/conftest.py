"""Fixtures de las pruebas de integración.

Construyen un escenario mínimo pero completo —geografía, roles, un productor
aprobado, un café con inventario y un comprador con dirección— para poder
ejercitar los flujos de negocio de principio a fin.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_session
from app.main import app
from app.models.catalog import (
    CoffeeAttributes,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)
from app.models.enums import (
    CoffeeProcess,
    CoffeeState,
    GrindType,
    ProducerStatus,
    ProducerType,
    ProductStatus,
    RoastLevel,
    RoleCode,
    UserStatus,
)
from app.models.geo import Department, Municipality, Region
from app.models.producer import Farm, ProducerProfile
from app.models.user import Address, Permission, Role, RolePermission, User, UserRole

TEST_PASSWORD = "PruebaMonkGrain2026"  # noqa: S105 — credencial de pruebas


@pytest.fixture(autouse=True)
def reset_rate_limits() -> Generator[None, None, None]:
    """Limpia los contadores de peticiones antes de cada prueba.

    Los contadores viven en Redis y son compartidos: sin esta limpieza, la
    quinta prueba que inicia sesión chocaría con el límite que dejó la anterior
    y fallaría por una razón ajena a lo que pretende verificar. El limitador se
    prueba aparte, en `test_rate_limit.py`.
    """
    import redis

    from app.core.rate_limit import get_redis

    try:
        client = get_redis()
        keys = list(client.scan_iter("rl:*"))
        if keys:
            client.delete(*keys)
    except redis.RedisError:
        # Sin Redis disponible no hay contadores que limpiar; la prueba sigue.
        pass

    yield


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    """Cliente HTTP que comparte la sesión transaccional de la prueba.

    Sin esta sustitución, la API abriría su propia sesión y no vería los datos
    creados por la prueba, que viven en una transacción sin confirmar.
    """

    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def roles(session: Session) -> dict[str, Role]:
    """Roles y permisos mínimos para ejercitar la autorización."""
    permissions = {
        code: Permission(code=code, resource=code.split(".")[0], action=code.split(".")[1])
        for code in ("order.create", "order.view_own", "review.create", "product.create")
    }
    session.add_all(permissions.values())
    session.flush()

    created: dict[str, Role] = {}
    for role_code, permission_codes in (
        (RoleCode.CONSUMER, ("order.create", "order.view_own", "review.create")),
        (RoleCode.PRODUCER, ("product.create",)),
        (RoleCode.ADMIN, ()),
    ):
        role = Role(code=role_code.value, name=role_code.value.title())
        session.add(role)
        session.flush()
        for permission_code in permission_codes:
            session.add(
                RolePermission(role_id=role.id, permission_id=permissions[permission_code].id)
            )
        created[role_code.value] = role

    session.flush()
    return created


@pytest.fixture
def geography(session: Session) -> Municipality:
    department = Department(dane_code="41", name="Huila")
    session.add(department)
    session.flush()

    municipality = Municipality(
        department_id=department.id,
        dane_code="41551",
        name="Pitalito",
        centroid_lat=Decimal("1.853900"),
        centroid_lng=Decimal("-76.051300"),
    )
    session.add(municipality)
    session.add(Region(code="huila", name="Huila"))
    session.flush()
    return municipality


@pytest.fixture
def buyer(session: Session, roles: dict[str, Role], geography: Municipality) -> User:
    """Comprador verificado con una dirección de entrega."""
    user = User(
        email="comprador@prueba.co",
        password_hash=hash_password(TEST_PASSWORD),
        full_name="Comprador de Prueba",
        status=UserStatus.ACTIVE,
        data_consent=True,
        data_consent_at=datetime.now(UTC),
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.CONSUMER.value].id))
    session.add(
        Address(
            user_id=user.id,
            recipient_name="Comprador de Prueba",
            phone="3001234567",
            department_id=geography.department_id,
            municipality_id=geography.id,
            street_address="Calle 10 # 5-20",
            is_default=True,
        )
    )
    session.flush()
    return user


@pytest.fixture
def producer(session: Session, roles: dict[str, Role], geography: Municipality) -> ProducerProfile:
    """Productor aprobado con finca."""
    user = User(
        email="productor@prueba.co",
        password_hash=hash_password(TEST_PASSWORD),
        full_name="Productor de Prueba",
        status=UserStatus.ACTIVE,
        data_consent=True,
        data_consent_at=datetime.now(UTC),
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.PRODUCER.value].id))

    profile = ProducerProfile(
        user_id=user.id,
        type=ProducerType.FARM,
        legal_name="Finca de Prueba S.A.S.",
        document_number="900111222-3",
        brand_name="Café de Prueba",
        department_id=geography.department_id,
        municipality_id=geography.id,
        status=ProducerStatus.APPROVED,
        reviewed_at=datetime.now(UTC),
        # Exigidos para publicar (artículo 53 de la Ley 1480 de 2011).
        notification_address="Calle 10 # 5-32, Manizales",
        contact_phone="3105550142",
    )
    session.add(profile)
    session.flush()

    session.add(
        Farm(
            producer_id=profile.id,
            name="Finca de Prueba",
            municipality_id=geography.id,
            approx_lat=geography.centroid_lat,
            approx_lng=geography.centroid_lng,
            # Coordenada exacta almacenada, que nunca debe salir en la API.
            exact_lat=Decimal("1.860000"),
            exact_lng=Decimal("-76.060000"),
        )
    )
    session.flush()
    return profile


@pytest.fixture
def second_producer(
    session: Session, roles: dict[str, Role], geography: Municipality
) -> ProducerProfile:
    """Segundo vendedor, necesario para probar la división del pedido."""
    user = User(
        email="productor2@prueba.co",
        password_hash=hash_password(TEST_PASSWORD),
        full_name="Segundo Productor",
        status=UserStatus.ACTIVE,
        data_consent=True,
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=roles[RoleCode.PRODUCER.value].id))

    profile = ProducerProfile(
        user_id=user.id,
        type=ProducerType.COOPERATIVE,
        legal_name="Cooperativa de Prueba",
        document_number="800333444-5",
        brand_name="Coop de Prueba",
        department_id=geography.department_id,
        municipality_id=geography.id,
        status=ProducerStatus.APPROVED,
        notification_address="Carrera 8 # 12-40, Manizales",
        contact_phone="3105550199",
    )
    session.add(profile)
    session.flush()
    return profile


def _create_product(
    session: Session,
    producer: ProducerProfile,
    *,
    slug: str,
    name: str,
    price: Decimal,
    stock: int,
    wholesale_price: Decimal | None = None,
) -> ProductVariant:
    """Crea un producto publicado con una variante e inventario."""
    farm = session.scalar(select(Farm).where(Farm.producer_id == producer.id))

    product = Product(
        producer_id=producer.id,
        farm_id=farm.id if farm else None,
        slug=slug,
        name=name,
        description="Café de prueba para la suite de integración.",
        state=CoffeeState.ROASTED,
        status=ProductStatus.PUBLISHED,
        base_price=price,
        wholesale_price=wholesale_price,
        wholesale_min_qty=10 if wholesale_price else None,
        published_at=datetime.now(UTC),
    )
    session.add(product)
    session.flush()

    session.add(
        CoffeeAttributes(
            product_id=product.id,
            variety="Caturra",
            process=CoffeeProcess.WASHED,
            roast=RoastLevel.MEDIUM,
            altitude_masl=1750,
            cupping_score=Decimal("86.50"),
            sensory_profile="Dulce, con acidez cítrica.",
        )
    )
    session.add(ProductImage(product_id=product.id, image_key=f"test/{slug}.jpg", is_primary=True))

    variant = ProductVariant(
        product_id=product.id,
        sku=f"{slug.upper()}-250",
        weight_grams=Decimal("250"),
        grind=GrindType.WHOLE_BEAN,
        price=price,
        wholesale_price=wholesale_price,
        is_active=True,
    )
    session.add(variant)
    session.flush()

    session.add(
        Inventory(variant_id=variant.id, stock_qty=stock, reserved_qty=0, low_stock_threshold=5)
    )
    session.flush()
    return variant


@pytest.fixture
def product_variant(session: Session, producer: ProducerProfile) -> ProductVariant:
    return _create_product(
        session,
        producer,
        slug="cafe-de-prueba",
        name="Café de Prueba",
        price=Decimal("40000"),
        stock=10,
        wholesale_price=Decimal("35000"),
    )


@pytest.fixture
def second_variant(session: Session, second_producer: ProducerProfile) -> ProductVariant:
    return _create_product(
        session,
        second_producer,
        slug="cafe-de-prueba-dos",
        name="Segundo Café de Prueba",
        price=Decimal("50000"),
        stock=8,
    )


@pytest.fixture
def buyer_token(client: TestClient, buyer: User) -> str:
    """Access token del comprador, obtenido por el endpoint real de login."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": buyer.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


@pytest.fixture
def producer_token(client: TestClient, producer: ProducerProfile, session: Session) -> str:
    user = session.get(User, producer.user_id)
    assert user is not None
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


@pytest.fixture
def auth_headers(buyer_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {buyer_token}"}
