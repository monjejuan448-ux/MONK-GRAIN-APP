"""Reglas de negocio del catálogo."""

import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams
from app.models.catalog import Product, ProductVariant
from app.models.enums import RoleCode
from app.models.producer import ProducerProfile
from app.models.user import User
from app.modules.catalog.repository import CatalogRepository
from app.schemas.catalog import (
    CertificationResponse,
    CoffeeAttributesResponse,
    FarmSummary,
    ProducerDetail,
    ProducerListItem,
    ProducerSummary,
    ProductDetail,
    ProductFilters,
    ProductImageResponse,
    ProductListItem,
    VariantResponse,
)


def build_media_url(key: str | None) -> str | None:
    """Convierte una clave de almacenamiento en URL pública."""
    if not key:
        return None
    if key.startswith(("http://", "https://")):
        return key
    return f"{settings.s3_public_url}/{settings.s3_bucket}/{key}"


def can_see_wholesale_prices(user: User | None) -> bool:
    """Solo un comprador empresarial verificado ve precios mayoristas.

    La comprobación se hace aquí y no en la interfaz: si dependiera del
    frontend, bastaría con llamar a la API directamente para verlos
    (HU-CE-02, CA2).
    """
    if user is None:
        return False
    if RoleCode.ADMIN.value in user.role_codes:
        return True
    return (
        RoleCode.BUSINESS.value in user.role_codes
        and user.business_profile is not None
        and user.business_profile.is_verified
    )


class CatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CatalogRepository(session)

    # ------------------------------------------------------------------
    # Listado y detalle
    # ------------------------------------------------------------------
    def list_products(
        self, filters: ProductFilters, params: PageParams, user: User | None = None
    ) -> Page[ProductListItem]:
        products, total = self.repo.list_products(filters, params)
        items = [self._to_list_item(product) for product in products]
        return Page.create(items, total, params)

    def get_product_detail(self, slug: str, user: User | None = None) -> ProductDetail:
        product = self.repo.get_product_by_slug(slug)
        if product is None:
            raise NotFoundError("No encontramos este café.")

        show_wholesale = can_see_wholesale_prices(user)
        base = self._to_list_item(product)
        certifications = self.repo.get_product_certifications(product.id)

        return ProductDetail(
            **base.model_dump(),
            description=product.description,
            images=[
                ProductImageResponse(
                    id=image.id,
                    image_key=build_media_url(image.image_key) or "",
                    alt_text=image.alt_text,
                    is_primary=image.is_primary,
                )
                for image in sorted(product.images, key=lambda i: (not i.is_primary, i.sort_order))
            ],
            variants=[
                self._to_variant(variant, show_wholesale)
                for variant in product.variants
                if variant.is_active and variant.deleted_at is None
            ],
            attributes=(
                CoffeeAttributesResponse.model_validate(product.attributes)
                if product.attributes
                else None
            ),
            certifications=[
                CertificationResponse.model_validate(certification)
                for certification in certifications
            ],
            farm=FarmSummary.model_validate(product.farm) if product.farm else None,
            category=None,
            dispatch_days=product.dispatch_days,
            storage_conditions=product.storage_conditions,
            allows_samples=product.allows_samples,
            created_at=product.created_at,
        )

    def get_related_products(self, slug: str) -> list[ProductListItem]:
        product = self.repo.get_product_by_slug(slug)
        if product is None:
            raise NotFoundError("No encontramos este café.")
        return [self._to_list_item(related) for related in self.repo.get_related_products(product)]

    # ------------------------------------------------------------------
    # Productores
    # ------------------------------------------------------------------
    def list_producers(
        self,
        params: PageParams,
        department: str | None = None,
        region: str | None = None,
        producer_type: str | None = None,
    ) -> Page[ProducerListItem]:
        producers, total = self.repo.list_producers(params, department, region, producer_type)
        # Un único conteo agrupado para todo el listado, en vez de uno por
        # productor: evita el problema N+1.
        counts = self.repo.count_products_by_producer([p.id for p in producers])
        items = [
            self._to_producer_item(producer, counts.get(producer.id, 0)) for producer in producers
        ]
        return Page.create(items, total, params)

    def get_producer_detail(self, producer_id: uuid.UUID) -> ProducerDetail:
        producer = self.repo.get_producer(producer_id)
        if producer is None:
            raise NotFoundError("No encontramos este productor.")

        products, _ = self.repo.list_products(
            ProductFilters(producer_id=producer.id, sort="rating"),
            PageParams(page=1, page_size=12),
        )
        base = self._to_producer_item(producer)

        return ProducerDetail(
            **base.model_dump(),
            farms=[FarmSummary.model_validate(farm) for farm in producer.farms],
            certifications=[],
            products=[self._to_list_item(product) for product in products],
        )

    # ------------------------------------------------------------------
    # Conversión a schemas
    # ------------------------------------------------------------------
    def _to_list_item(self, product: Product) -> ProductListItem:
        primary_image = next(
            (image for image in product.images if image.is_primary),
            product.images[0] if product.images else None,
        )
        farm = product.farm
        municipality = farm.municipality if farm else None

        # Kilos vendibles sumando las variantes activas. Se calcula aquí y no en
        # la consulta porque las variantes ya vienen cargadas: una agregación en
        # SQL añadiría un recorrido a la tabla sin ahorrar nada.
        available_kg = sum(
            variant.inventory.available_qty
            for variant in product.variants
            if variant.is_active and variant.deleted_at is None and variant.inventory is not None
        )

        return ProductListItem(
            id=product.id,
            slug=product.slug,
            name=product.name,
            state=product.state,
            base_price=product.base_price,
            currency=product.currency,
            primary_image_url=build_media_url(primary_image.image_key) if primary_image else None,
            producer=ProducerSummary(
                id=product.producer.id,
                legal_name=product.producer.legal_name,
                brand_name=product.producer.brand_name,
                type=product.producer.type.value,
                logo_key=build_media_url(product.producer.logo_key),
                rating_avg=product.producer.rating_avg,
            ),
            region=farm.region.name if farm and farm.region else None,
            municipality=municipality.name if municipality else None,
            department=municipality.department.name if municipality else None,
            yield_factor=product.attributes.yield_factor if product.attributes else None,
            moisture_pct=product.attributes.moisture_pct if product.attributes else None,
            available_kg=available_kg,
            rating_avg=product.rating_avg,
            rating_count=product.rating_count,
            is_available=available_kg > 0,
        )

    def _to_variant(self, variant: ProductVariant, show_wholesale: bool) -> VariantResponse:
        return VariantResponse(
            id=variant.id,
            sku=variant.sku,
            presentation=variant.presentation,
            min_qty_kg=variant.min_qty_kg,
            price=variant.price,
            # El precio mayorista se omite por completo si no corresponde: no se
            # envía y se oculta en la interfaz, se envía solo a quien puede verlo.
            wholesale_price=variant.wholesale_price if show_wholesale else None,
            available_qty=variant.inventory.available_qty if variant.inventory else 0,
            is_active=variant.is_active,
        )

    def _to_producer_item(
        self, producer: ProducerProfile, product_count: int | None = None
    ) -> ProducerListItem:
        first_farm = producer.farms[0] if producer.farms else None
        municipality = first_farm.municipality if first_farm else None

        return ProducerListItem(
            id=producer.id,
            legal_name=producer.legal_name,
            brand_name=producer.brand_name,
            type=producer.type.value,
            logo_key=build_media_url(producer.logo_key),
            cover_key=build_media_url(producer.cover_key),
            story=producer.story,
            municipality=municipality.name if municipality else None,
            department=municipality.department.name if municipality else None,
            rating_avg=producer.rating_avg,
            rating_count=producer.rating_count,
            product_count=(
                product_count
                if product_count is not None
                else self.repo.count_producer_products(producer.id)
            ),
        )
