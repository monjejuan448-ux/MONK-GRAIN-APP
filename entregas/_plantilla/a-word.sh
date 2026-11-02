#!/usr/bin/env bash
# ============================================================
# Convierte un documento de evidencia a .docx
# ============================================================
# Algunas evidencias piden «documento Word» y no PDF —AA3-EV02 es
# una—. El origen sigue siendo el mismo HTML: así el texto se
# versiona una sola vez y las dos salidas no pueden divergir.
#
# LibreOffice necesita que se le diga el filtro de entrada; sin
# `--infilter` responde «no export filter found» y aborta. Y se
# le quitan al estilo las reglas de paginación, que no entiende y
# que solo sirven al PDF.
#
# Uso:
#   ./entregas/_plantilla/a-word.sh GA7/AA3_EV02_Pruebas_Modulo
# ============================================================

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/entregas"
CARPETA="${1:?Indica la carpeta de la evidencia, por ejemplo GA7/AA3_EV02_Pruebas_Modulo}"
DESTINO="$RAIZ/$CARPETA"

if ! command -v libreoffice >/dev/null 2>&1; then
  echo "LibreOffice no está instalado; es lo que hace la conversión." >&2
  exit 1
fi

for documento in "$DESTINO"/*.html; do
  [ -e "$documento" ] || { echo "No hay .html en $CARPETA" >&2; exit 1; }
  nombre="$(basename "${documento%.html}")"
  temporal="$DESTINO/_para_word.html"

  python3 - "$RAIZ/_plantilla/estilo.css" "$documento" "$temporal" <<'PY'
import pathlib, re, sys

css = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
cuerpo = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")

# `@page` y los saltos son del PDF; LibreOffice los ignora o los
# interpreta mal, así que no viajan al documento de Word.
css = re.sub(r"@page[^{]*\{[^}]*(\{[^}]*\}[^}]*)*\}", "", css, flags=re.S)
css = re.sub(r"\s*break-(after|inside)\s*:[^;]+;", "", css)

pathlib.Path(sys.argv[3]).write_text(
    f'<!DOCTYPE html>\n<html lang="es"><head><meta charset="utf-8">\n'
    f"<style>{css}</style></head><body>\n{cuerpo}\n</body></html>",
    encoding="utf-8",
)
PY

  libreoffice --headless \
    --infilter="HTML (StarWriter)" \
    --convert-to 'docx:MS Word 2007 XML' \
    --outdir "$DESTINO" "$temporal" >/dev/null 2>&1

  mv "$DESTINO/_para_word.docx" "$DESTINO/$nombre.docx"
  rm -f "$temporal"

  peso=$(( $(stat -c%s "$DESTINO/$nombre.docx") / 1024 ))
  echo "  $CARPETA/$nombre.docx  (${peso} KB)"
done
