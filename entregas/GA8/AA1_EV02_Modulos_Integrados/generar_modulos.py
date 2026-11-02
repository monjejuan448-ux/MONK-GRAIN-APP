#!/usr/bin/env python3
"""Genera MODULOS.md: datos de entrada y salida de cada endpoint, por módulo.

GA8-220501096-AA1-EV02

La evidencia pide «documentación por módulo y componente (datos de entrada y
salida)». Escribir eso a mano para 107 endpoints daría un documento de
cincuenta páginas desactualizado en la primera semana. Se genera del
documento OpenAPI que publica el servicio en marcha, resolviendo las
referencias a los esquemas para que los campos aparezcan en el texto y no
como un `$ref` que nadie va a seguir.

Y el informe de pruebas por módulo sale del XML de JUnit que produce pytest,
no de contar funciones a ojo: así los números son los que de verdad se
ejecutaron.

Uso:
    curl -s http://localhost:8000/openapi.json > openapi.json
    docker compose exec backend pytest -q --junitxml=/tmp/junit.xml
    docker compose exec backend cat /tmp/junit.xml > junit.xml
    python3 generar_modulos.py openapi.json junit.xml MODULOS.md
"""

import collections
import json
import sys
import xml.etree.ElementTree as ET

# El orden del recorrido de un usuario, no el alfabético.
ORDEN = [
    "sistema", "autenticación", "usuarios", "catálogo", "carrito", "pedidos",
    "devoluciones", "reseñas", "oferta y demanda", "panel del productor",
    "liquidaciones", "administración",
]

# Qué módulo del código implementa cada grupo de la API, y qué archivos de
# prueba lo cubren. Esto no lo puede deducir una máquina del OpenAPI: la
# etiqueta es en español y el paquete en inglés.
MODULOS = {
    "sistema": ("app/main.py", ["test_performance"]),
    "autenticación": ("app/modules/auth/", ["test_auth_flow", "test_rate_limit"]),
    "usuarios": ("app/modules/users/", ["test_profile", "test_addresses"]),
    "catálogo": ("app/modules/catalog/", ["test_catalog", "test_pergamino"]),
    "carrito": ("app/modules/cart/", ["test_checkout", "test_wishlist"]),
    "pedidos": ("app/modules/orders/", ["test_checkout", "test_receipt"]),
    "devoluciones": ("app/modules/returns/", ["test_returns"]),
    "reseñas": ("app/modules/reviews/", ["test_reviews"]),
    "oferta y demanda": ("app/modules/trading/", ["test_trading"]),
    "panel del productor": ("app/modules/producers/",
                            ["test_producer_catalog", "test_certifications",
                             "test_fulfillment"]),
    "liquidaciones": ("app/modules/payments/", ["test_settlements"]),
    "administración": ("app/modules/admin/", ["test_admin"]),
}

MAX_CAMPOS = 14   # más allá de esto, la tabla deja de ser legible


def tipo_de(esquema, esquemas, profundidad=0):
    """Nombre legible del tipo, siguiendo `$ref` y `anyOf`."""
    if profundidad > 4 or not isinstance(esquema, dict):
        return "—"

    ref = esquema.get("$ref")
    if ref:
        return ref.rsplit("/", 1)[-1]

    opciones = esquema.get("anyOf") or esquema.get("oneOf")
    if opciones:
        # Pydantic representa «opcional» como anyOf con null. Lo que
        # interesa es el tipo útil, y marcar que admite vacío.
        utiles = [o for o in opciones if o.get("type") != "null"]
        admite_nulo = len(utiles) != len(opciones)
        nombre = tipo_de(utiles[0], esquemas, profundidad + 1) if utiles else "—"
        return f"{nombre}?" if admite_nulo else nombre

    if esquema.get("type") == "array":
        return f"lista de {tipo_de(esquema.get('items', {}), esquemas, profundidad + 1)}"

    if esquema.get("enum"):
        return "uno de: " + ", ".join(f"`{v}`" for v in esquema["enum"][:6])

    equivalencias = {"string": "texto", "integer": "entero", "number": "decimal",
                     "boolean": "sí/no", "object": "objeto"}
    return equivalencias.get(esquema.get("type"), esquema.get("type") or "—")


def campos_de(nombre_esquema, esquemas, profundidad=0):
    """Lista de (campo, tipo, obligatorio) de un esquema por su nombre."""
    esquema = esquemas.get(nombre_esquema)
    if not isinstance(esquema, dict):
        return []
    obligatorios = set(esquema.get("required") or [])
    salida = []
    for campo, definicion in (esquema.get("properties") or {}).items():
        salida.append((campo, tipo_de(definicion, esquemas, profundidad),
                       campo in obligatorios))
    return salida


