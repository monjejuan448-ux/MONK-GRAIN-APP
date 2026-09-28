"""Pruebas del mercado de dos lados: el comprador publica, el vendedor responde.

Lo que se verifica aquí es el recorrido completo —solicitud, postura, respuesta—
y sobre todo las tres cosas que pueden salir mal con dinero de por medio: que el
precio acordado sea el que se cobra y no el del catálogo, que unos kilos no se
prometan dos veces, y que ni el comprador ni el vendedor alcancen lo que no es
suyo.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Inventory, ProductVariant
from app.models.enums import DemandStatus, OfferStatus
from app.models.order import Order, OrderItem
from app.models.trading import DemandOffer, DemandRequest
from app.models.user import Address, User

pytestmark = pytest.mark.integration

API = "/api/v1"


def _demand_payload(**overrides: object) -> dict:
    return {
        "title": "Busco pergamino factor 94 o mejor",
        "description": "Para trilla de exportación. Pago contra análisis en bodega.",
        "wanted_kg": 250,
        "max_yield_factor": "94.00",
        "max_moisture_pct": "12.00",
        "offered_price_per_kg": "21000",
        "expires_on": str(date.today() + timedelta(days=30)),
        **overrides,
    }


def _create_demand(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = client.post(f"{API}/demands", json=_demand_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


def _make_offer(
    client: TestClient,
    producer_token: str,
    demand_id: str,
    variant: ProductVariant,
    *,
    kg: int = 250,
    price: str = "20000",
) -> tuple[int, dict]:
    response = client.post(
        f"{API}/producer/demands/{demand_id}/offers",
        json={"variant_id": str(variant.id), "offered_kg": kg, "price_per_kg": price},
        headers={"Authorization": f"Bearer {producer_token}"},
    )
    return response.status_code, response.json()


class TestPublishingADemand:
    def test_a_buyer_publishes_what_they_are_looking_for(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        body = _create_demand(client, auth_headers)

        assert body["wanted_kg"] == 250
        assert body["covered_kg"] == 0
        assert body["remaining_kg"] == 250
        assert body["status"] == DemandStatus.OPEN.value
        assert body["is_receiving"] is True
        assert body["offers"] == []

    def test_the_origin_department_is_derived_from_the_municipality(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        from app.models.geo import Municipality

        municipality = session.scalar(select(Municipality))
        assert municipality is not None

        body = _create_demand(client, auth_headers, municipality_id=municipality.id)

        assert body["municipality"] == "Pitalito"
        assert body["department"] == "Huila"

    def test_a_date_in_the_past_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.post(
            f"{API}/demands",
            json=_demand_payload(expires_on=str(date.today() - timedelta(days=1))),
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_a_validity_beyond_a_quarter_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        """Más allá de 90 días el precio ofrecido ya no corresponde a la cosecha."""
        response = client.post(
            f"{API}/demands",
            json=_demand_payload(expires_on=str(date.today() + timedelta(days=200))),
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert "90" in response.text

    def test_an_impossible_yield_factor_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        response = client.post(
            f"{API}/demands", json=_demand_payload(max_yield_factor="10"), headers=auth_headers
        )

        assert response.status_code == 422

    def test_an_anonymous_visitor_cannot_publish(self, client: TestClient) -> None:
        assert client.post(f"{API}/demands", json=_demand_payload()).status_code == 401


class TestTheSellerSide:
    def test_a_seller_sees_the_open_demand(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        producer_token: str,
    ) -> None:
        _create_demand(client, auth_headers)

        response = client.get(
            f"{API}/producer/demands", headers={"Authorization": f"Bearer {producer_token}"}
        )

        assert response.status_code == 200, response.text
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["wanted_kg"] == 250

    def test_an_expired_demand_is_not_listed(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        producer_token: str,
    ) -> None:
        """El vencimiento se juzga al consultar, sin un proceso que recorra la
        tabla cada noche marcando estados."""
        created = _create_demand(client, auth_headers)
        demand = session.get(DemandRequest, uuid.UUID(created["id"]))
        assert demand is not None
        demand.expires_on = date.today() - timedelta(days=1)
        session.flush()

        response = client.get(
            f"{API}/producer/demands", headers={"Authorization": f"Bearer {producer_token}"}
        )

        assert response.json()["items"] == []

    def test_a_buyer_cannot_browse_the_sellers_inbox(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        """Las solicitudes no son públicas: dicen qué busca alguien y a qué precio."""
        assert client.get(f"{API}/producer/demands", headers=auth_headers).status_code == 403

    def test_the_matching_filter_hides_what_the_seller_cannot_satisfy(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """El lote del vendedor tiene factor 92: una solicitud que pide 88 o
        menos no le sirve de nada."""
        _create_demand(client, auth_headers, max_yield_factor="88.00")

        headers = {"Authorization": f"Bearer {producer_token}"}
        todas = client.get(f"{API}/producer/demands", headers=headers).json()
        propias = client.get(
            f"{API}/producer/demands", params={"only_matching": True}, headers=headers
        ).json()

        assert todas["total"] == 1
        assert propias["total"] == 0

    def test_the_matching_filter_keeps_what_the_seller_can_satisfy(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        _create_demand(client, auth_headers, max_yield_factor="94.00")

        response = client.get(
            f"{API}/producer/demands",
            params={"only_matching": True},
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.json()["total"] == 1


class TestMakingAnOffer:
    def test_a_seller_answers_with_one_of_their_lots(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)

        status_code, body = _make_offer(
            client, producer_token, demand["id"], variant_with_minimum, kg=250, price="20500"
        )

        assert status_code == 201, body
        assert body["offered_kg"] == 250
        assert Decimal(body["price_per_kg"]) == Decimal("20500.00")
        assert Decimal(body["line_total"]) == Decimal("5125000.00")
        assert body["status"] == OfferStatus.PENDING.value

    def test_offering_more_kilos_than_available_is_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """El lote de prueba tiene 10 kg."""
        demand = _create_demand(client, auth_headers)

        status_code, body = _make_offer(
            client, producer_token, demand["id"], product_variant, kg=500
        )

        assert status_code == 422
        assert body["error"]["details"]["available_kg"] == 10

    def test_offering_below_the_lots_own_minimum_is_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)

        status_code, body = _make_offer(
            client, producer_token, demand["id"], variant_with_minimum, kg=50
        )

        assert status_code == 422
        assert body["error"]["details"]["min_qty_kg"] == 125

    def test_the_same_lot_cannot_be_offered_twice(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """Sin esto un vendedor inundaría la solicitud con la misma oferta."""
        demand = _create_demand(client, auth_headers)
        _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        status_code, _ = _make_offer(
            client, producer_token, demand["id"], variant_with_minimum, price="19000"
        )

        assert status_code == 409

    def test_offering_someone_elses_lot_is_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        second_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)

        status_code, _ = _make_offer(client, producer_token, demand["id"], second_variant)

        assert status_code == 404

    def test_an_unpublished_lot_cannot_back_an_offer(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """El comprador tiene que poder ver la ficha de lo que acepta."""
        from app.models.catalog import Product
        from app.models.enums import ProductStatus

        product = session.get(Product, variant_with_minimum.product_id)
        assert product is not None
        product.status = ProductStatus.DRAFT
        session.flush()

        demand = _create_demand(client, auth_headers)
        status_code, body = _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        assert status_code == 422
        assert "Publica el lote" in body["error"]["message"]

    def test_a_closed_demand_takes_no_offers(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)
        client.post(f"{API}/demands/{demand['id']}/close", headers=auth_headers)

        status_code, _ = _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        assert status_code == 422

    def test_a_seller_withdraws_a_pending_offer(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        response = client.post(
            f"{API}/producer/offers/{offer['id']}/withdraw",
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == OfferStatus.WITHDRAWN.value


class TestRespondingToAnOffer:
    def test_accepting_puts_the_agreed_kilos_in_the_cart_at_the_agreed_price(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """El precio del catálogo es 22.000; el acordado, 20.500. Lo que entra al
        carrito es el acordado."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(
            client, producer_token, demand["id"], variant_with_minimum, kg=250, price="20500"
        )

        response = client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        cart = client.get(f"{API}/cart", headers=auth_headers).json()
        item = cart["groups"][0]["items"][0]
        assert item["quantity"] == 250
        assert Decimal(item["unit_price"]) == Decimal("20500.00")
        assert Decimal(item["line_total"]) == Decimal("5125000.00")
        assert item["is_negotiated"] is True

    def test_the_negotiated_price_survives_a_catalogue_price_change(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """Lo acordado es lo acordado: que el vendedor suba su lista después no
        altera un trato cerrado, y tampoco dispara el aviso de «cambió el precio»."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(
            client, producer_token, demand["id"], variant_with_minimum, kg=250, price="20500"
        )
        client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        )

        variant_with_minimum.price = Decimal("30000")
        session.flush()

        item = client.get(f"{API}/cart", headers=auth_headers).json()["groups"][0]["items"][0]
        assert Decimal(item["unit_price"]) == Decimal("20500.00")
        assert item["price_changed"] is False

    def test_the_order_charges_the_negotiated_price(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """La comisión se calcula sobre el subtotal, así que un precio equivocado
        aquí se arrastraría hasta la liquidación del vendedor."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(
            client, producer_token, demand["id"], variant_with_minimum, kg=250, price="20500"
        )
        client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        )

        address = session.scalar(select(Address).where(Address.user_id == buyer.id))
        assert address is not None
        response = client.post(
            f"{API}/orders",
            json={"shipping_address_id": str(address.id), "accept_terms": True},
            headers=auth_headers,
        )

        assert response.status_code == 201, response.text
        order = session.scalar(select(Order))
        assert order is not None
        item = session.scalar(select(OrderItem))
        assert item is not None
        assert item.unit_price == Decimal("20500.00")
        assert item.line_total == Decimal("5125000.00")
        assert order.subtotal == Decimal("5125000.00")

    def test_accepting_part_of_what_was_wanted_leaves_the_demand_open(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """Quien busca 250 kg y consigue 125 sigue necesitando los otros 125: en
        pergamino lo normal es armar la carga con varios vendedores."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum, kg=125)

        body = client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        ).json()

        assert body["status"] == DemandStatus.PARTIALLY_COVERED.value
        assert body["covered_kg"] == 125
        assert body["remaining_kg"] == 125
        assert body["is_receiving"] is True

    def test_covering_everything_marks_it_fulfilled_and_closes_the_rest(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """Ya no falta café: lo pendiente se rechaza en vez de dejar a un
        caficultor esperando una respuesta que no va a llegar."""
        demand = _create_demand(client, auth_headers, wanted_kg=200)
        _, big = _make_offer(client, producer_token, demand["id"], variant_with_minimum, kg=250)
        _, small = _make_offer(
            client, producer_token, demand["id"], product_variant, kg=10, price="40000"
        )

        body = client.post(
            f"{API}/demands/offers/{big['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        ).json()

        assert body["status"] == DemandStatus.FULFILLED.value
        rejected = next(o for o in body["offers"] if o["id"] == small["id"])
        assert rejected["status"] == OfferStatus.REJECTED.value
        assert "se completó" in (rejected["response_note"] or "")

    def test_rejecting_records_the_reason(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        body = client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": False, "note": "El factor está por encima de lo que necesito."},
            headers=auth_headers,
        ).json()

        rejected = body["offers"][0]
        assert rejected["status"] == OfferStatus.REJECTED.value
        assert rejected["response_note"] == "El factor está por encima de lo que necesito."
        # Rechazar no cubre nada: la solicitud sigue buscando.
        assert body["covered_kg"] == 0
        assert body["status"] == DemandStatus.OPEN.value

    def test_a_blank_note_is_not_stored_as_an_explanation(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        body = client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": False, "note": "   "},
            headers=auth_headers,
        ).json()

        assert body["offers"][0]["response_note"] is None

    def test_responding_twice_is_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum)
        client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": False},
            headers=auth_headers,
        )

        second = client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        )

        assert second.status_code == 422

    def test_kilos_sold_between_the_offer_and_the_answer_block_the_acceptance(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """El inventario se vuelve a comprobar al aceptar: entre que el vendedor
        ofreció y el comprador respondió pudo vender ese café a otro."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum, kg=250)

        inventory = session.get(Inventory, variant_with_minimum.id)
        assert inventory is not None
        inventory.stock_qty = 100
        session.flush()

        response = client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        )

        assert response.status_code == 422
        assert response.json()["error"]["details"]["available_kg"] == 100


