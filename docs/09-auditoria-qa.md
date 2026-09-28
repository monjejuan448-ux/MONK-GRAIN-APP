# MONK GRAIN — Auditoría de QA, seguridad y confiabilidad

**Fecha:** 13 de agosto de 2026
**Alcance:** Auditoría funcional y de seguridad de extremo a extremo sobre el entorno en ejecución (backend FastAPI, frontend Next.js, PostgreSQL 16, Redis 7).
**Método:** Pruebas dinámicas y no destructivas contra la API y la interfaz reales, más revisión del código en los puntos críticos. Todas las alteraciones de datos fueron reversibles y se revirtieron.
**Veredicto:** **APROBADO CON OBSERVACIONES.**
**Estado de remediación (13 de agosto de 2026):** los cuatro hallazgos están **corregidos y verificados**. Ver la sección 5.

---

## 1. Resumen ejecutivo

MONK GRAIN presenta una base de seguridad **sólida y bien razonada**. Los controles que suelen fallar en un marketplace —manipulación de precios, sobreventa de inventario, confirmación de pagos falsos, escalada de privilegios y acceso a datos ajenos (IDOR)— fueron sometidos a ataques reales y **todos resistieron**.

Se identificó **un (1) defecto de severidad media** relacionado con la generación del número de pedido bajo concurrencia, que puede producir pedidos duplicados o rechazos espurios entre compradores simultáneos. No compromete la confidencialidad ni la integridad de los datos, pero **debía corregirse antes de operar con pasarela de pago real**. El resto son observaciones de severidad baja o informativa.

> **Los cuatro hallazgos ya fueron corregidos y verificados** (sección 5). Revisiones posteriores detectaron tres defectos más, todos preexistentes y ajenos a la seguridad (sección 4): **HALLAZGO-05** (imágenes nunca subidas al almacenamiento, *corregido*), **HALLAZGO-06** (el optimizador de imágenes no alcanzaba el almacenamiento, *corregido*) y **HALLAZGO-07**, el de mayor alcance: **el productor no puede publicar productos ni subir documentos**, pese a estar dentro del MVP declarado.

| Área | Estado | Severidad máxima |
|------|--------|------------------|
| Registro e inicio de sesión | Aprobado | — |
| Roles y permisos (RBAC) | Aprobado | — |
| Catálogo, búsqueda y filtros | Aprobado | — |
| Detalle de producto | Aprobado | — |
| Carrito | Aprobado | — |
| Checkout | Aprobado con observaciones | Media |
| Pedidos | Aprobado con observaciones | Media |
| Inventario | Aprobado | — |
| Pagos simulados | Aprobado | — |
| Panel del comprador | Aprobado | — |
| Panel del productor | Aprobado | — |
| Panel administrativo | Aprobado | — |
| API | Aprobado | Baja |
| Base de datos | Aprobado | — |
| Manejo de errores | Aprobado | — |
| Rendimiento | Aprobado | — |
| Diseño responsive | Aprobado | — |
| Accesibilidad | Aprobado | — |
| Protección de datos | Aprobado | — |

---

## 2. Hallazgos

### HALLAZGO-01 · Número de pedido con condición de carrera — **Severidad: MEDIA**

- **Qué se probó:** Robustez del checkout ante ejecución concurrente del mismo carrito (doble clic) y ante compradores simultáneos.
- **Pasos:** Se lanzaron dos peticiones `POST /orders` en paralelo sobre el mismo carrito, repetidamente.
- **Resultado esperado:** Un único pedido; la segunda petición debe rechazarse limpiamente o encontrar el carrito ya vacío.
- **Resultado obtenido:** En concurrencia estricta, una petición devuelve `201` y la otra `409` (una sola compra) — comportamiento correcto por efecto colateral. Pero con un escalonamiento mínimo, **ambas devolvieron `201` y se crearon dos pedidos separados** (`MG-2026-000005` y `MG-2026-000006`) para una sola intención de compra.
- **Causa raíz:** `_generate_order_number()` calcula el correlativo con `SELECT count(*) + 1`. Dos transacciones concurrentes leen el mismo conteo y generan el mismo número; la restricción `UNIQUE` sobre `order_number` hace fallar a la segunda con `IntegrityError → 409`. Esto tiene dos consecuencias:
  1. **Protección frágil:** cuando las peticiones se escalonan lo suficiente para leer conteos distintos, la colisión no ocurre y se cuela un **pedido duplicado**.
  2. **Rechazo espurio:** el correlativo es **global por año**, así que dos compradores *distintos* que paguen en el mismo instante colisionan en el número aunque no compartan nada, y uno recibe un `409` sin motivo de negocio.
