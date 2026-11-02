#!/usr/bin/env python3
"""Genera ENDPOINTS.md desde el documento OpenAPI del servicio en marcha.

GA7-220501096-AA5-EV03

Un catálogo de endpoints escrito a mano se desactualiza en la primera
semana: alguien añade una ruta y no se acuerda de este archivo. Generarlo
desde el OpenAPI que publica el propio servicio hace imposible esa deriva,
porque la fuente es el código que de verdad está corriendo.

Lo único escrito a mano es el párrafo que describe cada grupo. Eso no lo
puede saber una máquina, y es justamente lo que hace útil el documento.

Uso:
    docker compose up -d
    curl -s http://localhost:8000/openapi.json > openapi.json
    python3 generar_endpoints.py [openapi.json] [ENDPOINTS.md]
"""

import collections
import json
import sys

# El orden del recorrido de un usuario, no el alfabético: primero entrar,
# después mirar, comprar, y al final lo que solo ven vendedor y administrador.
ORDEN = [
    "sistema", "autenticación", "usuarios", "catálogo", "carrito", "pedidos",
    "devoluciones", "reseñas", "oferta y demanda", "panel del productor",
    "liquidaciones", "administración",
]

QUE_ES = {
    "sistema": "Comprobación de vida del servicio. Es el único endpoint sin prefijo de versión: el orquestador que lo consulta no debe tener que saber en qué versión va la API.",
    "autenticación": "Registro, verificación de correo, ingreso, renovación y recuperación de contraseña. Es el único grupo donde casi todo es público, y por eso el que más topes de frecuencia lleva.",
    "usuarios": "El perfil de quien está dentro: datos, direcciones y consentimientos. Nadie consulta aquí la cuenta de otro.",
    "catálogo": "Lo que se puede comprar. Público y de solo lectura: los lotes los crea el productor desde su panel, no desde aquí.",
    "carrito": "La selección antes de pagar. Vive en el servidor y no en el navegador, porque el precio y la disponibilidad del pergamino cambian y el carrito tiene que enterarse.",
    "pedidos": "Lo comprado, con su estado y sus sub-órdenes. Un pedido con lotes de tres fincas genera tres sub-órdenes bajo un único número.",
    "devoluciones": "Solicitud, aprobación y seguimiento de una devolución, con los plazos que fijó la revisión legal.",
    "reseñas": "Opiniones sobre los lotes y sobre los vendedores, solo de quien compró.",
    "oferta y demanda": "El mercado en su segundo sentido: el comprador publica lo que busca y los caficultores responden con su precio.",
    "panel del productor": "Todo lo que hace un vendedor con su finca: lotes, variantes, fotos, pedidos recibidos y certificaciones. Es el grupo más grande, y se nota que es donde vive el trabajo diario.",
    "liquidaciones": "El dinero de vuelta al vendedor: cuentas bancarias, cierre de periodo y pago. Es lo más reciente de la API.",
    "administración": "Aprobación de vendedores, moderación y parámetros. Todo exige el permiso explícito, no basta el rol.",
}

# `/auth/refresh` y `/auth/logout` no llevan cabecera `Authorization`, pero
# tampoco son públicos: reciben el refresh token en el cuerpo. Sin esta nota,
# la tabla diría la verdad y daría a entender lo contrario.
TOKEN_EN_EL_CUERPO = {"/api/v1/auth/refresh", "/api/v1/auth/logout"}


def recolectar(documento):
    """Agrupa las operaciones por etiqueta, ordenadas por ruta."""
    grupos = collections.defaultdict(list)
    for ruta, item in sorted(documento["paths"].items()):
        for metodo, operacion in item.items():
            if metodo not in ("get", "post", "put", "patch", "delete"):
                continue
            grupos[(operacion.get("tags") or ["-"])[0]].append({
                "metodo": metodo.upper(),
                "ruta": ruta,
                "resumen": operacion.get("summary") or "",
                # `security` en la operación significa que FastAPI exige la
                # cabecera. Su ausencia no implica que el endpoint sea abierto.
                "cabecera": bool(operacion.get("security")),
            })
    return grupos


def marca(operacion):
    if operacion["cabecera"]:
        return "sí"
    if operacion["ruta"] in TOKEN_EN_EL_CUERPO:
        return "cuerpo"
    return "—"


