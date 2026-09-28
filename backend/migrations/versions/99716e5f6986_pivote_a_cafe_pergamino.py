"""Pivote del dominio: de café tostado al detal a pergamino seco por kilogramo

MONK GRAIN pasa a comerciar un solo producto: **pergamino seco**, el café
beneficiado y secado que aún conserva el pergamino y no ha pasado por trilla.

Qué cambia en el esquema:

- `coffee_state` deja de admitir `green`, `roasted` y `ground` y pasa a admitir
  únicamente `pergamino`. El tipo se reconstruye, porque PostgreSQL no permite
  retirar valores de un ENUM existente.
- La ficha técnica cambia de catación a análisis del pergamino: salen el nivel de
  tueste, la fecha de tueste, el puntaje de catación, las notas de cata y el
  perfil sensorial; entran el factor de rendimiento, la almendra sana, la
  pasilla, el daño por broca, la granulometría, el método de secado, el código de
  lote y el código SICA.
- Las variantes dejan de describir un empaque en gramos con su molienda y pasan a
  describir cómo se entrega el lote, con un mínimo de compra en kilogramos. El
  precio pasa a ser **por kilogramo** y las existencias, **kilos**.
- `shipments.weight_grams` pasa a `weight_kg`, con su valor convertido.

Advertencia sobre los datos existentes
--------------------------------------
Las filas anteriores describían bolsas de café tostado. La conversión preserva la
estructura, no el significado: un precio de 40.000 que era el costo de una bolsa
de 500 g queda como «40.000 por kilogramo», y unas existencias de 100 bolsas
quedan como «100 kg». **Los importes y las cantidades de los productos anteriores
deben revisarse o recargarse** con `python -m app.db.demo_data` sobre una base
limpia. La migración lo deja anotado en la presentación de cada variante para que
no pase inadvertido.

Revision ID: 99716e5f6986
Revises: 2840b05b463c
Create Date: 2026-09-28 17:39:43.018398
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "99716e5f6986"
down_revision: str | None = "2840b05b463c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Ficha técnica: del análisis de taza al análisis del pergamino
    # ------------------------------------------------------------------
    op.add_column(
        "coffee_attributes",
        sa.Column("yield_factor", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "coffee_attributes",
        sa.Column("healthy_bean_pct", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "coffee_attributes",
        sa.Column("pasilla_pct", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "coffee_attributes",
        sa.Column("borer_damage_pct", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "coffee_attributes",
        sa.Column("screen_sizes", postgresql.ARRAY(sa.SmallInteger()), nullable=True),
    )
    op.add_column("coffee_attributes", sa.Column("lot_code", sa.String(length=60), nullable=True))
    op.add_column("coffee_attributes", sa.Column("sica_code", sa.String(length=40), nullable=True))
    op.add_column(
        "coffee_attributes", sa.Column("drying_method", sa.String(length=80), nullable=True)
    )
    op.add_column("coffee_attributes", sa.Column("notes", sa.Text(), nullable=True))

    # El perfil sensorial escrito a mano es lo único de la ficha anterior que
    # conserva valor descriptivo: se traslada a las observaciones del lote antes
    # de eliminar la columna.
    op.execute(
        """
        UPDATE coffee_attributes
           SET notes = sensory_profile
         WHERE sensory_profile IS NOT NULL
        """
    )

    op.drop_index(op.f("ix_coffee_attributes_score"), table_name="coffee_attributes")
    op.drop_index(op.f("ix_coffee_attributes_filters"), table_name="coffee_attributes")
    op.create_index(
        "ix_coffee_attributes_filters",
        "coffee_attributes",
        ["process", "altitude_masl"],
        unique=False,
    )
    op.create_index(
        "ix_coffee_attributes_yield_factor", "coffee_attributes", ["yield_factor"], unique=False
    )

    op.drop_constraint(
        op.f("ck_coffee_attributes_cupping_score_range"), "coffee_attributes", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_coffee_attributes_yield_factor_range"),
        "coffee_attributes",
        "yield_factor IS NULL OR (yield_factor >= 80 AND yield_factor <= 130)",
    )
    op.create_check_constraint(
        op.f("ck_coffee_attributes_healthy_bean_range"),
        "coffee_attributes",
        "healthy_bean_pct IS NULL OR (healthy_bean_pct >= 0 AND healthy_bean_pct <= 100)",
    )
    op.create_check_constraint(
        op.f("ck_coffee_attributes_pasilla_range"),
        "coffee_attributes",
        "pasilla_pct IS NULL OR (pasilla_pct >= 0 AND pasilla_pct <= 100)",
    )
    op.create_check_constraint(
        op.f("ck_coffee_attributes_borer_damage_range"),
        "coffee_attributes",
        "borer_damage_pct IS NULL OR (borer_damage_pct >= 0 AND borer_damage_pct <= 100)",
    )

    op.drop_column("coffee_attributes", "tasting_notes")
    op.drop_column("coffee_attributes", "roast_date")
    op.drop_column("coffee_attributes", "sensory_profile")
    op.drop_column("coffee_attributes", "cupping_score")
    op.drop_column("coffee_attributes", "roast")

    # ------------------------------------------------------------------
    # Variantes: de empaque en gramos a mínimo de compra en kilogramos
    # ------------------------------------------------------------------
    # Las columnas nuevas entran con valor por defecto para que las filas
    # existentes queden válidas; el defecto se retira después, porque la
    # aplicación siempre envía ambos campos y dejarlo permitiría insertar una
    # oferta sin presentación.
    op.add_column(
        "product_variants",
        sa.Column("presentation", sa.String(length=80), nullable=False, server_default="A granel"),
    )
    op.add_column(
        "product_variants",
        sa.Column("min_qty_kg", sa.Integer(), nullable=False, server_default="1"),
    )

    # Se deja constancia en la propia fila de que describía un empaque del
    # dominio anterior, para que nadie tome su precio por un precio por kilo.
    op.execute(
        """
        UPDATE product_variants
           SET presentation = left(
                   'Revisar: antes ' || round(weight_grams)::text || ' g', 80
               )
         WHERE weight_grams IS NOT NULL
        """
    )

    op.alter_column("product_variants", "presentation", server_default=None)
    op.alter_column("product_variants", "min_qty_kg", server_default=None)

    op.drop_constraint(
        op.f("ck_product_variants_variant_weight_positive"), "product_variants", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_product_variants_variant_min_qty_positive"), "product_variants", "min_qty_kg > 0"
    )
    op.drop_column("product_variants", "weight_grams")
    op.drop_column("product_variants", "grind")

    # ------------------------------------------------------------------
    # Estado del café: el ENUM queda con un único valor
    # ------------------------------------------------------------------
    # PostgreSQL no permite retirar valores de un ENUM, así que se construye el
    # tipo nuevo, se convierte la columna con un USING que lleva todo a
    # `pergamino`, y se descarta el viejo.
    op.execute("CREATE TYPE coffee_state_new AS ENUM ('pergamino')")
    op.execute(
        """
        ALTER TABLE products
          ALTER COLUMN state DROP DEFAULT,
          ALTER COLUMN state TYPE coffee_state_new
            USING 'pergamino'::coffee_state_new
        """
    )
    op.execute("DROP TYPE coffee_state")
    op.execute("ALTER TYPE coffee_state_new RENAME TO coffee_state")

    # Los tipos del dominio anterior quedarían huérfanos al haber eliminado sus
    # columnas: en pergamino no hay tueste ni molienda.
    op.execute("DROP TYPE IF EXISTS roast_level")
    op.execute("DROP TYPE IF EXISTS grind_type")

    # ------------------------------------------------------------------
    # Peso del envío: gramos a kilogramos
    # ------------------------------------------------------------------
    # Es la misma magnitud en otra unidad, así que se renombra y se convierte el
    # valor en lugar de añadir una columna y perder lo que hubiera.
    op.alter_column(
        "shipments",
        "weight_grams",
        new_column_name="weight_kg",
        existing_type=sa.Numeric(precision=10, scale=2),
        existing_nullable=True,
    )
    op.execute("UPDATE shipments SET weight_kg = weight_kg / 1000 WHERE weight_kg IS NOT NULL")


def downgrade() -> None:
    op.execute("UPDATE shipments SET weight_kg = weight_kg * 1000 WHERE weight_kg IS NOT NULL")
    op.alter_column(
        "shipments",
        "weight_kg",
        new_column_name="weight_grams",
        existing_type=sa.Numeric(precision=10, scale=2),
        existing_nullable=True,
    )

    # Se reconstruyen los tipos del dominio anterior. Los datos no vuelven: la
    # ida eliminó el tueste, la molienda y el puntaje de catación, y no hay de
    # dónde recuperarlos. La vuelta restituye la forma del esquema, no su
    # contenido.
    op.execute("CREATE TYPE roast_level AS ENUM ('light', 'medium', 'medium_dark', 'dark')")
    op.execute("CREATE TYPE grind_type AS ENUM ('whole_bean', 'coarse', 'medium', 'fine')")

    op.execute("CREATE TYPE coffee_state_old AS ENUM ('green', 'roasted', 'ground')")
    op.execute(
        """
        ALTER TABLE products
          ALTER COLUMN state TYPE coffee_state_old
            USING 'roasted'::coffee_state_old
        """
    )
    op.execute("DROP TYPE coffee_state")
    op.execute("ALTER TYPE coffee_state_old RENAME TO coffee_state")

    op.add_column(
        "product_variants",
        sa.Column(
            "grind",
            postgresql.ENUM(name="grind_type", create_type=False),
            autoincrement=False,
            nullable=True,
        ),
    )
    # 500 g es la presentación más frecuente del catálogo anterior: sirve de
    # relleno para que la columna pueda volver a ser obligatoria.
    op.add_column(
        "product_variants",
        sa.Column(
            "weight_grams",
            sa.NUMERIC(precision=10, scale=2),
            autoincrement=False,
            nullable=False,
            server_default="500",
        ),
    )
    op.alter_column("product_variants", "weight_grams", server_default=None)
    op.drop_constraint(
        op.f("ck_product_variants_variant_min_qty_positive"), "product_variants", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_product_variants_variant_weight_positive"),
        "product_variants",
        "weight_grams > 0::numeric",
    )
    op.drop_column("product_variants", "min_qty_kg")
    op.drop_column("product_variants", "presentation")

    op.add_column(
        "coffee_attributes",
        sa.Column(
            "roast",
            postgresql.ENUM(name="roast_level", create_type=False),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "coffee_attributes",
        sa.Column(
            "cupping_score", sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "coffee_attributes",
        sa.Column("sensory_profile", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "coffee_attributes", sa.Column("roast_date", sa.DATE(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "coffee_attributes",
        sa.Column(
            "tasting_notes",
            postgresql.ARRAY(sa.VARCHAR(length=50)),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.execute("UPDATE coffee_attributes SET sensory_profile = notes WHERE notes IS NOT NULL")

    op.drop_constraint(
        op.f("ck_coffee_attributes_borer_damage_range"), "coffee_attributes", type_="check"
    )
    op.drop_constraint(
        op.f("ck_coffee_attributes_pasilla_range"), "coffee_attributes", type_="check"
    )
    op.drop_constraint(
        op.f("ck_coffee_attributes_healthy_bean_range"), "coffee_attributes", type_="check"
    )
    op.drop_constraint(
        op.f("ck_coffee_attributes_yield_factor_range"), "coffee_attributes", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_coffee_attributes_cupping_score_range"),
        "coffee_attributes",
        "cupping_score IS NULL OR cupping_score >= 0::numeric AND cupping_score <= 100::numeric",
    )

    op.drop_index("ix_coffee_attributes_yield_factor", table_name="coffee_attributes")
    op.drop_index("ix_coffee_attributes_filters", table_name="coffee_attributes")
    op.create_index(
        op.f("ix_coffee_attributes_filters"),
        "coffee_attributes",
        ["process", "roast", "altitude_masl"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coffee_attributes_score"), "coffee_attributes", ["cupping_score"], unique=False
    )

    op.drop_column("coffee_attributes", "notes")
    op.drop_column("coffee_attributes", "drying_method")
    op.drop_column("coffee_attributes", "sica_code")
    op.drop_column("coffee_attributes", "lot_code")
    op.drop_column("coffee_attributes", "screen_sizes")
    op.drop_column("coffee_attributes", "borer_damage_pct")
    op.drop_column("coffee_attributes", "pasilla_pct")
    op.drop_column("coffee_attributes", "healthy_bean_pct")
    op.drop_column("coffee_attributes", "yield_factor")