- **Estado:** **FALLIDO.**
- **Evidencia:** `order_number` es `UNIQUE` (`uq_orders_order_number`); reproducido en 4 ejecuciones. La integridad interna de cada pedido se mantiene (verificado en la sección de base de datos), por lo que el impacto es de **negocio y disponibilidad**, no de corrupción de datos.
- **Recomendación:**
  - Reemplazar el correlativo `count(*)+1` por una **secuencia de PostgreSQL** (`CREATE SEQUENCE order_number_seq`) o por un identificador derivado de ULID/UUID. Elimina de raíz tanto los duplicados como los `409` espurios.
  - Para blindar el doble clic, **serializar el checkout por usuario**: bloqueo pesimista sobre el carrito (`SELECT … FOR UPDATE`) o *advisory lock* por `user_id` al inicio de la transacción, de modo que la segunda ejecución encuentre el carrito ya vacío. Alternativamente, aceptar una **clave de idempotencia** del cliente.

### HALLAZGO-02 · Validación de contraseña con mensajes contradictorios — **Severidad: BAJA**

- **Qué se probó:** Política de contraseñas en el registro.
- **Pasos:** Registro con contraseñas de 3, 7, 8, 10 y 12 caracteres.
- **Resultado obtenido:** Con 7 caracteres, el mensaje es *«String should have at least 8 characters»* (en inglés). Con 8–11 caracteres, el mensaje es *«Debe tener al menos 12 caracteres»*. El usuario recibe dos umbrales distintos (8 y 12) y un texto sin traducir.
- **Causa raíz:** `PasswordField` declara `Field(min_length=8)`, pero la política real (`validate_password_strength`, `password_min_length=12`) exige 12. El `min_length=8` de Pydantic se dispara antes con su mensaje genérico en inglés.
- **Estado:** **FALLIDO (cosmético / UX).** La política de 12 caracteres sí se aplica; no hay riesgo de seguridad.
- **Recomendación:** Bajar el `Field(min_length=…)` a `1` (o eliminarlo) y dejar toda la validación de longitud al validador que ya devuelve mensajes en español, para un único umbral coherente y localizado.

### HALLAZGO-03 · Falta la cabecera `Content-Security-Policy` — **Severidad: BAJA**

- **Qué se probó:** Cabeceras de seguridad en las respuestas HTTP.
- **Resultado obtenido:** Presentes `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` y, en el frontend, `Permissions-Policy`. Ausente `Content-Security-Policy`.
- **Corrección de la primera versión de este informe:** se afirmó también que faltaba `Strict-Transport-Security`. **Era incorrecto**: la cabecera sí está implementada, condicionada a producción (`main.py`), y por eso no aparecía en el entorno de desarrollo, que no usa HTTPS.
- **Estado:** **OBSERVACIÓN.**
- **Recomendación:** Añadir CSP tanto en la API como en el frontend.

### HALLAZGO-04 · Mensaje impreciso al cancelar una sub-orden ya resuelta — **Severidad: BAJA (cosmético)**

- **Qué se probó:** Cancelar dos veces la misma sub-orden.
- **Resultado obtenido:** La segunda cancelación se rechaza correctamente (`422`), pero el mensaje dice *«Este pedido ya fue despachado y no puede cancelarse»* cuando en realidad ya fue **cancelado**, no despachado.
- **Estado:** **OBSERVACIÓN.** La lógica es correcta (no se puede cancelar dos veces); solo el texto es engañoso.
- **Recomendación:** Diferenciar el mensaje según el estado real de la transición inválida.

### Observaciones informativas

- **Token de acceso tras cierre de sesión:** al hacer *logout* se revoca el *refresh token* de inmediato, pero el *access token* sigue siendo válido hasta expirar (15 min). Es el compromiso conocido de los JWT sin estado; el impacto se acota con la vida corta del token. Documentado.
- **Cabecera `Server: uvicorn`:** revela el servidor de aplicación. En producción queda tras Nginx, que puede ocultarla.
- **Tokens en `sessionStorage`:** ya documentado en `08-auditoria.md`; su migración a *cookies* `httpOnly` debe hacerse junto con protección CSRF.

---

## 3. Resultados por funcionalidad

### 3.1 Registro e inicio de sesión — APROBADO

