"""Pruebas de las certificaciones del vendedor.

Un sello en la ficha es una afirmación con consecuencias comerciales, así que
estas pruebas cuidan tres cosas: que solo se exhiba lo acreditado y vigente, que
el documento no quede al alcance de terceros, y que la vigencia se calcule con
la fecha real y no con un campo que alguien deba acordarse de actualizar.
"""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalog import ProductVariant
from app.models.enums import CertStatus
from app.models.producer import Certification, ProducerProfile
from app.models.user import User

pytestmark = pytest.mark.integration

API = "/api/v1"


@pytest.fixture
def certifications(session: Session) -> dict[str, int]:
    """Catálogo mínimo de certificaciones.

    Los identificadores se leen de la base en vez de fijarse a mano: son
    autoincrementales y suponer que valen 1 y 2 haría fallar las pruebas en
    cuanto cambiara el orden de la siembra.
    """
    rows = {
        "organic": Certification(code="organic", name="Orgánico", issuing_body="Ecocert"),
        "fairtrade": Certification(code="fairtrade", name="Comercio Justo"),
    }
    session.add_all(rows.values())
    session.flush()
    return {code: row.id for code, row in rows.items()}


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, content: bytes, content_type: str) -> str:
        self.objects[key] = content
        return key

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def public_url(self, key: str) -> str:
        return f"https://almacenamiento.prueba/{key}"

    def signed_url(self, key: str, expires_in: int = 300) -> str:
        return f"https://almacenamiento.prueba/{key}?firma=simulada&caduca={expires_in}"


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr(
        "app.modules.producers.certification_service.get_storage", lambda: fake, raising=True
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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer\n%%EOF"


def _register(
    client: TestClient,
    headers: dict[str, str],
    certification_id: int,
    *,
    expires_at: date | None = None,
    with_document: bool = True,
) -> dict:
    data: dict[str, str] = {"certification_id": str(certification_id)}
    if expires_at:
        data["expires_at"] = expires_at.isoformat()

    files = {"file": ("certificado.pdf", PDF, "application/pdf")} if with_document else None
    response = client.post(
        f"{API}/producer/certifications", data=data, files=files, headers=headers
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


class TestRegistration:
    def test_registers_a_certification_with_its_document(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        result = _register(
            client,
            producer_headers,
            certifications["organic"],
            expires_at=date.today() + timedelta(days=365),
        )

        assert result["certification_code"] == "organic"
        assert result["has_document"] is True
        assert result["status"] == CertStatus.ACTIVE.value
        assert len(storage.objects) == 1

    def test_the_document_is_stored_outside_the_public_prefixes(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        """Un certificado lleva datos del productor: no es escaparate."""
        _register(client, producer_headers, certifications["organic"])

        key = next(iter(storage.objects))
        assert key.startswith("certifications/")
        assert not key.startswith(("products/", "producers/", "demo/"))

    def test_rejects_an_executable_disguised_as_certificate(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        response = client.post(
            f"{API}/producer/certifications",
            data={"certification_id": str(certifications["organic"])},
            files={"file": ("certificado.pdf", b"\x7fELF\x02\x01\x01\x00", "application/pdf")},
            headers=producer_headers,
        )

        assert response.status_code == 422
        assert storage.objects == {}

    def test_rejects_issue_date_after_expiry(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        response = client.post(
            f"{API}/producer/certifications",
            data={
                "certification_id": str(certifications["organic"]),
                "issued_at": "2026-06-01",
                "expires_at": "2025-01-01",
            },
            headers=producer_headers,
        )

        assert response.status_code == 422

    def test_cannot_declare_the_same_certification_twice(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        _register(client, producer_headers, certifications["organic"])

        response = client.post(
            f"{API}/producer/certifications",
            data={"certification_id": str(certifications["organic"])},
            headers=producer_headers,
        )

        assert response.status_code == 422


class TestExpiry:
    def test_a_past_date_reads_as_expired(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        """El estado sale de la fecha, sin depender de ningún proceso previo."""
        result = _register(
            client,
            producer_headers,
            certifications["organic"],
            expires_at=date.today() - timedelta(days=10),
        )

        assert result["status"] == CertStatus.EXPIRED.value
        assert result["days_to_expiry"] == -10

    def test_a_close_date_warns_before_expiring(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        """Avisa con margen para que dé tiempo a renovar."""
        result = _register(
            client,
            producer_headers,
            certifications["organic"],
            expires_at=date.today() + timedelta(days=30),
        )

        assert result["status"] == CertStatus.EXPIRING.value

    def test_without_expiry_it_stays_active(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        result = _register(client, producer_headers, certifications["organic"], expires_at=None)

        assert result["status"] == CertStatus.ACTIVE.value
        assert result["days_to_expiry"] is None


class TestProductAssociation:
    def test_attaches_an_accredited_certification(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        product_variant: ProductVariant,
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        _register(
            client,
            producer_headers,
            certifications["organic"],
            expires_at=date.today() + timedelta(days=200),
        )

        response = client.post(
            f"{API}/producer/catalog/{product_variant.product_id}/certifications/{certifications['organic']}",
            headers=producer_headers,
        )

        assert response.status_code == 200
        assert [item["code"] for item in response.json()] == ["organic"]

    def test_cannot_claim_a_certification_it_does_not_hold(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        product_variant: ProductVariant,
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        """La ficha no debe lucir un sello sin respaldo."""
        response = client.post(
            f"{API}/producer/catalog/{product_variant.product_id}/certifications/{certifications['fairtrade']}",
            headers=producer_headers,
        )

        assert response.status_code == 422
        assert "registra esta certificación" in response.json()["error"]["message"]

    def test_cannot_claim_an_expired_certification(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        product_variant: ProductVariant,
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        _register(
            client,
            producer_headers,
            certifications["organic"],
            expires_at=date.today() - timedelta(days=1),
        )

        response = client.post(
            f"{API}/producer/catalog/{product_variant.product_id}/certifications/{certifications['organic']}",
            headers=producer_headers,
        )

        assert response.status_code == 422
        assert "vencida" in response.json()["error"]["message"]

    def test_attaching_twice_is_harmless(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        product_variant: ProductVariant,
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        _register(client, producer_headers, certifications["organic"])
        organic = certifications["organic"]
        url = f"{API}/producer/catalog/{product_variant.product_id}/certifications/{organic}"

        client.post(url, headers=producer_headers)
        response = client.post(url, headers=producer_headers)

        assert response.status_code == 200
        assert len(response.json()) == 1


class TestDocumentAccess:
    def test_the_owner_gets_a_short_lived_link(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        certification = _register(client, producer_headers, certifications["organic"])

        response = client.get(
            f"{API}/producer/certifications/{certification['id']}/document",
            headers=producer_headers,
        )

        assert response.status_code == 200
        assert response.json()["expires_in_seconds"] <= 900

    def test_another_producer_cannot_reach_the_document(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        certification = _register(client, producer_headers, certifications["organic"])

        response = client.get(
            f"{API}/producer/certifications/{certification['id']}/document",
            headers=second_producer_headers,
        )

        assert response.status_code == 403

    def test_a_buyer_cannot_reach_the_document(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        auth_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        certification = _register(client, producer_headers, certifications["organic"])

        response = client.get(
            f"{API}/producer/certifications/{certification['id']}/document", headers=auth_headers
        )

        assert response.status_code == 403

    def test_missing_document_is_reported_as_such(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        certification = _register(
            client, producer_headers, certifications["organic"], with_document=False
        )

        response = client.get(
            f"{API}/producer/certifications/{certification['id']}/document",
            headers=producer_headers,
        )

        assert response.status_code == 404

    def test_deleting_removes_the_stored_document(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        certification = _register(client, producer_headers, certifications["organic"])
        assert len(storage.objects) == 1

        response = client.delete(
            f"{API}/producer/certifications/{certification['id']}", headers=producer_headers
        )

        assert response.status_code == 204
        assert storage.objects == {}

    def test_another_producer_cannot_delete_it(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        second_producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        certification = _register(client, producer_headers, certifications["organic"])

        response = client.delete(
            f"{API}/producer/certifications/{certification['id']}",
            headers=second_producer_headers,
        )

        assert response.status_code == 403
        assert len(storage.objects) == 1

    def test_an_unknown_certification_is_not_found(
        self,
        client: TestClient,
        producer_headers: dict[str, str],
        storage: FakeStorage,
        certifications: dict[str, int],
    ) -> None:
        response = client.get(
            f"{API}/producer/certifications/{uuid.uuid4()}/document", headers=producer_headers
        )

        assert response.status_code == 404
