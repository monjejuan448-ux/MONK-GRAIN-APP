"""Días hábiles según el calendario colombiano.

El Estatuto del Consumidor cuenta en **días hábiles** casi todos sus plazos: los
cinco del retracto (artículo 47), los cinco para presentar la queja de reversión
del pago (artículo 51) y los quince para responder una reclamación de garantía
(Decreto 735 de 2013). Contar «cinco días» a secas acorta el plazo del comprador
cada vez que cae un festivo, y un derecho del consumidor es irrenunciable: no se
puede recortar por comodidad de implementación.

Los festivos no se guardan en una tabla que alguien tendría que mantener año a
año. Se calculan: la Ley 51 de 1983 fija cuáles se trasladan al lunes siguiente
y los de Semana Santa se derivan de la Pascua, que es determinista.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

# Festivos de fecha fija que se celebran el día que caen.
_FIXED_HOLIDAYS: tuple[tuple[int, int], ...] = (
    (1, 1),  # Año Nuevo
    (5, 1),  # Día del Trabajo
    (7, 20),  # Independencia
    (8, 7),  # Batalla de Boyacá
    (12, 8),  # Inmaculada Concepción
    (12, 25),  # Navidad
)

# Festivos que la Ley 51 de 1983 traslada al lunes siguiente cuando no caen en
# lunes. Es la llamada «ley Emiliani».
_MOVED_HOLIDAYS: tuple[tuple[int, int], ...] = (
    (1, 6),  # Reyes Magos
    (3, 19),  # San José
    (6, 29),  # San Pedro y San Pablo
    (8, 15),  # Asunción de la Virgen
    (10, 12),  # Día de la Raza
    (11, 1),  # Todos los Santos
    (11, 11),  # Independencia de Cartagena
)

# Días de desplazamiento respecto del Domingo de Pascua. Jueves y Viernes Santo
# se celebran en su fecha; los tres restantes ya vienen trasladados al lunes.
_EASTER_OFFSETS: tuple[int, ...] = (
    -3,  # Jueves Santo
    -2,  # Viernes Santo
    43,  # Ascensión del Señor
    64,  # Corpus Christi
    71,  # Sagrado Corazón de Jesús
)


def _easter_sunday(year: int) -> date:
    """Domingo de Pascua por el algoritmo gregoriano anónimo (Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lunar = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lunar) // 451
    month, day = divmod(h + lunar - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _next_monday(day: date) -> date:
    """Traslada al lunes siguiente. Un lunes se queda donde está."""
    return day + timedelta(days=(7 - day.weekday()) % 7)


@lru_cache(maxsize=32)
def holidays(year: int) -> frozenset[date]:
    """Festivos nacionales de un año. Son dieciocho en Colombia."""
    easter = _easter_sunday(year)
    return frozenset(
        [date(year, month, day) for month, day in _FIXED_HOLIDAYS]
        + [_next_monday(date(year, month, day)) for month, day in _MOVED_HOLIDAYS]
        + [easter + timedelta(days=offset) for offset in _EASTER_OFFSETS]
    )


def is_business_day(day: date) -> bool:
    """Un día hábil no es sábado, ni domingo, ni festivo nacional."""
    return day.weekday() < 5 and day not in holidays(day.year)


def add_business_days(start: date, days: int) -> date:
    """Fecha resultante de sumar `days` días hábiles a `start`.

    El día de partida no cuenta: los plazos legales corren «a partir del día
    siguiente». Sumar cero devuelve la misma fecha, aunque sea inhábil, porque
    todavía no ha empezado a correr nada.
    """
    if days < 0:
        raise ValueError("El plazo en días hábiles no puede ser negativo.")

    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if is_business_day(current):
            remaining -= 1
    return current


def business_days_between(start: date, end: date) -> int:
    """Días hábiles transcurridos entre dos fechas, sin contar la de inicio.

    Devuelve un número negativo si `end` es anterior a `start`, de modo que el
    signo indique por sí solo si un plazo ya venció.
    """
    if end < start:
        return -business_days_between(end, start)

    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if is_business_day(current):
            count += 1
    return count
