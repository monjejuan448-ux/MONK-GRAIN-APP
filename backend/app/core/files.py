"""Validación de los archivos que suben los vendedores.

Todo lo que llega en una petición lo controla quien la envía: la extensión del
nombre y la cabecera `Content-Type` son declaraciones, no hechos. Un `.jpg`
puede ser un ejecutable y un `image/png` puede ser un HTML con JavaScript.

Por eso aquí no se cree nada de lo que dice el cliente:

- El tipo se deduce de los **primeros bytes** del contenido.
- Las imágenes se **reescriben** con Pillow, lo que descarta cualquier carga
  incrustada en los metadatos y garantiza que el resultado es realmente una
  imagen.
- El nombre de almacenamiento lo genera el servidor; el del usuario nunca llega
  al disco, de modo que un `../../etc/passwd` no tiene dónde surtir efecto.
- El tamaño se comprueba mientras se lee, no después, para no cargar en memoria
  un archivo enorme antes de rechazarlo.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.exceptions import BusinessRuleError
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

# Lado máximo de una imagen almacenada. Una fotografía de móvil moderna supera
# de largo lo que necesita una ficha de producto.
MAX_IMAGE_DIMENSION = 2000

# Límite de píxeles antes de decodificar: frena las «bombas de descompresión»,
# archivos de pocos kilobytes que al abrirse ocupan gigabytes de memoria.
Image.MAX_IMAGE_PIXELS = 50_000_000

# Firmas de los formatos aceptados. Se comparan contra el contenido real.
_IMAGE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # se confirma más abajo con el marcador WEBP
)

_PDF_SIGNATURE = b"%PDF-"


@dataclass(frozen=True)
class StoredFile:
    """Archivo ya validado y listo para guardarse."""

    content: bytes
    content_type: str
    extension: str

    def key_for(self, prefix: str) -> str:
        """Ruta de almacenamiento con nombre generado por el servidor."""
        return f"{prefix}/{uuid.uuid4().hex}{self.extension}"


async def _read_within_limit(upload: UploadFile, limit: int) -> bytes:
    """Lee el archivo abortando en cuanto supera el límite."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(64 * 1024):
        total += len(chunk)
        if total > limit:
            raise BusinessRuleError(
                f"El archivo supera el máximo permitido de {limit // (1024 * 1024)} MB."
            )
        chunks.append(chunk)

    if total == 0:
        raise BusinessRuleError("El archivo está vacío.")
    return b"".join(chunks)


def _sniff_image_type(content: bytes) -> str | None:
    """Deduce el tipo de imagen a partir de sus primeros bytes."""
    for signature, media_type in _IMAGE_SIGNATURES:
        if not content.startswith(signature):
            continue
        # RIFF lo usan varios formatos; solo es WebP si lo declara en el byte 8.
        if media_type == "image/webp" and content[8:12] != b"WEBP":
            continue
        return media_type
    return None


async def validate_image(upload: UploadFile) -> StoredFile:
    """Valida y normaliza una imagen de producto.

    Devuelve siempre un JPEG reescrito por Pillow. Convertir en vez de conservar
    el original es deliberado: garantiza que el archivo guardado es una imagen y
    solo una imagen.
    """
    content = await _read_within_limit(upload, MAX_IMAGE_BYTES)

    if _sniff_image_type(content) is None:
        # El SVG cae aquí a propósito: admite JavaScript y no tiene cabida en la
        # fotografía de un café.
        raise BusinessRuleError("El archivo debe ser una imagen JPEG, PNG o WebP.")

    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        # `verify` deja el archivo inutilizable: hay que abrirlo otra vez.
        with Image.open(io.BytesIO(content)) as opened:
            normalized = opened.convert("RGB")
            normalized.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
            buffer = io.BytesIO()
            # `exif` se descarta al no copiarlo: la ubicación GPS de la cámara no
            # debe viajar con la foto de la finca.
            normalized.save(buffer, format="JPEG", quality=85, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("image_rejected", reason=str(exc))
        raise BusinessRuleError("No pudimos procesar la imagen. Prueba con otro archivo.") from exc

    return StoredFile(content=buffer.getvalue(), content_type="image/jpeg", extension=".jpg")


async def validate_document(upload: UploadFile) -> StoredFile:
    """Valida un certificado o documento.

    Se aceptan PDF e imagen. El PDF se guarda tal cual —reescribirlo invalidaría
    su firma digital, que es justo lo que da valor a un certificado—, así que se
    sirve siempre como descarga y nunca incrustado en la página.
    """
    content = await _read_within_limit(upload, MAX_DOCUMENT_BYTES)

    if content.startswith(_PDF_SIGNATURE):
        return StoredFile(content=content, content_type="application/pdf", extension=".pdf")

    if _sniff_image_type(content) is not None:
        upload.file.seek(0)
        return await validate_image(upload)

    raise BusinessRuleError("El documento debe ser un PDF o una imagen JPEG, PNG o WebP.")