class TestIsolation:
    def test_nobody_answers_a_demand_that_is_not_theirs(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """La postura la responde el comprador de la solicitud, nadie más."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        response = client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 404

    def test_nobody_reads_a_demand_that_is_not_theirs(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        producer_token: str,
    ) -> None:
        """404 y no 403: distinguirlos revelaría que la solicitud existe."""
        demand = _create_demand(client, auth_headers)

        response = client.get(
            f"{API}/demands/{demand['id']}",
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        assert response.status_code == 404

    def test_a_seller_only_sees_their_own_offers(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
        buyer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)
        _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        mine = client.get(
            f"{API}/producer/offers", headers={"Authorization": f"Bearer {producer_token}"}
        )
        as_buyer = client.get(f"{API}/producer/offers", headers=auth_headers)

        assert mine.json()["total"] == 1
        assert as_buyer.status_code == 403


class TestEditingAndClosing:
    def test_the_buyer_extends_the_validity(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        demand = _create_demand(client, auth_headers)
        new_date = str(date.today() + timedelta(days=60))

        response = client.patch(
            f"{API}/demands/{demand['id']}",
            json={"expires_on": new_date},
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()["expires_on"] == new_date

    def test_the_wanted_kilos_are_not_editable(
        self, client: TestClient, session: Session, auth_headers: dict[str, str], buyer: User
    ) -> None:
        """Cambiarlos invalidaría las posturas que ya respondieron a otra cifra."""
        demand = _create_demand(client, auth_headers)

        client.patch(
            f"{API}/demands/{demand['id']}", json={"wanted_kg": 9999}, headers=auth_headers
        )

        refreshed = session.get(DemandRequest, uuid.UUID(demand["id"]))
        assert refreshed is not None
        assert refreshed.wanted_kg == 250

    def test_closing_rejects_what_was_pending(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        demand = _create_demand(client, auth_headers)
        _make_offer(client, producer_token, demand["id"], variant_with_minimum)

        body = client.post(f"{API}/demands/{demand['id']}/close", headers=auth_headers).json()

        assert body["status"] == DemandStatus.CANCELLED.value
        assert body["offers"][0]["status"] == OfferStatus.REJECTED.value
        assert body["is_receiving"] is False

    def test_closing_after_covering_part_of_it_is_a_close_not_a_cancellation(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """Una solicitud con compras hechas no se «cancela»: se cierra. Mezclarlo
        borraría del historial que hubo negocio."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum, kg=125)
        client.post(
            f"{API}/demands/offers/{offer['id']}/respond",
            json={"accept": True},
            headers=auth_headers,
        )

        body = client.post(f"{API}/demands/{demand['id']}/close", headers=auth_headers).json()

        assert body["status"] == DemandStatus.CLOSED.value

    def test_closing_twice_is_rejected(
        self, client: TestClient, auth_headers: dict[str, str], buyer: User
    ) -> None:
        demand = _create_demand(client, auth_headers)
        client.post(f"{API}/demands/{demand['id']}/close", headers=auth_headers)

        second = client.post(f"{API}/demands/{demand['id']}/close", headers=auth_headers)

        assert second.status_code == 422


class TestOfferOrdering:
    def test_pending_offers_come_first_and_cheapest_first(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        product_variant: ProductVariant,
        producer_token: str,
    ) -> None:
        """Es el orden en que un comprador quiere revisar: lo que puede decidir,
        y de eso lo más barato por kilo."""
        demand = _create_demand(client, auth_headers, wanted_kg=1000)
        _, expensive = _make_offer(
            client, producer_token, demand["id"], product_variant, kg=10, price="40000"
        )
        _, cheap = _make_offer(
            client, producer_token, demand["id"], variant_with_minimum, kg=125, price="19000"
        )

        body = client.get(f"{API}/demands/{demand['id']}", headers=auth_headers).json()

        assert [offer["id"] for offer in body["offers"]] == [cheap["id"], expensive["id"]]

    def test_withdrawn_offers_are_not_counted(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """Anunciar «3 posturas» y listar una sola resta credibilidad."""
        demand = _create_demand(client, auth_headers)
        _, offer = _make_offer(client, producer_token, demand["id"], variant_with_minimum)
        client.post(
            f"{API}/producer/offers/{offer['id']}/withdraw",
            headers={"Authorization": f"Bearer {producer_token}"},
        )

        body = client.get(f"{API}/demands/{demand['id']}", headers=auth_headers).json()

        assert body["offer_count"] == 0


class TestDatabaseGuards:
    def test_a_negotiated_price_without_its_offer_is_rejected(
        self, session: Session, buyer: User, product_variant: ProductVariant
    ) -> None:
        """Un precio distinto del de catálogo sin la postura que lo respalda
        sería arbitrario y sin rastro. Lo impide la base de datos."""
        from sqlalchemy.exc import IntegrityError

        from app.models.cart import Cart, CartItem

        cart = Cart(user_id=buyer.id)
        session.add(cart)
        session.flush()

        session.add(
            CartItem(
                cart_id=cart.id,
                variant_id=product_variant.id,
                quantity=5,
                unit_price_snapshot=Decimal("40000"),
                negotiated_price=Decimal("1"),
                demand_offer_id=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_the_same_seller_and_lot_cannot_repeat_on_one_demand(
        self,
        session: Session,
        client: TestClient,
        auth_headers: dict[str, str],
        buyer: User,
        variant_with_minimum: ProductVariant,
        producer_token: str,
    ) -> None:
        """La restricción vive en la base de datos, no solo en el servicio."""
        from sqlalchemy.exc import IntegrityError

        from app.models.producer import ProducerProfile

        demand = _create_demand(client, auth_headers)
        _make_offer(client, producer_token, demand["id"], variant_with_minimum)
        profile = session.scalar(select(ProducerProfile))
        assert profile is not None

        session.add(
            DemandOffer(
                demand_id=uuid.UUID(demand["id"]),
                producer_id=profile.id,
                product_id=variant_with_minimum.product_id,
                variant_id=variant_with_minimum.id,
                offered_kg=125,
                price_per_kg=Decimal("18000"),
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
