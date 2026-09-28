# 16 — Defectos encontrados y corregidos

Registro de lo que estaba roto al retomar el proyecto, en qué consistía y cómo se verificó la corrección. Cada entrada tiene su prueba de regresión.

**Fecha:** 28 de septiembre de 2026
**Punto de partida:** 238 pruebas, 84 % de cobertura, sin control de versiones
**Estado al cierre:** 390 pruebas, 87 % de cobertura

---

## 1. El patrón de fondo

Siete de los defectos que siguen son la misma cosa: **un endpoint construido, probado y funcionando, sin ninguna forma de alcanzarlo desde la interfaz.** El backend iba por delante del frontend, y la diferencia no se notaba porque las pruebas de integración llaman a la API directamente.

Es el tipo de defecto que ninguna suite de pruebas del backend puede encontrar, y que una auditoría por inspección tampoco: hay que intentar usar el producto.

---

## 2. Bloqueantes: los dos flujos centrales estaban cortados

### 2.1 Un comprador nuevo no podía comprar

**Síntoma.** El checkout, sin direcciones registradas, mostraba: *«Agrega una desde tu perfil»*. Pero `/mi-cuenta/perfil` y `/mi-cuenta/direcciones` respondían 404, y `POST /users/me/addresses` no tenía ningún llamador en el frontend.

Todo usuario registrado que no tuviera una dirección precargada en la base de datos quedaba en un callejón sin salida **en el paso final de la compra**.

**Corrección.**
- Pantalla `/mi-cuenta/direcciones` con alta, edición, baja y predeterminada, con departamento y municipio del catálogo DANE en cascada.
- Nuevo endpoint `PATCH /users/me/addresses/{id}`: solo existían alta y baja, así que no había forma de corregir un dato ni de cambiar la predeterminada.
- El checkout enlaza con `?volver=checkout` y devuelve al comprador al punto donde se quedó.
- Con cero direcciones, el formulario se abre solo: llegar a una pantalla vacía desde un checkout bloqueado y tener que buscar el botón sería alargar justo el camino que se viene a desatascar.

**Verificación en ejecución.** Un comprador registrado desde cero —con el correo de verificación leído de Mailpit— crea su dirección y completa el pedido `MG-2026-000024`.

**Pruebas.** 25 en `test_addresses.py`, que no existía: las direcciones no tenían ninguna.

### 2.2 Un productor no podía despachar

**Síntoma.** `/productor/pedidos` respondía 404. La función `updateOrderStatus` estaba escrita en `features/dashboard/api.ts` y **nunca se invocaba**. El panel mostraba «Pedidos recientes» en modo lectura y enlazaba a una página inexistente.

No había UI para confirmar → preparar → despachar ni para registrar la guía. El ciclo del pedido quedaba cortado justo después del pago.

**Corrección.** Pantalla `/productor/pedidos` con filtros por estado, avance según el grafo de transiciones, captura de transportadora y guía al despachar, y motivo obligatorio al cancelar.

**Verificación en ejecución.** El vendedor confirma, prepara, despacha con guía `SE-4412009` de Servientrega y marca como entregado el pedido anterior. El salto inválido `shipped → confirmed` se rechaza enumerando las transiciones permitidas.

**Pruebas.** 18 en `test_fulfillment.py`, que no existía.

---

## 3. Defectos de corrección encontrados al construir esas pantallas

### 3.1 Fuga de inventario en la cancelación del vendedor

**Gravedad: alta.** Cuando **el productor** cancelaba una sub-orden vía `PATCH /orders/sub-orders/{id}/status`, el inventario reservado **no se liberaba**. Las unidades quedaban retenidas para siempre: invendibles y sin pedido que las justificara.

Solo `cancel_sub_order` —la cancelación del comprador— llamaba a `_release_reserved_stock`. El camino del vendedor no.

Estaba latente porque **no existía UI que lo alcanzara**. Al construir la bandeja del productor, pasó a ser alcanzable.

**Corrección.** `update_sub_order_status` libera los kilos y registra el motivo al transicionar a `CANCELLED`, igual que la otra vía.

**Prueba de regresión.** `test_cancelling_returns_the_reserved_stock_to_the_catalogue`.

### 3.2 `shipping_city` mostraba el barrio

La bandeja del vendedor llenaba el destino con `snapshot.get("neighborhood")`. El barrio es opcional, así que el campo llegaba vacío en la mayoría de los pedidos, y cuando llegaba decía «Centro» en lugar del municipio.

Un vendedor necesita el municipio para cotizar el flete y elegir transportadora.

**Corrección.** Se resuelve el nombre del municipio desde el identificador de la copia inmutable de la dirección, en **una sola consulta para toda la página**.

**Verificación.** La bandeja pasa de `None, None, None` a `Pitalito, Neiva, Neiva`.

### 3.3 Un lote agotado aparecía como disponible en favoritos

`is_available` se calculaba con `product.is_purchasable`, que solo comprueba que el lote siga publicado y sin borrar: **ignoraba el inventario**. Un café agotado salía como disponible, que es exactamente lo que ese campo existe para evitar —y lo que su propio comentario prometía, citando HU-CC-04 CA3.

**Corrección.** Mismo criterio que el catálogo: alguna variante activa con existencias reales. El inventario entra en la misma carga para no consultar variante por variante.

