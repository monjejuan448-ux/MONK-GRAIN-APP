#!/usr/bin/env bash
#
# Empaqueta las evidencias que la guía pide entregar en ZIP.
#
# De las 17 evidencias de GA7, nueve se entregan comprimidas y el resto en
# PDF o en video. La regla general de la guía dice:
#
#   «Los ZIP/RAR se nombran NOMBRE_APELLIDO_AA#_EV## e incluyen un archivo
#    con el enlace del repositorio.»
#
# Cada ZIP lleva, además del código, su informe en PDF y el
# ENLACE_REPOSITORIO.txt. El código va con la ruta que tiene en el
# repositorio, para que quien descomprima vea dónde vive de verdad y no un
# montón de archivos sueltos.
#
# Se excluye siempre lo que se regenera: target/, __pycache__, node_modules.
# Un ZIP con el JAR dentro pesa 48 MB y no aporta nada que no salga de
# `mvn package`.
#
# Uso:
#   ./entregas/_plantilla/empaquetar.sh            # las nueve
#   ./entregas/_plantilla/empaquetar.sh AA5_EV01   # solo una

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APRENDIZ="ELIANA_CHACON"
DESTINO="$RAIZ/entregas/_zip"

# Rutas que nunca entran en un ZIP, porque se regeneran.
EXCLUIR=(-x '*/target/*' -x '*/__pycache__/*' -x '*/node_modules/*'
         -x '*.pyc' -x '*/.DS_Store')

mkdir -p "$DESTINO"

# empaquetar <AA#_EV##> <carpeta de la evidencia> [rutas extra del repositorio...]
#
# La carpeta de la evidencia entra completa menos los .html de origen (el PDF
# ya está, y el HTML solo sirve para reconstruirlo). Las rutas extra son
# código del producto que vive fuera de `entregas/`.
empaquetar() {
  local clave="$1"; shift
  local carpeta="$1"; shift
  local zip="$DESTINO/${APRENDIZ}_${clave}.zip"

  rm -f "$zip"
  cd "$RAIZ"

  zip -q -r "$zip" "$carpeta" -x '*.html' "${EXCLUIR[@]}"

  local extra
  for extra in "$@"; do
    if [[ ! -e "$extra" ]]; then
      echo "  ✗ falta $extra" >&2
      return 1
    fi
    zip -q -r "$zip" "$extra" "${EXCLUIR[@]}"
  done

  printf '  %-28s %s  (%s)\n' "${APRENDIZ}_${clave}.zip" \
    "$(unzip -l "$zip" | tail -1 | awk '{print $2" archivos"}')" \
    "$(du -h "$zip" | cut -f1)"
}

# ------------------------------------------------------------------
# Las nueve evidencias que se entregan comprimidas
# ------------------------------------------------------------------
declare -A EVIDENCIAS=(
  [AA2_EV01]="entregas/GA7/AA2_EV01_Modulo_JDBC"
  [AA2_EV02]="entregas/GA7/AA2_EV02_Modulo_Servlets_JSP"
  [AA3_EV01]="entregas/GA7/AA3_EV01_Modulo_Framework"
  [AA3_EV02]="entregas/GA7/AA3_EV02_Pruebas_Modulo"
  [AA4_EV03]="entregas/GA7/AA4_EV03_Componente_Proyecto"
  [AA5_EV01]="entregas/GA7/AA5_EV01_API_Registro_Login"
  [AA5_EV02]="entregas/GA7/AA5_EV02_Postman_API"
  [AA5_EV03]="entregas/GA7/AA5_EV03_APIs_Proyecto"
  [AA5_EV04]="entregas/GA7/AA5_EV04_Postman_Proyecto"
)

# Código del producto que cada evidencia necesita llevar dentro, porque vive
# fuera de su carpeta de entrega.
#
# AA3-EV02 y AA5-EV02 prueban el módulo de la evidencia anterior, así que
# llevan su código: un ZIP con el informe de las pruebas y sin lo probado no
# se puede ejecutar.
#
# AA4-EV03 es la única evidencia cuyo código vive en el producto y no en un
# módulo aparte: el hook, los cuatro componentes, la página refactorizada y
# las pruebas.
#
# AA5-EV03 y EV04 van sobre la API del proyecto entero. Se incluyen los
# routers, los esquemas y el núcleo —que es donde están los 107 endpoints y
# los 24 permisos— y no el backend completo, que arrastraría migraciones,
# datos de demostración y 453 pruebas sin relación con la evidencia.
declare -A EXTRAS=(
  [AA3_EV02]="entregas/GA7/AA3_EV01_Modulo_Framework/negociacion-pergamino"
  [AA5_EV02]="entregas/GA7/AA5_EV01_API_Registro_Login/autenticacion-pergamino"
  [AA4_EV03]="web/src/hooks/useProtectedResource.ts
              web/src/features/trading
              web/src/app/(public)/productor/posturas/page.tsx
              web/tests/TradingComponents.test.tsx"
  [AA5_EV03]="backend/app/main.py backend/app/modules backend/app/schemas backend/app/core"
  [AA5_EV04]="backend/app/main.py backend/app/modules backend/app/schemas backend/app/core"
)

SOLO="${1:-}"
HECHOS=0

echo
for clave in $(printf '%s\n' "${!EVIDENCIAS[@]}" | sort); do
  if [[ -n "$SOLO" && "$clave" != "$SOLO" ]]; then
    continue
  fi
  # shellcheck disable=SC2086 — se quiere la división en palabras de EXTRAS
  empaquetar "$clave" "${EVIDENCIAS[$clave]}" ${EXTRAS[$clave]:-}
  HECHOS=$((HECHOS + 1))
done

if [[ "$HECHOS" -eq 0 ]]; then
  echo "No hay ninguna evidencia con la clave «$SOLO»." >&2
  echo "Claves: $(printf '%s ' $(printf '%s\n' "${!EVIDENCIAS[@]}" | sort))" >&2
  exit 1
fi

echo
echo "$HECHOS archivo(s) en entregas/_zip/"
echo