def entrada_de(operacion, esquemas):
    """Qué recibe el endpoint: parámetros de ruta y consulta, y cuerpo."""
    partes = []

    for parametro in operacion.get("parameters") or []:
        donde = {"path": "ruta", "query": "consulta",
                 "header": "cabecera"}.get(parametro.get("in"), parametro.get("in"))
        tipo = tipo_de(parametro.get("schema", {}), esquemas)
        marca = "obligatorio" if parametro.get("required") else "opcional"
        partes.append((f"{parametro['name']} *({donde})*", tipo, marca == "obligatorio"))

    cuerpo = operacion.get("requestBody")
    if cuerpo:
        contenido = (cuerpo.get("content") or {})
        for tipo_medio, detalle in contenido.items():
            ref = (detalle.get("schema") or {}).get("$ref")
            if ref:
                nombre = ref.rsplit("/", 1)[-1]
                partes.append((f"**cuerpo** `{nombre}`", f"*{tipo_medio}*", True))
                partes.extend(("  · " + c, t, o)
                              for c, t, o in campos_de(nombre, esquemas))
            else:
                partes.append(("**cuerpo**", tipo_de(detalle.get("schema", {}), esquemas), True))
    return partes


def salida_de(operacion, esquemas):
    """Qué devuelve el endpoint en el caso correcto."""
    for codigo, respuesta in sorted((operacion.get("responses") or {}).items()):
        if not codigo.startswith("2"):
            continue
        contenido = (respuesta.get("content") or {})
        for _, detalle in contenido.items():
            esquema = detalle.get("schema") or {}
            ref = esquema.get("$ref")
            if ref:
                nombre = ref.rsplit("/", 1)[-1]
                return codigo, nombre, campos_de(nombre, esquemas)
            return codigo, tipo_de(esquema, esquemas), []
        return codigo, "sin cuerpo", []
    return "—", "—", []


def pruebas_por_archivo(ruta_junit):
    """{archivo: (pruebas, fallos, segundos)} desde el XML de JUnit."""
    arbol = ET.parse(ruta_junit)
    resumen = collections.defaultdict(lambda: [0, 0, 0.0])
    for caso in arbol.iter("testcase"):
        archivo = (caso.get("classname") or "").split(".")
        # classname es «tests.integration.test_trading.TestAlgo»
        nombre = next((p for p in archivo if p.startswith("test_")), "?")
        fila = resumen[nombre]
        fila[0] += 1
        if caso.find("failure") is not None or caso.find("error") is not None:
            fila[1] += 1
        fila[2] += float(caso.get("time") or 0)
    return {k: tuple(v) for k, v in resumen.items()}


