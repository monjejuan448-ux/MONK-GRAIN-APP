"""order number sequence

Sustituye el correlativo calculado con `SELECT count(*) + 1` por una secuencia
de PostgreSQL.

El conteo no era atómico: dos checkouts simultáneos leían el mismo total y
generaban el mismo número. La restricción `UNIQUE` sobre `order_number` hacía
fallar a uno de los dos, de modo que dos compradores sin relación entre sí
chocaban por el simple hecho de pagar a la vez.

`nextval` no participa en la transacción: no toma bloqueos y no se revierte con
un `ROLLBACK`. Eso permite checkouts concurrentes sin serializarlos, a cambio de
que la numeración pueda saltarse algún valor cuando un pedido falla a medias.
El hueco es deliberado y admisible: `order_number` identifica un pedido, no es
una numeración fiscal de facturación.

Revision ID: 59c2f7a91062
Revises: db2be3833cad
Create Date: 2026-08-13 22:54:15.923072

"""

from collections.abc import Sequence

from alembic import op

revision: str = "59c2f7a91062"
down_revision: str | None = "db2be3833cad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS order_number_seq AS bigint START WITH 1")

    # La secuencia arranca por encima del pedido más alto que ya exista, para no
    # reutilizar un número emitido antes de esta migración.
    op.execute(
        """
        SELECT setval(
            'order_number_seq',
            GREATEST(
                (SELECT COALESCE(MAX(substring(order_number from '[0-9]+$')::bigint), 0)
                   FROM orders),
                1
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS order_number_seq")
