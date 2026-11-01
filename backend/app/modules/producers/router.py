"""Endpoints del panel del productor."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.files import validate_document, validate_image
from app.core.pagination import Page, PageParams
from app.core.permissions import ProducerUser
from app.core.rate_limit import rate_limit
from app.db.session import get_session
from app.models.enums import SubOrderStatus
from app.modules.producers.catalog_service import ProducerCatalogService
from app.modules.producers.certification_service import CertificationService
from app.modules.producers.service import ProducerService
from app.schemas.catalog import InventoryUpdate
from app.schemas.certification import (
    CertificateDocumentLink,
    CertificationCatalogItem,
    ProducerCertificationInput,
    ProducerCertificationResponse,
)
from app.schemas.dashboard import (
    InventoryAlert,
    ProducerDashboard,
    ProducerOrderItem,
    ProducerProductItem,
    SettlementSummary,
)
from app.schemas.producer_catalog import (
    ProducerProductDetail,
    ProducerProfileResponse,
    ProducerProfileUpdate,
    ProductInput,
    VariantInput,
)

router = APIRouter(prefix="/producer", tags=["panel del productor"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/dashboard", response_model=ProducerDashboard, summary="Resumen del productor")
def get_dashboard(producer: ProducerUser, session: SessionDep) -> ProducerDashboard:
    """Ventas, pedidos pendientes, productos y calificaciones (HU-PRO-08)."""
    return ProducerService(session).get_dashboard(producer)


@router.get("/orders", response_model=Page[ProducerOrderItem], summary="Pedidos recibidos")
def list_orders(
    producer: ProducerUser,
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
    status: SubOrderStatus | None = None,
) -> Page[ProducerOrderItem]:
    return ProducerService(session).list_orders(producer, params, status)


@router.get("/products", response_model=Page[ProducerProductItem], summary="Mis productos")
def list_products(
    producer: ProducerUser, session: SessionDep, params: Annotated[PageParams, Depends()]
) -> Page[ProducerProductItem]:
    return ProducerService(session).list_products(producer, params)


@router.get(
    "/inventory/alerts",
    response_model=list[InventoryAlert],
    summary="Alertas de bajo inventario",
)
def inventory_alerts(producer: ProducerUser, session: SessionDep) -> list[InventoryAlert]:
    """Variantes cuyo stock disponible cayó bajo el umbral (HU-PRO-05, CA3)."""
    return ProducerService(session).list_inventory_alerts(producer)


@router.patch(
    "/inventory/{variant_id}",
    response_model=InventoryAlert,
    summary="Actualizar el stock de una presentación",
)
def update_inventory(
    variant_id: uuid.UUID,
    payload: InventoryUpdate,
    producer: ProducerUser,
    session: SessionDep,
) -> InventoryAlert:
    return ProducerService(session).update_inventory(
        producer, variant_id, payload.stock_qty, payload.low_stock_threshold
    )


@router.get(
    "/settlements/summary",
    response_model=SettlementSummary,
    summary="Resumen de liquidación pendiente",
)
def settlement_summary(producer: ProducerUser, session: SessionDep) -> SettlementSummary:
    """Ventas brutas, comisión y neto pendiente de pago (HU-PRO-11, CA2)."""
    return ProducerService(session).get_settlement_summary(producer)


# ======================================================================
# Publicación del catálogo propio
#
# El vendedor crea su café en borrador, le añade fotografías y
# presentaciones, y lo publica cuando reúne lo mínimo (HU-PRO-03).
# ======================================================================


@router.get(
    "/catalog",
    response_model=Page[ProducerProductDetail],
    summary="Mi catálogo, borradores incluidos",
)
def list_own_catalog(
    producer: ProducerUser,
    session: SessionDep,
    params: Annotated[PageParams, Depends()],
) -> Page[ProducerProductDetail]:
    return ProducerCatalogService(session).list_products(producer, params)


@router.post(
    "/catalog",
    response_model=ProducerProductDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar un café nuevo",
)
def create_product(
    payload: ProductInput, producer: ProducerUser, session: SessionDep
) -> ProducerProductDetail:
    """Crea el café en borrador; sale al catálogo con `/publish`."""
    return ProducerCatalogService(session).create_product(producer, payload)


@router.get(
    "/catalog/{product_id}",
    response_model=ProducerProductDetail,
    summary="Detalle de un café propio",
)
def get_own_product(
    product_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> ProducerProductDetail:
    return ProducerCatalogService(session).get_product(producer, product_id)


@router.put(
    "/catalog/{product_id}",
    response_model=ProducerProductDetail,
    summary="Editar un café propio",
)
def update_product(
    product_id: uuid.UUID,
    payload: ProductInput,
    producer: ProducerUser,
    session: SessionDep,
) -> ProducerProductDetail:
    return ProducerCatalogService(session).update_product(producer, product_id, payload)


@router.post(
    "/catalog/{product_id}/publish",
    response_model=ProducerProductDetail,
    summary="Sacar el café al catálogo",
)
def publish_product(
    product_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> ProducerProductDetail:
    """Falla indicando qué falta si el café aún no reúne los requisitos."""
    return ProducerCatalogService(session).publish(producer, product_id)


@router.post(
    "/catalog/{product_id}/unpublish",
    response_model=ProducerProductDetail,
    summary="Retirar el café del catálogo",
)
def unpublish_product(
    product_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> ProducerProductDetail:
    return ProducerCatalogService(session).unpublish(producer, product_id)


@router.post(
    "/catalog/{product_id}/images",
    response_model=ProducerProductDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Subir una fotografía del café",
    # Subir un archivo cuesta leerlo completo, validar su contenido real y
    # escribirlo en el almacenamiento: es la operación más cara de la API y la
    # única donde repetirla en bucle no le cuesta nada a quien lo hace.
    dependencies=[Depends(rate_limit("upload", limit=20, window_seconds=60))],
)
async def upload_product_image(
    product_id: uuid.UUID,
    producer: ProducerUser,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="JPEG, PNG o WebP, hasta 5 MB")],
    alt_text: Annotated[str | None, Form(max_length=200)] = None,
) -> ProducerProductDetail:
    """El archivo se valida por su contenido y se reescribe como JPEG."""
    stored = await validate_image(file)
    return ProducerCatalogService(session).add_image(producer, product_id, stored, alt_text)


@router.delete(
    "/catalog/{product_id}/images/{image_id}",
    response_model=ProducerProductDetail,
    summary="Eliminar una fotografía",
)
def delete_product_image(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    producer: ProducerUser,
    session: SessionDep,
) -> ProducerProductDetail:
    return ProducerCatalogService(session).delete_image(producer, product_id, image_id)


@router.post(
    "/catalog/{product_id}/variants",
    response_model=ProducerProductDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar una presentación",
)
def add_variant(
    product_id: uuid.UUID,
    payload: VariantInput,
    producer: ProducerUser,
    session: SessionDep,
) -> ProducerProductDetail:
    """Precio por kilo, mínimo de compra y kilos disponibles de una oferta."""
    return ProducerCatalogService(session).add_variant(producer, product_id, payload)


@router.put(
    "/catalog/{product_id}/variants/{variant_id}",
    response_model=ProducerProductDetail,
    summary="Editar una presentación",
)
def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: VariantInput,
    producer: ProducerUser,
    session: SessionDep,
) -> ProducerProductDetail:
    return ProducerCatalogService(session).update_variant(producer, product_id, variant_id, payload)


@router.delete(
    "/catalog/{product_id}/variants/{variant_id}",
    response_model=ProducerProductDetail,
    summary="Retirar una presentación",
)
def delete_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    producer: ProducerUser,
    session: SessionDep,
) -> ProducerProductDetail:
    return ProducerCatalogService(session).delete_variant(producer, product_id, variant_id)


# ======================================================================
# Certificaciones
#
# Respaldan lo que el café afirma ser. Llevan vigencia, y su documento
# no es público: se entrega con un enlace de vida corta (RF-04.5, RF-07.3).
# ======================================================================


@router.get(
    "/certifications/catalog",
    response_model=list[CertificationCatalogItem],
    summary="Certificaciones que puedo declarar",
)
def list_certification_catalog(
    producer: ProducerUser, session: SessionDep
) -> list[CertificationCatalogItem]:
    return CertificationService(session).list_catalog()


@router.get(
    "/certifications",
    response_model=list[ProducerCertificationResponse],
    summary="Mis certificaciones y su vigencia",
)
def list_own_certifications(
    producer: ProducerUser, session: SessionDep
) -> list[ProducerCertificationResponse]:
    """El estado se recalcula con la fecha, no se lee de un campo estático."""
    return CertificationService(session).list_own(producer)


@router.post(
    "/certifications",
    response_model=ProducerCertificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una certificación",
    dependencies=[Depends(rate_limit("upload", limit=20, window_seconds=60))],
)
async def add_certification(
    producer: ProducerUser,
    session: SessionDep,
    certification_id: Annotated[int, Form()],
    certificate_number: Annotated[str | None, Form(max_length=100)] = None,
    issued_at: Annotated[date | None, Form()] = None,
    expires_at: Annotated[date | None, Form()] = None,
    file: Annotated[UploadFile | None, File(description="PDF o imagen, hasta 10 MB")] = None,
) -> ProducerCertificationResponse:
    """El documento viaja en el mismo envío, en formato multiparte."""
    payload = ProducerCertificationInput(
        certification_id=certification_id,
        certificate_number=certificate_number,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    document = await validate_document(file) if file is not None else None
    return CertificationService(session).add(producer, payload, document)


@router.get(
    "/certifications/{certification_id}/document",
    response_model=CertificateDocumentLink,
    summary="Enlace temporal al documento",
)
def get_certificate_document(
    certification_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> CertificateDocumentLink:
    """Devuelve un enlace firmado que caduca en minutos."""
    return CertificationService(session).document_link(producer, certification_id)


@router.delete(
    "/certifications/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una certificación",
)
def delete_certification(
    certification_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> None:
    CertificationService(session).delete(producer, certification_id)


@router.get(
    "/catalog/{product_id}/certifications",
    response_model=list[CertificationCatalogItem],
    summary="Certificaciones declaradas en un café",
)
def list_product_certifications(
    product_id: uuid.UUID, producer: ProducerUser, session: SessionDep
) -> list[CertificationCatalogItem]:
    return CertificationService(session).list_product_certifications(producer, product_id)


@router.post(
    "/catalog/{product_id}/certifications/{certification_id}",
    response_model=list[CertificationCatalogItem],
    summary="Asociar una certificación al café",
)
def attach_certification(
    product_id: uuid.UUID,
    certification_id: int,
    producer: ProducerUser,
    session: SessionDep,
) -> list[CertificationCatalogItem]:
    """Solo se declara en un café lo que el productor tiene acreditado y vigente."""
    return CertificationService(session).attach_to_product(producer, product_id, certification_id)


@router.delete(
    "/catalog/{product_id}/certifications/{certification_id}",
    response_model=list[CertificationCatalogItem],
    summary="Quitar una certificación del café",
)
def detach_certification(
    product_id: uuid.UUID,
    certification_id: int,
    producer: ProducerUser,
    session: SessionDep,
) -> list[CertificationCatalogItem]:
    return CertificationService(session).detach_from_product(producer, product_id, certification_id)


# ======================================================================
# Perfil comercial
#
# El artículo 53 de la Ley 1480 de 2011 obliga a la plataforma a llevar
# un registro con la dirección de notificaciones y el teléfono de cada
# oferente. Sin estos datos no se puede publicar un café.
# ======================================================================


@router.get(
    "/profile",
    response_model=ProducerProfileResponse,
    summary="Datos de mi negocio",
)
def get_producer_profile(producer: ProducerUser, session: SessionDep) -> ProducerProfileResponse:
    return ProducerService(session).get_profile(producer)


@router.put(
    "/profile",
    response_model=ProducerProfileResponse,
    summary="Actualizar los datos de mi negocio",
)
def update_producer_profile(
    payload: ProducerProfileUpdate, producer: ProducerUser, session: SessionDep
) -> ProducerProfileResponse:
    """La razón social y el documento no se editan aquí: los verificó el equipo."""
    return ProducerService(session).update_profile(producer, payload)
