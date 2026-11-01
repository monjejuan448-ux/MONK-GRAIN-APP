"""Integridad del catálogo de la división político-administrativa.

`addresses.municipality_id` es obligatorio y apunta a este catálogo, así que un
municipio que falte no es un hueco en una tabla de referencia: es alguien que no
puede registrar una dirección y por tanto no puede terminar una compra. El
catálogo estuvo recortado a los 54 municipios cafeteros y eso dejaba fuera a
Bogotá, Cali, Barranquilla y Cartagena —donde están las trilladoras y los
puertos, es decir, quien compra el pergamino—.

Son comprobaciones sobre el archivo de datos, no sobre la base: lo que se
protege es que nadie vuelva a recortarlo ni lo corrompa al regenerarlo.
"""

import pytest

from app.db.divipola import DEPARTMENTS, MUNICIPALITIES

pytestmark = pytest.mark.unit


class TestCobertura:
    def test_estan_los_33_departamentos(self) -> None:
        """32 departamentos más Bogotá D.C., que el DANE cuenta aparte."""
        assert len(DEPARTMENTS) == 33

    def test_el_pais_entero_y_no_solo_la_zona_cafetera(self) -> None:
        # Antes eran 54. El recorte es justo el defecto que esto vigila.
        assert len(MUNICIPALITIES) > 1100

    @pytest.mark.parametrize(
        ("dane_code", "nombre"),
        [
            ("11001", "Bogotá"),
            ("76001", "Cali"),
            ("08001", "Barranquilla"),
            ("13001", "Cartagena"),
            ("05001", "Medellín"),
            ("68001", "Bucaramanga"),
            ("47001", "Santa Marta"),
            ("13430", "Magangué"),
        ],
    )
    def test_las_ciudades_donde_esta_quien_compra(self, dane_code: str, nombre: str) -> None:
        """Las cuatro primeras faltaban y bloqueaban la compra."""
        encontrado = next((m for m in MUNICIPALITIES if m[1] == dane_code), None)

        assert encontrado is not None, f"falta {nombre} ({dane_code})"
        assert nombre in encontrado[2]

    def test_siguen_estando_los_municipios_cafeteros(self) -> None:
        """La ampliación no debía perder lo que ya había."""
        codigos = {m[1] for m in MUNICIPALITIES}

        # Pitalito, Acevedo, San Agustín e Isnos (Huila); Sandoná (Nariño).
        assert {"41551", "41006", "41668", "41359", "52683"} <= codigos


class TestIntegridad:
    def test_no_hay_codigos_repetidos(self) -> None:
        codigos = [m[1] for m in MUNICIPALITIES]

        assert len(codigos) == len(set(codigos))

    def test_cada_municipio_pertenece_a_un_departamento_declarado(self) -> None:
        declarados = {d[0] for d in DEPARTMENTS}
        huerfanos = {m[0] for m in MUNICIPALITIES} - declarados

        assert huerfanos == set()

    def test_el_codigo_del_municipio_empieza_por_el_de_su_departamento(self) -> None:
        """Es la regla del DANE: dos dígitos de departamento y tres de
        municipio. Si alguna fila no la cumple, el catálogo se desalineó al
        regenerarlo."""
        descuadrados = [m for m in MUNICIPALITIES if not m[1].startswith(m[0])]

        assert descuadrados == []

    def test_los_codigos_tienen_la_longitud_que_exige_el_dane(self) -> None:
        assert all(len(d[0]) == 2 for d in DEPARTMENTS)
        assert all(len(m[1]) == 5 for m in MUNICIPALITIES)

    def test_ningun_nombre_llega_en_mayusculas(self) -> None:
        """El DANE los publica en mayúsculas; el catálogo los guarda en
        capitalización española, que es como se muestran al usuario."""
        gritando = [m[2] for m in MUNICIPALITIES if m[2].isupper()]

        assert gritando == []

    def test_las_coordenadas_caen_dentro_de_colombia(self) -> None:
        """Una latitud y una longitud invertidas pasarían desapercibidas hasta
        que un mapa pusiera una finca en mitad del océano."""
        fuera = [
            (m[1], m[2], m[3], m[4])
            for m in MUNICIPALITIES
            if not (-4.5 <= m[3] <= 13.5 and -82.0 <= m[4] <= -66.0)
        ]

        assert fuera == []
