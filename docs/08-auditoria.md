# MONK GRAIN — Fase 11: Auditoría de seguridad, rendimiento y accesibilidad

Revisión ejecutada **contra el sistema en funcionamiento**, no una lista de comprobación teórica. Cada punto se verificó lanzando la petición real y observando el resultado.

Fecha: 13 de agosto de 2026 · Entorno: Docker local con datos de demostración.

---

## Resumen

| Área | Comprobaciones | Resultado |
|---|---|---|
| Seguridad | 9 | Sin vulnerabilidades explotables |
| Rendimiento | 4 | 1 problema encontrado y corregido |
| Accesibilidad | 12 | Conforme WCAG 2.1 AA en lo verificado |

**Un hallazgo real corregido:** problema N+1 en el listado de productores, de 15 a 5 consultas.

---

## 1. Seguridad

### 1.1 Inyección SQL

Se lanzaron cargas maliciosas contra los filtros del catálogo:

| Carga | Respuesta |
|---|---|
| `' OR '1'='1` | 200, sin datos adicionales |
| `'; DROP TABLE users;--` | 200, **la tabla sobrevivió** (11 usuarios intactos) |
| `1' UNION SELECT NULL,NULL--` | 200, sin fuga |

**Por qué no funciona:** todas las consultas pasan por SQLAlchemy con parámetros vinculados. El valor viaja separado de la sentencia, de modo que el motor nunca lo interpreta como SQL. En el código no hay una sola cadena SQL construida por concatenación.

### 1.2 Cross-site scripting almacenado

Se registró un usuario con el nombre `<script>alert(1)</script>` y se inyectó `<img src=x onerror=alert(1)>` en un campo visible del catálogo.

**El dato se almacena tal cual** —lo cual es correcto: la base de datos guarda lo que el usuario escribió— y **se escapa al renderizar**. En el HTML servido aparece como `&lt;img src=x onerror...`, nunca como etiqueta activa.

La defensa es el escapado automático de React. Se verificó buscando la etiqueta sin escapar en el HTML entregado: 0 coincidencias; escapada: 1.

> **Advertencia para el futuro:** esta protección depende de que el contenido se renderice con React. Si algún día se genera un PDF, un correo con HTML o se usa `dangerouslySetInnerHTML`, ahí habrá que escapar explícitamente. El modelo `Message` documenta la intención de sanear el cuerpo antes de persistirlo; **esa sanitización todavía no está implementada** porque el módulo de mensajería no se ha construido. Debe hacerse cuando se construya.

### 1.3 Escalada de privilegios

| Intento | Resultado |
|---|---|
| Comprador → `/admin/dashboard` | **403** |
| Comprador → `/producer/dashboard` | **403** |
| Comprador → `/admin/audit-logs` | **403** |
| Productor → panel de otro productor | **403** (verificado en fase 8) |
| Comprador → pedido de otra persona | **403** (probado en la suite) |

La comprobación ocurre en el servidor mediante dependencias de FastAPI. Ocultar una opción en la interfaz no es control de acceso.

### 1.4 Manipulación de tokens

| Ataque | Resultado |
|---|---|
| Token con `alg: none` y `roles: ["admin"]` | **401** |
| Carga útil alterada con firma original | **401** |
| Token firmado con otra clave | **401** (prueba unitaria) |
| Token expirado | **401** (prueba unitaria) |
| Access token usado donde se espera refresh | **401** (prueba unitaria) |

El algoritmo se fija explícitamente al decodificar, de modo que un token que declare `none` no se acepta jamás.

### 1.5 Exposición de datos sensibles

Se buscaron seis campos críticos en las respuestas de `/auth/me` y de la ficha de producto:

```
password_hash   0 apariciones
bank_account    0
exact_lat       0
exact_lng       0
token_hash      0
secret_key      0
```

La coordenada exacta de las fincas existe en la base de datos pero **no está declarada en ningún schema de salida**: la protección es estructural, no depende de recordar omitirla en cada endpoint.

### 1.6 Cabeceras de seguridad

| Cabecera | API | Web |
|---|---|---|
| `X-Content-Type-Options: nosniff` | ✓ | ✓ |
| `X-Frame-Options: DENY` | ✓ | ✓ |
| `Referrer-Policy: strict-origin-when-cross-origin` | ✓ | ✓ |
| `Permissions-Policy` | — | ✓ |
| `Strict-Transport-Security` | Solo en producción | Nginx |

Se aplican tanto en Nginx como en la propia aplicación: un despliegue sin proxy no queda desprotegido.

### 1.7 CORS

| Origen | Cabecera devuelta |
|---|---|
| `http://localhost:3000` (permitido) | `access-control-allow-origin` presente |
| `https://sitio-atacante.com` | **Sin cabecera** — el navegador bloquea |

### 1.8 Identificadores no enumerables

Pedidos, usuarios, productos y pagos usan UUID. Un identificador secuencial permitiría recorrer los pedidos ajenos y estimar el volumen de negocio.

### 1.9 Límite de peticiones

Verificado en la fase 7: el sexto intento de inicio de sesión en un minuto devuelve **429**. Los contadores viven en Redis, compartidos entre instancias.

---

## 2. Rendimiento

### 2.1 Tiempos de respuesta

Media de cinco mediciones sobre el conjunto de demostración:

| Endpoint | Tiempo |
|---|---|
| `GET /products?page_size=12` | 41 ms |
| `GET /products/{slug}` | 34 ms |
| `GET /producers` | 40 ms |

Holgadamente por debajo del objetivo de 2 s del requisito RNF-01.

### 2.2 Uso de índices

