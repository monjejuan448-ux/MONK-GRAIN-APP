# MONK GRAIN — Documentación de la API

Referencia de la API REST: **87 operaciones sobre 74 rutas**, más el webhook de pagos, que no se publica en el esquema. La documentación interactiva, generada automáticamente desde el código, está en `http://localhost:8000/docs` y permite probar cada endpoint desde el navegador.

---

## Convenciones generales

**Base:** `/api/v1`

**Formato:** JSON en peticiones y respuestas. Codificación UTF-8.

**Importes:** viajan como **cadena**, no como número. En JSON el tipo `number` es de punto flotante y perdería la precisión que `NUMERIC(14,2)` protege en la base de datos. Conviértelos a decimal en el cliente, nunca a `float`.

```json
{ "grand_total": "214000.00", "currency": "COP" }
```

**Fechas:** ISO 8601 con zona horaria (`2026-08-13T01:22:36.451Z`).

**Identificadores:** UUID para entidades de negocio; enteros para catálogos geográficos.

### Autenticación

Los endpoints protegidos esperan el access token en la cabecera:

```
Authorization: Bearer <access_token>
```

El access token dura 15 minutos. Cuando expira, se renueva con `POST /auth/refresh`, que **rota** el refresh token: el anterior queda revocado en el acto.

### Formato de error

Todos los errores comparten la misma estructura:

```json
{
  "error": {
    "code": "business_rule_violation",
    "message": "Solo quedan 3 unidades disponibles de esta presentación.",
    "details": { "available_qty": 3 }
  }
}
```

| Código HTTP | `code` | Cuándo ocurre |
|---|---|---|
| 400 | `domain_error` | Error de negocio genérico |
| 401 | `unauthorized` | Sin autenticación o credenciales inválidas |
| 403 | `forbidden` | Autenticado pero sin permiso sobre el recurso |
| 404 | `not_found` | El recurso no existe o no es visible para quien consulta |
| 409 | `conflict` | Choca con el estado actual del recurso |
| 422 | `validation_error` | Datos mal formados; incluye `details.fields` |
| 422 | `business_rule_violation` | Regla de negocio incumplida |
| 422 | `insufficient_stock` | Inventario insuficiente |
| 422 | `invalid_state_transition` | Cambio de estado no permitido |
| 429 | `rate_limit_exceeded` | Demasiadas peticiones |
| 500 | `internal_error` | Error inesperado |

Los errores de validación detallan el campo afectado:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Algunos datos enviados no son válidos.",
    "details": {
      "fields": [
        { "field": "data_consent", "message": "Debes autorizar el tratamiento de tus datos personales para crear una cuenta." }
      ]
    }
  }
}
```

### Paginación

Los listados aceptan `page` (desde 1) y `page_size` (máximo 100) y responden con:

```json
{
  "items": [],
  "total": 9,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "has_next": false,
  "has_previous": false
}
```

### Límite de peticiones

| Endpoint | Límite |
|---|---|
| `POST /auth/login` | 5 por minuto |
| `POST /auth/register` | 5 cada 5 minutos |
| `POST /auth/password-reset` | 3 cada 10 minutos |
| `POST /auth/resend-verification` | 3 cada 10 minutos |
| Resto | 120 por minuto |

Superarlo devuelve `429`. El contador vive en Redis, compartido entre instancias.

### Cabeceras de respuesta

Toda respuesta incluye `X-Request-ID`. Guárdalo al reportar un problema: permite localizar la petición exacta en los registros del servidor.

---

## Autenticación — 10 endpoints

### `POST /auth/register`
Crea una cuenta de comprador y envía el correo de verificación.

```json
{
  "email": "maria@ejemplo.co",
  "password": "ClaveSegura2026",
  "full_name": "María López",
  "phone": "3001234567",
  "data_consent": true
}
```

- `password`: mínimo 12 caracteres, con al menos una letra y un número.
- `data_consent`: **obligatorio y explícito**. La Ley 1581 de 2012 no admite consentimiento tácito.

**202** — Mensaje neutro. Es **idéntico** exista o no el correo: de lo contrario el endpoint serviría para averiguar qué cuentas están registradas.

### `POST /auth/verify-email`
Activa la cuenta con el token del correo. El token es de un solo uso y vence en 24 horas.

```json
{ "token": "hsL3Sn4mSkzbbExnExYF..." }
```

**200** cuenta activada · **401** token inválido o vencido

### `POST /auth/resend-verification`
Reenvía el enlace. No revela si la cuenta existe ni si ya estaba verificada. **202**

### `POST /auth/login`

```json
{ "email": "maria@ejemplo.co", "password": "ClaveSegura2026" }
```

**200**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_at": "2026-08-13T02:15:00Z"
}
```