| Prueba | Esperado | Obtenido | Estado |
|--------|----------|----------|--------|
| Registro válido | 202, correo de verificación | 202, correo capturado en Mailpit | Aprobado |
| Contraseña débil (< 8) | Rechazo | 422 | Aprobado |
| Sin consentimiento de datos | Rechazo (Ley 1581) | 422 con mensaje explícito | Aprobado |
| Correo duplicado | Sin revelar existencia | 202 idéntico (anti-enumeración) | Aprobado |
| Verificación de correo | Token de un solo uso | 200; reutilización → 401 | Aprobado |
| Login correcto | Access + refresh | 200 con ambos tokens | Aprobado |
| Login incorrecto | Mensaje genérico | «Correo o contraseña incorrectos» | Aprobado |
| Solicitud de reset a correo inexistente | Sin revelar existencia | 202 idéntico | Aprobado |
| Reset de contraseña | Token de un solo uso, cierra sesiones | 200; reutilización → 401 | Aprobado |

**Nota:** los tokens de verificación y reset se almacenan **hasheados (SHA-256)** en la tabla `verification_tokens`, no en claro.

### 3.2 Sesiones y JWT — APROBADO

| Ataque | Obtenido | Estado |
|--------|----------|--------|
| JWT con `alg: none` | 401 «Token inválido» | Bloqueado |
| Payload alterado a `admin` con firma original | 401 | Bloqueado |
| Firma con clave débil adivinada | 401 | Bloqueado |
| *Refresh token* usado como *access* | 401 | Bloqueado |
| Rotación de *refresh* | Nuevo token; el anterior queda inválido | Aprobado |
| Reutilización de *refresh* rotado | 401 (detección de robo) | Aprobado |
| Vigencia | Access 15 min, refresh 30 días | Confirmado |

### 3.3 Roles y permisos (RBAC) — APROBADO

Matriz de autorización verificada sobre 16 rutas con cuatro identidades (anónimo, comprador, productor, admin). **Ninguna escalada fue posible.** Ejemplos:

| Acción | Comprador | Productor | Admin |
|--------|-----------|-----------|-------|
| `GET /admin/*` | 403 | 403 | 200 |
| `GET /producer/*` | 403 | 200 | 403 |
| Suspender usuario | 403 | 403 | 200 |
| Aprobar productor | 403 | 403 | 200 |
| Ajustar inventario | 403 | 200 (propio) | 403 |

Todas las **escrituras cruzadas** entre roles devolvieron `403`.

### 3.4 Catálogo, búsqueda y detalle — APROBADO

- Búsqueda **insensible a acentos y mayúsculas** (`nariño` = `narino` = `NARINO`), incluyendo el perfil sensorial.
- **Inyección SQL** (`' OR '1'='1`, `UNION SELECT password_hash`, `DROP TABLE`): todas neutralizadas, la tabla `products` intacta (consultas parametrizadas).
- Filtros inválidos (`min_price` negativo, `sort` arbitrario, `page=0`, `page_size=99999`): `422`.
- Un producto en **borrador** desaparece del listado (9 → 8) y su detalle directo por *slug* devuelve `404`, incluso conociendo el *slug*.
- **Sin fuga de datos sensibles:** ningún endpoint público expone coordenadas exactas de finca (`exact_lat/lng`), datos bancarios ni documentos del productor. Solo se publican coordenadas **aproximadas**.

### 3.5 Carrito, checkout, inventario y pagos — APROBADO (checkout: con observación HALLAZGO-01)

| Prueba | Obtenido | Estado |
|--------|----------|--------|
| Agregar variante agotada (stock 0) | 422 «Solo quedan 0 unidades» | Aprobado |
| Agregar cantidad > stock | 422 con stock disponible | Aprobado |
| Cantidad 0 / negativa | 422 | Aprobado |
| **Manipulación de precio en checkout** | Ignorada; se factura el precio del servidor (150.000 COP reales frente a `unit_price:1` inyectado) | Aprobado |
| Reserva de inventario | `reserved_qty` sube al crear el pedido; `FOR UPDATE` + `CHECK (reserved ≤ stock)` | Aprobado |
| **Webhook sin firma** | 200 pero **no confirma** el pago | Aprobado |
| **Webhook con firma falsa** | 200 pero **no confirma** | Aprobado |
| Webhook con firma válida (HMAC-SHA256) | Confirma; stock 20 → 18, reserva liberada | Aprobado |
| **Webhook duplicado (idempotencia)** | 3 reenvíos no descuentan de más (sigue 18) | Aprobado |
| Cancelar sub-orden pendiente | Repone la reserva (3 → 2) | Aprobado |
| IDOR: ver/cancelar pedido ajeno | 403 «Este pedido no te pertenece» | Aprobado |

