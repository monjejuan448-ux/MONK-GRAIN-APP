"""Schemas compartidos por varios módulos."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_strength


class ORMModel(BaseModel):
    """Base de los schemas que se construyen desde modelos SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Respuesta genérica de confirmación."""

    message: str


class TimestampFields(BaseModel):
    created_at: datetime
    updated_at: datetime


# Un correo se normaliza a minúsculas antes de guardarse; la columna es CITEXT,
# de modo que la unicidad tampoco depende de esa normalización.
Email = Annotated[EmailStr, Field(max_length=255)]


class PasswordField(BaseModel):
    """Mixin que valida la robustez de la contraseña.

    Las reglas viven en `core.security` para que la API y cualquier otro punto
    de entrada apliquen exactamente el mismo criterio.
    """

    # Sin `min_length`: la longitud mínima la decide `validate_password_strength`
    # con el valor configurado. Declararla aquí además hacía que Pydantic
    # rechazara antes las contraseñas muy cortas con su mensaje genérico en
    # inglés, anunciando un mínimo (8) distinto del real (12).
    password: str = Field(max_length=128)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        problems = validate_password_strength(value)
        if problems:
            raise ValueError(" ".join(problems))
        return value
