"""Endpoints del carrito y la lista de deseos."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.permissions import CurrentUser
from app.db.session import get_session
from app.modules.cart.service import CartService
from app.schemas.cart import (
    CartItemAdd,
    CartItemUpdate,
    CartResponse,
    WishlistItemAdd,
    WishlistItemResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(tags=["carrito"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/cart", response_model=CartResponse, summary="Ver el carrito")
def get_cart(
    user: CurrentUser,
    session: SessionDep,
    coupon: Annotated[str | None, Query(max_length=40)] = None,
) -> CartResponse:
    """Devuelve el carrito agrupado por vendedor, con totales y avisos."""
    return CartService(session).get_cart(user, coupon)


@router.post(
    "/cart/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar al carrito",
)
def add_item(payload: CartItemAdd, user: CurrentUser, session: SessionDep) -> CartResponse:
    return CartService(session).add_item(user, payload.variant_id, payload.quantity)


@router.patch("/cart/items/{item_id}", response_model=CartResponse, summary="Cambiar la cantidad")
def update_item(
    item_id: uuid.UUID, payload: CartItemUpdate, user: CurrentUser, session: SessionDep
) -> CartResponse:
    return CartService(session).update_item(user, item_id, payload.quantity)


@router.delete("/cart/items/{item_id}", response_model=CartResponse, summary="Quitar del carrito")
def remove_item(item_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> CartResponse:
    return CartService(session).remove_item(user, item_id)


@router.delete("/cart", response_model=MessageResponse, summary="Vaciar el carrito")
def clear_cart(user: CurrentUser, session: SessionDep) -> MessageResponse:
    CartService(session).clear(user)
    return MessageResponse(message="Carrito vaciado.")


@router.post(
    "/cart/merge",
    response_model=CartResponse,
    summary="Fusionar el carrito anónimo tras iniciar sesión",
)
def merge_cart(items: list[CartItemAdd], user: CurrentUser, session: SessionDep) -> CartResponse:
    """Incorpora al carrito del usuario lo que agregó antes de autenticarse."""
    pairs = [(item.variant_id, item.quantity) for item in items]
    return CartService(session).merge_anonymous_cart(user, pairs)


# ------------------------------------------------------------------
# Lista de deseos
# ------------------------------------------------------------------
@router.get("/wishlist", response_model=list[WishlistItemResponse], summary="Ver favoritos")
def list_wishlist(user: CurrentUser, session: SessionDep) -> list[WishlistItemResponse]:
    return CartService(session).list_wishlist(user)


@router.post(
    "/wishlist",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar a favoritos",
)
def add_to_wishlist(
    payload: WishlistItemAdd, user: CurrentUser, session: SessionDep
) -> MessageResponse:
    CartService(session).add_to_wishlist(user, payload.product_id)
    return MessageResponse(message="Añadido a tus favoritos.")


@router.delete(
    "/wishlist/{product_id}", response_model=MessageResponse, summary="Quitar de favoritos"
)
def remove_from_wishlist(
    product_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> MessageResponse:
    CartService(session).remove_from_wishlist(user, product_id)
    return MessageResponse(message="Eliminado de tus favoritos.")
