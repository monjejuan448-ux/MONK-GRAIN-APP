"""Pruebas de la validación de archivos subidos.

Es la primera superficie del sistema que recibe contenido de terceros, así que
las pruebas se escriben desde la perspectiva de quien intenta colar algo: un
script disfrazado de imagen, un nombre con rutas relativas, un archivo enorme.
"""

import io

import pytest
from fastapi import UploadFile
from PIL import Image

from app.core.exceptions import BusinessRuleError
from app.core.files import (
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    validate_document,
    validate_image,
)

pytestmark = pytest.mark.unit


def _upload(
    content: bytes, filename: str = "foto.jpg", content_type: str = "image/jpeg"
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers={"content-type": content_type},  # type: ignore[arg-type]
    )


def _jpeg(width: int = 800, height: int = 600, color: str = "brown") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png(width: int = 400, height: int = 300) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "green").save(buffer, format="PNG")
    return buffer.getvalue()


class TestImageValidation:
    async def test_accepts_a_real_jpeg(self) -> None:
        stored = await validate_image(_upload(_jpeg()))

        assert stored.content_type == "image/jpeg"
        assert stored.extension == ".jpg"
        assert stored.content.startswith(b"\xff\xd8\xff")

    async def test_converts_png_to_jpeg(self) -> None:
        """Todo se normaliza a JPEG: el formato de salida no lo elige quien sube."""
        stored = await validate_image(
            _upload(_png(), filename="logo.png", content_type="image/png")
        )

        assert stored.content_type == "image/jpeg"
        assert Image.open(io.BytesIO(stored.content)).format == "JPEG"

    async def test_rejects_a_script_renamed_as_image(self) -> None:
        """Extensión y `Content-Type` los controla el atacante; el contenido no."""
        payload = b"<?php system($_GET['cmd']); ?>"

        with pytest.raises(BusinessRuleError, match="imagen"):
            await validate_image(_upload(payload, filename="inocente.jpg"))

    async def test_rejects_svg_because_it_can_run_scripts(self) -> None:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

        with pytest.raises(BusinessRuleError):
            await validate_image(_upload(svg, filename="vector.svg", content_type="image/svg+xml"))

    async def test_rejects_html_disguised_with_an_image_content_type(self) -> None:
        html = b"<html><body><script>document.cookie</script></body></html>"

        with pytest.raises(BusinessRuleError):
            await validate_image(_upload(html, filename="x.png", content_type="image/png"))

    async def test_rejects_a_file_over_the_size_limit(self) -> None:
        oversized = b"\xff\xd8\xff" + b"\x00" * (MAX_IMAGE_BYTES + 1)

        with pytest.raises(BusinessRuleError, match="MB"):
            await validate_image(_upload(oversized))

    async def test_rejects_an_empty_file(self) -> None:
        with pytest.raises(BusinessRuleError, match="vacío"):
            await validate_image(_upload(b""))

    async def test_shrinks_oversized_images(self) -> None:
        """Una foto de móvil se reduce a lo que necesita una ficha."""
        stored = await validate_image(_upload(_jpeg(width=4000, height=3000)))

        with Image.open(io.BytesIO(stored.content)) as result:
            assert max(result.size) <= MAX_IMAGE_DIMENSION

    async def test_strips_exif_metadata(self) -> None:
        """La ubicación GPS de la cámara no debe viajar con la foto de la finca.

        Se reencodifica la imagen, así que los metadatos del original no llegan
        al archivo almacenado (HU-PRO-03; no exponer datos sensibles del
        productor).
        """
        buffer = io.BytesIO()
        image = Image.new("RGB", (500, 500), "brown")
        exif = image.getexif()
        exif[0x9286] = "coordenadas reservadas"  # UserComment
        image.save(buffer, format="JPEG", exif=exif)

        stored = await validate_image(_upload(buffer.getvalue()))

        with Image.open(io.BytesIO(stored.content)) as result:
            assert dict(result.getexif()) == {}


class TestStorageKeys:
    async def test_key_ignores_the_name_sent_by_the_client(self) -> None:
        """Un nombre con rutas relativas no puede escapar del prefijo."""
        stored = await validate_image(_upload(_jpeg(), filename="../../../etc/passwd.jpg"))

        key = stored.key_for("products/abc")

        assert key.startswith("products/abc/")
        assert ".." not in key
        assert key.endswith(".jpg")

    async def test_two_uploads_never_collide(self) -> None:
        stored = await validate_image(_upload(_jpeg()))

        assert stored.key_for("products/abc") != stored.key_for("products/abc")


class TestDocumentValidation:
    async def test_accepts_a_pdf(self) -> None:
        pdf = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF"

        stored = await validate_document(
            _upload(pdf, filename="certificado.pdf", content_type="application/pdf")
        )

        assert stored.content_type == "application/pdf"
        assert stored.extension == ".pdf"
        # El PDF se guarda intacto: reescribirlo invalidaría su firma digital.
        assert stored.content == pdf

    async def test_accepts_a_scanned_certificate_as_image(self) -> None:
        stored = await validate_document(_upload(_jpeg(), filename="escaneo.jpg"))

        assert stored.content_type == "image/jpeg"

    async def test_rejects_an_executable_named_as_pdf(self) -> None:
        elf = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 64

        with pytest.raises(BusinessRuleError, match="PDF"):
            await validate_document(
                _upload(elf, filename="certificado.pdf", content_type="application/pdf")
            )
