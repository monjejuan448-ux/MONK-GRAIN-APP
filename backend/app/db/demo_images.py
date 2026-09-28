"""Genera y sube las imágenes de muestra del catálogo de demostración.

Las fotografías reales las aporta cada vendedor al publicar su café. Este script
solo cubre el entorno de demostración, donde no hay vendedores reales subiendo
archivos: sin él, todas las fichas se muestran con el marcador de «sin
fotografía» y no se llega a ejercitar el camino en que la imagen sí existe.

Las imágenes son **sintéticas** —un degradado con el nombre del café— y no
pretenden pasar por fotografías. Su función es que la demostración muestre el
catálogo con y sin imagen, no simular contenido real.

Uso:
    docker compose exec backend python -m app.db.demo_images
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.integrations.storage.s3 import S3Storage
from app.models.catalog import Product, ProductImage

logger = get_logger(__name__)

WIDTH, HEIGHT = 1200, 900

# Tonos de la paleta de marca, del tueste claro al oscuro.
GRADIENTS: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((0x6F, 0x4E, 0x37), (0x3B, 0x24, 0x17)),
    ((0xC7, 0x9A, 0x55), (0x6F, 0x4E, 0x37)),
    ((0x1F, 0x4D, 0x3A), (0x3B, 0x24, 0x17)),
    ((0x7A, 0x9B, 0x76), (0x1F, 0x4D, 0x3A)),
]


def _vertical_gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        draw.line(
            [(0, y), (WIDTH, y)],
            fill=tuple(round(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)),
        )
    return image


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Carga una tipografía del sistema; si no hay ninguna, usa la de PIL."""
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_image(name: str, producer: str, index: int) -> bytes:
    """Compone la imagen de muestra de un café."""
    top, bottom = GRADIENTS[index % len(GRADIENTS)]
    image = _vertical_gradient(top, bottom)
    draw = ImageDraw.Draw(image)

    # Grano de café estilizado: el contorno y, en el centro, el surco.
    cx, cy = WIDTH // 2, HEIGHT // 2 - 60
    draw.ellipse([cx - 150, cy - 210, cx + 150, cy + 210], outline=(255, 255, 255), width=8)
    # El surco es media elipse estrecha centrada en el grano; si su caja
    # delimitadora se desplaza, la curva se sale del contorno.
    draw.arc(
        [cx - 60, cy - 205, cx + 60, cy + 205], start=90, end=270, fill=(255, 255, 255), width=8
    )

    title_font = _font(58)
    subtitle_font = _font(34)

    def centered(text: str, y: int, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((WIDTH - (box[2] - box[0])) / 2, y), text, font=font, fill=(244, 235, 221))

    centered(name[:38], HEIGHT - 260, title_font)
    centered(producer[:40], HEIGHT - 180, subtitle_font)
    centered("IMAGEN DE MUESTRA", HEIGHT - 90, _font(24))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82)
    return buffer.getvalue()


def main() -> None:
    # Deja el bucket listo con la política vigente: pública solo la parte que es
    # escaparate, privado todo lo demás.
    storage = S3Storage()
    storage.ensure_bucket()

    session = SessionLocal()
    uploaded = 0
    try:
        images = session.scalars(select(ProductImage)).all()
        for index, image_row in enumerate(images):
            product = session.get(Product, image_row.product_id)
            if product is None:
                continue

            producer = product.producer
            label = producer.brand_name or producer.legal_name if producer else "MONK GRAIN"

            storage.put(
                image_row.image_key,
                build_image(product.name, label, index),
                "image/jpeg",
            )
            uploaded += 1
    finally:
        session.close()

    logger.info("demo_images_uploaded", count=uploaded, bucket=settings.s3_bucket)
    # Este módulo se ejecuta a mano desde la consola: el resultado se imprime
    # además de registrarse, igual que en `create_admin`.
    print(f"Imágenes de muestra subidas: {uploaded} (bucket «{settings.s3_bucket}»)")  # noqa: T201


if __name__ == "__main__":
    main()
