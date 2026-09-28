"""Consultas del catálogo."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.pagination import PageParams, paginate_query
from app.models.catalog import (
    CoffeeAttributes,
    Inventory,
    Product,
    ProductCertification,
    ProductVariant,
    Review,
)
from app.models.enums import ProductStatus, ReviewStatus
from app.models.geo import Department, Municipality, Region
from app.models.producer import Certification, Farm, ProducerProfile
from app.schemas.catalog import ProductFilters

# Estados en los que una reseña se muestra y cuenta para el promedio. Una
# denuncia sin resolver no es una decisión de moderación: la reseña sigue ahí
# hasta que un administrador la oculte.
VISIBLE_REVIEW_STATUSES = (ReviewStatus.PUBLISHED, ReviewStatus.REPORTED)


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Consultas base
    # ------------------------------------------------------------------
    def _published_products(self) -> Select[tuple[Product]]:
        """Productos visibles al público.

        Un producto es comprable solo si está publicado, no eliminado y su
        vendedor está aprobado y no suspendido: la suspensión de un vendedor
        retira su catálogo sin borrar nada (HU-ADM-02, CA3).
        """
        return (
            select(Product)
            .join(ProducerProfile, Product.producer_id == ProducerProfile.id)
            .where(
                Product.status == ProductStatus.PUBLISHED,
                Product.deleted_at.is_(None),
                ProducerProfile.status == "approved",
                ProducerProfile.deleted_at.is_(None),
            )
        )

    def _with_listing_relations(self, statement: Select[tuple[Product]]) -> Select[tuple[Product]]:
        """Carga anticipada de lo que necesita el listado.

        Sin esto, renderizar 20 productos dispararía más de 60 consultas
        adicionales (el problema N+1).
        """
        return statement.options(
            joinedload(Product.producer).joinedload(ProducerProfile.user),
            joinedload(Product.attributes),
            joinedload(Product.farm)
            .joinedload(Farm.municipality)
            .joinedload(Municipality.department),
            joinedload(Product.farm).joinedload(Farm.region),
            selectinload(Product.images),
            selectinload(Product.variants).joinedload(ProductVariant.inventory),
        )

    # ------------------------------------------------------------------
    # Listado con filtros
    # ------------------------------------------------------------------
    def list_products(
        self, filters: ProductFilters, params: PageParams
    ) -> tuple[list[Product], int]:
        statement = self._published_products()
        statement = self._apply_filters(statement, filters)
        statement = self._apply_sorting(statement, filters.sort)
        statement = self._with_listing_relations(statement)

        return paginate_query(self.session, statement, params)

    def _apply_filters(
        self, statement: Select[tuple[Product]], filters: ProductFilters
    ) -> Select[tuple[Product]]:
        """Aplica los filtros combinables del catálogo."""
        # Ordenar por puntaje también requiere la tabla de atributos, aunque no
        # se esté filtrando por ninguno de sus campos.
        needs_attributes = (
            any((filters.variety, filters.process, filters.roast, filters.min_score is not None))
            or filters.sort == "score"
        )
        needs_geography = any((filters.department, filters.municipality, filters.region))

        if needs_attributes:
            statement = statement.join(CoffeeAttributes, CoffeeAttributes.product_id == Product.id)
        if needs_geography:
            statement = (
                statement.join(Farm, Product.farm_id == Farm.id)
                .join(Municipality, Farm.municipality_id == Municipality.id)
                .join(Department, Municipality.department_id == Department.id)
                .outerjoin(Region, Farm.region_id == Region.id)
            )

        if filters.q:
            # Búsqueda por nombre de producto, marca del productor o municipio.
            # `unaccent` permite que "narino" encuentre "Nariño"; `ilike` cubre
            # coincidencias parciales sin exigir la palabra completa.
            pattern = f"%{filters.q.strip()}%"
            statement = statement.where(
                or_(
                    func.unaccent(Product.name).ilike(func.unaccent(pattern)),
                    func.unaccent(Product.description).ilike(func.unaccent(pattern)),
                    func.unaccent(ProducerProfile.brand_name).ilike(func.unaccent(pattern)),
                    func.unaccent(ProducerProfile.legal_name).ilike(func.unaccent(pattern)),
                )
            )

        if filters.department:
            statement = statement.where(Department.dane_code == filters.department)
        if filters.municipality:
            statement = statement.where(Municipality.dane_code == filters.municipality)
        if filters.region:
            statement = statement.where(Region.code == filters.region)

        if filters.variety:
            statement = statement.where(
                func.unaccent(CoffeeAttributes.variety).ilike(func.unaccent(f"%{filters.variety}%"))
            )
        if filters.process:
            statement = statement.where(CoffeeAttributes.process == filters.process)
        if filters.roast:
            statement = statement.where(CoffeeAttributes.roast == filters.roast)
        if filters.min_score is not None:
            statement = statement.where(CoffeeAttributes.cupping_score >= filters.min_score)

        if filters.state:
            statement = statement.where(Product.state == filters.state)
        if filters.producer_id:
            statement = statement.where(Product.producer_id == filters.producer_id)
        if filters.min_price is not None:
            statement = statement.where(Product.base_price >= filters.min_price)
        if filters.max_price is not None:
            statement = statement.where(Product.base_price <= filters.max_price)

        if filters.certification:
            statement = statement.where(
                Product.id.in_(
                    select(ProductCertification.product_id)
                    .join(
                        Certification,
                        Certification.id == ProductCertification.certification_id,
                    )
                    .where(Certification.code == filters.certification)
                )
            )

        return statement

    def _apply_sorting(
        self, statement: Select[tuple[Product]], sort: str
    ) -> Select[tuple[Product]]:
        """Ordena el conjunto ya filtrado (HU-VIS-03, CA4)."""
        ordering: dict[str, ColumnElement[Any]] = {
            "price_asc": Product.base_price.asc(),
            "price_desc": Product.base_price.desc(),
            "rating": Product.rating_avg.desc(),
            "popular": Product.sales_count.desc(),
            "newest": Product.published_at.desc(),
            "score": CoffeeAttributes.cupping_score.desc().nullslast(),
        }
        # El identificador desempata para que la paginación sea estable: sin un
        # criterio único, dos productos con el mismo precio podrían alternar de
        # página entre consultas.
        return statement.order_by(ordering.get(sort, Product.published_at.desc()), Product.id)

    # ------------------------------------------------------------------
    # Detalle
    # ------------------------------------------------------------------
    def get_product_by_slug(self, slug: str) -> Product | None:
        statement = self._published_products().where(Product.slug == slug)
        statement = self._with_listing_relations(statement).options(selectinload(Product.reviews))
        return self.session.scalars(statement).unique().one_or_none()

    def get_product_by_id(self, product_id: uuid.UUID) -> Product | None:
        return self.session.get(Product, product_id)

    def get_product_certifications(self, product_id: uuid.UUID) -> list[Certification]:
        return list(
            self.session.scalars(
                select(Certification)
                .join(
                    ProductCertification,
                    ProductCertification.certification_id == Certification.id,
                )
                .where(ProductCertification.product_id == product_id)
            ).all()
        )

    def get_related_products(self, product: Product, limit: int = 4) -> list[Product]:
        """Productos afines: misma región o mismo productor."""
        statement = (
            self._published_products()
            .where(Product.id != product.id)
            .where(
                or_(
                    Product.producer_id == product.producer_id,
                    Product.category_id == product.category_id,
                )
            )
            .order_by(Product.rating_avg.desc())
            .limit(limit)
        )
        return list(self.session.scalars(self._with_listing_relations(statement)).unique().all())

    # ------------------------------------------------------------------
    # Variantes e inventario
    # ------------------------------------------------------------------
    def get_variant(self, variant_id: uuid.UUID) -> ProductVariant | None:
        return self.session.scalar(
            select(ProductVariant)
            .where(
                ProductVariant.id == variant_id,
                ProductVariant.deleted_at.is_(None),
                ProductVariant.is_active.is_(True),
            )
            .options(
                joinedload(ProductVariant.inventory),
                joinedload(ProductVariant.product).joinedload(Product.producer),
            )
        )

    def get_variant_for_update(self, variant_id: uuid.UUID) -> Inventory | None:
        """Bloquea la fila de inventario para modificarla con seguridad.

        `FOR UPDATE` impide que dos compras simultáneas del mismo lote lean el
        mismo stock y lo descuenten dos veces (HU-PRO-05, CA4).
        """
        return self.session.scalar(
            select(Inventory).where(Inventory.variant_id == variant_id).with_for_update()
        )

    # ------------------------------------------------------------------
    # Productores
    # ------------------------------------------------------------------
    def list_producers(
        self,
        params: PageParams,
        department: str | None = None,
        region: str | None = None,
        producer_type: str | None = None,
    ) -> tuple[list[ProducerProfile], int]:
        statement = (
            select(ProducerProfile)
            .where(
                ProducerProfile.status == "approved",
                ProducerProfile.deleted_at.is_(None),
            )
            # `selectinload` para las colecciones: `joinedload` multiplicaría las
            # filas del productor por cada finca y falsearía la paginación.
            # El departamento se carga junto al municipio para no dispararar una
            # consulta por productor al leerlo después.
            .options(
                selectinload(ProducerProfile.farms)
                .joinedload(Farm.municipality)
                .joinedload(Municipality.department),
                selectinload(ProducerProfile.certifications),
            )
        )

        if department:
            statement = statement.join(
                Department, ProducerProfile.department_id == Department.id
            ).where(Department.dane_code == department)

        if producer_type:
            statement = statement.where(ProducerProfile.type == producer_type)

        if region:
            statement = statement.where(
                ProducerProfile.id.in_(
                    select(Farm.producer_id)
                    .join(Region, Farm.region_id == Region.id)
                    .where(Region.code == region)
                )
            )

        statement = statement.order_by(ProducerProfile.rating_avg.desc(), ProducerProfile.id)
        return paginate_query(self.session, statement, params)

    def get_producer(self, producer_id: uuid.UUID) -> ProducerProfile | None:
        return self.session.scalar(
            select(ProducerProfile)
            .where(
                ProducerProfile.id == producer_id,
                ProducerProfile.status == "approved",
                ProducerProfile.deleted_at.is_(None),
            )
            .options(
                selectinload(ProducerProfile.farms).joinedload(Farm.municipality),
                selectinload(ProducerProfile.farms).joinedload(Farm.region),
                selectinload(ProducerProfile.certifications),
            )
        )

    def count_products_by_producer(self, producer_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Cuenta los productos publicados de varios productores de una vez.

        Consultar uno por uno provocaría el problema N+1: un listado de cien
        productores dispararía cien consultas de conteo.
        """
        if not producer_ids:
            return {}

        rows = self.session.execute(
            select(Product.producer_id, func.count(Product.id))
            .where(
                Product.producer_id.in_(producer_ids),
                Product.status == ProductStatus.PUBLISHED,
                Product.deleted_at.is_(None),
            )
            .group_by(Product.producer_id)
        ).all()

        counts = dict.fromkeys(producer_ids, 0)
        counts.update({row[0]: int(row[1]) for row in rows})
        return counts

    def count_producer_products(self, producer_id: uuid.UUID) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(Product)
                .where(
                    Product.producer_id == producer_id,
                    Product.status == ProductStatus.PUBLISHED,
                    Product.deleted_at.is_(None),
                )
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Reseñas
    # ------------------------------------------------------------------
    def list_product_reviews(
        self, product_id: uuid.UUID, params: PageParams
    ) -> tuple[list[Review], int]:
        statement = (
            select(Review)
            .where(
                Review.product_id == product_id,
                Review.status.in_(VISIBLE_REVIEW_STATUSES),
                Review.deleted_at.is_(None),
            )
            .order_by(Review.created_at.desc(), Review.id)
        )
        return paginate_query(self.session, statement, params)

    def recalculate_product_rating(self, product_id: uuid.UUID) -> None:
        """Recalcula el promedio del producto y de su productor.

        Se invoca al publicar, editar, eliminar u ocultar una reseña. Solo una
        decisión de moderación —`HIDDEN`— retira una reseña del promedio
        (HU-ADM-06, CA3). Una reseña meramente denunciada sigue contando: si
        bastara con reportarla para que dejara de pesar en la calificación, el
        botón de denunciar sería un modo indirecto de silenciar cualquier
        opinión incómoda, que es justo lo que se quiso evitar al no ocultarla.

        Los dos `flush` de este método no son ceremonia. La sesión de la
        aplicación se crea con `autoflush=False`, de modo que una consulta no
        ve los cambios que todavía están en memoria. Quien llama aquí acaba de
        modificar una reseña —darla de baja, ocultarla— y sin escribirla antes
        la agregación contaría la versión anterior.
        """
        self.session.flush()

        aggregate = self.session.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.product_id == product_id,
                Review.status.in_(VISIBLE_REVIEW_STATUSES),
                Review.deleted_at.is_(None),
            )
        ).one()

        average = (
            Decimal(str(aggregate[0])).quantize(Decimal("0.01"))
            if aggregate[0]
            else Decimal("0.00")
        )
        product = self.session.get(Product, product_id)
        if product is None:
            return

        product.rating_avg = average
        product.rating_count = aggregate[1] or 0

        # Sin este `flush` explícito, la agregación de abajo lee el promedio
        # anterior del producto: la sesión de la aplicación se crea con
        # `autoflush=False`, así que una consulta no arrastra los cambios
        # pendientes. El resultado era que el promedio del productor se quedaba
        # en cero mientras el del café ya figuraba actualizado.
        self.session.flush()

        producer_aggregate = self.session.execute(
            select(func.avg(Product.rating_avg), func.sum(Product.rating_count)).where(
                Product.producer_id == product.producer_id,
                Product.rating_count > 0,
                Product.deleted_at.is_(None),
            )
        ).one()

        producer = self.session.get(ProducerProfile, product.producer_id)
        if producer is not None:
            producer.rating_avg = (
                Decimal(str(producer_aggregate[0])).quantize(Decimal("0.01"))
                if producer_aggregate[0]
                else Decimal("0.00")
            )
            producer.rating_count = int(producer_aggregate[1] or 0)

        self.session.flush()
