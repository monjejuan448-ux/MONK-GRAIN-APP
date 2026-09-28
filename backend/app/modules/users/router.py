"""Perfil del usuario y direcciones de entrega."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import CurrentUser
from app.db.session import get_session
from app.models.geo import Department, Municipality
from app.models.user import Address
from app.schemas.common import MessageResponse, ORMModel

router = APIRouter(prefix="/users", tags=["usuarios"])

SessionDep = Annotated[Session, Depends(get_session)]


class AddressCreate(BaseModel):
    label: str | None = Field(default=None, max_length=50)
    recipient_name: str = Field(min_length=3, max_length=150)
    phone: str = Field(min_length=7, max_length=30)
    municipality_id: int
    street_address: str = Field(min_length=5, max_length=255)
    neighborhood: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    is_default: bool = False


class AddressResponse(ORMModel):
    id: uuid.UUID
    label: str | None
    recipient_name: str
    phone: str
    street_address: str
    neighborhood: str | None
    notes: str | None
    municipality_id: int
    department_id: int
    is_default: bool


@router.get(
    "/me/addresses",
    response_model=list[AddressResponse],
    summary="Mis direcciones de entrega",
)
def list_addresses(user: CurrentUser, session: SessionDep) -> list[AddressResponse]:
    addresses = session.scalars(
        select(Address)
        .where(Address.user_id == user.id, Address.deleted_at.is_(None))
        .order_by(Address.is_default.desc(), Address.created_at.desc())
    ).all()
    return [AddressResponse.model_validate(address) for address in addresses]


@router.post(
    "/me/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar una dirección",
)
def create_address(
    payload: AddressCreate, user: CurrentUser, session: SessionDep
) -> AddressResponse:
    """Registra una dirección de entrega.

    El departamento se deriva del municipio en lugar de recibirse aparte: así no
    puede llegar una combinación imposible como Pitalito en Antioquia.
    """
    municipality = session.get(Municipality, payload.municipality_id)
    if municipality is None:
        raise NotFoundError("El municipio indicado no existe.")

    if payload.is_default:
        # Solo puede haber una dirección predeterminada; la restricción de la
        # base de datos lo garantiza, así que se retira la anterior primero.
        session.execute(
            update(Address)
            .where(Address.user_id == user.id, Address.is_default.is_(True))
            .values(is_default=False)
        )

    address = Address(
        user_id=user.id,
        label=payload.label,
        recipient_name=payload.recipient_name,
        phone=payload.phone,
        department_id=municipality.department_id,
        municipality_id=municipality.id,
        street_address=payload.street_address,
        neighborhood=payload.neighborhood,
        notes=payload.notes,
        is_default=payload.is_default,
    )
    session.add(address)
    session.commit()

    return AddressResponse.model_validate(address)


@router.delete(
    "/me/addresses/{address_id}",
    response_model=MessageResponse,
    summary="Eliminar una dirección",
)
def delete_address(
    address_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> MessageResponse:
    """Da de baja una dirección.

    La baja es lógica: los pedidos que la usaron conservan su copia inmutable,
    pero la dirección no debe desaparecer de la base de datos (HU-CC-03, CA4).
    """
    address = session.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == user.id,
            Address.deleted_at.is_(None),
        )
    )
    if address is None:
        raise NotFoundError("No encontramos esta dirección.")

    from datetime import UTC, datetime

    address.deleted_at = datetime.now(UTC)
    address.is_default = False
    session.commit()

    return MessageResponse(message="Dirección eliminada.")


class MunicipalityResponse(ORMModel):
    id: int
    name: str
    dane_code: str


class DepartmentResponse(ORMModel):
    id: int
    name: str
    dane_code: str


@router.get(
    "/geo/departments",
    response_model=list[DepartmentResponse],
    summary="Departamentos de Colombia",
)
def list_departments(session: SessionDep) -> list[DepartmentResponse]:
    departments = session.scalars(select(Department).order_by(Department.name)).all()
    return [DepartmentResponse.model_validate(item) for item in departments]


@router.get(
    "/geo/departments/{department_id}/municipalities",
    response_model=list[MunicipalityResponse],
    summary="Municipios de un departamento",
)
def list_municipalities(department_id: int, session: SessionDep) -> list[MunicipalityResponse]:
    municipalities = session.scalars(
        select(Municipality)
        .where(Municipality.department_id == department_id)
        .order_by(Municipality.name)
    ).all()
    return [MunicipalityResponse.model_validate(item) for item in municipalities]