**401** — Contraseña incorrecta y correo inexistente devuelven el **mismo mensaje**: `"Correo o contraseña incorrectos."` Tampoco difieren en tiempo de respuesta.

### `POST /auth/refresh`
Renueva la sesión. El refresh token usado **se revoca** al emitir el nuevo: si uno filtrado se reutiliza después, ya no sirve.

```json
{ "refresh_token": "eyJhbGciOi..." }
```

### `POST /auth/logout`
Revoca el refresh token de la sesión actual. **200**

### `POST /auth/password-reset`
Envía el enlace de restablecimiento. Respuesta idéntica exista o no la cuenta. **202**

### `POST /auth/password-reset/confirm`
Fija la nueva contraseña y **cierra todas las sesiones activas**: si alguien tenía acceso indebido, el cambio lo expulsa.

```json
{ "token": "MJVczAi9GbfEq50b...", "password": "NuevaClave2026" }
```

### `POST /auth/change-password` 🔒
Requiere la contraseña actual. También cierra todas las sesiones.

### `GET /auth/me` 🔒
Perfil del usuario autenticado con sus roles y permisos efectivos. **Nunca** incluye el hash de la contraseña ni datos bancarios.

```json
{
  "id": "3944...", "email": "maria@ejemplo.co", "full_name": "María López",
  "status": "active",
  "roles": [{ "code": "consumer", "name": "Comprador" }],
  "permissions": ["order.create", "order.view_own", "review.create"]
}
```

---

## Catálogo — 5 endpoints (públicos)

### `GET /products`
Listado con filtros combinables.

| Parámetro | Descripción |
|---|---|
| `q` | Búsqueda por nombre, descripción o marca. Ignora tildes: `narino` encuentra *Nariño* |
| `department` / `municipality` | Código DANE |
| `region` | `huila`, `narino`, `cauca`, `tolima`, `eje_cafetero`, `antioquia`, `santander`, `sierra_nevada` |
| `variety` | Variedad botánica (Caturra, Castillo, Geisha…) |
| `process` | `washed`, `natural`, `honey`, `anaerobic`, `other` |
| `roast` | `light`, `medium`, `medium_dark`, `dark` |
| `state` | `green`, `roasted`, `ground` |
| `certification` | `organic`, `fairtrade`, `rainforest`, `denominacion_origen`… |
| `min_price` / `max_price` | Rango en COP |
| `min_score` | Puntaje de catación mínimo (0–100) |
| `sort` | `newest`, `price_asc`, `price_desc`, `score`, `rating`, `popular` |

Los filtros se combinan entre sí y el orden se aplica sobre el conjunto ya filtrado.

> `rating` ordena por calificación de las reseñas; `score`, por puntaje de catación. Son cosas distintas.

Solo aparecen productos publicados de vendedores aprobados: suspender a un vendedor retira su catálogo sin borrar nada.

### `GET /products/{slug}`
Ficha completa con la trazabilidad: variedad, proceso, tueste, altitud, perfil sensorial, puntaje, fechas de cosecha y tueste, finca, certificaciones y presentaciones con stock.

