"""seller notification data and withdrawal return reason

Dos exigencias del Estatuto del Consumidor (Ley 1480 de 2011) que el esquema no
contemplaba:

1. **Artículo 53.** Los portales de contacto deben llevar un registro con la
   dirección física de notificaciones y el teléfono de cada oferente, y
   entregarlos a quien tenga una reclamación. `producer_profiles` solo guardaba
   departamento y municipio, que no bastan para notificar a nadie.

2. **Artículo 47.** El derecho de retracto es una causal de devolución con
   plazo, costos y forma de reembolso propios. El enum `return_reason` solo
   admitía motivos por defecto del producto, de modo que un retracto había que
   registrarlo como «otro» y perdía su tratamiento diferenciado.

Las columnas admiten nulo a propósito: hay perfiles creados antes de esta
obligación y una columna obligatoria dejaría filas inválidas o exigiría inventar
datos. El dato se exige al publicar el primer café, junto al resto de
requisitos.

Revision ID: ae0cdd0bb859
Revises: 59c2f7a91062
Create Date: 2026-08-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ae0cdd0bb859"
down_revision: str | None = "59c2f7a91062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "producer_profiles",
        sa.Column("notification_address", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "producer_profiles",
        sa.Column("contact_phone", sa.String(length=30), nullable=True),
    )

    # PostgreSQL admite añadir valores a un enum dentro de la transacción desde
    # la versión 12; lo que no permite es usarlos antes de confirmarla.
    op.execute("ALTER TYPE return_reason ADD VALUE IF NOT EXISTS 'withdrawal'")


def downgrade() -> None:
    op.drop_column("producer_profiles", "contact_phone")
    op.drop_column("producer_profiles", "notification_address")

    # PostgreSQL no permite eliminar un valor de un enum. Revertirlo exigiría
    # recrear el tipo y reescribir la columna, algo que no se hace de forma
    # automática porque perdería las filas que ya usen el valor.