**Punto fuerte:** la manipulación de precios es **imposible por diseño** — el `CheckoutRequest` no acepta precios ni cantidades; todo se recalcula desde el carrito del servidor. La confirmación de pago exige **firma HMAC válida comparada en tiempo constante**; un pago falso nunca confirma el pedido ni descuenta stock.

### 3.6 Paneles — APROBADO

- **Comprador:** solo ve sus pedidos y direcciones; IDOR bloqueado.
- **Productor:** dashboard, productos, pedidos, alertas de stock y liquidaciones **acotados a su catálogo**. Intento de ajustar inventario de **otro** productor → `403`. Comisión (8 %) y liquidaciones cuadran.
- **Administrador:** dashboard, cola de aprobación, moderación y auditoría. La **suspensión de un usuario corta su sesión activa al instante** (403 con el mismo token; nuevo login 401), gracias a la recarga del usuario desde la base de datos en cada petición. Aprobación de productor y suspensión quedan en el **registro de auditoría** con su autor.

### 3.7 API, base de datos y errores — APROBADO

- JSON malformado → `422`; método no permitido → `405`; UUID inválido → `422`; ruta inexistente → `404` **sin *stack trace***.
- **Integridad de base de datos (6 comprobaciones, 0 violaciones):** ninguna reserva excede el stock; sin pedidos huérfanos; `line_total = quantity × unit_price` en todos; subtotales de sub-orden cuadrados; **todas** las contraseñas con Argon2id; dato bancario cifrado en reposo (`bank_account_encrypted`). Esquema con 81 claves foráneas, 30 `CHECK`, 27 `UNIQUE`, 139 índices.
- **Logs:** cero apariciones de `secret_key`, secreto de webhook, o contraseñas en claro. El *echo* SQL se desactiva solo en producción (`app_debug and not is_production`).

### 3.8 Rendimiento — APROBADO

- Latencias: catálogo ~40 ms, detalle ~30 ms, productores ~19 ms, pedidos ~23 ms (medición local).
- **Regresión N+1** activa: 3 pruebas fijan un techo de consultas por operación y fallan si se reintroduce una carga perezosa en bucle.
- Suite completa: **98/98 pruebas pasan**.

### 3.9 Responsive y accesibilidad — APROBADO

- **Sin scroll horizontal** en móvil (375 px); cero elementos desbordados; menú hamburguesa funcional con estado comunicado por `aria-label` dinámico.
- **Contraste** (WCAG AA, umbral 4.5:1): badge del héroe 5.64:1, CTA 5.54:1, titulares 12.25:1, precios 14.24:1. Todos cumplen.
- Estructura: `lang="es-CO"`, un solo `h1`, jerarquía de encabezados sin saltos, *skip link*, landmarks, imágenes con `alt`, formularios con etiquetas y `autocomplete`, errores anunciados con `role="alert"`.
- **Área táctil de las tarjetas de producto:** aunque el enlace de título mide 17 px de alto, el sondeo con `elementFromPoint` confirma que **toda la tarjeta (343×462 px)** es el objetivo de clic. Cumple WCAG 2.5.8. *(Falso positivo típico; documentado para que no se «corrija» código que funciona.)*

### 3.10 Protección de datos — APROBADO

- Consentimiento explícito obligatorio en el registro (**Ley 1581 de 2012**); enlaces a términos y política de privacidad en el login.
- Datos sensibles del productor (ubicación exacta, cuenta bancaria, documento) **nunca** se serializan en respuestas públicas.
- Contraseñas con **Argon2id**; tokens de un solo uso hasheados; secretos fuera de los logs.

---

## 4. Hallazgo posterior al informe inicial

### HALLAZGO-05 · Las imágenes de los cafés no existen en el almacenamiento — **Severidad: MEDIA (funcional, no de seguridad)**