**Dos restricciones que se aplican en el servidor:**

- La finca expone `approx_lat`/`approx_lng` a nivel de municipio. La coordenada exacta existe en la base de datos pero **no se serializa nunca**: publicarla sería un riesgo de seguridad física para el productor.
- `wholesale_price` llega como `null` salvo para compradores empresariales verificados. No se trata de ocultarlo en la interfaz: **el dato no sale del servidor**, de modo que llamar a la API directamente tampoco lo revela.

### `GET /products/{slug}/related`
Hasta 4 cafés afines, del mismo productor o categoría.

### `GET /producers`
Listado de productores aprobados. Filtros: `department`, `region`, `type` (`farmer`, `farm`, `cooperative`, `roaster`).

### `GET /producers/{producer_id}`
Perfil público con historia, fincas, certificaciones y productos publicados.

---

## Carrito y favoritos — 9 endpoints 🔒

### `GET /cart`
Carrito **agrupado por vendedor**, porque el pedido se dividirá así.

```json
{
  "groups": [
    {
      "producer_name": "Café El Mirador",
      "items": [{ "product_name": "Microlote Geisha Lavado", "quantity": 2, "line_total": "156000.00", "price_changed": false, "is_available": true }],
      "subtotal": "156000.00",
      "estimated_shipping": "0.00"
    }
  ],
  "item_count": 2,
  "subtotal": "156000.00",
  "shipping_total": "0.00",
  "grand_total": "156000.00",
  "has_warnings": false
}
```

Cada ítem indica si su precio cambió (`price_changed`, con `previous_price`) o si dejó de haber stock. `has_warnings` avisa de que algo requiere atención antes del checkout.

El envío se calcula **por vendedor**: cada productor despacha por separado, y el umbral de envío gratis se evalúa sobre su propio subtotal.

Parámetro opcional `coupon` para previsualizar el descuento sin aplicarlo definitivamente.

### `POST /cart/items`
```json
{ "variant_id": "uuid", "quantity": 2 }
```
Agregar de nuevo la misma variante **suma** a la línea existente. **201** · **422** si supera el stock, indicando cuántas quedan.

### `PATCH /cart/items/{item_id}` · `DELETE /cart/items/{item_id}` · `DELETE /cart`

### `POST /cart/merge`
Incorpora el carrito que se armó antes de iniciar sesión. Suma cantidades sin duplicar líneas y las recorta al stock disponible en vez de fallar: perder el carrito al autenticarse es peor experiencia que ajustar una cantidad.

```json
[{ "variant_id": "uuid", "quantity": 2 }]
```

### `GET /wishlist` · `POST /wishlist` · `DELETE /wishlist/{product_id}`
Un favorito que dejó de estar disponible se marca con `is_available: false` en lugar de desaparecer sin explicación.

---

## Pedidos — 5 endpoints

### `POST /orders` 🔒
Convierte el carrito en un pedido. **Es la operación más delicada del sistema.**

```json
{
  "shipping_address_id": "uuid",
  "accept_terms": true,
  "coupon_code": "BIENVENIDO10",
  "customer_notes": "Dejar en portería"
}
```

Todo ocurre en **una sola transacción**: valida la dirección y el carrito, revalida precios y disponibilidad contra la base de datos, reserva inventario con bloqueo pesimista, crea el pedido y una sub-orden por vendedor, calcula la comisión con la tasa vigente y vacía el carrito. Ante cualquier error no queda pedido a medias ni stock reservado sin dueño.

**201**
```json
{
  "order": {
    "order_number": "MG-2026-000001",
    "status": "pending",
    "grand_total": "214000.00",
    "sub_orders": [
      { "sub_order_number": "MG-2026-000001-1", "producer_name": "Café El Mirador", "status": "pending", "subtotal": "156000.00", "shipping_cost": "0.00" },
      { "sub_order_number": "MG-2026-000001-2", "producer_name": "Café de Altura Nariño", "status": "pending", "subtotal": "46000.00", "shipping_cost": "12000.00" }
    ]
  },
  "payment_reference": "SIM-MG-2026-000001-0288E414",
  "message": "Tu pedido fue creado. El pago está en proceso con un proveedor simulado: no se realizó ningún cobro real."
}
```

