# Comprobante del pedido en PDF

**Fase 19.** Documento funcional del comprobante descargable.

El checkout anunciaba un comprobante que no existía. La historia HU-CC-11 lo
pedía desde la fase 2 y `pyproject.toml` ya declaraba WeasyPrint, pero no había
ningún endpoint que generara nada.

---

## 1. No es una factura, y lo dice

La distinción no es un matiz. La **factura electrónica** la expide cada vendedor
ante la DIAN y es una obligación suya; la plataforma debe *poner a disposición
el servicio* que se lo permita (artículo 616-1 del Estatuto Tributario y
Resolución DIAN 000165 de 2023, riesgo R-6 del expediente legal), pero no la
emite.

Lo que sí corresponde a MONK GRAIN es la **constancia de la relación de
consumo**: el literal e) del artículo 50 de la Ley 1480 de 2011 obliga a poder
acreditarla, y remite al plazo de conservación de diez años del artículo 60 del
Código de Comercio.

El documento lleva la advertencia impresa en la cabecera. Sin ella, alguien
podría presentarlo como soporte tributario.

---

## 2. Qué lleva, y por qué

| Bloque | Origen |
|---|---|
| Número de pedido, fecha de compra y de emisión | HU-CC-11, CA1 |
| Comprador y dirección de entrega | HU-CC-11, CA1 |
| Estado y medio de pago, con la referencia | trazabilidad de la transacción |
| **Identificación de cada vendedor** | artículo 53 de la Ley 1480 |
| Ítems con nombre y presentación congelados | ADR-06 |
| Productos, envío y descuento por separado | artículo 26 de la Ley 1480 |
| Derechos de retracto y garantía, y la SIC | artículos 47, 8 y 11 |

### Los datos del vendedor

El comprobante incluye razón social, documento, dirección de notificaciones y
teléfono de cada vendedor. Esos campos **no salen en ningún endpoint público**
—se verificó en la fase 17 que no se filtran—, y aquí sí aparecen a propósito:
el comprobante solo lo recibe quien contrató con ese vendedor, y **un
comprobante que no diga contra quién se reclama no sirve de constancia**.

### Las cifras son las que se cobraron

El nombre del café y su presentación salen de `product_name_snapshot` y
`variant_label_snapshot`, congelados al confirmar la compra. Si el vendedor
renombra el café o cambia el precio mañana, el comprobante de hoy sigue diciendo
lo que se compró.

### El pago simulado se declara

Mientras el proveedor sea simulado, el documento lo dice. Un comprobante que lo
callara sugeriría un cobro que no ocurrió.

---

## 3. Endpoint

```
GET /orders/{order_id}/receipt        →  application/pdf
```

Lo descarga su comprador o un administrador; a cualquier otro se le responde
**403** (HU-CC-11, CA2), incluido el vendedor que despachó el pedido: el
comprobante es del comprador.

Dos cabeceras merecen mención:

- `Content-Disposition: attachment` fuerza la descarga en lugar de abrir el PDF
  dentro del dominio de la API.
- `Cache-Control: private, no-store`, porque el documento contiene la dirección
  del comprador y los datos de contacto de los vendedores.

El PDF **se genera al vuelo y no se guarda**. Los datos de los que sale ya viven
en la base de datos; almacenar una copia solo añadiría un archivo que puede
quedar desincronizado con el pedido.

---

## 4. Cómo está hecho

**WeasyPrint 69** convierte HTML+CSS en PDF. La maquetación vive en
`app/templates/receipt.html`, fuera del módulo Python: es presentación, y
mezclarla con la lógica obliga a tocar código para mover un margen.

**Jinja2 con autoescapado.** El nombre de un café, una nota de entrega o la
historia de una finca son texto que escribió un usuario. Sin escapar podrían
alterar la estructura del documento; hay una prueba que lo comprueba inyectando
una etiqueta `<style>` en las notas del pedido.

**Tipografía DejaVu**, presente en la imagen base. No se carga ninguna fuente ni
imagen externa: el contenedor no tiene por qué alcanzar la red para imprimir un
comprobante.

**Los importes se formatean a mano** —`$ 150.000`, sin decimales— porque
`locale` depende de que el sistema tenga instalada la configuración regional, y
un contenedor mínimo no la tiene.

**El municipio y el departamento se resuelven al imprimir.** La instantánea de
la dirección guarda identificadores; si alguno desapareciera del catálogo
geográfico, el resto de la dirección sigue siendo legible.

**Cada bloque de vendedor lleva `page-break-inside: avoid`**, de modo que en un
pedido con varias fincas ninguna queda partida entre dos páginas. Verificado con
un pedido de tres vendedores que ocupa dos páginas.

---

## 5. Interfaz

El botón **«Comprobante en PDF»** está en la cabecera del detalle del pedido,
en `/mi-cuenta/pedidos/[id]`.

No se abre la URL en una pestaña nueva: el endpoint exige la cabecera de
autorización y una navegación del navegador no la lleva. Se pide con `fetch`, se
convierte en un `blob` y la descarga se dispara desde un enlace temporal que se
libera tras el clic.

---

## 6. Verificación

**Suite:** 238 pruebas en verde (227 previas + 11 nuevas).

Las pruebas leen el **texto real del PDF generado** con `pypdf`, en vez de dar
por bueno que el archivo empieza por `%PDF`. Validadas reintroduciendo los
defectos:

| Defecto reintroducido | Pruebas que fallaron |
|---|---|
| Quitar el autoescapado de la plantilla | 1 |
| Permitir descargar el comprobante ajeno | 1 |
| Omitir los datos del artículo 53 | 1 |

**Contra el entorno en ejecución:**

```
Sin sesión                    → 401
El vendedor del propio pedido → 403
Pedido inexistente            → 404
Su comprador                  → 200 · application/pdf · 17 KB
                                attachment; filename="MONK-GRAIN-MG-2026-000022.pdf"
                                Cache-Control: private, no-store
Pedido de tres vendedores     → 2 páginas, ningún bloque partido,
                                totales 112.000 + 36.000 = 148.000
Botón en la interfaz          → petición con autorización, 200, sin errores de consola
```

Ruff, Ruff format, Mypy, TypeScript, ESLint y Prettier sin hallazgos.

---

## 7. Un defecto corregido de paso

El icono de cuenta de la barra de navegación apuntaba **siempre** a
`/ingresar`, con sesión o sin ella. Un comprador autenticado que lo pulsaba
volvía a la pantalla de acceso, de modo que el panel del comprador —y con él las
devoluciones, las reseñas y este comprobante— quedaba fuera de la navegación
principal.

Corregido resolviendo la sesión tras el montaje: decidir el destino durante el
renderizado del servidor produciría una discrepancia de hidratación, porque
`sessionStorage` no existe allí. Hasta que resuelve, el icono apunta a iniciar
sesión, que es el destino correcto para quien no la tiene.

---

## 8. Lo que sigue pendiente

**El resumen del pedido antes de confirmar.** El literal a) del artículo 50
exige poner a disposición un resumen **descargable e imprimible antes de
concluir la transacción**. Este comprobante es posterior a la compra: cubre la
constancia, no ese deber previo. Está anotado como riesgo R-8 en el expediente
legal.

**El acuse de recibo del día siguiente.** El literal b) del mismo artículo obliga
a enviar un acuse de recibo del pedido a más tardar el día calendario siguiente.
Hoy existe la notificación en la aplicación, no el envío.

**La factura electrónica.** Riesgo R-6: hay que confirmar con el contador y el
equipo si el servicio que permite al vendedor expedirla existe o hay que
construirlo.
