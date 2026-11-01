"""Cifrado simétrico de los datos que no deben leerse desde la base.

Hoy solo lo usa la cuenta bancaria del vendedor. La columna
`producer_profiles.bank_account_encrypted` existía desde el primer esquema y los
textos legales prometían el cifrado, pero no había con qué cifrar: la columna
nunca se escribía y el proyecto no tenía ninguna librería de criptografía. La
promesa se retiró de los documentos y vuelve ahora que es cierta.

Se usa **Fernet** y no AES a mano porque trae autenticación incluida: un valor
manipulado en la base falla al descifrar en vez de devolver basura que el
programa tomaría por buena.
"""

import base64
import json
from functools import lru_cache
from typing import Any

# `cryptography` no publica stubs de tipos, de ahí el `ignore` puntual. Se
# acota a estas tres líneas en lugar de silenciar el módulo entero.
from cryptography.fernet import Fernet, InvalidToken  # type: ignore[import-not-found]
from cryptography.hazmat.primitives import hashes  # type: ignore[import-not-found]
from cryptography.hazmat.primitives.kdf.hkdf import HKDF  # type: ignore[import-not-found]

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DecryptionError(RuntimeError):
    """El valor guardado no se pudo descifrar con la clave actual."""


@lru_cache
def _fernet() -> Fernet:
    """Construye el cifrador a partir de la clave configurada.

    Con `ENCRYPTION_KEY` definida se usa esa. Sin ella, se **deriva** de
    `SECRET_KEY` por HKDF, de modo que el entorno de desarrollo funciona sin
    configurar nada más.

    La derivación tiene una trampa que conviene conocer: `SECRET_KEY` se rota
    como cosa normal —es la que firma los tokens—, y al rotarla los datos ya
    cifrados dejan de poder leerse. Por eso en producción debe definirse
    `ENCRYPTION_KEY` aparte, y por eso se avisa al arrancar cuando no está.
    """
    if settings.encryption_key:
        return Fernet(settings.encryption_key.encode())

    logger.warning(
        "encryption_key_derived_from_secret_key",
        detail=(
            "ENCRYPTION_KEY no está definida y la clave de cifrado se derivó de "
            "SECRET_KEY. Rotar SECRET_KEY haría ilegibles los datos ya cifrados. "
            "Define ENCRYPTION_KEY antes de guardar datos reales."
        ),
    )
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        # Separa este uso de cualquier otro que llegue a derivar de la misma
        # clave: dos propósitos distintos no deben compartir material.
        info=b"monkgrain.field-encryption.v1",
    ).derive(settings.secret_key.encode())
    return Fernet(base64.urlsafe_b64encode(derived))


def generate_key() -> str:
    """Clave nueva, para poner en `ENCRYPTION_KEY`."""
    return str(Fernet.generate_key().decode())


def encrypt_json(payload: dict[str, Any]) -> bytes:
    """Cifra un diccionario para guardarlo en una columna binaria."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return bytes(_fernet().encrypt(raw))


def decrypt_json(blob: bytes) -> dict[str, Any]:
    """Recupera lo cifrado por `encrypt_json`.

    Un `InvalidToken` casi siempre significa que la clave cambió —o que se
    derivó de un `SECRET_KEY` distinto—, no que el dato esté corrupto. Se
    distingue con una excepción propia para que quien llame pueda decirlo con
    esas palabras en vez de devolver un error genérico.
    """
    try:
        decoded: dict[str, Any] = json.loads(_fernet().decrypt(blob).decode("utf-8"))
        return decoded
    except InvalidToken as exc:
        logger.error("decryption_failed", reason="invalid_token")
        raise DecryptionError(
            "No pudimos descifrar el dato guardado. Suele ocurrir cuando la clave "
            "de cifrado cambió después de haberlo guardado."
        ) from exc
