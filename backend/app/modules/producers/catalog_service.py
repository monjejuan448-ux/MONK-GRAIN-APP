"""Publicación y edición del catálogo propio del vendedor.

Cada operación arranca comprobando que el café pertenece a quien lo pide. Ese
control se repite en todos los métodos a propósito: es la frontera que impide
que un productor toque el catálogo de otro, y no debe depender de que quien
llame se acuerde de verificarlo antes.

El café nace en borrador y solo se publica cuando reúne lo mínimo para que un
comprador pueda decidir: descripción, una fotografía y al menos una presentación
a la venta.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.files import StoredFile
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate_query
from app.integrations.storage import get_storage
from app.models.catalog import (
    CoffeeAttributes,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
)
from app.models.enums import ProductStatus
from app.models.producer import Farm, ProducerProfile
from app.models.user import User
from app.schemas.producer_catalog import (
    CoffeeAttributesInput,
    ProducerProductDetail,
    ProductImageResponse,
    ProductInput,
    VariantDetail,
    VariantInput,
)

logger = get_logger(__name__)

MAX_IMAGES_PER_PRODUCT = 8


def slugify(value: str) -> str:
    """Convierte un nombre en un identificador para la URL.

    Se descartan los acentos en vez de codificarlos: `café-huila` es más legible
    y más fácil de compartir que su versión con caracteres escapados.
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return slug or "cafe"


class ProducerCatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.storage = get_storage()

    # ------------------------------------------------------------------
    # Acceso y pertenencia
    # ------------------------------------------------------------------
    def _profile(self, user: User) -> ProducerProfile:
        if user.producer_profile is None:
            raise ForbiddenError("Tu cuenta no tiene un perfil de productor.")
        return user.producer_profile

    def _owned_product(self, user: User, product_id: uuid.UUID) -> Product:
        """Recupera un café comprobando que es de quien lo pide."""
        profile = self._profile(user)
        product = self.session.scalar(
            select(Product)
            .where(Product.id == product_id, Product.deleted_at.is_(None))
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.inventory),
                selectinload(Product.attributes),
                # `_missing_to_publish` consulta los datos de notificación del
                # vendedor; sin cargarlos aquí, cada café del listado dispararía
                # una consulta extra.
                joinedload(Product.producer),
            )
            # Sin `populate_existing`, SQLAlchemy devuelve el objeto que ya tiene
            # en la sesión con sus colecciones tal como se cargaron antes: una
            # imagen o una presentación recién añadida no aparecería en la
            # respuesta de la propia operación que acaba de crearla.
            .execution_options(populate_existing=True)
        )
        if product is None:
            raise NotFoundError("No encontramos este café.")
        # Mismo mensaje que si no existiera sería preferible para no revelar su
        # existencia, pero aquí el dueño legítimo necesita saber que el café es
        # ajeno y no que se ha borrado.
        if product.producer_id != profile.id:
            raise ForbiddenError("Este café no pertenece a tu catálogo.")
        return product

    def _unique_slug(self, name: str) -> str:
        """Añade un sufijo si el slug ya está tomado por otro café."""
        base = slugify(name)
        candidate = base
        suffix = 2
        while self.session.scalar(select(Product.id).where(Product.slug == candidate)) is not None:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    # ------------------------------------------------------------------
    # Alta y edición
    # ------------------------------------------------------------------
    def create_product(self, user: User, payload: ProductInput) -> ProducerProductDetail:
        """Crea el café en borrador."""
        profile = self._profile(user)

        if profile.status != "approved":
            raise ForbiddenError(
                "Tu solicitud de vendedor aún no fue aprobada. "
                "Podrás publicar cafés cuando el equipo la revise."
            )

        if payload.farm_id is not None:
            self._assert_own_farm(profile, payload.farm_id)

        product = Product(
            producer_id=profile.id,
            farm_id=payload.farm_id,
            category_id=payload.category_id,
            slug=self._unique_slug(payload.name),
            name=payload.name,
            description=payload.description,
            state=payload.state,
            # Nace en borrador: publicar es un acto explícito y con requisitos.
            status=ProductStatus.DRAFT,
            base_price=payload.base_price,
            wholesale_price=payload.wholesale_price,
            wholesale_min_qty=payload.wholesale_min_qty,
            dispatch_days=payload.dispatch_days,
            storage_conditions=payload.storage_conditions,
            allows_samples=payload.allows_samples,
        )
        self.session.add(product)
        self.session.flush()

        self._apply_attributes(product, payload.attributes)
        self.session.commit()

        logger.info("product_created", product_id=str(product.id), producer_id=str(profile.id))
        return self._to_detail(self._owned_product(user, product.id))

    def update_product(
        self, user: User, product_id: uuid.UUID, payload: ProductInput
    ) -> ProducerProductDetail:
        """Edita los datos del café.

        El `slug` no se regenera al renombrar: cambiarlo rompería los enlaces ya
        compartidos y las referencias de los buscadores.
        """
        product = self._owned_product(user, product_id)

        if payload.farm_id is not None:
            self._assert_own_farm(product.producer, payload.farm_id)

        product.name = payload.name
        product.description = payload.description
        product.state = payload.state
        product.base_price = payload.base_price
        product.wholesale_price = payload.wholesale_price
        product.wholesale_min_qty = payload.wholesale_min_qty
        product.farm_id = payload.farm_id
        product.category_id = payload.category_id
        product.dispatch_days = payload.dispatch_days
        product.storage_conditions = payload.storage_conditions
        product.allows_samples = payload.allows_samples

        self._apply_attributes(product, payload.attributes)
        self.session.commit()

        logger.info("product_updated", product_id=str(product.id))
        return self._to_detail(self._owned_product(user, product_id))

    def _assert_own_farm(self, profile: ProducerProfile, farm_id: uuid.UUID) -> None:
        farm = self.session.get(Farm, farm_id)
        if farm is None or farm.producer_id != profile.id:
            raise ForbiddenError("Esta finca no pertenece a tu perfil.")

    def _apply_attributes(self, product: Product, payload: CoffeeAttributesInput) -> None:
        attributes = product.attributes or CoffeeAttributes(product_id=product.id)
        for field, value in payload.model_dump().items():
            setattr(attributes, field, value)
        self.session.add(attributes)

    # ------------------------------------------------------------------
    # Publicación
    # ------------------------------------------------------------------
    def _missing_to_publish(self, product: Product) -> list[str]:
        """Requisitos que faltan para que el café pueda salir al catálogo."""
        missing: list[str] = []
        if not product.images:
            missing.append("Agrega al menos una fotografía del café.")
        sellable = (v for v in product.variants if v.is_active and v.deleted_at is None)
        if not any(sellable):
            missing.append("Agrega al menos una presentación a la venta.")
        if len(product.description.strip()) < 20:
            missing.append("La descripción debe tener al menos 20 caracteres.")

        # El artículo 53 de la Ley 1480 de 2011 obliga a la plataforma a tener
        # la dirección de notificaciones y el teléfono de cada oferente, para
        # poder entregárselos a quien presente una reclamación. Se comprueba al
        # publicar y no al crear el perfil porque es el momento en que el
        # vendedor empieza a ofrecer al público.
        producer = product.producer
        if producer is not None and not (producer.notification_address or "").strip():
            missing.append(
                "Registra la dirección de notificaciones de tu negocio en tu perfil: "
                "la ley exige tenerla para atender reclamaciones."
            )
        if producer is not None and not (producer.contact_phone or "").strip():
            missing.append("Registra un teléfono de contacto en tu perfil.")

        return missing

    def publish(self, user: User, product_id: uuid.UUID) -> ProducerProductDetail:
        """Saca el café al catálogo público."""
        product = self._owned_product(user, product_id)

        missing = self._missing_to_publish(product)
        if missing:
            raise BusinessRuleError(
                "Este café todavía no puede publicarse.", details={"missing": missing}
            )

        product.status = ProductStatus.PUBLISHED
        # Se conserva la primera fecha de publicación: es la que ordena el
        # catálogo por novedad, y despublicar y volver a publicar no debería
        # devolver un café antiguo a los primeros puestos.
        product.published_at = product.published_at or datetime.now(UTC)
        self.session.commit()

        logger.info("product_published", product_id=str(product.id))
        return self._to_detail(self._owned_product(user, product_id))

    def unpublish(self, user: User, product_id: uuid.UUID) -> ProducerProductDetail:
        """Retira el café del catálogo sin borrarlo.

        Los pedidos que ya lo incluyen conservan su copia inmutable de nombre y
        precio, así que retirarlo no altera el historial de nadie.
        """
        product = self._owned_product(user, product_id)
        product.status = ProductStatus.UNPUBLISHED
        self.session.commit()

        logger.info("product_unpublished", product_id=str(product.id))
        return self._to_detail(self._owned_product(user, product_id))

    # ------------------------------------------------------------------
    # Imágenes
    # ------------------------------------------------------------------
    def add_image(
        self, user: User, product_id: uuid.UUID, stored: StoredFile, alt_text: str | None
    ) -> ProducerProductDetail:
        product = self._owned_product(user, product_id)

        if len(product.images) >= MAX_IMAGES_PER_PRODUCT:
            raise BusinessRuleError(
                f"Un café admite hasta {MAX_IMAGES_PER_PRODUCT} fotografías. "
                "Elimina alguna antes de subir otra."
            )

        key = stored.key_for(f"products/{product.id}")
        self.storage.put(key, stored.content, stored.content_type)

        image = ProductImage(
            product_id=product.id,
            image_key=key,
            # Sin texto alternativo la ficha queda inaccesible para quien usa
            # lector de pantalla; el nombre del café es mejor que nada.
            alt_text=alt_text or product.name,
            sort_order=len(product.images),
            is_primary=not product.images,
        )
        self.session.add(image)
        self.session.commit()

        logger.info("product_image_added", product_id=str(product.id), key=key)
        return self._to_detail(self._owned_product(user, product_id))

    def delete_image(
        self, user: User, product_id: uuid.UUID, image_id: uuid.UUID
    ) -> ProducerProductDetail:
        product = self._owned_product(user, product_id)

        image = next((img for img in product.images if img.id == image_id), None)
        if image is None:
            raise NotFoundError("No encontramos esta fotografía.")

        was_primary = image.is_primary
        key = image.image_key

        self.session.delete(image)
        self.session.flush()

        # La ficha necesita una imagen principal: si se borró esa, asciende la
        # siguiente en vez de dejar el café sin portada.
        remaining = [img for img in product.images if img.id != image_id]
        if was_primary and remaining:
            remaining[0].is_primary = True

        self.session.commit()
        self.storage.delete(key)

        logger.info("product_image_deleted", product_id=str(product.id), key=key)
        return self._to_detail(self._owned_product(user, product_id))

    # ------------------------------------------------------------------
    # Presentaciones
    # ------------------------------------------------------------------
    def add_variant(
        self, user: User, product_id: uuid.UUID, payload: VariantInput
    ) -> ProducerProductDetail:
        product = self._owned_product(user, product_id)

        variant = ProductVariant(
            product_id=product.id,
            sku=self._build_sku(product, payload),
            presentation=payload.presentation,
            min_qty_kg=payload.min_qty_kg,
            price=payload.price,
            wholesale_price=payload.wholesale_price,
            is_active=payload.is_active,
        )
        self.session.add(variant)
        self.session.flush()

        self.session.add(
            Inventory(
                variant_id=variant.id,
                stock_qty=payload.stock_qty,
                reserved_qty=0,
                low_stock_threshold=payload.low_stock_threshold,
            )
        )
        self.session.commit()

        logger.info("variant_added", product_id=str(product.id), variant_id=str(variant.id))
        return self._to_detail(self._owned_product(user, product_id))

    def update_variant(
        self, user: User, product_id: uuid.UUID, variant_id: uuid.UUID, payload: VariantInput
    ) -> ProducerProductDetail:
        product = self._owned_product(user, product_id)

        variant = next((v for v in product.variants if v.id == variant_id), None)
        if variant is None:
            raise NotFoundError("No encontramos esta presentación.")

        variant.presentation = payload.presentation
        variant.min_qty_kg = payload.min_qty_kg
        variant.price = payload.price
        variant.wholesale_price = payload.wholesale_price
        variant.is_active = payload.is_active

        if variant.inventory is not None:
            if payload.stock_qty < variant.inventory.reserved_qty:
                raise BusinessRuleError(
                    f"No puedes dejar el stock por debajo de las "
                    f"{variant.inventory.reserved_qty} unidades ya reservadas."
                )
            variant.inventory.stock_qty = payload.stock_qty
            variant.inventory.low_stock_threshold = payload.low_stock_threshold

        self.session.commit()
        return self._to_detail(self._owned_product(user, product_id))

    def delete_variant(
        self, user: User, product_id: uuid.UUID, variant_id: uuid.UUID
    ) -> ProducerProductDetail:
        """Retira una presentación.

        Se marca como eliminada en vez de borrarla: los pedidos históricos
        apuntan a ella y una baja física dejaría líneas de pedido sin referencia.
        """
        product = self._owned_product(user, product_id)

        variant = next((v for v in product.variants if v.id == variant_id), None)
        if variant is None:
            raise NotFoundError("No encontramos esta presentación.")

        if variant.inventory is not None and variant.inventory.reserved_qty > 0:
            raise BusinessRuleError(
                "Esta presentación tiene unidades reservadas en pedidos en curso. "
                "Podrás retirarla cuando esos pedidos se completen."
            )

        variant.deleted_at = datetime.now(UTC)
        variant.is_active = False
        self.session.commit()

        logger.info("variant_deleted", product_id=str(product.id), variant_id=str(variant_id))
        return self._to_detail(self._owned_product(user, product_id))

    def _build_sku(self, product: Product, payload: VariantInput) -> str:
        """Referencia legible y única de la oferta.

        Se compone del nombre del lote y su mínimo en kilos, que es lo que la
        distingue de otra oferta del mismo café.
        """
        base = slugify(product.name)[:28].upper()
        presentation = slugify(payload.presentation)[:10].upper() or "STD"
        candidate = f"{base}-{payload.min_qty_kg}KG-{presentation}"
        suffix = 2
        while (
            self.session.scalar(select(ProductVariant.id).where(ProductVariant.sku == candidate))
            is not None
        ):
            candidate = f"{base}-{payload.min_qty_kg}KG-{presentation}-{suffix}"
            suffix += 1
        return candidate[:60]

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def get_product(self, user: User, product_id: uuid.UUID) -> ProducerProductDetail:
        return self._to_detail(self._owned_product(user, product_id))

    def list_products(self, user: User, params: PageParams) -> Page[ProducerProductDetail]:
        """Todos los cafés del vendedor, incluidos los borradores."""
        profile = self._profile(user)
        statement = (
            select(Product)
            .where(Product.producer_id == profile.id, Product.deleted_at.is_(None))
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.inventory),
                selectinload(Product.attributes),
                # `_missing_to_publish` consulta los datos de notificación del
                # vendedor; sin cargarlos aquí, cada café del listado dispararía
                # una consulta extra.
                joinedload(Product.producer),
            )
            .order_by(Product.created_at.desc())
        )
        products, total = paginate_query(self.session, statement, params)
        return Page.create([self._to_detail(product) for product in products], total, params)

    def _to_detail(self, product: Product) -> ProducerProductDetail:
        images = sorted(product.images, key=lambda img: img.sort_order)
        variants = [v for v in product.variants if v.deleted_at is None]

        return ProducerProductDetail(
            id=product.id,
            slug=product.slug,
            name=product.name,
            description=product.description,
            state=product.state,
            status=product.status,
            base_price=product.base_price,
            wholesale_price=product.wholesale_price,
            wholesale_min_qty=product.wholesale_min_qty,
            currency=product.currency,
            dispatch_days=product.dispatch_days,
            storage_conditions=product.storage_conditions,
            allows_samples=product.allows_samples,
            images=[
                ProductImageResponse(
                    id=image.id,
                    image_url=self.storage.public_url(image.image_key),
                    alt_text=image.alt_text,
                    sort_order=image.sort_order,
                    is_primary=image.is_primary,
                )
                for image in images
            ],
            variants=[
                VariantDetail(
                    id=variant.id,
                    sku=variant.sku,
                    label=variant.label,
                    presentation=variant.presentation,
                    min_qty_kg=variant.min_qty_kg,
                    price=variant.price,
                    wholesale_price=variant.wholesale_price,
                    is_active=variant.is_active,
                    stock_qty=variant.inventory.stock_qty if variant.inventory else 0,
                    reserved_qty=variant.inventory.reserved_qty if variant.inventory else 0,
                )
                for variant in variants
            ],
            attributes=(
                CoffeeAttributesInput.model_validate(product.attributes, from_attributes=True)
                if product.attributes
                else None
            ),
            missing_to_publish=self._missing_to_publish(product),
        )
