"""Datos iniciales del sistema.

Carga los catálogos indispensables para que la aplicación funcione: roles,
permisos, departamentos y municipios cafeteros de Colombia, regiones y
certificaciones. Es idempotente: puede ejecutarse varias veces sin duplicar.

Uso:
    docker compose exec backend python -m app.db.seed
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.models.enums import RoleCode
from app.models.geo import Department, Municipality, Region
from app.models.producer import Certification
from app.models.user import Permission, Role

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Permisos
# ------------------------------------------------------------------
PERMISSIONS: list[tuple[str, str, str, str]] = [
    # (code, resource, action, description)
    ("product.create", "product", "create", "Publicar productos"),
    ("product.update", "product", "update", "Editar productos propios"),
    ("product.delete", "product", "delete", "Despublicar productos propios"),
    ("product.moderate", "product", "moderate", "Moderar productos de cualquier vendedor"),
    ("inventory.manage", "inventory", "manage", "Gestionar inventario propio"),
    ("order.create", "order", "create", "Realizar pedidos"),
    ("order.view_own", "order", "view_own", "Ver pedidos propios"),
    ("order.manage_sales", "order", "manage_sales", "Gestionar pedidos recibidos como vendedor"),
    ("order.view_all", "order", "view_all", "Ver todos los pedidos de la plataforma"),
    ("order.refund", "order", "refund", "Autorizar reembolsos"),
    ("review.create", "review", "create", "Escribir reseñas de compras verificadas"),
    ("review.moderate", "review", "moderate", "Moderar reseñas reportadas"),
    ("producer.approve", "producer", "approve", "Aprobar o rechazar vendedores"),
    ("user.manage", "user", "manage", "Gestionar cuentas y roles"),
    ("commission.manage", "commission", "manage", "Configurar comisiones de la plataforma"),
    ("settlement.manage", "settlement", "manage", "Gestionar liquidaciones a vendedores"),
    ("coupon.manage", "coupon", "manage", "Crear y administrar cupones"),
    ("content.manage", "content", "manage", "Gestionar blog, banners y contenido"),
    ("category.manage", "category", "manage", "Gestionar categorías del catálogo"),
    ("report.view", "report", "view", "Consultar métricas y exportar reportes"),
    ("audit.view", "audit", "view", "Consultar el registro de auditoría"),
    ("quote.request", "quote", "request", "Solicitar muestras y cotizaciones"),
    ("quote.answer", "quote", "answer", "Responder solicitudes comerciales"),
    ("wholesale.view", "wholesale", "view", "Ver precios mayoristas"),
]

ROLES: list[tuple[RoleCode, str, str]] = [
    (RoleCode.VISITOR, "Visitante", "Navega el catálogo sin cuenta"),
    (RoleCode.CONSUMER, "Comprador", "Compra café al detal"),
    (RoleCode.BUSINESS, "Comprador empresarial", "Compra por volumen con precios mayoristas"),
    (RoleCode.PRODUCER, "Productor", "Publica y vende su café"),
    (RoleCode.ADMIN, "Administrador", "Administra la plataforma"),
]

ROLE_PERMISSIONS: dict[RoleCode, list[str]] = {
    RoleCode.VISITOR: [],
    RoleCode.CONSUMER: [
        "order.create",
        "order.view_own",
        "review.create",
    ],
    RoleCode.BUSINESS: [
        "order.create",
        "order.view_own",
        "review.create",
        "quote.request",
        "wholesale.view",
    ],
    RoleCode.PRODUCER: [
        "product.create",
        "product.update",
        "product.delete",
        "inventory.manage",
        "order.manage_sales",
        "order.view_own",
        "quote.answer",
    ],
    # El administrador recibe todos los permisos salvo los que solo tienen
    # sentido como parte comercial: no compra ni vende en nombre de nadie.
    RoleCode.ADMIN: [
        "product.moderate",
        "order.view_all",
        "order.refund",
        "review.moderate",
        "producer.approve",
        "user.manage",
        "commission.manage",
        "settlement.manage",
        "coupon.manage",
        "content.manage",
        "category.manage",
        "report.view",
        "audit.view",
    ],
}


# ------------------------------------------------------------------
# Geografía cafetera de Colombia (códigos DANE)
# ------------------------------------------------------------------
REGIONS: list[tuple[str, str, str]] = [
    ("huila", "Huila", "Mayor productor del país. Cafés dulces, de acidez cítrica y cuerpo medio."),
    ("narino", "Nariño", "Altitudes extremas cerca del ecuador. Acidez marcada y notas florales."),
    ("cauca", "Cauca", "Cafés de altura con acidez brillante y dulzor de panela."),
    ("tolima", "Tolima", "Perfil balanceado con notas a frutos rojos y chocolate."),
    ("eje_cafetero", "Eje Cafetero", "Caldas, Quindío y Risaralda. El perfil clásico colombiano."),
    ("antioquia", "Antioquia", "Cafés de cuerpo pronunciado y notas a nuez y caramelo."),
    ("santander", "Santander", "Cultivos tradicionales bajo sombrío. Cuerpo alto y baja acidez."),
    ("sierra_nevada", "Sierra Nevada", "Cafés de origen indígena, cultivados en reserva natural."),
]

# Departamentos con producción cafetera relevante y sus municipios principales.
# (código DANE departamento, nombre, [(código municipio, nombre, lat, lng)])
GEOGRAPHY: list[tuple[str, str, list[tuple[str, str, float, float]]]] = [
    (
        "41",
        "Huila",
        [
            ("41001", "Neiva", 2.9273, -75.2819),
            ("41551", "Pitalito", 1.8539, -76.0513),
            ("41396", "La Plata", 2.3897, -75.8919),
            ("41006", "Acevedo", 1.8064, -75.8878),
            ("41668", "San Agustín", 1.8808, -76.2681),
            ("41359", "Isnos", 1.9283, -76.2153),
            ("41615", "Rivera", 2.7772, -75.2569),
            ("41298", "Garzón", 2.1961, -75.6278),
        ],
    ),
    (
        "52",
        "Nariño",
        [
            ("52001", "Pasto", 1.2136, -77.2811),
            ("52356", "Ipiales", 0.8256, -77.6444),
            ("52683", "Sandoná", 1.2833, -77.4711),
            ("52480", "Nariño", 1.2903, -77.3583),
            ("52693", "San Lorenzo", 1.5058, -77.2178),
            ("52254", "El Tambo", 1.4083, -77.3903),
        ],
    ),
    (
        "19",
        "Cauca",
        [
            ("19001", "Popayán", 2.4448, -76.6147),
            ("19392", "Inzá", 2.5497, -76.0625),
            ("19548", "Piendamó", 2.6383, -76.5311),
            ("19130", "Cajibío", 2.6222, -76.5706),
            ("19701", "Santander de Quilichao", 3.0089, -76.4847),
            ("19022", "Almaguer", 1.9142, -76.8547),
        ],
    ),
    (
        "73",
        "Tolima",
        [
            ("73001", "Ibagué", 4.4389, -75.2322),
            ("73449", "Melgar", 4.2044, -74.6408),
            ("73168", "Chaparral", 3.7236, -75.4839),
            ("73616", "Rioblanco", 3.5289, -75.6428),
            ("73555", "Planadas", 3.1978, -75.6425),
        ],
    ),
    (
        "17",
        "Caldas",
        [
            ("17001", "Manizales", 5.0689, -75.5174),
            ("17174", "Chinchiná", 4.9822, -75.6058),
            ("17614", "Riosucio", 5.4222, -75.7031),
            ("17873", "Villamaría", 5.0397, -75.5100),
            ("17380", "La Merced", 5.3944, -75.5461),
        ],
    ),
    (
        "63",
        "Quindío",
        [
            ("63001", "Armenia", 4.5339, -75.6811),
            ("63690", "Salento", 4.6378, -75.5706),
            ("63111", "Buenavista", 4.3597, -75.7392),
            ("63302", "Génova", 4.2064, -75.7889),
            ("63548", "Pijao", 4.3350, -75.7036),
        ],
    ),
    (
        "66",
        "Risaralda",
        [
            ("66001", "Pereira", 4.8133, -75.6961),
            ("66682", "Santa Rosa de Cabal", 4.8697, -75.6217),
            ("66170", "Dosquebradas", 4.8339, -75.6753),
            ("66400", "La Virginia", 4.8994, -75.8828),
            ("66594", "Quinchía", 5.3400, -75.7311),
        ],
    ),
    (
        "05",
        "Antioquia",
        [
            ("05001", "Medellín", 6.2442, -75.5812),
            ("05055", "Argelia", 5.7314, -75.1428),
            ("05364", "Jericó", 5.7908, -75.7847),
            ("05002", "Abejorral", 5.7897, -75.4286),
            ("05659", "San Vicente", 6.2822, -75.3325),
            ("05756", "Sonsón", 5.7147, -75.3106),
        ],
    ),
    (
        "68",
        "Santander",
        [
            ("68001", "Bucaramanga", 7.1193, -73.1227),
            ("68209", "Confines", 6.3550, -73.2394),
            ("68755", "Socorro", 6.4636, -73.2611),
            ("68370", "Jesús María", 6.0000, -73.7833),
        ],
    ),
    (
        "47",
        "Magdalena",
        [
            ("47001", "Santa Marta", 11.2408, -74.1990),
            ("47053", "Aracataca", 10.5919, -74.1889),
            ("47245", "El Banco", 9.0006, -73.9756),
            ("47660", "San Sebastián de Buenavista", 9.2394, -74.3506),
        ],
    ),
]

CERTIFICATIONS: list[tuple[str, str, str]] = [
    ("organic", "Orgánico", "Certificación de producción orgánica"),
    ("fairtrade", "Comercio Justo", "Fairtrade International"),
    ("rainforest", "Rainforest Alliance", "Rainforest Alliance"),
    ("utz", "UTZ Certified", "UTZ / Rainforest Alliance"),
    ("4c", "4C", "Common Code for the Coffee Community"),
    ("bird_friendly", "Bird Friendly", "Smithsonian Migratory Bird Center"),
    ("denominacion_origen", "Denominación de Origen", "Café de Colombia — FNC"),
]


def seed_permissions_and_roles(session: Session) -> None:
    """Crea permisos, roles y su asociación."""
    existing_permissions = {
        permission.code: permission for permission in session.scalars(select(Permission)).all()
    }
    for code, resource, action, description in PERMISSIONS:
        if code not in existing_permissions:
            permission = Permission(
                code=code, resource=resource, action=action, description=description
            )
            session.add(permission)
            existing_permissions[code] = permission
    session.flush()

    existing_roles = {role.code: role for role in session.scalars(select(Role)).all()}
    for role_code, name, description in ROLES:
        role = existing_roles.get(role_code.value)
        if role is None:
            role = Role(code=role_code.value, name=name, description=description)
            session.add(role)
            existing_roles[role_code.value] = role
        session.flush()

        # Reconcilia los permisos del rol con la definición vigente.
        desired = {
            existing_permissions[code]
            for code in ROLE_PERMISSIONS[role_code]
            if code in existing_permissions
        }
        role.permissions = sorted(desired, key=lambda permission: permission.code)

    logger.info(
        "seed_roles_permissions",
        roles=len(existing_roles),
        permissions=len(existing_permissions),
    )


def seed_geography(session: Session) -> None:
    """Carga departamentos, municipios y regiones cafeteras."""
    existing_departments = {
        department.dane_code: department for department in session.scalars(select(Department)).all()
    }
    existing_municipalities = {
        municipality.dane_code for municipality in session.scalars(select(Municipality)).all()
    }

    municipality_count = 0
    for dept_code, dept_name, municipalities in GEOGRAPHY:
        department = existing_departments.get(dept_code)
        if department is None:
            department = Department(dane_code=dept_code, name=dept_name)
            session.add(department)
            session.flush()
            existing_departments[dept_code] = department

        for mun_code, mun_name, lat, lng in municipalities:
            if mun_code in existing_municipalities:
                continue
            session.add(
                Municipality(
                    department_id=department.id,
                    dane_code=mun_code,
                    name=mun_name,
                    centroid_lat=lat,
                    centroid_lng=lng,
                )
            )
            municipality_count += 1

    existing_regions = {region.code for region in session.scalars(select(Region)).all()}
    for code, name, description in REGIONS:
        if code not in existing_regions:
            session.add(Region(code=code, name=name, description=description))

    session.flush()
    logger.info(
        "seed_geography",
        departments=len(existing_departments),
        new_municipalities=municipality_count,
        regions=len(REGIONS),
    )


def seed_certifications(session: Session) -> None:
    """Carga el catálogo de certificaciones."""
    existing = {
        certification.code for certification in session.scalars(select(Certification)).all()
    }
    created = 0
    for code, name, issuing_body in CERTIFICATIONS:
        if code not in existing:
            session.add(Certification(code=code, name=name, issuing_body=issuing_body))
            created += 1
    session.flush()
    logger.info("seed_certifications", created=created, total=len(CERTIFICATIONS))


def run_seed() -> None:
    """Ejecuta la carga completa de datos iniciales."""
    configure_logging()
    session = SessionLocal()
    try:
        seed_permissions_and_roles(session)
        seed_geography(session)
        seed_certifications(session)
        session.commit()
        logger.info("seed_completed")
    except Exception:
        session.rollback()
        logger.exception("seed_failed")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()
