#!/usr/bin/env python3
"""Convierte los documentos de evidencia de HTML a PDF.

Cada evidencia se escribe en HTML —que se versiona y se puede revisar en un
`diff`— y de ahí sale el PDF que pide la guía. Lo contrario, escribir el PDF a
mano, deja un binario que nadie puede revisar ni corregir después.

Se ejecuta dentro del contenedor del backend, que es donde vive WeasyPrint:

    docker compose exec -T backend python /app/entregas/_plantilla/construir.py

Sin argumentos construye todas las evidencias que tengan un `.html`. Con
argumentos, solo las carpetas indicadas:

    ... construir.py GA7/AA1_EV01_Plan_Trabajo
"""

import sys
from pathlib import Path

from weasyprint import CSS, HTML

# El script vive en `entregas/_plantilla/`, de modo que la raíz de entregas es
# su directorio padre.
RAIZ = Path(__file__).resolve().parent.parent
ESTILO = RAIZ / "_plantilla" / "estilo.css"


# Envoltorio del fragmento. Cada evidencia se escribe como contenido suelto
# —portada, secciones— sin repetir la estructura del documento en los 23
# archivos. El `charset` va aquí y no en cada uno porque olvidarlo en uno solo
# produce acentos rotos («TÃ©cnico» en lugar de «Técnico») que no se ven hasta
# abrir el PDF.
ESQUELETO = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
</head>
<body>
{contenido}
</body>
</html>"""


def construir(documento: Path) -> Path:
    """Renderiza un HTML a PDF junto al original, con el mismo nombre."""
    salida = documento.with_suffix(".pdf")
    contenido = documento.read_text(encoding="utf-8")
    pagina = ESQUELETO.format(titulo=documento.stem, contenido=contenido)

    HTML(string=pagina, base_url=str(documento.parent)).write_pdf(
        str(salida), stylesheets=[CSS(filename=str(ESTILO))]
    )
    return salida


def main(argv: list[str]) -> int:
    if not ESTILO.exists():
        print(f"No encuentro la hoja de estilo: {ESTILO}", file=sys.stderr)
        return 1

    if argv:
        carpetas = [RAIZ / arg for arg in argv]
        faltan = [c for c in carpetas if not c.is_dir()]
        if faltan:
            for c in faltan:
                print(f"No existe la carpeta: {c}", file=sys.stderr)
            return 1
        documentos = sorted(d for c in carpetas for d in c.glob("*.html"))
    else:
        documentos = sorted(RAIZ.glob("GA*/*/*.html"))

    if not documentos:
        print("No hay documentos .html que construir.")
        return 0

    for documento in documentos:
        salida = construir(documento)
        peso = salida.stat().st_size / 1024
        print(f"  {salida.relative_to(RAIZ)}  ({peso:.0f} KB)")

    print(f"\n{len(documentos)} documento(s) construido(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
