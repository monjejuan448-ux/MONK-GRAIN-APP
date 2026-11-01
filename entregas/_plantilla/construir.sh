#!/usr/bin/env bash
# ============================================================
# Construye los PDF de las evidencias.
# ============================================================
# WeasyPrint vive en la imagen del backend, no en el equipo, así
# que se usa esa imagen con la carpeta `entregas/` montada. Es un
# contenedor desechable: no toca `docker-compose.yml` ni el
# entorno de desarrollo, que no tienen por qué saber nada de las
# evidencias del curso.
#
# `--user` evita que los PDF queden a nombre de root y haya que
# borrarlos con sudo después.
#
# Uso:
#   ./entregas/_plantilla/construir.sh                  (todas)
#   ./entregas/_plantilla/construir.sh GA7/AA1_EV01_Plan_Trabajo
# ============================================================

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGEN="monk-grain-app-backend"

if ! docker image inspect "$IMAGEN" >/dev/null 2>&1; then
  echo "No encuentro la imagen '$IMAGEN'. Levanta el proyecto antes:" >&2
  echo "  docker compose up -d backend" >&2
  exit 1
fi

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e XDG_CACHE_HOME=/tmp \
  -v "$RAIZ/entregas:/entregas" \
  "$IMAGEN" \
  python /entregas/_plantilla/construir.py "$@"
