"""Datos de demostración: caficultores y lotes de pergamino colombianos.

Sirven para probar el catálogo, los filtros y el flujo de compra sin depender de
que existan vendedores reales. Los datos son verosímiles —variedades, procesos,
altitudes, factores de rendimiento, humedades y análisis físicos corresponden a
los de la caficultura colombiana— pero las fincas, las personas y los lotes son
ficticios.

Los precios son por kilogramo de pergamino seco y las existencias, kilos.

Uso:
    docker compose exec backend python -m app.db.demo_data
"""

import unicodedata
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.catalog import (
    Category,
    CoffeeAttributes,
    Inventory,
    Product,
    ProductCertification,
    ProductImage,
    ProductVariant,
)
from app.models.enums import (
    CoffeeProcess,
    CoffeeState,
    ProducerStatus,
    ProducerType,
    ProductStatus,
    RoleCode,
    UserStatus,
)
from app.models.geo import Municipality, Region
from app.models.producer import Certification, Farm, ProducerProfile
from app.models.user import Role, User, UserRole

logger = get_logger(__name__)

DEMO_PASSWORD = "MonkGrain2026Demo"  # noqa: S105 — credencial de datos de prueba


def slugify(text: str) -> str:
    """Genera un slug ASCII a partir de un texto en español."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "-".join(part for part in ascii_text.replace("/", " ").split() if part)


# Las categorías agrupan el pergamino por lo que decide una compra: el factor de
# rendimiento. Más bajo es mejor café y más vale el kilo.
CATEGORIES = [
    (
        "pergamino-exportacion",
        "Pergamino de exportación",
        "Factor 92 o menor, apto para trilla de excelso de exportación",
    ),
    (
        "pergamino-estandar",
        "Pergamino estándar",
        "Factor entre 93 y 96, el rango de la compra corriente",
    ),
    ("microlotes", "Microlotes", "Lotes pequeños de variedades y beneficios especiales"),
    (
        "pergamino-certificado",
        "Pergamino certificado",
        "Lotes con certificación orgánica, Fairtrade, Rainforest o UTZ vigente",
    ),
]

# (correo, nombre, tipo, razón social, documento, marca, historia, municipio DANE, región)
# Tuplas heterogéneas de datos de prueba; el tipo exacto no aporta aquí.
PRODUCERS: list[tuple[Any, ...]] = [
    (
        "finca.elmirador@ejemplo.co",
        "Ana María Trujillo",
        ProducerType.FARM,
        "Finca El Mirador S.A.S.",
        "900123456-1",
        "Café El Mirador",
        "Tres generaciones cultivando café en las laderas de Pitalito. Mi abuelo "
        "sembró los primeros cafetos en 1962; hoy trabajamos 6 hectáreas con "
        "sombrío nativo y procesamos cada lote por separado para conservar el "
        "carácter de cada parcela.",
        "41551",
        "huila",
    ),
    (
        "coop.narino@ejemplo.co",
        "Jaime Ortega",
        ProducerType.COOPERATIVE,
        "Cooperativa de Caficultores de Nariño",
        "800234567-2",
        "Café de Altura Nariño",
        "Reunimos a 340 familias caficultoras de Sandoná y La Unión, en fincas "
        "situadas entre 1.800 y 2.100 metros. La altura y la cercanía al "
        "ecuador dan a nuestros cafés una acidez viva y notas florales que los "
        "distinguen.",
        "52683",
        "narino",
    ),
    (
        "hacienda.altavista@ejemplo.co",
        "Carlos Betancourt",
        ProducerType.FARM,
        "Hacienda Alta Vista",
        "901345678-3",
        "Alta Vista",
        "En el corazón del Eje Cafetero, cultivamos variedades tradicionales y "
        "experimentales. Fuimos de las primeras fincas de Quindío en aplicar "
        "fermentación anaeróbica controlada.",
        "63690",
        "eje_cafetero",
    ),
    (
        "tostaduria.monje@ejemplo.co",
        "Lucía Vargas",
        ProducerType.ROASTER,
        "Tostaduría La Montaña S.A.S.",
        "901456789-4",
        "La Montaña Tostadores",
        "Compramos directamente a caficultores del Cauca y el Huila, y tostamos "
        "en pequeños lotes en Popayán. Cada empaque indica la finca, el "
        "productor y la fecha exacta de tueste.",
        "19001",
        "cauca",
    ),
    (
        "finca.laesperanza@ejemplo.co",
        "Pedro Nel Quiceno",
        ProducerType.FARMER,
        "Pedro Nel Quiceno Restrepo",
        "10234567",
        "Finca La Esperanza",
        "Soy caficultor en Jericó, Antioquia. Cultivo 3 hectáreas de Caturra y "
        "Colombia bajo sombra de guamo y nogal. Beneficio el café con agua de "
        "nacimiento y lo seco al sol en marquesina.",
        "05364",
        "antioquia",
    ),
]

# Lotes de pergamino seco. Los datos son verosímiles —variedades, procesos,
# altitudes, factores de rendimiento y análisis físicos corresponden a los de la
# caficultura colombiana— pero las fincas, las personas y los lotes son ficticios.
#
# (productor_idx, nombre, categoría, variedad, proceso, altitud, descripción,
#  factor, humedad, almendra_sana, pasilla, broca, mallas, secado, lote,
#  cosecha, precio_kg, certificaciones, ofertas)
#
# Cada oferta es (presentación, mínimo_kg, precio_kg, precio_volumen, kilos).
PRODUCTS: list[tuple[Any, ...]] = [
    (
        0,
        "Microlote Geisha Pergamino",
        "microlotes",
        "Geisha",
        CoffeeProcess.WASHED,
        1850,
        "Microlote de Geisha beneficiado por lavado y secado en marquesina durante "
        "18 días. Factor 86, el más bajo de la finca en esta cosecha. Trillado da "
        "una almendra grande y muy uniforme.",
        Decimal("86.00"),
        Decimal("10.80"),
        Decimal("97.50"),
        Decimal("1.20"),
        Decimal("0.40"),
        [17, 18],
        "Marquesina, 18 días",
        "GE-2026-003",
        date(2026, 4, 15),
        Decimal("31000"),
        ["organic", "denominacion_origen"],
        [("A granel, en costal de fique", 125, Decimal("31000"), None, 375)],
    ),
    (
        0,
        "El Mirador Caturra Honey",
        "pergamino-exportacion",
        "Caturra",
        CoffeeProcess.HONEY,
        1720,
        "Beneficio honey con mucílago parcial y secado lento. Factor 90 y humedad "
        "controlada al 11 %. Lote homogéneo de una sola parcela.",
        Decimal("90.00"),
        Decimal("11.00"),
        Decimal("95.00"),
        Decimal("2.80"),
        Decimal("0.90"),
        [15, 16, 17],
        "Marquesina, 14 días",
        "MI-2026-011",
        date(2026, 3, 20),
        Decimal("24500"),
        ["denominacion_origen"],
        [
            ("A granel, en costal de fique", 125, Decimal("24500"), None, 1250),
            (
                "Empacado en la finca, bultos de 70 kg",
                700,
                Decimal("25500"),
                Decimal("23800"),
                2100,
            ),
        ],
    ),
    (
        1,
        "Nariño Altura Lavado",
        "pergamino-exportacion",
        "Castillo",
        CoffeeProcess.WASHED,
        2050,
        "Consolidado de 23 caficultores asociados de Sandoná, todos por encima de "
        "2.000 metros. Análisis físico por lote y humedad verificada en el acopio.",
        Decimal("91.50"),
        Decimal("10.50"),
        Decimal("94.20"),
        Decimal("3.50"),
        Decimal("1.10"),
        [15, 16, 17],
        "Secador mecánico Guardiola",
        "SA-2026-047",
        date(2026, 5, 10),
        Decimal("23000"),
        ["fairtrade", "organic"],
        [
            ("A granel, en costal de fique", 125, Decimal("23000"), None, 2500),
            ("Bultos de 70 kg", 700, Decimal("23800"), Decimal("22200"), 4900),
        ],
    ),
    (
        1,
        "Sandoná Pergamino Corriente",
        "pergamino-estandar",
        "Colombia",
        CoffeeProcess.WASHED,
        1900,
        "Pergamino de compra corriente del acopio de la asociación. Factor 94, el "
        "estándar de la Federación. Disponibilidad continua durante la cosecha.",
        Decimal("94.00"),
        Decimal("11.50"),
        Decimal("89.00"),
        Decimal("6.50"),
        Decimal("2.10"),
        [14, 15, 16],
        "Patio de cemento y secador mecánico",
        "SA-2026-052",
        date(2026, 5, 22),
        Decimal("18200"),
        ["fairtrade"],
        [
            ("A granel, en costal de fique", 125, Decimal("18200"), None, 6250),
            ("Bultos de 70 kg", 1400, Decimal("18900"), Decimal("17600"), 9800),
        ],
    ),
    (
        2,
        "Quindío Clásico",
        "pergamino-estandar",
        "Colombia",
        CoffeeProcess.WASHED,
        1600,
        "El pergamino clásico del Eje Cafetero. Factor 93, secado en silo con aire "
        "caliente y control de humedad cada cuatro horas.",
        Decimal("93.00"),
        Decimal("11.20"),
        Decimal("90.50"),
        Decimal("5.80"),
        Decimal("1.80"),
        [14, 15, 16, 17],
        "Silo con aire caliente",
        "AV-2026-019",
        date(2026, 4, 5),
        Decimal("19000"),
        [],
        [
            ("A granel, en costal de fique", 125, Decimal("19000"), None, 5000),
            ("Bultos de 70 kg", 700, Decimal("19600"), Decimal("18400"), 7000),
        ],
    ),
    (
        2,
        "Alta Vista Pink Bourbon",
        "microlotes",
        "Pink Bourbon",
        CoffeeProcess.ANAEROBIC,
        1780,
        "Fermentación anaeróbica de 72 horas antes del lavado, secado a la sombra "
        "en camas africanas. Factor 88 y almendra sana del 96 %.",
        Decimal("88.00"),
        Decimal("10.60"),
        Decimal("96.10"),
        Decimal("1.90"),
        Decimal("0.60"),
        [16, 17, 18],
        "Camas africanas a la sombra, 21 días",
        "AV-2026-024",
        date(2026, 2, 28),
        Decimal("28500"),
        ["rainforest"],
        [("A granel, en costal de fique", 125, Decimal("28500"), None, 875)],
    ),
    (
        3,
        "Acopio Cauca — Lote Consolidado",
        "pergamino-estandar",
        "Caturra",
        CoffeeProcess.WASHED,
        1900,
        "Consolidado del centro de acopio de Popayán, de pequeños productores del "
        "norte del Cauca. Se analiza cada entrega y se mezcla por factor.",
        Decimal("92.50"),
        Decimal("11.00"),
        Decimal("92.00"),
        Decimal("4.60"),
        Decimal("1.40"),
        [15, 16, 17],
        "Patio de cemento",
        "PO-2026-088",
        date(2026, 3, 12),
        Decimal("20500"),
        ["utz"],
        [
            ("A granel, en costal de fique", 250, Decimal("20500"), None, 12500),
            ("Bultos de 70 kg", 1400, Decimal("21200"), Decimal("19800"), 14000),
        ],
    ),
    (
        4,
        "La Esperanza Sombrío Nativo",
        "pergamino-certificado",
        "Caturra",
        CoffeeProcess.NATURAL,
        1680,
        "Beneficio natural con la cereza entera secada al sol en marquesina durante "
        "21 días. Lote pequeño de una finca de tres hectáreas bajo sombra de guamo "
        "y nogal.",
        Decimal("92.00"),
        Decimal("11.30"),
        Decimal("93.40"),
        Decimal("4.10"),
        Decimal("1.60"),
        [15, 16],
        "Marquesina, 21 días",
        "ES-2026-006",
        date(2026, 4, 18),
        Decimal("22000"),
        ["organic"],
        [("A granel, en costal de fique", 62, Decimal("22000"), None, 620)],
    ),
    (
        4,
        "La Esperanza Lote de Traspatio",
        "pergamino-estandar",
        "Colombia",
        CoffeeProcess.WASHED,
        1580,
        "Último pergamino de la cosecha principal, ya vendido casi por completo. "
        "Se deja publicado para dejar constancia del lote y su análisis.",
        Decimal("96.00"),
        Decimal("11.80"),
        Decimal("86.50"),
        Decimal("8.20"),
        Decimal("2.90"),
        [14, 15],
        "Marquesina, 16 días",
        "ES-2026-007",
        date(2026, 3, 30),
        Decimal("16800"),
        [],
        # Sin existencias a propósito: el catálogo debe saber mostrar un lote
        # agotado, y los favoritos marcarlo como tal.
        [("A granel, en costal de fique", 62, Decimal("16800"), None, 0)],
    ),
]

FARMS: list[tuple[Any, ...]] = [
    (0, "Finca El Mirador", "Vereda Bruselas", Decimal("6.00"), 1650, 1900),
    (1, "Asociación Sandoná", "Vereda El Ingenio", Decimal("120.00"), 1800, 2100),
    (2, "Hacienda Alta Vista", "Vereda Boquía", Decimal("18.50"), 1600, 1850),
    (3, "Centro de acopio Popayán", None, None, None, None),
    (4, "Finca La Esperanza", "Vereda La Soledad", Decimal("3.20"), 1580, 1750),
]


def _get_or_create_categories(session: Session) -> dict[str, Category]:
    existing = {c.slug: c for c in session.scalars(select(Category)).all()}
    for order, (slug, name, description) in enumerate(CATEGORIES):
        if slug not in existing:
            category = Category(slug=slug, name=name, description=description, sort_order=order)
            session.add(category)
            existing[slug] = category
    session.flush()
    return existing


def _create_producers(session: Session) -> list[ProducerProfile]:
    """Crea los usuarios productores con su perfil aprobado y su finca."""
    producer_role = session.scalar(select(Role).where(Role.code == RoleCode.PRODUCER.value))
    if producer_role is None:
        raise RuntimeError("Falta el rol 'producer'. Ejecuta primero `python -m app.db.seed`.")

    municipalities = {m.dane_code: m for m in session.scalars(select(Municipality)).all()}
    regions = {r.code: r for r in session.scalars(select(Region)).all()}

    profiles: list[ProducerProfile] = []
    for index, (
        email,
        full_name,
        ptype,
        legal_name,
        document,
        brand,
        story,
        mun_code,
        region_code,
    ) in enumerate(PRODUCERS):
        existing = session.scalar(select(User).where(User.email == email))
        if existing is not None:
            profile = session.scalar(
                select(ProducerProfile).where(ProducerProfile.user_id == existing.id)
            )
            if profile:
                profiles.append(profile)
                continue

        municipality = municipalities[mun_code]
        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=full_name,
            status=UserStatus.ACTIVE,
            data_consent=True,
            data_consent_at=datetime.now(UTC),
        )
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=producer_role.id))

        profile = ProducerProfile(
            user_id=user.id,
            type=ptype,
            legal_name=legal_name,
            document_number=document,
            brand_name=brand,
            story=story,
            department_id=municipality.department_id,
            municipality_id=municipality.id,
            status=ProducerStatus.APPROVED,
            reviewed_at=datetime.now(UTC),
            production_capacity_kg=Decimal("5000.00"),
            # Datos de notificación exigidos por el artículo 53 de la Ley 1480
            # de 2011: sin ellos el vendedor no puede publicar.
            notification_address=f"Calle 10 # 5-32, {municipality.name}",
            contact_phone="3105550142",
        )
        session.add(profile)
        session.flush()

        # Finca asociada, con ubicación aproximada tomada del centroide del
        # municipio: nunca se registra la coordenada exacta (ADR-08).
        farm_index, farm_name, village, area, alt_min, alt_max = FARMS[index]
        session.add(
            Farm(
                producer_id=profile.id,
                name=farm_name,
                municipality_id=municipality.id,
                region_id=regions[region_code].id if region_code in regions else None,
                village=village,
                area_hectares=area,
                altitude_min_masl=alt_min,
                altitude_max_masl=alt_max,
                approx_lat=municipality.centroid_lat,
                approx_lng=municipality.centroid_lng,
                environmental_practices=(
                    "Sombrío con especies nativas, manejo de aguas mieles y compostaje de la pulpa."
                ),
            )
        )
        session.flush()
        profiles.append(profile)

    return profiles


def _create_products(
    session: Session, producers: list[ProducerProfile], categories: dict[str, Category]
) -> int:
    certifications = {c.code: c for c in session.scalars(select(Certification)).all()}
    created = 0

    for (
        producer_index,
        name,
        category_slug,
        variety,
        process,
        altitude,
        description,
        yield_factor,
        moisture,
        healthy_bean,
        pasilla,
        borer,
        screens,
        drying,
        lot_code,
        harvest,
        price_per_kg,
        cert_codes,
        offers,
    ) in PRODUCTS:
        slug = slugify(name)
        if session.scalar(select(Product).where(Product.slug == slug)) is not None:
            continue

        producer = producers[producer_index]
        farm = session.scalar(select(Farm).where(Farm.producer_id == producer.id))

        volume_prices = [offer[3] for offer in offers if offer[3] is not None]
        # Mínimo en kilos a partir del cual aplica el precio por volumen: el de la
        # primera oferta que lo declara.
        volume_min = next((offer[1] for offer in offers if offer[3] is not None), None)

        product = Product(
            producer_id=producer.id,
            farm_id=farm.id if farm else None,
            category_id=categories[category_slug].id,
            slug=slug,
            name=name,
            description=description,
            state=CoffeeState.PERGAMINO,
            status=ProductStatus.PUBLISHED,
            # Precio por kilogramo del lote.
            base_price=price_per_kg,
            wholesale_price=min(volume_prices) if volume_prices else None,
            wholesale_min_qty=volume_min,
            dispatch_days=5,
            storage_conditions=(
                "Almacenar sobre estibas, en bodega ventilada y a la sombra, sin "
                "contacto con el piso ni con paredes húmedas. El pergamino toma "
                "humedad del ambiente y olores de lo que se guarde a su lado."
            ),
            # Todo lote de pergamino admite muestra: ningún comprador cierra una
            # compra por volumen sin trillar y catar una muestra antes.
            allows_samples=True,
            published_at=datetime.now(UTC),
        )
        session.add(product)
        session.flush()

        session.add(
            CoffeeAttributes(
                product_id=product.id,
                variety=variety,
                process=process,
                altitude_masl=altitude,
                harvest_date=harvest,
                yield_factor=yield_factor,
                moisture_pct=moisture,
                healthy_bean_pct=healthy_bean,
                pasilla_pct=pasilla,
                borer_damage_pct=borer,
                screen_sizes=screens,
                drying_method=drying,
                lot_code=lot_code,
                # Código SICA ficticio, derivado del código del lote para que sea
                # estable entre ejecuciones.
                sica_code=f"SICA-{abs(hash(lot_code)) % 10**8:08d}",
                notes=None,
            )
        )

        session.add(
            ProductImage(
                product_id=product.id,
                image_key=f"demo/{slug}.jpg",
                alt_text=f"Pergamino seco de {producer.brand_name}: {name}",
                is_primary=True,
                sort_order=0,
            )
        )

        for code in cert_codes:
            if code in certifications:
                session.add(
                    ProductCertification(
                        product_id=product.id, certification_id=certifications[code].id
                    )
                )

        for presentation, min_kg, price, volume_price, stock_kg in offers:
            variant = ProductVariant(
                product_id=product.id,
                sku=f"{slug[:24].upper()}-{min_kg}KG",
                presentation=presentation,
                min_qty_kg=min_kg,
                price=price,
                wholesale_price=volume_price,
                is_active=True,
            )
            session.add(variant)
            session.flush()
            session.add(
                Inventory(
                    variant_id=variant.id,
                    # Existencias en kilogramos.
                    stock_qty=stock_kg,
                    reserved_qty=0,
                    # Aviso de existencias bajas cuando ya no alcanza para dos
                    # compras del mínimo.
                    low_stock_threshold=min_kg * 2,
                )
            )

        created += 1

    return created


def run_demo_data() -> None:
    configure_logging()
    session = SessionLocal()
    try:
        categories = _get_or_create_categories(session)
        producers = _create_producers(session)
        created = _create_products(session, producers, categories)
        session.commit()
        logger.info(
            "demo_data_loaded",
            producers=len(producers),
            products_created=created,
            categories=len(categories),
        )
        print(  # noqa: T201 — salida esperada de un script de línea de comandos
            f"\nDatos de demostración cargados:\n"
            f"  productores : {len(producers)}\n"
            f"  productos   : {created} nuevos\n"
            f"  categorías  : {len(categories)}\n\n"
            f"Acceso de prueba a los perfiles de productor:\n"
            f"  correo     : {PRODUCERS[0][0]}\n"
            f"  contraseña : {DEMO_PASSWORD}\n"
        )
    except Exception:
        session.rollback()
        logger.exception("demo_data_failed")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_demo_data()
