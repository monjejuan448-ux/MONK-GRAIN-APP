"""Modelos de datos de MONK GRAIN.

Este módulo importa todos los modelos para que queden registrados en la
metadata de SQLAlchemy. Alembic lo usa como punto único de entrada al detectar
cambios de esquema: un modelo que no se importe aquí quedaría fuera de las
migraciones.
"""

from app.db.base import Base
from app.models.cart import Cart, CartItem, Coupon, CouponUsage, Wishlist, WishlistItem
from app.models.catalog import (
    Category,
    CoffeeAttributes,
    Inventory,
    Product,
    ProductCertification,
    ProductImage,
    ProductVariant,
    Review,
)
from app.models.content import AuditLog, BlogPost, PlatformSetting
from app.models.geo import Department, Municipality, Region
from app.models.messaging import (
    CommercialRequest,
    Conversation,
    Message,
    Notification,
)
from app.models.order import Order, OrderItem, OrderStatusHistory, SubOrder
from app.models.payment import Commission, Payment, PaymentEvent, Settlement
from app.models.producer import (
    BusinessProfile,
    Certification,
    Farm,
    ProducerCertification,
    ProducerProfile,
)
from app.models.shipment import Return, Shipment, ShipmentEvent
from app.models.trading import DemandOffer, DemandRequest
from app.models.user import (
    Address,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
    VerificationToken,
)

__all__ = [
    "Base",
    # Identidad y acceso
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "RefreshToken",
    "VerificationToken",
    "Address",
    # Geografía
    "Department",
    "Municipality",
    "Region",
    # Productores
    "ProducerProfile",
    "BusinessProfile",
    "Farm",
    "Certification",
    "ProducerCertification",
    # Catálogo
    "Category",
    "Product",
    "CoffeeAttributes",
    "ProductImage",
    "ProductVariant",
    "Inventory",
    "ProductCertification",
    "Review",
    # Carrito y promociones
    "Cart",
    "CartItem",
    "Wishlist",
    "WishlistItem",
    "Coupon",
    "DemandOffer",
    "DemandRequest",
    "CouponUsage",
    # Pedidos
    "Order",
    "SubOrder",
    "OrderItem",
    "OrderStatusHistory",
    # Pagos
    "Payment",
    "PaymentEvent",
    "Commission",
    "Settlement",
    # Logística
    "Shipment",
    "ShipmentEvent",
    "Return",
    # Comunicación
    "Conversation",
    "Message",
    "Notification",
    "CommercialRequest",
    # Contenido y operación
    "BlogPost",
    "AuditLog",
    "PlatformSetting",
]
