"""Pruebas de la publicación de cafés por el vendedor.

El catálogo es lo que cada caficultor pone a la venta, así que estas pruebas
vigilan dos cosas: que el flujo de publicación exija lo mínimo para que un
comprador pueda decidir, y que ningún vendedor alcance el catálogo de otro.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Product, ProductVariant
from app.models.enums import ProductStatus
from app.models.producer import ProducerProfile
from app.models.user import User

pytestmark = pytest.mark.integration

API = "/api/v1"


class FakeStorage:
    """Almacenamiento en memoria: las pruebas no deben depender de MinIO."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, content: bytes, content_type: str) -> str:
        self.objects[key] = content
        return key

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def public_url(self, key: str) -> str:
        return f"https://almacenamiento.prueba/{key}"


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr(
        "app.modules.producers.catalog_service.get_storage", lambda: fake, raising=True
    )
    return fake


@pytest.fixture
def producer_headers(producer_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {producer_token}"}


@pytest.fixture
def second_producer_headers(
    client: TestClient, second_producer: ProducerProfile, session: Session
) -> dict[str, str]:
    from tests.integration.conftest import TEST_PASSWORD

    user = session.get(User, second_producer.user_id)
    assert user is not None
    response = client.post(
        f"{API}/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _jpeg_bytes(width: int = 900, height: int = 700) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "sienna").save(buffer, format="JPEG")
    return buffer.getvalue()


NEW_COFFEE = {
    "name": "Tolima Honey de Prueba",
    "description": "Lote de prueba con descripción suficientemente larga para el validador.",
    # `base_price` es el precio por kilogramo de pergamino seco.
    "base_price": "22000",
    "dispatch_days": 3,
    "attributes": {
        "variety": "Caturra",
        "process": "honey",
        "yield_factor": "91.50",
        "moisture_pct": "11.00",
        "screen_sizes": [15, 16, 17],
        "lot_code": "TO-2026-001",
    },
}

# Oferta mínima válida: cómo se entrega el lote, precio por kilo y kilos.
NEW_OFFER = {
    "presentation": "A granel, en costal de fique",
    "min_qty_kg": 125,
    "price": "22000",
    "stock_qty": 1250,
}


def _create(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {**NEW_COFFEE, **overrides}
    response = client.post(f"{API}/producer/catalog", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


class TestProductCreation:
    def test_new_coffee_starts_as_draft(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        """Publicar es un acto explícito: nada sale al catálogo por crearse."""
        product = _create(client, producer_headers)

        assert product["status"] == ProductStatus.DRAFT.value
        assert product["slug"] == "tolima-honey-de-prueba"

    def test_server_ignores_status_sent_by_the_client(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        """Nadie se publica a sí mismo colando el estado en el cuerpo."""
        product = _create(client, producer_headers, status="published", slug="elegido-por-mi")

        assert product["status"] == ProductStatus.DRAFT.value
        assert product["slug"] == "tolima-honey-de-prueba"

    def test_draft_is_absent_from_the_public_catalogue(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        _create(client, producer_headers)

        listing = client.get(f"{API}/products", params={"q": "Tolima Honey de Prueba"})

        assert listing.json()["total"] == 0

    def test_duplicate_names_get_distinct_slugs(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        first = _create(client, producer_headers)
        second = _create(client, producer_headers)

        assert first["slug"] != second["slug"]

    def test_wholesale_price_must_be_below_retail(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        response = client.post(
            f"{API}/producer/catalog",
            json={**NEW_COFFEE, "wholesale_price": "60000"},
            headers=producer_headers,
        )

        assert response.status_code == 422

    def test_rejects_a_price_of_zero(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        response = client.post(
            f"{API}/producer/catalog",
            json={**NEW_COFFEE, "base_price": "0"},
            headers=producer_headers,
        )

        assert response.status_code == 422


class TestPublishingRequirements:
    def test_cannot_publish_without_photo_or_variant(
        self, client: TestClient, producer_headers: dict[str, str]
    ) -> None:
        """Un comprador no puede decidir sobre un café sin foto ni presentación."""
        product = _create(client, producer_headers)

        response = client.post(
            f"{API}/producer/catalog/{product['id']}/publish", headers=producer_headers
        )

        assert response.status_code == 422
        missing = response.json()["error"]["details"]["missing"]
        assert len(missing) == 2

    def test_full_publication_flow(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
    ) -> None:
        """Recorrido completo: borrador, presentación, foto y publicación."""
        product = _create(client, producer_headers)
        product_id = product["id"]

        variant = client.post(
            f"{API}/producer/catalog/{product_id}/variants",
            json=NEW_OFFER,
            headers=producer_headers,
        )
        assert variant.status_code == 201
        assert variant.json()["variants"][0]["stock_qty"] == 1250
        assert variant.json()["variants"][0]["min_qty_kg"] == 125

        image = client.post(
            f"{API}/producer/catalog/{product_id}/images",
            files={"file": ("grano.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=producer_headers,
        )
        assert image.status_code == 201
        assert image.json()["images"][0]["is_primary"] is True
        assert image.json()["missing_to_publish"] == []
        assert len(storage.objects) == 1

        published = client.post(
            f"{API}/producer/catalog/{product_id}/publish", headers=producer_headers
        )
        assert published.status_code == 200
        assert published.json()["status"] == ProductStatus.PUBLISHED.value

        listing = client.get(f"{API}/products", params={"q": "Tolima Honey de Prueba"})
        assert listing.json()["total"] == 1

    def test_unpublishing_removes_it_from_the_catalogue(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
    ) -> None:
        product = _create(client, producer_headers)
        product_id = product["id"]
        client.post(
            f"{API}/producer/catalog/{product_id}/variants",
            json={**NEW_OFFER, "min_qty_kg": 10, "price": "52000", "stock_qty": 10},
            headers=producer_headers,
        )
        client.post(
            f"{API}/producer/catalog/{product_id}/images",
            files={"file": ("grano.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=producer_headers,
        )
        client.post(f"{API}/producer/catalog/{product_id}/publish", headers=producer_headers)

        client.post(f"{API}/producer/catalog/{product_id}/unpublish", headers=producer_headers)

        assert client.get(f"{API}/products", params={"q": "Tolima Honey"}).json()["total"] == 0


class TestImageHandling:
    def test_rejects_a_script_disguised_as_a_photo(
        self, client: TestClient, producer_headers: dict[str, str], storage: FakeStorage
    ) -> None:
        product = _create(client, producer_headers)

        response = client.post(
            f"{API}/producer/catalog/{product['id']}/images",
            files={"file": ("inocente.jpg", b"<?php system($_GET['c']); ?>", "image/jpeg")},
            headers=producer_headers,
        )

        assert response.status_code == 422
        assert storage.objects == {}

    def test_deleting_the_cover_promotes_the_next_photo(
        self, client: TestClient, producer_headers: dict[str, str], storage: FakeStorage
    ) -> None:
        """La ficha nunca debe quedarse sin portada."""
        product = _create(client, producer_headers)
        product_id = product["id"]
        for _ in range(2):
            client.post(
                f"{API}/producer/catalog/{product_id}/images",
                files={"file": ("grano.jpg", _jpeg_bytes(), "image/jpeg")},
                headers=producer_headers,
            )

        detail = client.get(f"{API}/producer/catalog/{product_id}", headers=producer_headers).json()
        primary_id = next(img["id"] for img in detail["images"] if img["is_primary"])

        response = client.delete(
            f"{API}/producer/catalog/{product_id}/images/{primary_id}", headers=producer_headers
        )

        images = response.json()["images"]
        assert len(images) == 1
        assert images[0]["is_primary"] is True
        assert len(storage.objects) == 1


class TestVariantManagement:
    def test_stock_cannot_drop_below_reserved_units(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        product_variant: ProductVariant,
        session: Session,
    ) -> None:
        """Esas unidades están comprometidas con pedidos en curso."""
        inventory = product_variant.inventory
        inventory.reserved_qty = 3
        session.commit()

        response = client.put(
            f"{API}/producer/catalog/{product_variant.product_id}/variants/{product_variant.id}",
            json={**NEW_OFFER, "min_qty_kg": 1, "price": "40000", "stock_qty": 1},
            headers=producer_headers,
        )

        assert response.status_code == 422
        assert "reservadas" in response.json()["error"]["message"]

    def test_variant_with_reservations_cannot_be_removed(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        product_variant: ProductVariant,
        session: Session,
    ) -> None:
        product_variant.inventory.reserved_qty = 2
        session.commit()

        response = client.delete(
            f"{API}/producer/catalog/{product_variant.product_id}/variants/{product_variant.id}",
            headers=producer_headers,
        )

        assert response.status_code == 422


class TestCatalogueIsolation:
    """Ningún vendedor alcanza el catálogo de otro."""

    def test_a_producer_cannot_read_someone_elses_coffee(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
    ) -> None:
        product = _create(client, producer_headers)

        response = client.get(
            f"{API}/producer/catalog/{product['id']}", headers=second_producer_headers
        )

        assert response.status_code == 403

    def test_a_producer_cannot_edit_someone_elses_coffee(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
        session: Session,
    ) -> None:
        product = _create(client, producer_headers)

        response = client.put(
            f"{API}/producer/catalog/{product['id']}",
            json={**NEW_COFFEE, "name": "Secuestrado", "base_price": "1"},
            headers=second_producer_headers,
        )

        assert response.status_code == 403
        stored = session.get(Product, uuid.UUID(product["id"]))
        assert stored is not None
        assert stored.name == NEW_COFFEE["name"]

    def test_a_producer_cannot_publish_someone_elses_coffee(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
    ) -> None:
        product = _create(client, producer_headers)

        response = client.post(
            f"{API}/producer/catalog/{product['id']}/publish", headers=second_producer_headers
        )

        assert response.status_code == 403

    def test_a_producer_cannot_add_variants_to_someone_elses_coffee(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
        session: Session,
    ) -> None:
        product = _create(client, producer_headers)

        response = client.post(
            f"{API}/producer/catalog/{product['id']}/variants",
            json={**NEW_OFFER, "min_qty_kg": 1, "price": "1", "stock_qty": 0},
            headers=second_producer_headers,
        )

        assert response.status_code == 403
        variants = session.scalars(
            select(ProductVariant).where(ProductVariant.product_id == uuid.UUID(product["id"]))
        ).all()
        assert variants == []

    def test_the_listing_only_shows_your_own_coffees(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
    ) -> None:
        _create(client, producer_headers)

        response = client.get(f"{API}/producer/catalog", headers=second_producer_headers)

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_a_buyer_cannot_publish_coffee(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(f"{API}/producer/catalog", json=NEW_COFFEE, headers=auth_headers)

        assert response.status_code == 403

    def test_publishing_requires_authentication(self, client: TestClient) -> None:
        assert client.post(f"{API}/producer/catalog", json=NEW_COFFEE).status_code == 401


class TestSellerNotificationData:
    """Registro de oferentes exigido por el artículo 53 de la Ley 1480 de 2011.

    La plataforma debe poder entregar a quien reclama la dirección de
    notificaciones y el teléfono de quien le vendió. Si el vendedor no los tiene
    registrados, su café no puede salir al catálogo.
    """

    def test_cannot_publish_without_notification_address(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        producer: ProducerProfile,
        storage: FakeStorage,
        session: Session,
    ) -> None:
        producer.notification_address = None
        session.commit()

        product = _create(client, producer_headers)
        product_id = product["id"]
        client.post(
            f"{API}/producer/catalog/{product_id}/variants",
            json={**NEW_OFFER, "min_qty_kg": 5, "price": "40000", "stock_qty": 5},
            headers=producer_headers,
        )
        client.post(
            f"{API}/producer/catalog/{product_id}/images",
            files={"file": ("grano.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=producer_headers,
        )

        response = client.post(
            f"{API}/producer/catalog/{product_id}/publish", headers=producer_headers
        )

        assert response.status_code == 422
        missing = response.json()["error"]["details"]["missing"]
        assert any("dirección de notificaciones" in item for item in missing)

    def test_cannot_publish_without_contact_phone(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        producer: ProducerProfile,
        session: Session,
    ) -> None:
        producer.contact_phone = None
        session.commit()

        product = _create(client, producer_headers)

        detail = client.get(
            f"{API}/producer/catalog/{product['id']}", headers=producer_headers
        ).json()

        assert any("teléfono" in item for item in detail["missing_to_publish"])

    def test_producer_can_register_its_notification_data(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        producer: ProducerProfile,
        session: Session,
    ) -> None:
        """Exigir un dato sin ofrecer dónde registrarlo bloquearía al vendedor."""
        producer.notification_address = None
        producer.contact_phone = None
        session.commit()

        response = client.put(
            f"{API}/producer/profile",
            json={
                "brand_name": "Finca de Prueba",
                "notification_address": "Vereda El Roble, finca La Palma, Manizales",
                "contact_phone": "3201234567",
            },
            headers=producer_headers,
        )

        assert response.status_code == 200
        assert response.json()["has_notification_data"] is True

    def test_profile_does_not_accept_changing_the_verified_identity(
        self, client: TestClient, producer_headers: dict[str, str], producer: ProducerProfile
    ) -> None:
        """La razón social y el documento los verificó el equipo al aprobar."""
        original_name = producer.legal_name

        client.put(
            f"{API}/producer/profile",
            json={
                "legal_name": "Otra Razón Social S.A.S.",
                "document_number": "900999888-1",
                "notification_address": "Calle 1 # 2-3, Manizales",
                "contact_phone": "3001112233",
            },
            headers=producer_headers,
        )

        detail = client.get(f"{API}/producer/profile", headers=producer_headers).json()
        assert detail["legal_name"] == original_name

    def test_another_producer_cannot_read_my_profile(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
        producer: ProducerProfile,
    ) -> None:
        response = client.get(f"{API}/producer/profile", headers=second_producer_headers)

        assert response.status_code == 200
        assert response.json()["id"] != str(producer.id)
