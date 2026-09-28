"""Calendario colombiano de días hábiles.

De estas funciones cuelgan todos los plazos del Estatuto del Consumidor. Un
error aquí no rompe nada visiblemente: simplemente le recorta días al comprador
para retractarse, o le regala días al vendedor para responder. Por eso las
fechas se contrastan contra el calendario oficial y no contra lo que devuelva la
implementación.
"""

from datetime import date

import pytest

from app.core.business_days import (
    add_business_days,
    business_days_between,
    holidays,
    is_business_day,
)

pytestmark = pytest.mark.unit


# Festivos oficiales publicados para cada año. 2025 tiene diecisiete y no
# dieciocho porque San Pedro y el Sagrado Corazón coinciden el mismo lunes.
EXPECTED_2025 = {
    date(2025, 1, 1),
    date(2025, 1, 6),
    date(2025, 3, 24),
    date(2025, 4, 17),
    date(2025, 4, 18),
    date(2025, 5, 1),
    date(2025, 6, 2),
    date(2025, 6, 23),
    date(2025, 6, 30),
    date(2025, 7, 20),
    date(2025, 8, 7),
    date(2025, 8, 18),
    date(2025, 10, 13),
    date(2025, 11, 3),
    date(2025, 11, 17),
    date(2025, 12, 8),
    date(2025, 12, 25),
}

EXPECTED_2026 = {
    date(2026, 1, 1),
    date(2026, 1, 12),
    date(2026, 3, 23),
    date(2026, 4, 2),
    date(2026, 4, 3),
    date(2026, 5, 1),
    date(2026, 5, 18),
    date(2026, 6, 8),
    date(2026, 6, 15),
    date(2026, 6, 29),
    date(2026, 7, 20),
    date(2026, 8, 7),
    date(2026, 8, 17),
    date(2026, 10, 12),
    date(2026, 11, 2),
    date(2026, 11, 16),
    date(2026, 12, 8),
    date(2026, 12, 25),
}


@pytest.mark.parametrize(("year", "expected"), [(2025, EXPECTED_2025), (2026, EXPECTED_2026)])
def test_holidays_match_the_official_calendar(year: int, expected: set[date]) -> None:
    assert holidays(year) == expected


def test_moved_holidays_land_on_monday() -> None:
    """La Ley 51 de 1983 traslada al lunes siguiente los festivos que no caen en lunes."""
    # El 6 de enero de 2026 es martes: el festivo se celebra el lunes 12.
    assert date(2026, 1, 6) not in holidays(2026)
    assert date(2026, 1, 12) in holidays(2026)
    assert date(2026, 1, 12).weekday() == 0

    # El 29 de junio de 2026 ya es lunes: se queda donde está.
    assert date(2026, 6, 29) in holidays(2026)


def test_holy_thursday_and_friday_are_not_moved() -> None:
    """Jueves y Viernes Santo se celebran en su fecha, no el lunes siguiente."""
    assert date(2026, 4, 2) in holidays(2026)  # jueves
    assert date(2026, 4, 3) in holidays(2026)  # viernes


def test_weekends_and_holidays_are_not_business_days() -> None:
    assert not is_business_day(date(2026, 8, 15))  # sábado
    assert not is_business_day(date(2026, 8, 16))  # domingo
    assert not is_business_day(date(2026, 8, 17))  # festivo trasladado
    assert is_business_day(date(2026, 8, 18))  # martes hábil


def test_five_business_days_skip_weekend_and_holiday() -> None:
    """Retracto: entrega el viernes 14 de agosto de 2026.

    El lunes 17 es festivo (Asunción trasladada), así que los cinco días hábiles
    caen martes, miércoles, jueves, viernes y lunes 24. Contar días corridos
    habría vencido el plazo el 19 y le habría quitado cinco días al comprador.
    """
    assert add_business_days(date(2026, 8, 14), 5) == date(2026, 8, 24)


def test_deadline_crossing_the_new_year() -> None:
    """Entrega en Nochebuena: el plazo salta Navidad, dos fines de semana y Año Nuevo."""
    assert add_business_days(date(2026, 12, 24), 5) == date(2027, 1, 4)


def test_fifteen_business_days_for_the_written_answer() -> None:
    """Decreto 735 de 2013: quince días hábiles para responder la reclamación.

    Radicada el viernes 14 de agosto de 2026, con el lunes 17 festivo, el
    decimoquinto día hábil es el lunes 7 de septiembre.
    """
    assert add_business_days(date(2026, 8, 14), 15) == date(2026, 9, 7)


def test_adding_zero_days_leaves_the_date_untouched() -> None:
    """Un plazo que no ha empezado a correr no mueve la fecha, ni siquiera en domingo."""
    assert add_business_days(date(2026, 8, 16), 0) == date(2026, 8, 16)


def test_negative_terms_are_rejected() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        add_business_days(date(2026, 8, 16), -1)


def test_counting_is_the_inverse_of_adding() -> None:
    start = date(2026, 8, 14)
    for days in range(0, 40):
        assert business_days_between(start, add_business_days(start, days)) == days


def test_counting_backwards_gives_a_negative_number() -> None:
    """El signo indica por sí solo si el plazo ya venció."""
    assert business_days_between(date(2026, 8, 24), date(2026, 8, 14)) == -5