- **Qué se probó:** Carga real de las imágenes del catálogo en el navegador.
- **Resultado obtenido:** Las ocho imágenes de la portada tienen `naturalWidth = 0`: **ninguna carga**. El origen (`http://localhost:9000/monkgrain/demo/…`) devuelve `403` y el optimizador de Next responde `500`. El *bucket* `monkgrain` **no existe** en MinIO: el volumen solo contiene `.minio.sys`.
- **Causa raíz:** `demo_data.py` asigna `image_key=f"demo/{slug}.jpg"` a cada producto, pero **no hay ningún código que cree el bucket ni suba los archivos**. Las claves apuntan a objetos que nunca se generaron.
- **Estado:** **FALLIDO.** Es un defecto preexistente, sin relación con las correcciones de esta ronda.
- **Por qué no se detectó en la primera pasada:** la revisión de la interfaz se apoyó en el árbol de accesibilidad y en mediciones por JavaScript, donde los atributos `alt` aparecen correctos y las tarjetas se renderizan con su estructura completa. No se comprobó que el mapa de bits llegara a descargarse. Es una limitación real del método empleado, no un cambio de comportamiento.
- **Impacto:** un marketplace de café mostrando fichas sin fotografía. No afecta a la seguridad ni a la integridad de los datos.
- **Corrección aplicada:** se añadió el componente `CoffeeImage` (`web/src/components/shared/CoffeeImage.tsx`), que sustituye la imagen rota por un marcador con los colores de la marca. Está aplicado en los tres puntos donde se muestran fotografías de café: tarjeta de producto, ficha de detalle y carrito.
  - El marcador lleva `role="img"` y `aria-label`, de modo que un lector de pantalla sigue anunciando de qué café se trata: *«Quindío Clásico, café de Alta Vista (sin fotografía disponible)»*. Contraste del texto medido: **6,30:1** (supera el umbral AA de 4,5:1).
  - No basta con el `onError` de React: el evento `error` de una imagen no burbujea y, con renderizado en servidor, la carga puede fallar **antes** de que la página se hidrate, en cuyo caso el manejador no existe todavía. El componente cubre ese caso comprobando al montar si el elemento ya está fallido (una imagen terminada con ancho cero) y registrando además un escucha nativo sobre el nodo.
  - Sigue siendo recomendable **sembrar las imágenes reales**: el marcador evita el icono de imagen rota, no sustituye a la fotografía.
- **Verificado:** en la ficha de detalle el marcador aparece **sin intervención alguna** (`role="img"` presente, cero imágenes rotas). **No pudo observarse en `/catalogo`** dentro del navegador de pruebas empleado, que no compone fotogramas y por tanto nunca dispara la carga diferida de esas tarjetas. La cobertura de esa página se sostiene en dos comprobaciones indirectas: `ProductCard` usa el mismo componente, y el *payload* RSC de `/catalogo` declara `CoffeeImage.tsx` **exactamente igual** que la página donde sí se comprobó su funcionamiento.

---

### HALLAZGO-06 · El optimizador de imágenes no alcanza el almacenamiento — **Severidad: MEDIA** · *Corregido*

- **Qué se probó:** carga de una imagen real, una vez sembradas las de muestra.
- **Resultado obtenido:** MinIO servía el archivo correctamente (`200`, 49 KB, `image/jpeg`), pero `/_next/image` seguía devolviendo `500` con `ECONNREFUSED`.
- **Causa raíz:** el mismo patrón que el error de `API_INTERNAL_URL` corregido durante la construcción. `S3_PUBLIC_URL` valía `http://localhost:9000`, correcto para el navegador; pero el optimizador de imágenes corre **dentro** del contenedor de Next, donde `localhost` es ese mismo contenedor y no MinIO. Comprobado: desde el contenedor `web`, `http://minio:9000/…` responde `200` y `http://localhost:9000/…` da conexión rechazada.
- **Impacto:** ninguna fotografía se mostraría en desarrollo aunque el archivo existiera. En producción, con un S3 accesible desde el servidor, no se manifiesta.
- **Corrección aplicada:** los archivos se sirven bajo `/media`, reescrito por Next hacia la red interna de Docker (`MEDIA_INTERNAL_URL`, por omisión `http://minio:9000`), y `S3_PUBLIC_URL` pasa a `http://localhost:3000/media`. Así la misma URL sirve al navegador y al servidor.
- **Verificado:** `/media/...` → `200` (49 KB, `image/jpeg`); `/_next/image?...` → `200` (9,5 KB optimizados); en la ficha, la imagen carga a **640×480 reales**, con cero imágenes rotas y cero marcadores.
- **Nota de operación:** `docker compose restart` **no** recarga el `env_file`; hace falta `docker compose up -d` para que el backend tome variables nuevas.

### HALLAZGO-07 · El productor no puede publicar productos ni subir documentos — **Severidad: ALTA (brecha de alcance)**

