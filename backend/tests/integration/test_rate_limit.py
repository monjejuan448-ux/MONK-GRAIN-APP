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
from app.core.rate_limit import client_identifier, is_internal_caller
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

    def test_rotating_the_client_identity_does_not_buy_more_login_attempts(
        self, client: TestClient
    ) -> None:
        """El agujero que esta prueba cierra.

        Antes, `client_identifier` tomaba el **primer** elemento de
        `X-Forwarded-For` —que lo escribe quien hace la petición—, de modo que
        cambiarlo en cada intento estrenaba cupo: doce intentos seguidos de
        inicio de sesión devolvían 401 y ninguno 429. El tope por cuenta pone
        techo al ensayo de contraseñas aunque el atacante se reparta entre
        direcciones, porque no mira ninguna cabecera.
        """
        objetivo = {"email": "victima@ejemplo.co", "password": "ContrasenaCualquiera1"}
        tope = settings.rate_limit_login_per_account_per_minute

        # Cada intento se presenta como un cliente distinto, así que el límite
        # por cliente no llega a dispararse nunca.
        for intento in range(tope):
            respuesta = client.post(
                f"{API}/auth/login",
                json=objetivo,
                headers={"X-Real-IP": f"181.49.20.{intento}"},
            )
            assert respuesta.status_code != 429, f"el intento {intento} no debía estar limitado"

        bloqueado = client.post(
            f"{API}/auth/login",
            json=objetivo,
            headers={"X-Real-IP": "181.49.20.200"},
        )

        assert bloqueado.status_code == 429

    def test_the_account_ceiling_does_not_block_other_accounts(self, client: TestClient) -> None:
        """Agotar el cupo de una cuenta no debe dejar fuera a las demás: si no,
        bastaría con ensayar contra el correo de alguien para impedirle entrar."""
        for intento in range(settings.rate_limit_login_per_account_per_minute + 1):
            client.post(
                f"{API}/auth/login",
                json={"email": "victima@ejemplo.co", "password": "ContrasenaCualquiera1"},
                headers={"X-Real-IP": f"181.49.20.{intento}"},
            )

        otra = client.post(
            f"{API}/auth/login",
            json={"email": "ajena@ejemplo.co", "password": "ContrasenaCualquiera1"},
            headers={"X-Real-IP": "200.1.2.3"},
        )

        assert otra.status_code != 429


class TestClientIdentity:
    """A quién se le cuenta cada petición.

    Es la decisión de la que dependía el agujero: Nginx compone
    `X-Forwarded-For` con `$proxy_add_x_forwarded_for`, que **añade** la
    dirección real al final de lo que mandó el cliente. Leer el primer elemento
    era leer un dato que escribe el atacante.
    """

    @staticmethod
    def _request(host: str | None, **headers: str) -> Request:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [
                (nombre.lower().replace("_", "-").encode(), valor.encode())
                for nombre, valor in headers.items()
            ],
            "client": (host, 12345) if host else None,
            "query_string": b"",
        }
        return Request(scope)

    def test_the_last_hop_wins_because_that_is_the_one_nginx_added(self) -> None:
        """Lo que el cliente inventa queda delante; lo que puso el proxy, detrás."""
        peticion = self._request("172.18.0.2", x_forwarded_for="1.2.3.4, 181.49.20.10")

        assert client_identifier(peticion) == "181.49.20.10"

    def test_spoofing_the_first_hop_does_not_change_the_identity(self) -> None:
        """Dos peticiones del mismo cliente real cuentan en el mismo cupo, por
        mucho que la cabecera diga otra cosa en cada una."""
        primera = self._request("172.18.0.2", x_forwarded_for="9.9.9.9, 181.49.20.10")
        segunda = self._request("172.18.0.2", x_forwarded_for="8.8.8.8, 181.49.20.10")

        assert client_identifier(primera) == client_identifier(segunda) == "181.49.20.10"

    def test_x_real_ip_wins_over_the_forwarded_chain(self) -> None:
        """Nginx la **sobreescribe** en cada petición, así que es la más fiable
        de las dos."""
        peticion = self._request(
            "172.18.0.2", x_real_ip="181.49.20.10", x_forwarded_for="1.2.3.4, 5.6.7.8"
        )

        assert client_identifier(peticion) == "181.49.20.10"

    def test_the_headers_are_ignored_when_the_peer_is_not_our_proxy(self) -> None:
        """Si la conexión no viene de nuestra red, nadie garantiza esas
        cabeceras: se cuenta la dirección real y se descarta el relato."""
        peticion = self._request("181.49.20.10", x_real_ip="10.0.0.1", x_forwarded_for="10.0.0.1")

        assert client_identifier(peticion) == "181.49.20.10"

    def test_without_any_proxy_header_the_peer_is_the_identity(self) -> None:
        assert client_identifier(self._request("172.18.0.7")) == "172.18.0.7"

    def test_an_empty_forwarded_header_falls_back_to_the_peer(self) -> None:
        """Una cabecera presente pero vacía no debe producir un identificador
        vacío, que metería a clientes distintos en el mismo cupo."""
        assert client_identifier(self._request("172.18.0.2", x_forwarded_for=" , ")) == "172.18.0.2"


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
