-- ============================================================
-- MONK GRAIN — Esquema del módulo de catálogo de pergamino
-- GA7-220501096-AA2-EV01
-- ============================================================
-- Refleja el dominio real del proyecto: lo que describe un lote
-- de café pergamino seco es su análisis físico, no su perfil de
-- taza. El dato que gobierna su valor es el FACTOR DE
-- RENDIMIENTO: los kilos de pergamino que hay que trillar para
-- obtener un saco de 70 kg de café excelso de exportación.
-- Más bajo es mejor; el estándar de la Federación es 94.
--
-- Los nombres van en inglés y los comentarios en español, que es
-- el estándar definido en la evidencia AA1-EV02 y el que usa el
-- esquema de la aplicación (`products`, `coffee_attributes`).
--
-- Base de datos propia (`monkgrain_java`) y no la de la
-- aplicación: un módulo de aprendizaje que inserta y borra no
-- debe tocar los datos de demostración del producto.
-- ============================================================

DROP TABLE IF EXISTS pergamino_lots;
DROP TABLE IF EXISTS producers;

-- ------------------------------------------------------------
-- Vendedores: caficultores, fincas y cooperativas
-- ------------------------------------------------------------
CREATE TABLE producers (
    producer_id   SERIAL       PRIMARY KEY,
    farm_name     VARCHAR(150) NOT NULL,
    municipality  VARCHAR(100) NOT NULL,
    department    VARCHAR(100) NOT NULL,
    -- Código del predio en el Sistema de Información Cafetera.
    -- No se contrasta con la Federación: se publica tal como lo
    -- declara el vendedor.
    sica_code     VARCHAR(40)
);

-- ------------------------------------------------------------
-- Lotes de pergamino con su análisis físico
-- ------------------------------------------------------------
CREATE TABLE pergamino_lots (
    lot_id            SERIAL        PRIMARY KEY,
    producer_id       INTEGER       NOT NULL,
    -- El código con el que el productor identifica el lote en su
    -- finca. Permite que una reclamación apunte a un lote
    -- concreto y no al café «en general» de esa finca.
    lot_code          VARCHAR(60)   NOT NULL,
    variety           VARCHAR(80),

    -- --- Análisis físico. Todo opcional: exigirlo para publicar
    -- --- dejaría fuera a la mayoría de caficultores pequeños,
    -- --- que no han mandado su café a un laboratorio.
    yield_factor      NUMERIC(5,2),
    moisture_pct      NUMERIC(4,2),
    healthy_bean_pct  NUMERIC(5,2),
    pasilla_pct       NUMERIC(5,2),
    borer_damage_pct  NUMERIC(5,2),

    -- --- Condiciones comerciales ---
    price_per_kg      NUMERIC(14,2) NOT NULL,
    available_kg      INTEGER       NOT NULL,
    harvest_date      DATE,
    published         BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_lot_producer
        FOREIGN KEY (producer_id) REFERENCES producers (producer_id)
        ON DELETE RESTRICT,

    -- Dos lotes del mismo productor no pueden compartir código:
    -- es lo que hace que una reclamación sea rastreable.
    CONSTRAINT uq_lot_code_per_producer UNIQUE (producer_id, lot_code),

    -- Fuera del rango 80-130 no existe café comercializable: un
    -- valor así es un error de digitación, no un café excepcional.
    CONSTRAINT ck_yield_factor_range
        CHECK (yield_factor IS NULL OR yield_factor BETWEEN 80 AND 130),

    CONSTRAINT ck_moisture_range
        CHECK (moisture_pct IS NULL OR moisture_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_healthy_bean_range
        CHECK (healthy_bean_pct IS NULL OR healthy_bean_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_pasilla_range
        CHECK (pasilla_pct IS NULL OR pasilla_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_borer_range
        CHECK (borer_damage_pct IS NULL OR borer_damage_pct BETWEEN 0 AND 100),

    -- El precio y los kilos no son negativos. La comprobación va
    -- en la base y no solo en la aplicación: así la regla se
    -- cumple venga la escritura de donde venga.
    CONSTRAINT ck_price_non_negative     CHECK (price_per_kg >= 0),
    CONSTRAINT ck_available_non_negative CHECK (available_kg >= 0)
);

-- Índice del filtro más usado del catálogo: el comprador acota el
-- factor que acepta y solo mira lo publicado.
CREATE INDEX ix_lots_published_factor
    ON pergamino_lots (published, yield_factor);

CREATE INDEX ix_lots_producer ON pergamino_lots (producer_id);