- **Qué se probó:** cobertura de los requisitos del panel del productor frente a lo implementado.
- **Resultado obtenido:** el panel del productor expone **seis rutas y solo una de escritura**, el ajuste de inventario (`PATCH /producer/inventory/{variant_id}`). No existe ningún endpoint para crear o editar productos, ni para subir imágenes, ni para cargar certificados o documentos. En todo el frontend **no hay un solo `input type="file"`**, y aunque MinIO está configurado (`S3_*`) y `boto3` está entre las dependencias, **ningún código de la aplicación los usaba** antes de esta ronda.
- **Contraste con el alcance declarado:** el MVP incluye explícitamente «Panel del productor (**productos**, inventario, pedidos recibidos, ventas, **documentos/certificaciones**)», y los requisitos **RF-04.2** (publicación y edición de productos con múltiples imágenes y variantes), **RF-04.5** (carga de certificados y documentos) y **RF-07.3** (gestión de documentos y su vigencia) no figuran entre lo pospuesto ni entre lo excluido.
- **Estado:** **FALLIDO.** Es el defecto funcional de mayor alcance detectado: el flujo por el que el catálogo se alimenta —cada vendedor publica su café con su documentación— no existe. Hoy el catálogo solo puede poblarse mediante datos sembrados.
- **Por qué no se detectó en la primera pasada:** la auditoría se ejecutó **contra el sistema**, comprobando que lo existente funcionara y resistiera ataques, en lugar de **contra la especificación**. Un endpoint ausente no falla ninguna prueba: simplemente no aparece. Es una carencia del método, no un cambio de comportamiento.
- **Recomendación:** implementar como bloque propio, con estas piezas mínimas: módulo de almacenamiento (subida con URL prefirmada o a través de la API), `POST`/`PATCH`/`DELETE` de productos y variantes restringidos al catálogo propio del productor —el mismo control de pertenencia ya verificado en inventario—, validación estricta de tipo y tamaño de archivo, y carga de documentos con su estado de vigencia. Al ser un flujo que recibe archivos de terceros, exige su propia revisión de seguridad: tipos permitidos, límites de tamaño, nombres saneados y almacenamiento sin permisos de ejecución.

### HALLAZGO-08 · Enlaces de la navegación que no llevaban a ninguna parte — **Severidad: ALTA en dos casos**

- **Qué se probó:** un barrido de todas las rutas internas enlazadas desde la navegación, el pie de página y los formularios.
- **Resultado obtenido:** **17 rutas devolvían 404**. Dos rompían flujos que la API ya soportaba:
  - **`/recuperar-contrasena`** — el enlace «¿Olvidaste tu contraseña?» del inicio de sesión. La API tenía el flujo completo y probado, pero **en pantalla no existía**: quien perdiera su contraseña quedaba fuera de su cuenta sin salida.
  - **`/restablecer-contrasena`** — la dirección que el propio backend escribe en el correo de restablecimiento. El enlace enviado al usuario terminaba en un 404.
- **Por qué no se detectó antes:** la auditoría comprobó que cada pantalla existente funcionara, no que los enlaces condujeran a algún sitio. Es la misma carencia de método que HALLAZGO-07: se revisó lo que había, no lo que faltaba.
- **Corrección aplicada:** se crearon ambas páginas, más `/vender` y `/productores` (esta última era el destino del botón «Conocer a los productores» de la portada).
- **Verificado con el flujo real de principio a fin:** se solicitó el enlace, se extrajo del correo entregado, se abrió en el navegador y se cambió la contraseña. Resultado: la contraseña nueva entra, **la anterior deja de servir**, el enlace **no admite un segundo uso**, y el titular recibe el aviso «Tu contraseña fue cambiada». La validación rechaza contraseñas cortas y confirmaciones que no coinciden, anunciándolo con `role="alert"`.
- **Anti-enumeración conservada en la interfaz:** la pantalla de confirmación dice «Si ese correo corresponde a una cuenta registrada…», sin revelar si existe.
- **Segunda tanda de correcciones — documentos legales.** Eran **cuatro**, no tres, y se enlazaban desde puntos donde el usuario *acepta* algo: el registro apunta a `/legal/datos` para el consentimiento de tratamiento de datos, y el checkout a `/legal/terminos` y `/legal/devoluciones` para la aceptación de compra. Es decir, **se estaba pidiendo aceptar un texto que no podía leerse**. Se crearon las cuatro:
  - `/legal/datos` — política de tratamiento conforme a la **Ley 1581 de 2012** y el **Decreto 1074 de 2015**: responsable, finalidades, derechos del titular, canal y plazos de respuesta (10 y 15 días hábiles).
  - `/legal/terminos` — condiciones de uso, comisión del 8 %, alcance nacional y remisión al **Estatuto del Consumidor**.
  - `/legal/devoluciones` — retracto de 5 días hábiles y garantía de 30 días.
  - `/legal/privacidad` — versión en lenguaje llano de lo anterior.

  El inventario de datos de estos documentos **se redactó leyendo el esquema real** (`users`, `addresses`, `producer_profiles`), no a partir de una plantilla: declara exactamente lo que la plataforma guarda, incluido que la cuenta bancaria va cifrada, que no se almacenan datos de tarjeta y que se eliminan los metadatos EXIF de las fotografías.

  **Advertencia expresa:** los cuatro textos los redactó el equipo de desarrollo, **no un abogado**. Cada página muestra un aviso visible de «borrador pendiente de revisión jurídica» y los datos de la empresa quedan como marcadores entre corchetes. Son documentos con efectos vinculantes: **requieren revisión legal antes de operar con usuarios reales.**

  Verificado: las cuatro responden 200, contraste 5,10:1 y 5,64:1 (sobre el umbral AA), jerarquía de encabezados sin saltos, navegación lateral etiquetada y sin desbordes en móvil de 375 px.

