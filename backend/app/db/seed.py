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
from app.db.divipola import DEPARTMENTS, MUNICIPALITIES
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

# La división político-administrativa completa vive en `divipola.py`: son los 33
# departamentos y las 1.122 entidades municipales del DANE. Antes había aquí una
# lista recortada a los 54 municipios cafeteros, y como `addresses.municipality_id`
# es obligatorio, eso dejaba sin poder comprar a cualquiera que viviera fuera de
# la zona cafetera —Bogotá, Cali, Barranquilla y Cartagena incluidas—.


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

    for dept_code, dept_name in DEPARTMENTS:
        if dept_code not in existing_departments:
            department = Department(dane_code=dept_code, name=dept_name)
            session.add(department)
            session.flush()
            existing_departments[dept_code] = department

    municipality_count = 0
    for dept_code, mun_code, mun_name, lat, lng in MUNICIPALITIES:
        if mun_code in existing_municipalities:
            continue
        session.add(
            Municipality(
                department_id=existing_departments[dept_code].id,
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
