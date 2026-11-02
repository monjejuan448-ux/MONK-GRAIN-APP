#!/usr/bin/env python3
"""Comprueba que los DTO de Kotlin coincidan con la API real.

GA8-220501096-AA2-EV02

El error más común de un cliente móvil es un nombre de campo mal escrito, y
es también el más difícil de ver: compila sin protestar y falla solo al
recibir la respuesta, en el teléfono del usuario. Un `@SerialName("yeld_factor")`
con una letra de menos no lo detecta ningún compilador.

Este guion lee `CatalogDto.kt`, saca los nombres que cada clase espera del
JSON, y los contrasta con el documento OpenAPI que publica el servicio en
marcha. Comprueba tres cosas:

  1. Que no se espere un campo que la API no manda  (el error clásico)
  2. Que lo obligatorio en la API no esté declarado como opcional de más
  3. Que lo que la API puede mandar nulo esté declarado con `?` en Kotlin
     —con kotlinx.serialization, un campo no nulo que llega nulo rompe la
     lectura del JSON entero, no solo ese campo—

Lo que la API manda y el DTO no declara NO es un error: `ignoreUnknownKeys`
está activado a propósito, para que el servidor pueda crecer sin obligar a
actualizar la aplicación instalada. Se informa como aviso.

Uso:
    curl -s http://localhost:8000/openapi.json > openapi.json
    python3 verificar_contrato.py openapi.json
"""

import json
import re
import sys
from pathlib import Path

RUTA_DTO = Path(__file__).parent / (
    "monkgrain-movil/app/src/main/java/co/monkgrain/movil/data/dto/CatalogDto.kt"
)

# Qué clase de Kotlin corresponde a qué esquema de la API. Es lo único que no
# se puede deducir: los nombres se eligieron distintos a propósito, para que
# el DTO no quede atado al nombre que el servidor le dé hoy.
EQUIVALENCIAS = {
    "ProducerSummaryDto": "ProducerSummary",
    "LotListItemDto": "ProductListItem",
    "VariantDto": "VariantResponse",
    "LotDetailDto": "ProductDetail",
    "PageDto": "Page_ProductListItem_",
}


def campos_de_kotlin(fuente: str) -> dict[str, dict[str, bool]]:
    """{clase: {nombre_json: admite_nulo}} leído del archivo de Kotlin."""
    clases: dict[str, dict[str, bool]] = {}
    clase_actual = None

    for linea in fuente.splitlines():
        encabezado = re.match(r"\s*data class (\w+)", linea)
        if encabezado:
            clase_actual = encabezado.group(1)
            clases[clase_actual] = {}
            continue
        if clase_actual is None:
            continue
        if linea.strip() == ")" or linea.startswith("}"):
            clase_actual = None
            continue

        # `@SerialName("available_kg") val availableKg: Int,`  o
        # `val slug: String,`
        propiedad = re.search(
            r'(?:@SerialName\("(?P<json>[^"]+)"\)\s*)?va[lr]\s+'
            r"(?P<kotlin>\w+)\s*:\s*(?P<tipo>[^,=]+)",
            linea,
        )
        if not propiedad:
            continue

        nombre = propiedad.group("json") or camel_a_snake(propiedad.group("kotlin"))
        tipo = propiedad.group("tipo").strip()
        clases[clase_actual][nombre] = tipo.endswith("?")

    return clases


def camel_a_snake(nombre: str) -> str:
    """`availableKg` → `available_kg`, para los campos sin `@SerialName`."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", nombre).lower()


def campos_de_api(esquema: dict) -> dict[str, bool]:
    """{nombre: admite_nulo} de un esquema del OpenAPI."""
    salida = {}
    for campo, definicion in (esquema.get("properties") or {}).items():
        opciones = definicion.get("anyOf") or definicion.get("oneOf") or []
        admite_nulo = any(o.get("type") == "null" for o in opciones)
        salida[campo] = admite_nulo
    return salida


def main() -> int:
    ruta_api = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    with open(ruta_api, encoding="utf-8") as f:
        esquemas = json.load(f)["components"]["schemas"]

    clases = campos_de_kotlin(RUTA_DTO.read_text(encoding="utf-8"))

    problemas = 0
    avisos = 0

    for clase, nombre_api in EQUIVALENCIAS.items():
        print(f"\n{clase}  ↔  {nombre_api}")

        if clase not in clases:
            print(f"  ✗ no se encontró la clase en {RUTA_DTO.name}")
            problemas += 1
            continue
        if nombre_api not in esquemas:
            print(f"  ✗ la API no publica un esquema llamado «{nombre_api}»")
            problemas += 1
            continue

        en_kotlin = clases[clase]
        en_api = campos_de_api(esquemas[nombre_api])
        obligatorios = set(esquemas[nombre_api].get("required") or [])

        # 1. Campos que el DTO espera y la API no manda.
        inventados = sorted(set(en_kotlin) - set(en_api))
        for campo in inventados:
            print(f"  ✗ `{campo}` no existe en la API")
            problemas += 1

        # 2. Lo obligatorio que llegaría nulo y el DTO no lo admite.
        for campo, admite_nulo_api in en_api.items():
            if campo not in en_kotlin:
                continue
            if admite_nulo_api and not en_kotlin[campo]:
                print(f"  ✗ `{campo}` puede llegar nulo y en Kotlin no lleva `?`")
                problemas += 1

        # 3. Lo que la API manda y el DTO ignora: aviso, no error.
        ignorados = sorted(set(en_api) - set(en_kotlin))
        if ignorados:
            print(f"  · ignora {len(ignorados)}: {', '.join(ignorados)}")
            avisos += len(ignorados)

        if not inventados:
            cubiertos = len(set(en_kotlin) & set(en_api))
            faltan_ob = sorted(obligatorios - set(en_kotlin))
            print(f"  ✓ {cubiertos} de {len(en_api)} campos, "
                  f"{len(obligatorios - set(faltan_ob))} de {len(obligatorios)} obligatorios")

    print(f"\n{'─' * 52}")
    if problemas:
        print(f"{problemas} problema(s) en el contrato. La app fallaría al leer la respuesta.")
        return 1
    print(f"Contrato correcto. {avisos} campo(s) de la API sin usar, que es legítimo:")
    print("`ignoreUnknownKeys` permite que el servidor crezca sin romper la app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