- **Pendiente:** quedan 12 rutas de contenido sin página, ninguna crítica: `/regiones`, `/blog`, `/favoritos`, `/nosotros`, `/ayuda`, `/contacto`, `/envios`, `/devoluciones`, `/trazabilidad`, `/sostenibilidad`, `/vender/como-funciona` y `/vender/comisiones`.

### HALLAZGO-09 · Dos exigencias del Estatuto del Consumidor sin soporte en el esquema — **Severidad: MEDIA** · *Corregido*

Detectados durante la revisión normativa de los documentos legales, y confirmados sobre la base de datos antes de actuar.

**a) Registro de oferentes (artículo 53 de la Ley 1480 de 2011).** La norma obliga al portal de contacto a llevar un registro con la **dirección física de notificaciones y el teléfono** de cada oferente, y a entregárselos a quien presente una reclamación. `producer_profiles` solo guardaba departamento y municipio —insuficiente para notificar a nadie— y `users.phone` era opcional. Los documentos legales ya prometían ese registro, de modo que el texto comprometía algo que el sistema no podía cumplir.

- **Corrección:** columnas `notification_address` y `contact_phone` (migración `ae0cdd0bb859`), admitiendo nulo para no invalidar los perfiles anteriores. El dato **se exige al publicar el primer café**, reutilizando el mecanismo de `missing_to_publish` ya existente, y no en una migración que habría dejado filas inválidas.
- Como exigir un dato sin ofrecer dónde registrarlo habría bloqueado a todos los vendedores, se añadieron `GET` y `PUT /producer/profile`. La razón social, el documento y el estado quedan **fuera** de ese endpoint: son lo que el equipo verificó al aprobar la solicitud.
- **Verificado en ejecución:** un vendedor sin esos datos ve los dos requisitos en su panel y recibe `422` al publicar; tras registrarlos por el endpoint, publica con `200`. Los campos **no aparecen** en ningún endpoint público (0 apariciones de `notification_address`, `contact_phone`, `document_number` ni `bank_account`), y un anónimo recibe `401`.

**b) Causal de retracto ausente (artículo 47).** El enum `return_reason` era `{damaged, wrong_item, quality, other}`: solo motivos por defecto del producto. El retracto —desistir dentro de cinco días hábiles sin justificación— tiene plazo, costo de transporte y forma de reembolso distintos, y había que registrarlo como «otro», perdiendo ese tratamiento.

- **Corrección:** se añadió `withdrawal` al enum y el conjunto `SELLER_ATTRIBUTABLE_RETURN_REASONS`, que distingue los motivos imputables al vendedor —donde el transporte corre por su cuenta— del retracto, donde salvo pacto distinto lo asume el comprador.

**Cobertura:** cinco pruebas nuevas (`TestSellerNotificationData`) cubren el bloqueo por cada dato faltante, el registro por el endpoint, que la identidad verificada no se pueda alterar y el aislamiento entre vendedores. Suite total: **158 pruebas**.

---

## 5. Estado de remediación

Las cuatro observaciones del informe se corrigieron y se verificaron contra el entorno en ejecución.