**Importante:** el inventario queda **reservado, no descontado**. Se descuenta al confirmarse el pago; si el pago se rechaza, vuelve al catálogo.

**Errores:** `422` sin aceptar términos, carrito vacío o stock insuficiente · `404` dirección inexistente o de otra persona.

### `GET /orders` 🔒 · `GET /orders/{order_id}` 🔒
Historial y detalle. Un pedido solo lo consulta su comprador o un administrador; cualquier otro recibe **403**.

El detalle incluye `shipping_address` como copia inmutable: si el comprador edita o borra la dirección después, el pedido conserva a dónde se envió realmente.

### `POST /orders/sub-orders/{sub_order_id}/cancel` 🔒
Cancela una sub-orden aún no despachada, liberando su inventario reservado.

```json
{ "reason": "Me equivoqué de presentación" }
```

**422** si ya fue despachada; en ese caso corresponde una devolución.

### `PATCH /orders/sub-orders/{sub_order_id}/status` 🔒 *(productor)*
Avanza el estado. Solo el vendedor dueño puede hacerlo.

```json
{ "status": "shipped", "carrier": "servientrega", "tracking_number": "SE123456789CO" }
```

**Transiciones permitidas:**

```
pending → confirmed | cancelled
confirmed → prepared | cancelled
prepared → shipped | cancelled
shipped → delivered | refunded
delivered → refunded
cancelled, refunded → (final)
```

Cualquier otra devuelve `422` con `invalid_state_transition`, indicando cuáles sí son válidas:

```json
{ "error": { "code": "invalid_state_transition", "message": "No se puede pasar de 'confirmed' a 'delivered'.",
  "details": { "current": "confirmed", "allowed": ["cancelled", "prepared"] } } }
```

El estado del **pedido** se deriva de sus sub-órdenes: `partially_shipped` cuando unas están enviadas y otras no, `completed` cuando todas terminaron, `refunded` cuando ninguna sigue viva y al menos una se devolvió. Un pedido reembolsado no es un pedido cancelado: se entregó y después se devolvió.

---

## Devoluciones — 10 endpoints 🔒

El detalle funcional —qué figura aplica, qué plazos corren y por qué— está en [docs/11](11-devoluciones.md). Aquí solo el contrato.

### `GET /orders/sub-orders/{sub_order_id}/return-eligibility`

Qué puede devolverse hoy de este envío y bajo qué figura. La interfaz lo consulta antes de pintar el formulario.

```json
{ "sub_order_id": "…", "sub_order_number": "MG-2026-000018-1", "can_request": true,
  "allowed_reasons": ["withdrawal", "damaged", "wrong_item", "quality", "other"],
  "withdrawal_deadline": "2026-08-24", "warranty_deadline": "2027-08-16",
  "delivered_at": "2026-08-16T03:20:20Z",
  "items": [{ "order_item_id": "…", "product_name": "La Esperanza Sombrío Nativo",
              "variant_label": "500 g · grano entero", "purchased_qty": 2,
              "returnable_qty": 2, "unit_price": "75000.00" }],
  "blocked_reason": null }
```

`allowed_reasons` refleja los plazos vivos: el retracto desaparece pasados los cinco días hábiles desde la entrega, la garantía sigue mucho después. Cuando `can_request` es `false`, `blocked_reason` lo explica en lenguaje llano.

### `POST /returns`

```json
{ "sub_order_id": "…", "reason": "damaged",
  "description": "El empaque llegó roto y el café estaba húmedo.",
  "declared_unopened": false,
  "items": [{ "order_item_id": "…", "quantity": 2 }] }
```

