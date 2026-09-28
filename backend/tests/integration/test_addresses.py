"""Pruebas de las direcciones de entrega (HU-CC-03).

La dirección es el único dato sin el cual un pedido no puede despacharse, y el
checkout la exige. Lo que se verifica aquí es que se pueda registrar, corregir y
dar de baja, que el departamento nunca contradiga al municipio, que haya como
máximo una predeterminada, y que nadie alcance las direcciones de otra cuenta.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.geo import Department, Municipality
from app.models.user import Address, User

pytestmark = pytest.mark.integration

API = "/api/v1"

NEW_ADDRESS = {
    "label": "Oficina",
    "recipient_name": "Comprador de Prueba",
    "phone": "3019876543",
    "street_address": "Carrera 15 # 88-40",
    "neighborhood": "Chapinero",
}


def _municipality_id(session: Session) -> int:
    municipality = session.scalar(select(Municipality))
    assert municipality is not None
    return municipality.id


class TestListing:
    def test_the_seeded_default_address_is_listed(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.get(f"{API}/users/me/addresses", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["is_default"] is True
        assert body[0]["street_address"] == "Calle 10 # 5-20"

    def test_an_anonymous_visitor_gets_nothing(self, client: TestClient, buyer: User) -> None:
        assert client.get(f"{API}/users/me/addresses").status_code == 401

    def test_the_default_one_comes_first(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        """El checkout preselecciona la primera: el orden no es cosmético."""
        client.post(
            f"{API}/users/me/addresses",
            json={**NEW_ADDRESS, "municipality_id": _municipality_id(session), "is_default": True},
            headers=auth_headers,
        )

        body = client.get(f"{API}/users/me/addresses", headers=auth_headers).json()

        assert body[0]["is_default"] is True
        assert body[0]["label"] == "Oficina"


class TestCreation:
    def test_a_buyer_registers_an_address(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        response = client.post(
            f"{API}/users/me/addresses",
            json={**NEW_ADDRESS, "municipality_id": _municipality_id(session)},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["label"] == "Oficina"
        assert body["neighborhood"] == "Chapinero"
        assert body["is_default"] is False

    def test_the_department_is_derived_from_the_municipality(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        """Nadie declara el departamento: así no entra «Pitalito en Antioquia»."""
        municipality = session.scalar(select(Municipality))
        assert municipality is not None

        body = client.post(
            f"{API}/users/me/addresses",
            json={**NEW_ADDRESS, "municipality_id": municipality.id},
            headers=auth_headers,
        ).json()

        assert body["department_id"] == municipality.department_id

    def test_a_municipality_that_does_not_exist_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.post(
            f"{API}/users/me/addresses",
            json={**NEW_ADDRESS, "municipality_id": 999_999},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_marking_a_new_one_as_default_demotes_the_previous(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        """El índice parcial de la base de datos solo admite una: si la anterior
        no se retirase, la inserción fallaría con violación de unicidad."""
        response = client.post(
            f"{API}/users/me/addresses",
            json={**NEW_ADDRESS, "municipality_id": _municipality_id(session), "is_default": True},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        defaults = [
            item
            for item in client.get(f"{API}/users/me/addresses", headers=auth_headers).json()
            if item["is_default"]
        ]
        assert len(defaults) == 1
        assert defaults[0]["label"] == "Oficina"

    def test_an_address_too_short_to_deliver_to_is_rejected(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
    ) -> None:
        response = client.post(
            f"{API}/users/me/addresses",
            json={
                **NEW_ADDRESS,
                "municipality_id": _municipality_id(session),
                "street_address": "Cra",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestEditing:
    def test_a_buyer_corrects_the_phone(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        response = client.patch(
            f"{API}/users/me/addresses/{address.id}",
            json={"phone": "3125550101"},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["phone"] == "3125550101"
        # Lo que no se mandó no se toca.
        assert response.json()["street_address"] == "Calle 10 # 5-20"

    def test_an_explicit_null_clears_an_optional_field(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        """`null` enviado a propósito borra; ausente deja como estaba."""
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None
        client.patch(
            f"{API}/users/me/addresses/{address.id}",
            json={"label": "Casa"},
            headers=auth_headers,
        )

        response = client.patch(
            f"{API}/users/me/addresses/{address.id}",
            json={"label": None},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["label"] is None

    def test_changing_the_municipality_moves_the_department_with_it(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        other_department = Department(dane_code="17", name="Caldas")
        session.add(other_department)
        session.flush()
        other_municipality = Municipality(
            department_id=other_department.id, dane_code="17001", name="Manizales"
        )
        session.add(other_municipality)
        session.flush()

        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        body = client.patch(
            f"{API}/users/me/addresses/{address.id}",
            json={"municipality_id": other_municipality.id},
            headers=auth_headers,
        ).json()

        assert body["municipality_id"] == other_municipality.id
        assert body["department_id"] == other_department.id

    def test_promoting_one_demotes_the_other(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        created = client.post(
            f"{API}/users/me/addresses",
            json={**NEW_ADDRESS, "municipality_id": _municipality_id(session)},
            headers=auth_headers,
        ).json()

        response = client.patch(
            f"{API}/users/me/addresses/{created['id']}",
            json={"is_default": True},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        listed = client.get(f"{API}/users/me/addresses", headers=auth_headers).json()
        assert [item["is_default"] for item in listed].count(True) == 1
        assert listed[0]["id"] == created["id"]

    def test_promoting_the_one_that_already_is_default_is_harmless(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        """Se excluye la propia fila al retirar la anterior; sin esa exclusión
        la dirección se desmarcaría a sí misma antes de volver a marcarse."""
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        response = client.patch(
            f"{API}/users/me/addresses/{address.id}",
            json={"is_default": True},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["is_default"] is True

    def test_a_municipality_that_does_not_exist_is_rejected(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        response = client.patch(
            f"{API}/users/me/addresses/{address.id}",
            json={"municipality_id": 999_999},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_editing_an_address_that_does_not_exist_gives_404(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.patch(
            f"{API}/users/me/addresses/{uuid.uuid4()}",
            json={"phone": "3125550101"},
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestIsolation:
    def test_nobody_edits_someone_elses_address(
        self, client: TestClient, session: Session, buyer: User, producer_token: str
    ) -> None:
        """Se responde 404 y no 403: distinguirlos revelaría que la dirección
        existe en otra cuenta."""
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        response = client.patch(
            f"{API}/users/me/addresses/{address.id}",
            json={"phone": "3125550101"},
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 404

    def test_nobody_deletes_someone_elses_address(
        self, client: TestClient, session: Session, buyer: User, producer_token: str
    ) -> None:
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        response = client.delete(
            f"{API}/users/me/addresses/{address.id}",
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 404

    def test_each_account_only_sees_its_own(
        self, client: TestClient, buyer: User, producer_token: str
    ) -> None:
        response = client.get(
            f"{API}/users/me/addresses",
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 200
        assert response.json() == []


class TestDeletion:
    def test_deleting_removes_it_from_the_list(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        response = client.delete(f"{API}/users/me/addresses/{address.id}", headers=auth_headers)

        assert response.status_code == 200
        assert client.get(f"{API}/users/me/addresses", headers=auth_headers).json() == []

    def test_the_row_survives_because_orders_point_at_it(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        """La baja es lógica: un pedido despachado conserva su referencia."""
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None
        address_id = address.id

        client.delete(f"{API}/users/me/addresses/{address_id}", headers=auth_headers)

        session.expire_all()
        still_there = session.get(Address, address_id)
        assert still_there is not None
        assert still_there.deleted_at is not None
        # Se libera la marca de predeterminada para que el índice parcial admita
        # una nueva dirección predeterminada.
        assert still_there.is_default is False

    def test_deleting_twice_gives_404(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None

        client.delete(f"{API}/users/me/addresses/{address.id}", headers=auth_headers)
        second = client.delete(f"{API}/users/me/addresses/{address.id}", headers=auth_headers)

        assert second.status_code == 404

    def test_a_new_default_can_be_registered_after_deleting_the_old_one(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None
        client.delete(f"{API}/users/me/addresses/{address.id}", headers=auth_headers)

        response = client.post(
            f"{API}/users/me/addresses",
            json={**NEW_ADDRESS, "municipality_id": _municipality_id(session), "is_default": True},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text


class TestGeography:
    def test_the_department_list_is_public(self, client: TestClient, session: Session) -> None:
        """El formulario de dirección lo necesita antes de iniciar sesión."""
        session.add(Department(dane_code="17", name="Caldas"))
        session.flush()

        response = client.get(f"{API}/users/geo/departments")

        assert response.status_code == 200
        assert any(item["name"] == "Caldas" for item in response.json())

    def test_the_municipalities_of_a_department_are_listed(
        self, client: TestClient, session: Session, geography: Municipality
    ) -> None:
        municipality = geography

        response = client.get(
            f"{API}/users/geo/departments/{municipality.department_id}/municipalities"
        )

        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Pitalito"]

    def test_a_department_without_municipalities_returns_an_empty_list(
        self, client: TestClient, session: Session
    ) -> None:
        empty = Department(dane_code="94", name="Guainía")
        session.add(empty)
        session.flush()

        response = client.get(f"{API}/users/geo/departments/{empty.id}/municipalities")

        assert response.status_code == 200
        assert response.json() == []