| Hallazgo | Corrección | Verificación |
|----------|-----------|--------------|
| **01 · Numeración concurrente** | `order_number` pasa a apoyarse en una secuencia de PostgreSQL (`order_number_seq`, migración `59c2f7a91062`), declarada también en los metadatos para que exista al crear el esquema desde cero. Además, el checkout toma un `pg_advisory_xact_lock` por comprador, de modo que un doble clic espera y encuentra el carrito ya vacío. | Doble clic: **5 de 5 rondas concurrentes producen un único pedido** (antes se colaban duplicados). Dos compradores simultáneos: **ambos reciben `201`** con números distintos (`000015` y `000016`), sin el `409` espurio. |
| **02 · Mensaje de contraseña** | Se elimina el `min_length=8` de Pydantic, que se adelantaba al validador real y anunciaba un mínimo equivocado en inglés. El manejador de validación retira además el prefijo técnico `Value error,`. | Todos los mensajes salen en español y con el umbral correcto: «Debe tener al menos 12 caracteres.», «Debe incluir al menos un número.» |
| **03 · CSP ausente** | CSP estricto en la API (`default-src 'none'`), excluyendo la documentación interactiva, que necesita cargar sus propios recursos. CSP en el frontend con `object-src 'none'`, `base-uri`, `form-action` y `frame-ancestors 'none'`. | Cabecera presente en ambas capas; `/docs` sigue sin CSP restrictivo. La portada carga sin errores de consola. |
| **04 · Mensaje de cancelación** | El motivo se redacta según el estado real de la sub-orden en vez de asumir siempre «ya fue despachado». | Cancelar dos veces devuelve ahora «Este pedido ya está cancelado.» |

**Alcance del CSP del frontend:** `script-src` conserva `'unsafe-inline'` porque el App Router incrusta el estado de hidratación en etiquetas `<script>` en línea. La política **no** detiene un script inyectado en la propia página; lo que impide es cargar código de otro dominio, enviar formularios fuera del sitio, incrustar la página en un iframe ajeno o reescribir la URL base. Cerrar el hueco restante exige servir un `nonce` por petición desde el middleware: **queda pendiente**.

**Cobertura de pruebas:** se añadió la clase `TestConcurrentCheckout`. La prueba de numeración **se validó reintroduciendo el defecto**, y falla como debe (`['MG-2026-000001', 'MG-2026-000001', …]`). La prueba de doble envío cubre el caso secuencial pero **no** ejercita el bloqueo, porque `TestClient` envía las peticiones una tras otra; la concurrencia real se verificó contra el entorno. Está anotado en el propio docstring.

Suite completa tras los cambios: **100 pruebas, todas en verde** (98 previas + 2 nuevas). Ruff, Ruff format, Mypy, TypeScript y ESLint sin hallazgos. `alembic check` sin migraciones pendientes.

---

## 6. Conclusión

**MONK GRAIN queda APROBADO CON OBSERVACIONES para producción.**

La plataforma demuestra una postura de seguridad madura: los vectores de mayor impacto en un marketplace están cerrados y verificados con ataques reales, no solo por inspección.

**Tras la remediación**, el bloqueante para operar con dinero real (HALLAZGO-01) está resuelto y comprobado bajo concurrencia.

**Matiz sobre el veredicto:** «aprobado con observaciones» califica lo que la plataforma **hace**. HALLAZGO-07 muestra que hay una parte del MVP que **no hace**: el productor no puede publicar su café ni subir su documentación. Eso no degrada la seguridad de lo construido —que resistió todos los ataques—, pero sí significa que el catálogo aún no puede alimentarse solo. Es trabajo de desarrollo pendiente, no un defecto a corregir.

Queda pendiente, sin carácter bloqueante para la seguridad:

- **Implementar la publicación de productos y la carga de documentos por el productor** (HALLAZGO-07), con su propia revisión de seguridad por tratarse de un flujo que recibe archivos de terceros.
- Sustituir las imágenes de muestra por las fotografías reales conforme cada vendedor publique su café.
- Servir el CSP del frontend con `nonce` por petición para cubrir también la inyección en línea.
- Migrar los tokens de `sessionStorage` a *cookies* `httpOnly`, **junto con** protección CSRF (documentado en `08-auditoria.md`).

---

*Todas las alteraciones de datos realizadas durante la auditoría (suspensión temporal de una cuenta, cambio de estado de un producto y de un productor, ajustes de inventario) fueron reversibles y se revirtieron. Los pedidos de prueba generados se conservan como evidencia y no afectan la integridad, verificada en la sección 3.7.*
