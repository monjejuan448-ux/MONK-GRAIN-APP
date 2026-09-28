"""Perfil del usuario y direcciones de entrega."""

import uuid
from datetime import UTC, datetime
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


class ProfileUpdate(BaseModel):
    """Datos personales que el titular puede corregir por sí mismo.

    El correo queda fuera a propósito: cambiarlo exige volver a verificarlo,
    porque es la llave de la recuperación de contraseña. El estado de la cuenta y
    los roles también, que son decisiones de la administración y no del titular.
    """

    full_name: str | None = Field(default=None, min_length=3, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    email_notifications_enabled: bool | None = None


class ProfileResponse(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    email_notifications_enabled: bool


@router.patch("/me", response_model=ProfileResponse, summary="Editar mis datos")
def update_profile(
    payload: ProfileUpdate, user: CurrentUser, session: SessionDep
) -> ProfileResponse:
    """Actualiza los datos personales del titular.

    Solo se aplican los campos presentes en la petición: un `null` explícito en
    `phone` significa borrarlo, mientras que su ausencia lo deja como estaba.
    """
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    session.commit()
    return ProfileResponse.model_validate(user)


class AddressCreate(BaseModel):
    label: str | None = Field(default=None, max_length=50)
    recipient_name: str = Field(min_length=3, max_length=150)
    phone: str = Field(min_length=7, max_length=30)
    municipality_id: int
    street_address: str = Field(min_length=5, max_length=255)
    neighborhood: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    is_default: bool = False


class AddressUpdate(BaseModel):
    """Cambios sobre una dirección ya registrada.

    Todos los campos son opcionales y solo se aplican los que vengan en la
    petición: se distinguen con `model_fields_set`, porque para `label`,
    `neighborhood` y `notes` un `null` explícito significa «bórralo» y no puede
    confundirse con «no lo mandé».
    """

    label: str | None = Field(default=None, max_length=50)
    recipient_name: str | None = Field(default=None, min_length=3, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    municipality_id: int | None = None
    street_address: str | None = Field(default=None, min_length=5, max_length=255)
    neighborhood: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    is_default: bool | None = None


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


def _owned_address(session: Session, user_id: uuid.UUID, address_id: uuid.UUID) -> Address:
    """Busca una dirección del usuario o falla con 404.

    Se filtra por `user_id` en la misma consulta y no después: preguntar primero
    por el identificador y comprobar el dueño más tarde revelaría, por la
    diferencia entre 404 y 403, qué direcciones existen en otras cuentas.
    """
    address = session.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == user_id,
            Address.deleted_at.is_(None),
        )
    )
    if address is None:
        raise NotFoundError("No encontramos esta dirección.")
    return address


@router.patch(
    "/me/addresses/{address_id}",
    response_model=AddressResponse,
    summary="Editar una dirección",
)
def update_address(
    address_id: uuid.UUID,
    payload: AddressUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> AddressResponse:
    """Actualiza los datos de una dirección de entrega.

    Los pedidos ya realizados no se ven afectados: cada uno guarda su copia
    inmutable de la dirección con la que se despachó (HU-CC-03, CA4). Corregir
    un teléfono hoy no reescribe lo que decía una guía de hace un mes.
    """
    address = _owned_address(session, user.id, address_id)
    changes = payload.model_dump(exclude_unset=True)

    # El departamento se deriva del municipio, igual que al crear: recibirlo
    # aparte permitiría guardar una combinación imposible.
    if "municipality_id" in changes:
        municipality = session.get(Municipality, changes["municipality_id"])
        if municipality is None:
            raise NotFoundError("El municipio indicado no existe.")
        address.department_id = municipality.department_id

    if changes.get("is_default") is True:
        # El índice parcial de la base de datos solo admite una predeterminada
        # por usuario, así que se retira la anterior antes de marcar esta.
        session.execute(
            update(Address)
            .where(
                Address.user_id == user.id,
                Address.is_default.is_(True),
                Address.id != address.id,
            )
            .values(is_default=False)
        )

    for field, value in changes.items():
        setattr(address, field, value)

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
    address = _owned_address(session, user.id, address_id)
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
