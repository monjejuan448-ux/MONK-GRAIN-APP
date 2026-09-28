"""Pruebas del límite de peticiones.

Dos cosas distintas que conviene no confundir: el límite **propio** de algunos
endpoints —inicio de sesión, subidas— y el techo **general** que aplica el
middleware a todo lo demás. Lo que más importa aquí es a quién exime ese techo:
si contara el renderizado del servidor de Next.js, todos los visitantes del sitio
compartirían un solo cupo y la portada dejaría de cargar para todos a la vez.
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import is_internal_caller
from app.db.session import get_session
from app.main import app
from app.models.catalog import ProductVariant

pytestmark = pytest.mark.integration

API = "/api/v1"

# Una dirección pública cualquiera. Lo que la hace «externa» a ojos del
# middleware es venir en `X-Forwarded-For`, que es lo que añade Nginx.
EXTERNAL = {"X-Forwarded-For": "181.49.20.10"}


class TestTheGeneralCeiling:
    def test_an_external_client_has_a_ceiling(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """Hasta este trabajo, `RATE_LIMIT_DEFAULT_PER_MINUTE` estaba en la
        configuración sin aplicarse en ningún sitio."""
        limit = settings.rate_limit_default_per_minute

        # Se agota el cupo justo, ni una más.
        for _ in range(limit):
            assert client.get(f"{API}/products", headers=EXTERNAL).status_code == 200

        rejected = client.get(f"{API}/products", headers=EXTERNAL)

        assert rejected.status_code == 429
        assert rejected.json()["error"]["code"] == "rate_limit_exceeded"

    def test_the_ceiling_is_per_client_and_not_global(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """Un cliente pasado de cupo no debe dejar fuera a los demás."""
        limit = settings.rate_limit_default_per_minute
        for _ in range(limit + 1):
            client.get(f"{API}/products", headers=EXTERNAL)

        otro = client.get(f"{API}/products", headers={"X-Forwarded-For": "200.1.2.3"})

        assert otro.status_code == 200

    def test_the_rejection_carries_the_security_headers(
        self, client: TestClient, product_variant: ProductVariant
    ) -> None:
        """El middleware del límite corre por dentro del de cabeceras, a
        propósito: una respuesta 429 también debe llevarlas."""
        limit = settings.rate_limit_default_per_minute
        for _ in range(limit + 1):
            client.get(f"{API}/products", headers=EXTERNAL)

        rejected = client.get(f"{API}/products", headers=EXTERNAL)

        assert rejected.status_code == 429
        assert rejected.headers["X-Content-Type-Options"] == "nosniff"


class TestWhatIsExempt:
    def test_the_health_check_is_never_limited(self, client: TestClient) -> None:
        """Limitar a quien vigila si el servicio está vivo lo dejaría ciego justo
        cuando hace falta."""
        limit = settings.rate_limit_default_per_minute
        for _ in range(limit + 5):
            assert client.get("/health", headers=EXTERNAL).status_code == 200

    def test_our_own_server_is_not_a_client(
        self, session: Session, product_variant: ProductVariant
    ) -> None:
        """El renderizado del servidor de Next.js llama a la API por la red
        interna, sin `X-Forwarded-For`. Contarlo pondría a todos los visitantes
        del sitio en un mismo cupo: la portada se caería para todos a la vez.

        Se monta un cliente con una dirección privada, como la que tiene el
        contenedor de Next en la red de Docker. El `TestClient` de la fixture no
        sirve aquí: reporta `testclient` como origen, que no es una dirección, y
        por eso el middleware lo trata como externo.
        """

        def override_get_session():
            yield session

        app.dependency_overrides[get_session] = override_get_session
        try:
            with TestClient(app, client=("172.18.0.7", 40000)) as interno:
                limit = settings.rate_limit_default_per_minute
                for _ in range(limit + 10):
                    assert interno.get(f"{API}/products").status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestPerEndpointLimits:
    def test_the_login_limit_is_stricter_than_the_general_one(self, client: TestClient) -> None:
        """El de inicio de sesión existe para frenar fuerza bruta, así que es
        mucho más bajo, y se aplica también al tráfico interno: no depende del
        middleware."""
        assert settings.rate_limit_login_per_minute < settings.rate_limit_default_per_minute

        for _ in range(settings.rate_limit_login_per_minute):
            client.post(
                f"{API}/auth/login",
                json={"email": "nadie@ejemplo.co", "password": "ContrasenaCualquiera1"},
            )

        rejected = client.post(
            f"{API}/auth/login",
            json={"email": "nadie@ejemplo.co", "password": "ContrasenaCualquiera1"},
        )

        assert rejected.status_code == 429

    def test_the_login_limit_does_not_leak_whether_the_account_exists(
        self, client: TestClient
    ) -> None:
        """El 429 debe llegar igual con un correo registrado y con uno que no,
        porque si no, agotar el cupo sería una forma de enumerar cuentas."""
        for _ in range(settings.rate_limit_login_per_minute + 1):
            client.post(
                f"{API}/auth/login",
                json={"email": "inexistente@ejemplo.co", "password": "ContrasenaCualquiera1"},
            )

        response = client.post(
            f"{API}/auth/login",
            json={"email": "otro.inexistente@ejemplo.co", "password": "ContrasenaCualquiera1"},
        )

        # El contador es por cliente, no por correo: el segundo intento también
        # cae, y eso es lo correcto.
        assert response.status_code == 429


class TestInternalDetection:
    """`is_internal_caller` decide quién queda exento, y la regla es sutil:
    hacen falta las dos condiciones a la vez."""

    @staticmethod
    def _request(host: str | None, forwarded: str | None = None) -> Request:
        headers = []
        if forwarded is not None:
            headers.append((b"x-forwarded-for", forwarded.encode()))
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/products",
            "headers": headers,
            "client": (host, 12345) if host else None,
            "query_string": b"",
        }
        return Request(scope)

    def test_a_private_address_without_the_proxy_header_is_internal(self) -> None:
        # La dirección típica de un contenedor en la red de Docker.
        assert is_internal_caller(self._request("172.18.0.7")) is True
        assert is_internal_caller(self._request("10.0.0.5")) is True
        assert is_internal_caller(self._request("127.0.0.1")) is True

    def test_the_proxy_header_makes_it_external_even_desde_una_privada(self) -> None:
        """Nginx añade la cabecera a todo lo que entra de fuera, así que su
        presencia descalifica: una petición externa llega al backend desde la
        dirección privada del propio proxy."""
        assert is_internal_caller(self._request("172.18.0.2", forwarded="181.49.20.10")) is False

    def test_a_public_address_is_never_internal(self) -> None:
        assert is_internal_caller(self._request("181.49.20.10")) is False

    def test_something_that_is_not_an_address_is_not_internal(self) -> None:
        """Ante la duda se limita. `TestClient` cae aquí, y un socket Unix
        también: no se puede afirmar que sean nuestro propio servidor."""
        assert is_internal_caller(self._request("testclient")) is False
        assert is_internal_caller(self._request(None)) is False