def generar(documento):
    grupos = recolectar(documento)
    total = sum(len(v) for v in grupos.values())
    L = []

    L += [
        "# ENDPOINTS — API de MONK GRAIN",
        "",
        "**GA7-220501096-AA5-EV03** · API del proyecto formativo",
        "",
        f"**Base:** `http://localhost:8000/api/v1` · **{total} endpoints** en "
        f"{len(grupos)} grupos",
        "**Formato:** JSON en entrada y salida, UTF-8.",
        "**Autenticación:** `Authorization: Bearer <access_token>`. El token lo",
        "entrega `POST /auth/login` y dura 30 minutos; se renueva con",
        "`POST /auth/refresh` sin volver a pedir la contraseña.",
        "",
        "> Este archivo **se genera** desde el documento OpenAPI que publica el",
        "> servicio en marcha (`GET /openapi.json`), con `generar_endpoints.py`.",
        "> No se edita a mano: un catálogo escrito a mano se desactualiza en la",
        "> primera semana, cuando alguien añade una ruta y no se acuerda de él.",
        "",
        "---",
        "",
        "## Resumen por grupo",
        "",
        "| Grupo | Endpoints | Qué resuelve |",
        "|---|---:|---|",
    ]
    for tag in ORDEN:
        if tag in grupos:
            ancla = tag.replace(" ", "-")
            L.append(f"| [{tag}](#{ancla}) | {len(grupos[tag])} | "
                     f"{QUE_ES[tag].split('.')[0]}. |")
    L += [f"| **Total** | **{total}** | |", "", "---", ""]

    L += [
        "## Convenciones",
        "",
        "| | |",
        "|---|---|",
        "| Rutas | Plural y en minúsculas: `/orders`, `/products`, no `/getOrder` |",
        "| Versión | `/api/v1` en el prefijo. La única excepción es `/health` |",
        "| Identificadores | UUID en la ruta: `/orders/{order_id}` |",
        "| Páginas | `?page=1&page_size=20`; la respuesta trae `items`, `total`, "
        "`page`, `page_size`, `total_pages`, `has_next` y `has_previous` |",
        "| Fechas | ISO 8601 con zona: `2026-11-02T03:17:46Z` |",
        "| Dinero | Cadena decimal, nunca coma flotante: `\"1850000.00\"` |",
        "| Peso | Kilogramos. La carga de 125 kg es una **lectura**, no una unidad de almacenamiento |",
        "| Errores | `{\"error\": {\"code\", \"message\", \"details\"?}}`. "
        "**No** es el `detail` de serie de FastAPI: un manejador propio lo "
        "envuelve, para que el cliente pueda ramificar por `code` sin "
        "analizar el texto del mensaje |",
        "",
        "### La columna «Token»",
        "",
        "| Valor | Significa |",
        "|---|---|",
        "| `sí` | Exige la cabecera `Authorization: Bearer <access_token>` |",
        "| `cuerpo` | No lleva cabecera, pero **tampoco es público**: recibe el *refresh token* en el cuerpo. Solo `/auth/refresh` y `/auth/logout` |",
        "| `—` | Público |",
        "",
        "### Códigos",
        "",
        "Cada error HTTP viaja con un `code` legible que el cliente puede",
        "comparar, en lugar de tener que reconocer el mensaje:",
        "",
        "```json",
        "{\"error\": {\"code\": \"business_rule_violation\",",
        "            \"message\": \"Este lote se vende desde 250 kg.\",",
        "            \"details\": {\"min_qty_kg\": 250}}}",
        "```",
        "",
        "`details` solo aparece cuando hay algo accionable dentro: en el ejemplo,",
        "el mínimo de kilos, para que el formulario pueda ponerlo en el campo sin",
        "leer el texto.",
        "",
        "| Código | Cuándo |",
        "|---|---|",
        "| `200` | Consulta o modificación correcta |",
        "| `201` | Se creó un recurso |",
        "| `202` | Se aceptó, pero no se confirma el efecto (registro, recuperación) |",
        "| `204` | Se hizo y no hay nada que devolver |",
        "| `400` | La petición no tiene sentido para el estado actual |",
        "| `401` | Sin credenciales, o caducadas |",
        "| `403` | Identificado, pero sin el permiso necesario |",
        "| `404` | No existe, o no es tuyo y no debes saber que existe |",
        "| `409` | Choca con el estado actual del recurso |",
        "| `422` | La validación rechazó el cuerpo |",
        "| `429` | Se pasó del tope de frecuencia |",
        "",
        "---",
        "",
    ]

    for tag in ORDEN:
        if tag not in grupos:
            continue
        operaciones = grupos[tag]
        con_cabecera = sum(1 for o in operaciones if o["cabecera"])
        en_cuerpo = sum(1 for o in operaciones if marca(o) == "cuerpo")
        publicos = len(operaciones) - con_cabecera - en_cuerpo

        L += [f"## {tag}", "", QUE_ES[tag], ""]
        resumen = f"**{len(operaciones)} endpoints** · {con_cabecera} con token"
        if en_cuerpo:
            resumen += f" · {en_cuerpo} con el token en el cuerpo"
        resumen += f" · {publicos} públicos"
        L += [resumen, "", "| Método | Ruta | Token | Qué hace |", "|---|---|:---:|---|"]
        for o in sorted(operaciones, key=lambda x: (x["ruta"], x["metodo"])):
            ruta = o["ruta"].replace("/api/v1", "")
            L.append(f"| `{o['metodo']}` | `{ruta}` | {marca(o)} | {o['resumen']} |")
        L.append("")

    L += [
        "---",
        "",
        "## Cómo regenerar este archivo",
        "",
        "```bash",
        "docker compose up -d",
        "curl -s http://localhost:8000/openapi.json > openapi.json",
        "python3 entregas/GA7/AA5_EV03_APIs_Proyecto/generar_endpoints.py openapi.json \\",
        "        entregas/GA7/AA5_EV03_APIs_Proyecto/ENDPOINTS.md",
        "```",
        "",
        "La documentación interactiva del mismo documento está en",
        "<http://localhost:8000/docs> (Swagger UI) y <http://localhost:8000/redoc>.",
        "",
    ]
    return "\n".join(L)


def main():
    entrada = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    salida = sys.argv[2] if len(sys.argv) > 2 else "ENDPOINTS.md"
    with open(entrada, encoding="utf-8") as f:
        documento = json.load(f)
    texto = generar(documento)
    with open(salida, "w", encoding="utf-8") as f:
        f.write(texto)
    total = sum(
        1 for item in documento["paths"].values() for m in item
        if m in ("get", "post", "put", "patch", "delete")
    )
    print(f"{salida}: {total} endpoints")


if __name__ == "__main__":
    main()
