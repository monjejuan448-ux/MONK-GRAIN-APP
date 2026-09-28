"""Datos de demostración: productores y cafés colombianos realistas.

Sirven para probar el catálogo, los filtros y el flujo de compra sin depender de
que existan productores reales. Los datos son verosímiles (variedades, procesos,
altitudes y perfiles sensoriales corresponden a los de la caficultura
colombiana) pero las fincas y personas son ficticias.

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
    GrindType,
    ProducerStatus,
    ProducerType,
    ProductStatus,
    RoastLevel,
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


CATEGORIES = [
    ("cafe-tostado", "Café tostado", "Listo para moler y preparar"),
    ("cafe-molido", "Café molido", "Molido según tu método de preparación"),
    ("cafe-verde", "Café verde", "Grano sin tostar para tostadores"),
    ("microlotes", "Microlotes", "Lotes pequeños de calidad excepcional"),
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

# (productor_idx, nombre, estado, variedad, proceso, tueste, altitud, perfil,
#  notas, puntaje, cosecha, precio_base, certificaciones, presentaciones)
PRODUCTS: list[tuple[Any, ...]] = [
    (
        0,
        "Microlote Geisha Lavado",
        CoffeeState.ROASTED,
        "Geisha",
        CoffeeProcess.WASHED,
        RoastLevel.LIGHT,
        1850,
        "Taza limpia y floral, de cuerpo sedoso y acidez cítrica brillante. "
        "Final prolongado con dulzor a panela.",
        ["jazmín", "bergamota", "durazno", "panela"],
        Decimal("89.50"),
        date(2026, 4, 15),
        Decimal("78000"),
        ["organic", "denominacion_origen"],
        [
            ("250 g", Decimal("250"), GrindType.WHOLE_BEAN, Decimal("78000"), None, 40),
            ("500 g", Decimal("500"), GrindType.WHOLE_BEAN, Decimal("145000"), None, 25),
        ],
    ),
    (
        0,
        "El Mirador Caturra Honey",
        CoffeeState.ROASTED,
        "Caturra",
        CoffeeProcess.HONEY,
        RoastLevel.MEDIUM,
        1720,
        "Dulzor pronunciado y cuerpo cremoso. Acidez media que recuerda a la "
        "manzana roja, con un fondo de caramelo.",
        ["caramelo", "manzana roja", "almendra"],
        Decimal("86.25"),
        date(2026, 3, 20),
        Decimal("42000"),
        ["denominacion_origen"],
        [
            ("250 g", Decimal("250"), GrindType.WHOLE_BEAN, Decimal("42000"), None, 60),
            ("250 g molido", Decimal("250"), GrindType.MEDIUM, Decimal("42000"), None, 45),
            (
                "1 kg",
                Decimal("1000"),
                GrindType.WHOLE_BEAN,
                Decimal("155000"),
                Decimal("138000"),
                30,
            ),
        ],
    ),
    (
        1,
        "Nariño Altura Lavado",
        CoffeeState.ROASTED,
        "Castillo",
        CoffeeProcess.WASHED,
        RoastLevel.MEDIUM,
        2050,
        "Acidez viva y estructurada, típica de las alturas nariñenses. Notas "
        "florales que dan paso a un dulzor de caña.",
        ["flores blancas", "caña de azúcar", "cítricos"],
        Decimal("87.00"),
        date(2026, 5, 10),
        Decimal("46000"),
        ["fairtrade", "organic"],
        [
            ("340 g", Decimal("340"), GrindType.WHOLE_BEAN, Decimal("46000"), None, 80),
            (
                "1 kg",
                Decimal("1000"),
                GrindType.WHOLE_BEAN,
                Decimal("128000"),
                Decimal("115000"),
                50,
            ),
        ],
    ),
    (
        1,
        "Verde Nariño Excelso",
        CoffeeState.GREEN,
        "Castillo",
        CoffeeProcess.WASHED,
        None,
        1950,
        "Café verde excelso listo para tostar. Humedad controlada al 10,5 % y "
        "cero defectos primarios.",
        ["floral", "cítrico"],
        Decimal("85.50"),
        date(2026, 5, 2),
        Decimal("32000"),
        ["fairtrade"],
        [
            ("1 kg", Decimal("1000"), None, Decimal("32000"), Decimal("27000"), 200),
            ("5 kg", Decimal("5000"), None, Decimal("150000"), Decimal("125000"), 60),
        ],
    ),
    (
        2,
        "Alta Vista Anaeróbico 72h",
        CoffeeState.ROASTED,
        "Pink Bourbon",
        CoffeeProcess.ANAEROBIC,
        RoastLevel.LIGHT,
        1780,
        "Fermentación anaeróbica de 72 horas. Perfil intenso y afrutado, con "
        "acidez málica y un final vinoso muy marcado.",
        ["frutos rojos", "vino tinto", "cacao", "mango"],
        Decimal("90.25"),
        date(2026, 2, 28),
        Decimal("95000"),
        ["rainforest"],
        [("250 g", Decimal("250"), GrindType.WHOLE_BEAN, Decimal("95000"), None, 18)],
    ),
    (
        2,
        "Quindío Clásico",
        CoffeeState.ROASTED,
        "Colombia",
        CoffeeProcess.WASHED,
        RoastLevel.MEDIUM_DARK,
        1600,
        "El perfil clásico del Eje Cafetero: cuerpo alto, acidez suave y notas "
        "a chocolate con nuez. Ideal para prensa francesa.",
        ["chocolate", "nuez", "caramelo"],
        Decimal("83.00"),
        date(2026, 4, 5),
        Decimal("34000"),
        [],
        [
            ("500 g", Decimal("500"), GrindType.WHOLE_BEAN, Decimal("34000"), None, 100),
            ("500 g molido", Decimal("500"), GrindType.COARSE, Decimal("34000"), None, 75),
        ],
    ),
    (
        3,
        "Selección del Tostador — Cauca",
        CoffeeState.GROUND,
        "Caturra",
        CoffeeProcess.WASHED,
        RoastLevel.MEDIUM,
        1900,
        "Mezcla de dos fincas caucanas, molida para método de goteo. Balanceado, "
        "con dulzor persistente y acidez cítrica agradable.",
        ["naranja", "panela", "chocolate con leche"],
        Decimal("84.75"),
        date(2026, 3, 12),
        Decimal("38000"),
        ["utz"],
        [
            ("340 g", Decimal("340"), GrindType.MEDIUM, Decimal("38000"), None, 90),
            ("340 g fino", Decimal("340"), GrindType.FINE, Decimal("38000"), None, 55),
        ],
    ),
    (
        4,
        "La Esperanza Sombrío Nativo",
        CoffeeState.ROASTED,
        "Caturra",
        CoffeeProcess.NATURAL,
        RoastLevel.MEDIUM,
        1680,
        "Secado al sol en marquesina durante 21 días. Cuerpo denso y dulzor "
        "intenso, con notas a fruta madura.",
        ["mora", "panela", "cacao"],
        Decimal("85.00"),
        date(2026, 4, 22),
        Decimal("40000"),
        ["bird_friendly", "organic"],
        [
            ("250 g", Decimal("250"), GrindType.WHOLE_BEAN, Decimal("40000"), None, 35),
            ("500 g", Decimal("500"), GrindType.WHOLE_BEAN, Decimal("75000"), None, 20),
        ],
    ),
    (
        4,
        "La Esperanza Descafeinado",
        CoffeeState.ROASTED,
        "Colombia",
        CoffeeProcess.WASHED,
        RoastLevel.MEDIUM,
        1650,
        "Descafeinado por el método de agua de montaña, sin solventes químicos. "
        "Conserva el dulzor y el cuerpo del café original.",
        ["chocolate", "caramelo", "avellana"],
        Decimal("82.50"),
        date(2026, 3, 30),
        Decimal("44000"),
        ["organic"],
        [("250 g", Decimal("250"), GrindType.WHOLE_BEAN, Decimal("44000"), None, 0)],
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
        state,
        variety,
        process,
        roast,
        altitude,
        sensory,
        notes,
        score,
        harvest,
        base_price,
        cert_codes,
        variants,
    ) in PRODUCTS:
        slug = slugify(name)
        if session.scalar(select(Product).where(Product.slug == slug)) is not None:
            continue

        producer = producers[producer_index]
        farm = session.scalar(select(Farm).where(Farm.producer_id == producer.id))

        category_slug = {
            CoffeeState.ROASTED: "cafe-tostado",
            CoffeeState.GROUND: "cafe-molido",
            CoffeeState.GREEN: "cafe-verde",
        }[state]

        wholesale_prices = [v[4] for v in variants if v[4] is not None]
        product = Product(
            producer_id=producer.id,
            farm_id=farm.id if farm else None,
            category_id=categories[category_slug].id,
            slug=slug,
            name=name,
            description=sensory,
            state=state,
            status=ProductStatus.PUBLISHED,
            base_price=base_price,
            wholesale_price=min(wholesale_prices) if wholesale_prices else None,
            wholesale_min_qty=10 if wholesale_prices else None,
            dispatch_days=3,
            storage_conditions=(
                "Conservar en lugar fresco y seco, lejos de la luz directa. "
                "Una vez abierto, mantener el empaque bien cerrado."
            ),
            allows_samples=state == CoffeeState.GREEN,
            published_at=datetime.now(UTC),
        )
        session.add(product)
        session.flush()

        session.add(
            CoffeeAttributes(
                product_id=product.id,
                variety=variety,
                process=process,
                roast=roast,
                altitude_masl=altitude,
                sensory_profile=sensory,
                tasting_notes=notes,
                cupping_score=score,
                harvest_date=harvest,
                roast_date=date(2026, 7, 1) if state != CoffeeState.GREEN else None,
                moisture_pct=Decimal("10.50"),
            )
        )

        session.add(
            ProductImage(
                product_id=product.id,
                image_key=f"demo/{slug}.jpg",
                alt_text=f"{name}, café de {producer.brand_name}",
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

        for _label, grams, grind, price, wholesale, stock in variants:
            grind_suffix = f"-{grind.value[:3].upper()}" if grind else ""
            sku = f"{slug[:20].upper()}-{int(grams)}{grind_suffix}"
            variant = ProductVariant(
                product_id=product.id,
                sku=sku,
                weight_grams=grams,
                grind=grind,
                price=price,
                wholesale_price=wholesale,
                is_active=True,
            )
            session.add(variant)
            session.flush()
            session.add(
                Inventory(
                    variant_id=variant.id, stock_qty=stock, reserved_qty=0, low_stock_threshold=5
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