def generar(documento, pruebas):
    esquemas = documento.get("components", {}).get("schemas", {})
    grupos = collections.defaultdict(list)
    for ruta, item in sorted(documento["paths"].items()):
        for metodo, operacion in item.items():
            if metodo in ("get", "post", "put", "patch", "delete"):
                grupos[(operacion.get("tags") or ["-"])[0]].append(
                    (metodo.upper(), ruta, operacion))

    total = sum(len(v) for v in grupos.values())
    L = [
        "# MÓDULOS INTEGRADOS — datos de entrada y salida",
        "",
        "**GA8-220501096-AA1-EV02**",
        "",
        f"{total} endpoints en {len(grupos)} módulos. Para cada uno: qué recibe,",
        "qué devuelve y qué pruebas lo cubren.",
        "",
        "> **Este archivo se genera.** Sale del documento OpenAPI que publica el",
        "> servicio en marcha y del XML de JUnit que produce `pytest`, con",
        "> `generar_modulos.py`. Ni los campos ni los números de prueba se",
        "> escriben a mano: así no pueden decir una cosa distinta del código.",
        "",
        "Convenciones de las tablas:",
        "",
        "| | |",
        "|---|---|",
        "| `texto?` | admite vacío (`null`) |",
        "| **ob.** | obligatorio |",
        "| `· campo` | campo dentro del cuerpo |",
        "",
        "---",
        "",
        "## Resumen",
        "",
        "| Módulo | Paquete | Endpoints | Pruebas | Fallos |",
        "|---|---|---:|---:|---:|",
    ]

    for etiqueta in ORDEN:
        if etiqueta not in grupos:
            continue
        paquete, archivos = MODULOS.get(etiqueta, ("—", []))
        n = sum(pruebas.get(a, (0, 0, 0))[0] for a in archivos)
        f = sum(pruebas.get(a, (0, 0, 0))[1] for a in archivos)
        L.append(f"| [{etiqueta}](#{etiqueta.replace(' ', '-')}) | `{paquete}` | "
                 f"{len(grupos[etiqueta])} | {n} | {f} |")

    # La columna «Pruebas» NO suma el total, y conviene explicar por qué antes
    # de que alguien lo tome por un error de cuenta.
    asignados = {a for _, archivos in MODULOS.values() for a in archivos}
    repetidos = {a: pruebas.get(a, (0, 0, 0))[0] for a in asignados
                 if sum(1 for _, ar in MODULOS.values() if a in ar) > 1}
    sin_modulo = {a: n for a, (n, _, _) in sorted(pruebas.items())
                  if a not in asignados}
    suma_columna = sum(sum(pruebas.get(a, (0, 0, 0))[0] for a in ar)
                       for _, ar in MODULOS.values())
    total_real = sum(n for n, _, _ in pruebas.values())

    L += ["",
          f"La columna «Pruebas» suma **{suma_columna}** y las ejecutadas son",
          f"**{total_real}**. La diferencia tiene dos causas, ninguna de ellas un",
          "error de cuenta:",
          ""]
    for archivo, n in repetidos.items():
        duenos = [e for e, (_, ar) in MODULOS.items() if archivo in ar]
        L.append(f"- `{archivo}.py` ({n} pruebas) cuenta en dos módulos "
                 f"—{' y '.join(duenos)}— porque recorre el paso de uno al otro. "
                 f"Sumado dos veces, infla la columna en {n}.")
    if sin_modulo:
        L.append(f"- {sum(sin_modulo.values())} pruebas no pertenecen a ningún "
                 "módulo de dominio: verifican `app/core/` —seguridad, catálogo "
                 "DANE, archivos, días hábiles— y el mapeo de los modelos. "
                 "Son " + ", ".join(f"`{a}.py` ({n})" for a, n in sin_modulo.items())
                 + ".")
    L += ["",
          f"Cuadra así: {suma_columna} − {sum(repetidos.values())} + "
          f"{sum(sin_modulo.values())} = {total_real}.",
          "", "---", ""]

    for etiqueta in ORDEN:
        if etiqueta not in grupos:
            continue
        paquete, archivos = MODULOS.get(etiqueta, ("—", []))
        L += [f"## {etiqueta}", "", f"**Paquete:** `{paquete}`", ""]

        if archivos:
            L += ["**Pruebas que lo cubren:**", "",
                  "| Archivo | Pruebas | Fallos | Segundos |", "|---|---:|---:|---:|"]
            for a in archivos:
                n, f, s = pruebas.get(a, (0, 0, 0.0))
                L.append(f"| `tests/**/{a}.py` | {n} | {f} | {s:.1f} |")
            L.append("")

        for metodo, ruta, operacion in grupos[etiqueta]:
            corta = ruta.replace("/api/v1", "")
            L += [f"### `{metodo} {corta}`", ""]
            if operacion.get("summary"):
                L += [operacion["summary"] + ".", ""]

            entradas = entrada_de(operacion, esquemas)
            if entradas:
                L += ["**Entrada**", "", "| Dato | Tipo | |", "|---|---|---|"]
                for campo, tipo, obligatorio in entradas[:MAX_CAMPOS]:
                    L.append(f"| {campo} | {tipo} | {'**ob.**' if obligatorio else ''} |")
                if len(entradas) > MAX_CAMPOS:
                    L.append(f"| *… y {len(entradas) - MAX_CAMPOS} más* | | |")
                L.append("")
            else:
                L += ["**Entrada:** nada.", ""]

            codigo, nombre, campos = salida_de(operacion, esquemas)
            L.append(f"**Salida** · `{codigo}` · `{nombre}`")
            L.append("")
            if campos:
                L += ["| Campo | Tipo |", "|---|---|"]
                for campo, tipo, _ in campos[:MAX_CAMPOS]:
                    L.append(f"| {campo} | {tipo} |")
                if len(campos) > MAX_CAMPOS:
                    L.append(f"| *… y {len(campos) - MAX_CAMPOS} más* | |")
                L.append("")
    return "\n".join(L) + "\n"


def main():
    api = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    junit = sys.argv[2] if len(sys.argv) > 2 else "junit.xml"
    salida = sys.argv[3] if len(sys.argv) > 3 else "MODULOS.md"

    with open(api, encoding="utf-8") as f:
        documento = json.load(f)
    pruebas = pruebas_por_archivo(junit)

    with open(salida, "w", encoding="utf-8") as f:
        f.write(generar(documento, pruebas))

    print(f"{salida}: {sum(n for n, _, _ in pruebas.values())} pruebas en "
          f"{len(pruebas)} archivos")


if __name__ == "__main__":
    main()
