-- ============================================================
-- MONK GRAIN — Extensiones de PostgreSQL
-- Se ejecuta una sola vez, al crear el volumen de datos.
-- ============================================================

-- CITEXT: texto insensible a mayúsculas. Se usa en users.email para que dos
-- cuentas no puedan diferenciarse solo por el uso de mayúsculas.
CREATE EXTENSION IF NOT EXISTS citext;

-- pg_trgm: índices de similitud para la búsqueda por texto del catálogo.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent: permite que "narino" encuentre "Nariño" en las búsquedas.
CREATE EXTENSION IF NOT EXISTS unaccent;