Devuelve **201** con la constancia: número de radicación (`DEV-2026-000001`), fecha y hora, importe del reembolso, quién asume el transporte de vuelta y los dos vencimientos.

**422** si el motivo ya no admite reclamación, si se piden más unidades de las compradas —descontando las que ya están en otra solicitud viva—, si se invoca el retracto sin declarar el empaque sellado, o si se reclama por garantía sin describir qué pasó.

El importe **no se envía**: lo calcula el servidor. El artículo 47 de la Ley 1480 prohíbe descuentos y retenciones, así que no existe campo por donde rebajarlo.

### `GET /returns` · `GET /returns/{id}`

Listado del comprador y constancia completa. La constancia la ven su autor, quien vende y un administrador; cualquier otro recibe **403**.

`available_actions` enumera las transiciones que **ese** usuario puede ejecutar ahora. Se calcula en el servidor: la interfaz lo pinta, pero ocultar un botón no es control de acceso.

### `POST /returns/{id}/evidence`

Multiparte, campo `files` repetible. Hasta 8 imágenes de 5 MB. Se validan por contenido y se reescriben como JPEG.

Las fotografías se guardan bajo `returns/`, **fuera de los prefijos públicos**, y se entregan con enlaces firmados que caducan en 300 segundos. **403** al pedir el objeto sin firma.

### `POST /returns/{id}/shipped`

El comprador declara que entregó el paquete al transportador. Solo él —o un administrador— puede hacerlo: es el único que lo sabe. **403** si lo intenta el vendedor.

### `GET /producer/returns` 🔒 *(rol `producer`)*

Reclamaciones sobre las ventas propias, **ordenadas por vencimiento**: el orden de la lista es el orden en que hay que responder.

### `POST /producer/returns/{id}/resolution` 🔒

```json
{ "approve": true, "resolution_notes": "Revisamos las fotografías: el empaque llegó roto." }
```

Respuesta escrita exigida por el Decreto 735 de 2013. `resolution_notes` es obligatorio también al aprobar y tiene un mínimo de 10 caracteres: es el documento que el comprador acompaña a su reclamación ante la Superintendencia.

### `POST /producer/returns/{id}/received` 🔒 · `POST /producer/returns/{id}/refund` 🔒

Confirmar la recepción y cerrar con el reembolso. Ninguno recibe cuerpo.

El reembolso repone inventario **solo en el retracto** —una bolsa sellada puede volver al catálogo, una dañada no—, rebaja la base de comisión en lo devuelto, y cierra la sub-orden, el pedido y el pago cuando ya no queda nada por devolver.

Las transiciones válidas son:

```
requested  → approved | rejected
approved   → in_transit | received | refunded
in_transit → received | refunded
received   → refunded
rejected, refunded → (terminales)
```

Cualquier otra devuelve **422** con `invalid_state_transition`.

---

## Usuarios y geografía — 5 endpoints

### `GET /users/me/addresses` 🔒 · `POST /users/me/addresses` 🔒

```json
{
  "recipient_name": "María López",
  "phone": "3001234567",
  "municipality_id": 12,
  "street_address": "Calle 45 # 12-30",
  "neighborhood": "La Castellana",
  "is_default": true
}
```

El departamento **se deriva del municipio**, no se recibe aparte: así no puede llegar una combinación imposible como Pitalito en Antioquia.

### `DELETE /users/me/addresses/{address_id}` 🔒
Baja lógica: los pedidos que la usaron conservan su copia.

### `GET /users/geo/departments` · `GET /users/geo/departments/{id}/municipalities`
Catálogo oficial con códigos DANE, para poblar los selectores de dirección.

---

## Panel del productor — 6 endpoints 🔒 *(rol `producer`)*

### `GET /producer/dashboard`
Ventas, ganancia neta, pedidos por atender, productos activos, calificación, más vendidos y serie mensual.