`EXPLAIN ANALYZE` del listado confirma **Index Scan Backward** sobre `ix_products_catalog`, sin recorrido secuencial de la tabla. El plan usa *Incremental Sort* aprovechando que el índice ya viene ordenado por `published_at`.

### 2.3 Problema N+1 — encontrado y corregido

Se instrumentó el motor para contar las consultas que dispara cada operación:

| Operación | Antes | Después |
|---|---|---|
| Listado de 9 productos | 6 | 6 |
| Ficha de producto | 7 | 7 |
| **Listado de 6 productores** | **15** | **5** |

El listado de productores ejecutaba una consulta de conteo y otra de departamento **por cada productor**. Con 6 productores eran 15 consultas; con 100 habrían sido más de 200, y el problema no se habría notado en desarrollo.

**Corrección:**
1. Un único conteo agrupado (`GROUP BY producer_id`) en lugar de uno por productor.
2. Carga anticipada del departamento junto al municipio.

El listado de productos ya estaba correcto gracias a la carga anticipada declarada en la fase 8.

### 2.4 Caché

El catálogo y las fichas se cachean en Redis con expiración corta. **Nunca se cachean** inventario, estados de pedido ni pagos: un dato de stock obsoleto produce sobreventa, y el ahorro no compensa ese riesgo.

---

## 3. Accesibilidad

Verificado sobre el DOM renderizado de las páginas principales.

### 3.1 Estructura y semántica

| Comprobación | Resultado |
|---|---|
| Un solo `<h1>` por página | ✓ |
| Jerarquía de encabezados sin saltos de nivel | ✓ |
| Landmarks (`header`, `nav`, `main`, `footer`) | ✓ |
| Idioma declarado (`lang="es-CO"`) | ✓ |

### 3.2 Nombres accesibles

| Comprobación | Incumplimientos |
|---|---|
| Imágenes sin `alt` | 0 |
| Enlaces sin nombre accesible | 0 |
| Botones sin nombre accesible | 0 |
| Campos sin etiqueta asociada | 0 |

### 3.3 Navegación por teclado

- **69 elementos focalizables** en el catálogo, todos alcanzables.
- **Cero `tabindex` positivos**: el orden de tabulación sigue el orden del documento y no se rompe.
- El **primer** elemento focalizable es el enlace «Saltar al contenido principal».
- Anillo de foco definido globalmente con `:focus-visible`.

### 3.4 Contraste

| Texto | Ratio | WCAG AA (4.5:1) |
|---|---|---|
| Principal sobre fondo | **14.01:1** | Cumple con holgura |
| Atenuado (`muted-foreground`) | **5.10:1** | Cumple |
| Distintivo de portada | 5.64:1 | Cumple *(corregido en fase 6)* |

El texto atenuado es el candidato natural a fallar, y pasa con margen.

### 3.5 Estados comunicados a la tecnología asistiva

- **25 controles con `aria-pressed`** en los filtros: quien usa lector de pantalla sabe cuáles están activos.
- Región `aria-live` que anuncia el número de resultados al cambiar los filtros.
- `aria-busy` en las vistas mientras cargan.
- Errores de formulario asociados al campo con `aria-describedby` y `aria-invalid`.

### 3.6 Objetivos táctiles — falso positivo aclarado

La medición inicial señaló 9 enlaces de 17 px de alto en las tarjetas de producto, aparentemente por debajo del mínimo de 24 px de WCAG 2.5.8.

**No es un incumplimiento.** El enlace usa un pseudo-elemento que cubre toda la tarjeta; `getBoundingClientRect()` mide solo la caja del texto. Se comprobó con `elementFromPoint` en tres puntos distintos —centro de la imagen, zona del precio y centro de la tarjeta— y en los tres el elemento que recibe el clic es el enlace del producto.

**Área real: 287 × 420 px**, no 17 px.

Se deja constancia porque una herramienta automática volvería a marcarlo, y conviene no “corregir” algo que ya funciona.

### 3.7 Preferencias del usuario

`prefers-reduced-motion` está respetado: quien pidió menos movimiento en su sistema operativo no recibe animaciones.

---

## 4. Asuntos pendientes

Ninguno bloquea el MVP, pero conviene resolverlos antes de abrir la plataforma al público:

| Asunto | Riesgo | Cuándo |
|---|---|---|
| Los tokens viven en `sessionStorage` | Un script inyectado podría leerlos. Hoy no hay vector conocido, pero cookies `httpOnly` eliminan la clase entera de problema | Antes de producción |
| Falta sanear el cuerpo de los mensajes | El módulo de mensajería aún no existe; debe hacerse al construirlo | Con el módulo |
| Sin cabecera `Content-Security-Policy` | Segunda línea de defensa frente a XSS | Antes de producción |
| Sin protección CSRF explícita | Hoy no aplica: la autenticación es por cabecera `Authorization`, no por cookie. **Será necesaria al migrar a cookies** | Junto con el cambio de cookies |
| `pg_stat_statements` no instalada | Impide medir consultas lentas en producción | Al desplegar |

> El cuarto punto merece cuidado: mover los tokens a cookies resuelve un riesgo pero **introduce** la exposición a CSRF. Ambos cambios deben hacerse a la vez, no uno primero.

---

## 5. Cómo repetir esta auditoría

Las comprobaciones de seguridad y rendimiento son reproducibles con `curl` y `psql` contra el entorno levantado; las de accesibilidad, ejecutando el análisis del DOM sobre las páginas renderizadas.

Conviene repetirla antes de cada despliegue a producción y tras cualquier cambio en autenticación, permisos o consultas del catálogo.

El conteo de consultas por operación es especialmente útil como prueba de regresión: un N+1 introducido por descuido no altera el resultado funcional y por eso pasa desapercibido, pero multiplica la carga de la base de datos.