**Prueba de regresión.** `test_a_sold_out_coffee_is_marked_not_available`.

### 3.4 El validador del mínimo de compra no se ejecutaba nunca

Era un `field_validator` sobre `min_qty_kg` que leía `stock_qty` de `info.data`. **Pydantic valida en el orden en que están declarados los campos**, y `stock_qty` va después: el diccionario nunca lo contenía, de modo que la comprobación no hacía nada.

Se descubrió al escribir la prueba: publicar una oferta con mínimo de 500 kg y 100 kg de existencias devolvía 201.

**Corrección.** `model_validator(mode="after")`, que corre sobre el modelo ya construido.

### 3.5 El enlace de la cola de moderación habría dado 404

La pantalla de reseñas denunciadas enlazaba al lote con `product_id`, pero la ruta pública del catálogo usa el **slug**. El schema `ReportedReview` no lo traía.

**Corrección.** `product_slug` añadido de punta a punta, con su prueba.

---

## 4. Funciones construidas e inalcanzables

| Función | Endpoints que existían | Qué faltaba |
|---|---|---|
| Favoritos | `GET`, `POST`, `DELETE /wishlist` | `/favoritos` daba 404; ningún llamador en el frontend. El enlace estaba en el panel de la cuenta desde el principio. |
| Datos personales | `GET /auth/me`, `POST /auth/change-password` | `/mi-cuenta/perfil` daba 404. Y no existía endpoint para editar nombre ni teléfono: se añadió `PATCH /users/me`. |
| Suspensión de cuentas | `POST /admin/users/{id}/suspend` | **No había listado ni búsqueda de usuarios.** Para suspender a alguien había que conocer su UUID de memoria. Se añadió `GET /admin/users` con búsqueda insensible a acentos y filtros por estado y rol. |
| Moderación de reseñas | `POST /admin/reviews/{id}/moderate`, `GET /admin/reviews/reported` | Ninguna pantalla. |
| Registro de auditoría | `GET /admin/audit-logs` | Ninguna pantalla. |

El panel de administración llamaba a **dos** de los seis endpoints que tenía disponibles.

---

## 5. Riesgos de ingeniería

### 5.1 No había control de versiones

261 archivos, cero historial. `.gitignore` y `.github/workflows/ci.yml` estaban escritos, pero **el repositorio nunca se inicializó y el CI nunca se había ejecutado**.

No se podía revisar qué hizo el desarrollo previo, ni volver atrás, ni ramificar.

**Corrección.** `git init` y commit de línea base antes de tocar una sola línea.

### 5.2 No existía `package-lock.json`

Las compilaciones no eran reproducibles: `^15.1.0` podía resolver distinto mañana. El CI declaraba `cache-dependency-path: web/package-lock.json` —que no encontraba nada— y usaba `npm ci || npm install`, que **ocultaba el fallo**.

**Corrección.** Lockfile generado a partir del árbol instalado y verificado con un `npm ci` limpio en un contenedor `node:22` (511 paquetes, éxito). El respaldo `|| npm install` retirado.

### 5.3 Ocho enlaces muertos en la navegación global

Doce rutas de contenido sin página, presentes en el pie y en la barra de navegación de **todas** las páginas del sitio. La auditoría de QA previa las calificó de «ninguna crítica»; dos de ellas están en la navegación principal.

**Corrección parcial.** Cuatro tenían una página equivalente y era un `href` equivocado, no una página por escribir: «Cambios y devoluciones» → `/legal/devoluciones`, «Cómo funciona» → `/vender#pasos`, «Comisiones» → `/vender#condiciones`, «Cafés por región» → `/catalogo`, que ya filtra por región.

Las ocho restantes siguen pendientes: son páginas de contenido cuyo texto depende del alcance del producto.

---

## 6. Desviaciones entre la documentación y la realidad

| El README decía | La realidad medida |
|---|---|
| 98 pruebas | 238 |
| 82 % de cobertura | 84 % |
| 48 tablas en un sitio, 51 en otro | 52 |

Se subestimaba a sí mismo. Las cifras del README se corrigieron y ahora se miden, no se estiman.

---

## 7. Lo que se deja anotado sin corregir

Con su motivo, para que la decisión sea explícita y no un olvido:

- **El frontend no tiene pruebas.** Vitest, Testing Library y jsdom están instalados; la carpeta `web/tests/` existe y está vacía. `npm test` falla por no encontrar archivos y el CI no lo ejecuta.
- **Los tokens viven en `sessionStorage`.** Migrarlos a cookies `httpOnly` exige además protección CSRF y middleware: es un cambio de arquitectura, no una corrección.
- **`RATE_LIMIT_DEFAULT_PER_MINUTE` está configurado y no se aplica en ningún sitio.** Solo los endpoints de autenticación tienen techo.
- **No hay proceso en segundo plano.** Nada vigila el vencimiento de certificaciones ni los plazos de devolución.
- **Las pruebas comparten una sola base de datos** (`monkgrain_test`, que el conftest borra y recrea por sesión). Dos ejecuciones simultáneas de `pytest` se estorban y producen cientos de errores que no son defectos del producto. El CI ejecuta una sola sesión, así que no le afecta.
- **`migrations/env.py` tiene un hallazgo de Ruff** (`SIM103`) que es anterior a este trabajo. El CI solo revisa `app` y `tests`, de modo que no lo detecta.