> Las ventas cuentan **solo pedidos con pago confirmado**. Sumar los pendientes daría al productor una lectura falsa de su negocio.

### `GET /producer/orders`
Pedidos recibidos, filtrables por `status`. Incluye el neto a recibir tras la comisión.

### `GET /producer/products`
Catálogo propio con stock total, número de presentaciones y aviso de bajo inventario.

### `GET /producer/inventory/alerts`
Presentaciones cuyo stock disponible cayó bajo el umbral definido.

### `PATCH /producer/inventory/{variant_id}`
```json
{ "stock_qty": 50, "low_stock_threshold": 10 }
```
**403** si se intenta dejar el stock por debajo de las unidades ya reservadas por pedidos en curso: esas unidades están comprometidas con compradores concretos.

### `GET /producer/settlements/summary`
Ventas brutas, comisión y neto pendiente de liquidar.

---

## Administración — 6 endpoints 🔒 *(rol `admin`)*

### `GET /admin/dashboard?days=30`
Usuarios, vendedores pendientes y aprobados, catálogo, pedidos por estado, facturación y comisiones del periodo. Los ingresos cuentan solo ventas consumadas.

### `GET /admin/producers/pending`
Solicitudes de vendedor por revisar, con datos de contacto y ubicación.

### `POST /admin/producers/{producer_id}/review`
```json
{ "approve": false, "reason": "Falta adjuntar el certificado de cámara de comercio vigente." }
```

El motivo es **obligatorio al rechazar**: una negativa sin explicación deja al productor sin saber qué corregir. Aprobar concede el rol `producer`. La decisión queda en auditoría y se notifica al interesado.

**422** si se omite el motivo o si la solicitud ya fue revisada.

### `POST /admin/users/{user_id}/suspend`
```json
{ "suspend": true, "reason": "Incumplimiento reiterado de las políticas" }
```
Suspender a un vendedor retira su catálogo de la vista pública sin borrar nada. No es posible suspenderse a uno mismo.

### `POST /admin/reviews/{review_id}/moderate`
Oculta o restablece una reseña y **recalcula el promedio** del producto y del productor excluyéndola.

### `GET /admin/audit-logs`
Registro de acciones sensibles con actor, acción, entidad, estado antes y después, IP y fecha. Filtrable por `action` y `actor_id`.

**Es de solo lectura.** No existe endpoint para modificarlo ni borrarlo, y el rol de aplicación en PostgreSQL solo tiene permisos de inserción y consulta sobre esa tabla: la inmutabilidad no depende de que nadie escriba un `DELETE`.

---

## Pagos

### `POST /payments/webhook`
Recibe la confirmación del proveedor. No aparece en la documentación pública.

La firma se valida **antes** de actuar: sin esa comprobación, cualquiera podría notificar un pago aprobado que nunca ocurrió.

Un evento con firma inválida se registra y se descarta, pero la respuesta es **200**, igual que la de un evento válido. Es deliberado: informar del rechazo permitiría a un atacante iterar hasta dar con una firma correcta.

El procesamiento es **idempotente**: un índice único sobre `(provider, provider_reference)` impide aplicar dos veces la misma confirmación.

Al aprobarse, la reserva de inventario se convierte en descuento efectivo y las sub-órdenes pasan a `confirmed`. Al rechazarse, el stock vuelve al catálogo.

---

## Sistema

### `GET /health`
```json
{ "status": "ok", "environment": "development" }
```

Sin autenticación. Pensado para el chequeo de salud del orquestador.

---

## Comprobante del pedido

### `GET /orders/{order_id}/receipt` 🔒 → `application/pdf`

Constancia de la compra (HU-CC-11). Detalle en [docs/13](13-comprobante.md).

