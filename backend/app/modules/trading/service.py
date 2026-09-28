"""Reglas de la negociación entre comprador y vendedor.

El flujo completo:

1. Un comprador publica lo que busca —kilos, techo de factor y de humedad,
   precio que ofrece, hasta cuándo—.
2. Los vendedores aprobados ven las solicitudes vigentes que sus lotes podrían
   satisfacer y responden con una postura respaldada por un lote publicado.
3. El comprador acepta o rechaza cada postura. Al aceptar, los kilos acordados
   entran a su carrito **al precio acordado**, y de ahí siguen por el checkout
   de siempre: pedido, sub-orden por vendedor, comisión y despacho.

La pieza que hace que todo esto no duplique el sistema de pedidos es esa: una
postura aceptada se convierte en una línea de carrito con precio negociado. No
hay un segundo camino hacia el pedido.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams, paginate_query
from app.models.cart import CartItem
from app.models.catalog import CoffeeAttributes, Inventory, Product, ProductVariant
from app.models.enums import (
    RECEIVING_DEMAND_STATUSES,
    DemandStatus,
    OfferStatus,
    ProductStatus,
)
from app.models.geo import Municipality
from app.models.producer import ProducerProfile
from app.models.trading import DemandOffer, DemandRequest
from app.models.user import User
from app.modules.cart.service import CartService
from app.schemas.trading import (
    DemandCreate,
    DemandDetail,
    DemandSummary,
    DemandUpdate,
    MyOfferSummary,
    OfferCreate,
    OfferRespond,
    OfferSummary,
)

logger = get_logger(__name__)


class TradingService:
    """Solicitudes de compra y posturas de venta."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Lado del comprador: solicitudes
    # ------------------------------------------------------------------
    def create_demand(self, user: User, payload: DemandCreate) -> DemandDetail:
        """Publica una solicitud de compra."""
        municipality: Municipality | None = None
        if payload.municipality_id is not None:
            municipality = self.session.get(Municipality, payload.municipality_id)
            if municipality is None:
                raise NotFoundError("El municipio indicado no existe.")

        demand = DemandRequest(
            buyer_id=user.id,
            title=payload.title.strip(),
            description=payload.description,
            wanted_kg=payload.wanted_kg,
            max_yield_factor=payload.max_yield_factor,
            max_moisture_pct=payload.max_moisture_pct,
            variety=payload.variety,
            process=payload.process,
            # El departamento se deriva del municipio, igual que en las
            # direcciones: recibirlo aparte permitiría una pareja imposible.
            department_id=municipality.department_id if municipality else None,
            municipality_id=municipality.id if municipality else None,
            offered_price_per_kg=payload.offered_price_per_kg,
            expires_on=payload.expires_on,
            status=DemandStatus.OPEN,
        )
        self.session.add(demand)
        self.session.commit()

        logger.info("demand_created", demand=str(demand.id), wanted_kg=demand.wanted_kg)
        return self.get_demand_detail(user, demand.id)

    def update_demand(
        self, user: User, demand_id: uuid.UUID, payload: DemandUpdate
    ) -> DemandDetail:
        """Ajusta el título, la descripción, el precio ofrecido o la vigencia."""
        demand = self._own_demand(user, demand_id)
        if demand.status not in RECEIVING_DEMAND_STATUSES:
            raise BusinessRuleError(
                "Esta solicitud ya está cerrada y no admite cambios.",
                details={"status": demand.status.value},
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(demand, field, value)

        self.session.commit()
        return self.get_demand_detail(user, demand.id)

    def close_demand(self, user: User, demand_id: uuid.UUID) -> DemandDetail:
        """Cierra la solicitud por decisión del comprador.

        Las posturas pendientes se rechazan en bloque: dejarlas colgando haría
        que un caficultor siguiera esperando una respuesta que no va a llegar.
        """
        demand = self._own_demand(user, demand_id)
        if demand.status not in RECEIVING_DEMAND_STATUSES:
            raise BusinessRuleError("Esta solicitud ya está cerrada.")

        now = datetime.now(UTC)
        for offer in demand.offers:
            if offer.status == OfferStatus.PENDING:
                offer.status = OfferStatus.REJECTED
                offer.response_note = "El comprador cerró la solicitud."
                offer.responded_at = now

        demand.status = DemandStatus.CANCELLED if demand.covered_kg == 0 else DemandStatus.CLOSED
        demand.closed_at = now
        self.session.commit()

        return self.get_demand_detail(user, demand.id)

    def list_my_demands(self, user: User, params: PageParams) -> Page[DemandSummary]:
        statement = (
            select(DemandRequest)
            .where(DemandRequest.buyer_id == user.id)
            .options(
                joinedload(DemandRequest.municipality).joinedload(Municipality.department),
                selectinload(DemandRequest.offers),
            )
            .order_by(DemandRequest.created_at.desc(), DemandRequest.id)
        )
        demands, total = paginate_query(self.session, statement, params)
        today = date.today()
        return Page.create([self._to_summary(demand, today) for demand in demands], total, params)

    def get_demand_detail(self, user: User, demand_id: uuid.UUID) -> DemandDetail:
        """Solicitud con sus posturas. Solo para su comprador."""
        demand = self._own_demand(user, demand_id)
        today = date.today()
        base = self._to_summary(demand, today)

        offers = sorted(
            demand.offers,
            # Primero lo pendiente, y dentro de eso lo más barato por kilo: es el
            # orden en que un comprador quiere revisar.
            key=lambda offer: (offer.status != OfferStatus.PENDING, offer.price_per_kg),
        )
        return DemandDetail(
            **base.model_dump(),
            description=demand.description,
            offers=[self._to_offer_summary(offer) for offer in offers],
        )

    # ------------------------------------------------------------------
    # Lado del vendedor: solicitudes abiertas y posturas
    # ------------------------------------------------------------------
    def list_open_demands(
        self,
        producer_user: User,
        params: PageParams,
        *,
        only_matching: bool = False,
    ) -> Page[DemandSummary]:
        """Solicitudes vigentes que un vendedor puede atender.

        `only_matching` acota a las que alguno de sus lotes publicados satisface:
        un caficultor con factor 94 no gana nada viendo solicitudes que piden 88 o
        menos.
        """
        profile = self._profile(producer_user)
        today = date.today()

        statement = (
            select(DemandRequest)
            .where(
                DemandRequest.status.in_(RECEIVING_DEMAND_STATUSES),
                DemandRequest.expires_on >= today,
            )
            .options(
                joinedload(DemandRequest.municipality).joinedload(Municipality.department),
                selectinload(DemandRequest.offers),
            )
            .order_by(DemandRequest.expires_on, DemandRequest.id)
        )

        if only_matching:
            statement = self._restrict_to_satisfiable(statement, profile)

        demands, total = paginate_query(self.session, statement, params)
        return Page.create([self._to_summary(demand, today) for demand in demands], total, params)

    def create_offer(
        self, producer_user: User, demand_id: uuid.UUID, payload: OfferCreate
    ) -> MyOfferSummary:
        """Envía una postura sobre una solicitud vigente."""
        profile = self._profile(producer_user)
        demand = self.session.get(DemandRequest, demand_id)
        if demand is None:
            raise NotFoundError("No encontramos esta solicitud.")

        if not demand.is_receiving(date.today()):
            raise BusinessRuleError(
                "Esta solicitud ya no admite posturas: está cerrada o venció.",
                details={"status": demand.status.value, "expires_on": str(demand.expires_on)},
            )

        variant = self._own_publishable_variant(profile, payload.variant_id)
        available = variant.inventory.available_qty if variant.inventory else 0

        if payload.offered_kg > available:
            raise BusinessRuleError(
                f"Solo tienes {available} kg disponibles de este lote.",
                details={"available_kg": available},
            )
        if payload.offered_kg < variant.min_qty_kg:
            raise BusinessRuleError(
                f"Esta oferta se vende desde {variant.min_qty_kg} kg.",
                details={"min_qty_kg": variant.min_qty_kg},
            )

        existing = self.session.scalar(
            select(DemandOffer).where(
                DemandOffer.demand_id == demand.id,
                DemandOffer.producer_id == profile.id,
                DemandOffer.variant_id == variant.id,
            )
        )
        if existing is not None:
            raise ConflictError(
                "Ya enviaste una postura con este lote. Retírala para enviar otra.",
                details={"offer_id": str(existing.id)},
            )

        offer = DemandOffer(
            demand_id=demand.id,
            producer_id=profile.id,
            product_id=variant.product_id,
            variant_id=variant.id,
            offered_kg=payload.offered_kg,
            price_per_kg=payload.price_per_kg,
            message=payload.message,
            status=OfferStatus.PENDING,
        )
        self.session.add(offer)
        self.session.commit()

        logger.info(
            "demand_offer_created",
            demand=str(demand.id),
            offer=str(offer.id),
            offered_kg=offer.offered_kg,
        )
        return self._to_my_offer(offer)

    def withdraw_offer(self, producer_user: User, offer_id: uuid.UUID) -> MyOfferSummary:
        """Retira una postura que el comprador aún no respondió."""
        profile = self._profile(producer_user)
        offer = self.session.get(DemandOffer, offer_id)
        if offer is None or offer.producer_id != profile.id:
            raise NotFoundError("No encontramos esta postura.")

        if offer.status != OfferStatus.PENDING:
            raise BusinessRuleError(
                "Solo se retira una postura que todavía está pendiente.",
                details={"status": offer.status.value},
            )

        offer.status = OfferStatus.WITHDRAWN
        self.session.commit()
        return self._to_my_offer(offer)

    def list_my_offers(self, producer_user: User, params: PageParams) -> Page[MyOfferSummary]:
        profile = self._profile(producer_user)
        statement = (
            select(DemandOffer)
            .where(DemandOffer.producer_id == profile.id)
            .options(
                joinedload(DemandOffer.demand).joinedload(DemandRequest.buyer),
                joinedload(DemandOffer.product),
            )
            .order_by(DemandOffer.created_at.desc(), DemandOffer.id)
        )
        offers, total = paginate_query(self.session, statement, params)
        return Page.create([self._to_my_offer(offer) for offer in offers], total, params)

    # ------------------------------------------------------------------
    # Respuesta del comprador
    # ------------------------------------------------------------------
    def respond_to_offer(
        self, user: User, offer_id: uuid.UUID, payload: OfferRespond
    ) -> DemandDetail:
        """Acepta o rechaza una postura.

        Aceptar deja los kilos acordados en el carrito del comprador al precio
        acordado. No se crea el pedido aquí a propósito: el comprador puede estar
        armando su carga con varios vendedores, y cerrar cada trato por separado
        le cobraría un envío por cada uno. Cuando termine, pasa por el checkout de
        siempre y el sistema arma una sub-orden por vendedor.
        """
        offer = self.session.get(DemandOffer, offer_id)
        if offer is None:
            raise NotFoundError("No encontramos esta postura.")

        demand = self.session.get(DemandRequest, offer.demand_id)
        if demand is None or demand.buyer_id != user.id:
            raise NotFoundError("No encontramos esta postura.")

        if offer.status != OfferStatus.PENDING:
            raise BusinessRuleError(
                "Esta postura ya fue respondida.",
                details={"status": offer.status.value},
            )
        if not demand.is_receiving(date.today()):
            raise BusinessRuleError("Esta solicitud está cerrada o venció.")

        offer.responded_at = datetime.now(UTC)
        offer.response_note = payload.note

        if not payload.accept:
            offer.status = OfferStatus.REJECTED
            self.session.commit()
            return self.get_demand_detail(user, demand.id)

        # Los kilos se comprueban de nuevo contra el inventario: entre que el
        # vendedor envió la postura y el comprador la acepta pudo venderlos.
        variant = self.session.get(ProductVariant, offer.variant_id)
        if variant is None or not variant.is_active or variant.deleted_at is not None:
            raise BusinessRuleError("El lote de esta postura ya no está disponible.")

        available = variant.inventory.available_qty if variant.inventory else 0
        if offer.offered_kg > available:
            raise BusinessRuleError(
                f"El vendedor ya no tiene los {offer.offered_kg} kg de esta postura: "
                f"quedan {available} kg.",
                details={"available_kg": available},
            )

        offer.status = OfferStatus.ACCEPTED
        self._add_negotiated_line(user, offer, variant)

        demand.covered_kg += offer.offered_kg
        demand.status = (
            DemandStatus.FULFILLED
            if demand.covered_kg >= demand.wanted_kg
            else DemandStatus.PARTIALLY_COVERED
        )
        if demand.status == DemandStatus.FULFILLED:
            demand.closed_at = datetime.now(UTC)
            # Ya no falta café: lo pendiente se rechaza en vez de dejarlo
            # esperando una respuesta que no va a llegar.
            for other in demand.offers:
                if other.id != offer.id and other.status == OfferStatus.PENDING:
                    other.status = OfferStatus.REJECTED
                    other.response_note = "La solicitud se completó con otras posturas."
                    other.responded_at = datetime.now(UTC)

        self.session.commit()
        logger.info(
            "demand_offer_accepted",
            offer=str(offer.id),
            demand=str(demand.id),
            covered_kg=demand.covered_kg,
        )
        return self.get_demand_detail(user, demand.id)

    def _add_negotiated_line(self, user: User, offer: DemandOffer, variant: ProductVariant) -> None:
        """Deja la postura aceptada como línea de carrito al precio acordado.

        Si el comprador ya tenía ese mismo lote en el carrito, se le suman los
        kilos y el precio pasa a ser el negociado: el trato cerrado manda sobre
        lo que hubiera agregado del catálogo.
        """
        cart = CartService(self.session).get_or_create_cart(user)
        existing = self.session.scalar(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant.id)
        )

        if existing is not None:
            existing.quantity += offer.offered_kg
            existing.negotiated_price = offer.price_per_kg
            existing.demand_offer_id = offer.id
        else:
            self.session.add(
                CartItem(
                    cart_id=cart.id,
                    variant_id=variant.id,
                    quantity=offer.offered_kg,
                    unit_price_snapshot=offer.price_per_kg,
                    negotiated_price=offer.price_per_kg,
                    demand_offer_id=offer.id,
                )
            )
        self.session.flush()

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def _own_demand(self, user: User, demand_id: uuid.UUID) -> DemandRequest:
        """Solicitud del comprador, o 404.

        Se filtra por comprador en la misma consulta: distinguir 404 de 403
        revelaría qué solicitudes existen en otras cuentas.
        """
        demand = self.session.scalar(
            select(DemandRequest)
            .where(DemandRequest.id == demand_id, DemandRequest.buyer_id == user.id)
            .options(
                joinedload(DemandRequest.municipality).joinedload(Municipality.department),
                selectinload(DemandRequest.offers).joinedload(DemandOffer.producer),
                selectinload(DemandRequest.offers).joinedload(DemandOffer.product),
            )
            .execution_options(populate_existing=True)
        )
        if demand is None:
            raise NotFoundError("No encontramos esta solicitud.")
        return demand

    def _profile(self, user: User) -> ProducerProfile:
        profile = user.producer_profile
        if profile is None:
            raise ForbiddenError("Esta sección es solo para vendedores.")
        return profile

    def _own_publishable_variant(
        self, profile: ProducerProfile, variant_id: uuid.UUID
    ) -> ProductVariant:
        """Oferta del propio vendedor, sobre un lote publicado.

        Se exige que el lote esté publicado: una postura respaldada por un
        borrador dejaría al comprador aceptando algo cuya ficha no puede ver.
        """
        variant = self.session.scalar(
            select(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                ProductVariant.id == variant_id,
                ProductVariant.deleted_at.is_(None),
                Product.producer_id == profile.id,
                Product.deleted_at.is_(None),
            )
            .options(
                joinedload(ProductVariant.inventory),
                joinedload(ProductVariant.product),
            )
        )
        if variant is None:
            raise NotFoundError("No encontramos esta oferta en tu catálogo.")

        if variant.product.status != ProductStatus.PUBLISHED:
            raise BusinessRuleError(
                "Publica el lote antes de ofrecerlo: el comprador necesita poder "
                "ver su ficha y su análisis.",
                details={"status": variant.product.status.value},
            )
        if not variant.is_active:
            raise BusinessRuleError("Esta oferta del lote está desactivada.")
        return variant

    def _restrict_to_satisfiable(
        self, statement: Select[tuple[DemandRequest]], profile: ProducerProfile
    ) -> Select[tuple[DemandRequest]]:
        """Acota el listado a las solicitudes que los lotes del vendedor cumplen.

        Se compara contra el mejor lote del vendedor —el de menor factor y menor
        humedad— y sus kilos vendibles. Un requisito que el comprador no puso
        (`NULL`) no excluye a nadie.
        """
        best = self.session.execute(
            select(
                func.min(CoffeeAttributes.yield_factor),
                func.min(CoffeeAttributes.moisture_pct),
                func.max(Inventory.stock_qty - Inventory.reserved_qty),
            )
            .select_from(Product)
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .join(Inventory, Inventory.variant_id == ProductVariant.id)
            .outerjoin(CoffeeAttributes, CoffeeAttributes.product_id == Product.id)
            .where(
                Product.producer_id == profile.id,
                Product.status == ProductStatus.PUBLISHED,
                Product.deleted_at.is_(None),
                ProductVariant.is_active.is_(True),
                ProductVariant.deleted_at.is_(None),
            )
        ).one()

        best_factor, best_moisture, best_available = best
        if best_available is None or best_available <= 0:
            # Sin kilos vendibles no hay solicitud que el vendedor pueda atender.
            return statement.where(DemandRequest.id.is_(None))

        if best_factor is not None:
            statement = statement.where(
                or_(
                    DemandRequest.max_yield_factor.is_(None),
                    DemandRequest.max_yield_factor >= best_factor,
                )
            )
        if best_moisture is not None:
            statement = statement.where(
                or_(
                    DemandRequest.max_moisture_pct.is_(None),
                    DemandRequest.max_moisture_pct >= best_moisture,
                )
            )
        return statement

    # ------------------------------------------------------------------
    # Conversión a schemas
    # ------------------------------------------------------------------
    def _to_summary(self, demand: DemandRequest, today: date) -> DemandSummary:
        municipality = demand.municipality
        return DemandSummary(
            id=demand.id,
            title=demand.title,
            buyer_name=demand.buyer.full_name,
            wanted_kg=demand.wanted_kg,
            covered_kg=demand.covered_kg,
            remaining_kg=demand.remaining_kg,
            max_yield_factor=demand.max_yield_factor,
            max_moisture_pct=demand.max_moisture_pct,
            variety=demand.variety,
            process=demand.process,
            municipality=municipality.name if municipality else None,
            department=municipality.department.name if municipality else None,
            offered_price_per_kg=demand.offered_price_per_kg,
            expires_on=demand.expires_on,
            status=demand.status,
            is_receiving=demand.is_receiving(today),
            # Las retiradas no cuentan: el comprador no las ve, y mostrar «3
            # posturas» para luego listar una sola resta credibilidad.
            offer_count=sum(1 for offer in demand.offers if offer.status != OfferStatus.WITHDRAWN),
            created_at=demand.created_at,
        )

    def _to_offer_summary(self, offer: DemandOffer) -> OfferSummary:
        product = offer.product
        attributes = product.attributes
        variant = self.session.get(ProductVariant, offer.variant_id)
        farm = product.farm

        return OfferSummary(
            id=offer.id,
            producer_id=offer.producer_id,
            producer_name=offer.producer.brand_name or offer.producer.legal_name,
            product_id=product.id,
            product_name=product.name,
            product_slug=product.slug,
            variant_id=offer.variant_id,
            presentation=variant.presentation if variant else "—",
            offered_kg=offer.offered_kg,
            price_per_kg=offer.price_per_kg,
            line_total=offer.price_per_kg * offer.offered_kg,
            message=offer.message,
            status=offer.status,
            response_note=offer.response_note,
            yield_factor=attributes.yield_factor if attributes else None,
            moisture_pct=attributes.moisture_pct if attributes else None,
            municipality=farm.municipality.name if farm and farm.municipality else None,
            available_kg=(variant.inventory.available_qty if variant and variant.inventory else 0),
            created_at=offer.created_at,
            responded_at=offer.responded_at,
        )

    def _to_my_offer(self, offer: DemandOffer) -> MyOfferSummary:
        variant = self.session.get(ProductVariant, offer.variant_id)
        demand = offer.demand
        return MyOfferSummary(
            id=offer.id,
            demand_id=demand.id,
            demand_title=demand.title,
            buyer_name=demand.buyer.full_name,
            wanted_kg=demand.wanted_kg,
            product_name=offer.product.name,
            presentation=variant.presentation if variant else "—",
            offered_kg=offer.offered_kg,
            price_per_kg=offer.price_per_kg,
            line_total=offer.price_per_kg * offer.offered_kg,
            status=offer.status,
            response_note=offer.response_note,
            demand_expires_on=demand.expires_on,
            created_at=offer.created_at,
            responded_at=offer.responded_at,
        )


def total_negotiated(items: list[CartItem]) -> Decimal:
    """Suma de las líneas con precio acordado. Se usa en las pruebas."""
    return sum(
        (item.effective_price * item.quantity for item in items if item.negotiated_price),
        Decimal("0"),
    )
