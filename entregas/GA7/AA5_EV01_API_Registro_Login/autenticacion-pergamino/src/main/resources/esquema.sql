-- ============================================================
-- MONK GRAIN - Servicio de autenticacion
-- GA7-220501096-AA5-EV01
--
-- Hibernate crea estas tablas solo con `ddl-auto=update`, pero el esquema
-- se deja escrito por dos razones: deja ver las restricciones que de otro
-- modo quedan escondidas en anotaciones, y permite montar la base sin
-- arrancar la aplicacion.
-- ============================================================

CREATE TABLE IF NOT EXISTS auth_accounts (
    id              BIGSERIAL     PRIMARY KEY,

    -- UNIQUE en la columna y no solo una consulta previa en el servicio:
    -- entre consultar y escribir caben dos peticiones simultaneas.
    email           VARCHAR(254)  NOT NULL UNIQUE,

    -- 60 caracteres exactos: es lo que mide un resumen BCrypt, que lleva
    -- dentro el algoritmo, el factor de coste y la sal.
    password_hash   VARCHAR(60)   NOT NULL,

    full_name       VARCHAR(120)  NOT NULL,

    -- El texto del enumerado y no su posicion: guardar 0, 1 o 2 haria que
    -- insertar un rol nuevo en medio cambiara el de todas las cuentas.
    role            VARCHAR(20)   NOT NULL DEFAULT 'BUYER',

    failed_attempts INTEGER       NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ,

    CONSTRAINT auth_accounts_role_valido
        CHECK (role IN ('BUYER', 'SELLER', 'ADMIN')),

    -- Un contador negativo solo puede venir de un error de programacion.
    CONSTRAINT auth_accounts_intentos_no_negativos
        CHECK (failed_attempts >= 0)
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id          BIGSERIAL    PRIMARY KEY,

    -- El resumen SHA-256 del token, nunca el token: quien se lleve una
    -- copia de la base no debe quedarse con sesiones vivas en la mano.
    token_hash  CHAR(64)     NOT NULL UNIQUE,

    -- ON DELETE CASCADE: borrar una cuenta cierra sus sesiones. Sin esto
    -- quedarian filas apuntando a una cuenta que ya no existe.
    account_id  BIGINT       NOT NULL
                REFERENCES auth_accounts(id) ON DELETE CASCADE,

    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ  NOT NULL,

    CONSTRAINT auth_sessions_caduca_despues_de_crearse
        CHECK (expires_at > created_at)
);

-- Para la limpieza de sesiones vencidas, que recorre por fecha.
CREATE INDEX IF NOT EXISTS auth_sessions_expires_at_idx
    ON auth_sessions (expires_at);

-- Para cerrar de una vez todas las sesiones de una cuenta.
CREATE INDEX IF NOT EXISTS auth_sessions_account_id_idx
    ON auth_sessions (account_id);