Lo descarga su comprador o un administrador; a cualquier otro —incluido el vendedor que despachó el pedido— se le responde **403**. El comprobante es del comprador.

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="MONK-GRAIN-MG-2026-000022.pdf"
Cache-Control: private, no-store
```

`attachment` fuerza la descarga en vez de abrir el PDF dentro del dominio de la API; `no-store` porque el documento lleva la dirección del comprador y los datos de contacto de los vendedores.

**No es una factura**, y el propio documento lo dice: la factura electrónica la expide cada vendedor ante la DIAN. Incluye la identificación de cada vendedor exigida por el artículo 53 de la Ley 1480 —razón social, documento, dirección de notificaciones y teléfono—, que no se publica en ningún endpoint abierto.

---

## Reseñas — 8 endpoints

El detalle funcional está en [docs/12](12-resenas.md).

### `GET /products/{product_id}/reviews`

Público, con sesión opcional. Si quien consulta la tiene, sus propias reseñas vienen marcadas con `is_mine` y `can_edit`.

```json
{ "items": [{ "id": "…", "rating": 5, "comment": "Dulce y con cuerpo.",
              "author_name": "Lucía R.", "is_verified_purchase": true,
              "can_edit": false, "is_mine": false, "created_at": "…" }],
  "total": 1 }
```

El nombre va abreviado —nombre de pila e inicial del apellido—: la ficha es pública y la indexan los buscadores.

### `GET /products/{product_id}/reviews/summary`

```json
{ "rating_avg": 4.5, "rating_count": 12,
  "distribution": { "1": 0, "2": 1, "3": 1, "4": 3, "5": 7 } }
```

### `POST /reviews` 🔒

```json
{ "order_item_id": "…", "rating": 5, "comment": "Tal cual lo describe la ficha." }
```

**422** si el pedido aún no figura como entregado o si la calificación no está entre 1 y 5. **409** si esa compra ya tiene reseña. **404** si la línea no pertenece a quien la envía: se responde 404 y no 403 a propósito, porque distinguirlos permitiría averiguar qué identificadores existen de verdad.

La reseña solo puede recaer sobre lo comprado y recibido. Quien lo garantiza no es esta validación sino la restricción única sobre `order_item_id`.

### `GET /reviews/pending` 🔒

Cafés entregados que este comprador todavía no ha reseñado (RF-06.4).

### `PUT /reviews/{id}` 🔒 · `DELETE /reviews/{id}` 🔒

Editar se admite **treinta días** desde la publicación; después, **422**. Eliminar, siempre. **403** sobre una reseña ajena.

### `POST /reviews/{id}/report` 🔒

```json
{ "reason": "Publica el teléfono del productor en el texto." }
```

Envía la reseña a la cola de moderación **sin ocultarla y sin retirarla del promedio**. Si denunciar bastara para que dejara de verse o de contar, el botón sería un modo indirecto de silenciar cualquier opinión incómoda.

**422** al reportar la propia. **409** al reportar dos veces la misma.

### `GET /admin/reviews/reported` 🔒 *(rol `admin`)*

Cola de moderación con el recuento y los motivos de cada denuncia (HU-ADM-06, CA1). Se modera con `POST /admin/reviews/{id}/moderate`, que sí retira la reseña de la ficha y del promedio.

---

## Estado de este documento

La API expone hoy **87 operaciones**. Este documento cubre autenticación, catálogo, carrito, pedidos, devoluciones, usuarios, panel del productor, administración y pagos, pero **no** los endpoints de publicación de cafés y certificaciones añadidos en las fases 14 y 15 (`/producer/catalog/*`, `/producer/certifications/*`, `/producer/profile`). Su comportamiento está descrito en el código y en `/docs`; falta trasladarlo aquí.

---

## Nota sobre la documentación interactiva

`/docs` y `/openapi.json` están **deshabilitados en producción**: publicar el mapa completo de la API facilita el trabajo a quien busque vulnerabilidades. En desarrollo son la referencia más fiable, porque se generan del código y no pueden quedar desactualizados.
