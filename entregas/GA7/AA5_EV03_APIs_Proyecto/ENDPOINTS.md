# ENDPOINTS — API de MONK GRAIN

**GA7-220501096-AA5-EV03** · API del proyecto formativo

**Base:** `http://localhost:8000/api/v1` · **107 endpoints** en 12 grupos
**Formato:** JSON en entrada y salida, UTF-8.
**Autenticación:** `Authorization: Bearer <access_token>`. El token lo
entrega `POST /auth/login` y dura 30 minutos; se renueva con
`POST /auth/refresh` sin volver a pedir la contraseña.

> Este archivo **se genera** desde el documento OpenAPI que publica el
> servicio en marcha (`GET /openapi.json`), con `generar_endpoints.py`.
> No se edita a mano: un catálogo escrito a mano se desactualiza en la
> primera semana, cuando alguien añade una ruta y no se acuerda de él.

---

## Resumen por grupo

| Grupo | Endpoints | Qué resuelve |
|---|---:|---|
| [sistema](#sistema) | 1 | Comprobación de vida del servicio. |
| [autenticación](#autenticación) | 10 | Registro, verificación de correo, ingreso, renovación y recuperación de contraseña. |
| [usuarios](#usuarios) | 7 | El perfil de quien está dentro: datos, direcciones y consentimientos. |
| [catálogo](#catálogo) | 5 | Lo que se puede comprar. |
| [carrito](#carrito) | 9 | La selección antes de pagar. |
| [pedidos](#pedidos) | 6 | Lo comprado, con su estado y sus sub-órdenes. |
| [devoluciones](#devoluciones) | 10 | Solicitud, aprobación y seguimiento de una devolución, con los plazos que fijó la revisión legal. |
| [reseñas](#reseñas) | 8 | Opiniones sobre los lotes y sobre los vendedores, solo de quien compró. |
| [oferta y demanda](#oferta-y-demanda) | 10 | El mercado en su segundo sentido: el comprador publica lo que busca y los caficultores responden con su precio. |
| [panel del productor](#panel-del-productor) | 27 | Todo lo que hace un vendedor con su finca: lotes, variantes, fotos, pedidos recibidos y certificaciones. |
| [liquidaciones](#liquidaciones) | 7 | El dinero de vuelta al vendedor: cuentas bancarias, cierre de periodo y pago. |
| [administración](#administración) | 7 | Aprobación de vendedores, moderación y parámetros. |
| **Total** | **107** | |

---

## Convenciones

| | |
|---|---|
| Rutas | Plural y en minúsculas: `/orders`, `/products`, no `/getOrder` |
| Versión | `/api/v1` en el prefijo. La única excepción es `/health` |
| Identificadores | UUID en la ruta: `/orders/{order_id}` |
| Páginas | `?page=1&page_size=20`; la respuesta trae `items`, `total`, `page`, `page_size`, `total_pages`, `has_next` y `has_previous` |
| Fechas | ISO 8601 con zona: `2026-11-02T03:17:46Z` |
| Dinero | Cadena decimal, nunca coma flotante: `"1850000.00"` |
| Peso | Kilogramos. La carga de 125 kg es una **lectura**, no una unidad de almacenamiento |
| Errores | `{"error": {"code", "message", "details"?}}`. **No** es el `detail` de serie de FastAPI: un manejador propio lo envuelve, para que el cliente pueda ramificar por `code` sin analizar el texto del mensaje |

### La columna «Token»

| Valor | Significa |
|---|---|
| `sí` | Exige la cabecera `Authorization: Bearer <access_token>` |
| `cuerpo` | No lleva cabecera, pero **tampoco es público**: recibe el *refresh token* en el cuerpo. Solo `/auth/refresh` y `/auth/logout` |
| `—` | Público |

### Códigos

Cada error HTTP viaja con un `code` legible que el cliente puede
comparar, en lugar de tener que reconocer el mensaje:

```json
{"error": {"code": "business_rule_violation",
            "message": "Este lote se vende desde 250 kg.",
            "details": {"min_qty_kg": 250}}}
```

`details` solo aparece cuando hay algo accionable dentro: en el ejemplo,
el mínimo de kilos, para que el formulario pueda ponerlo en el campo sin
leer el texto.

| Código | Cuándo |
|---|---|
| `200` | Consulta o modificación correcta |
| `201` | Se creó un recurso |
| `202` | Se aceptó, pero no se confirma el efecto (registro, recuperación) |
| `204` | Se hizo y no hay nada que devolver |
| `400` | La petición no tiene sentido para el estado actual |
| `401` | Sin credenciales, o caducadas |
| `403` | Identificado, pero sin el permiso necesario |
| `404` | No existe, o no es tuyo y no debes saber que existe |
| `409` | Choca con el estado actual del recurso |
| `422` | La validación rechazó el cuerpo |
| `429` | Se pasó del tope de frecuencia |

---

## sistema

Comprobación de vida del servicio. Es el único endpoint sin prefijo de versión: el orquestador que lo consulta no debe tener que saber en qué versión va la API.

**1 endpoints** · 0 con token · 1 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/health` | — | Comprobación de estado |

## autenticación

Registro, verificación de correo, ingreso, renovación y recuperación de contraseña. Es el único grupo donde casi todo es público, y por eso el que más topes de frecuencia lleva.

**10 endpoints** · 2 con token · 2 con el token en el cuerpo · 6 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `POST` | `/auth/change-password` | sí | Cambiar la contraseña |
| `POST` | `/auth/login` | — | Iniciar sesión |
| `POST` | `/auth/logout` | cuerpo | Cerrar sesión |
| `GET` | `/auth/me` | sí | Perfil del usuario actual |
| `POST` | `/auth/password-reset` | — | Solicitar el restablecimiento de la contraseña |
| `POST` | `/auth/password-reset/confirm` | — | Confirmar la nueva contraseña |
| `POST` | `/auth/refresh` | cuerpo | Renovar la sesión |
| `POST` | `/auth/register` | — | Registrar una cuenta de comprador |
| `POST` | `/auth/resend-verification` | — | Reenviar el correo de verificación |
| `POST` | `/auth/verify-email` | — | Verificar el correo electrónico |

## usuarios

El perfil de quien está dentro: datos, direcciones y consentimientos. Nadie consulta aquí la cuenta de otro.

**7 endpoints** · 5 con token · 2 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/users/geo/departments` | — | Departamentos de Colombia |
| `GET` | `/users/geo/departments/{department_id}/municipalities` | — | Municipios de un departamento |
| `PATCH` | `/users/me` | sí | Editar mis datos |
| `GET` | `/users/me/addresses` | sí | Mis direcciones de entrega |
| `POST` | `/users/me/addresses` | sí | Agregar una dirección |
| `DELETE` | `/users/me/addresses/{address_id}` | sí | Eliminar una dirección |
| `PATCH` | `/users/me/addresses/{address_id}` | sí | Editar una dirección |

## catálogo

Lo que se puede comprar. Público y de solo lectura: los lotes los crea el productor desde su panel, no desde aquí.

**5 endpoints** · 2 con token · 3 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/producers` | — | Listar productores |
| `GET` | `/producers/{producer_id}` | — | Perfil público de un productor |
| `GET` | `/products` | sí | Listar cafés con filtros |
| `GET` | `/products/{slug}` | sí | Ficha completa de un café |
| `GET` | `/products/{slug}/related` | — | Cafés relacionados |

## carrito

La selección antes de pagar. Vive en el servidor y no en el navegador, porque el precio y la disponibilidad del pergamino cambian y el carrito tiene que enterarse.

**9 endpoints** · 9 con token · 0 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `DELETE` | `/cart` | sí | Vaciar el carrito |
| `GET` | `/cart` | sí | Ver el carrito |
| `POST` | `/cart/items` | sí | Agregar al carrito |
| `DELETE` | `/cart/items/{item_id}` | sí | Quitar del carrito |
| `PATCH` | `/cart/items/{item_id}` | sí | Cambiar la cantidad |
| `POST` | `/cart/merge` | sí | Fusionar el carrito anónimo tras iniciar sesión |
| `GET` | `/wishlist` | sí | Ver favoritos |
| `POST` | `/wishlist` | sí | Agregar a favoritos |
| `DELETE` | `/wishlist/{product_id}` | sí | Quitar de favoritos |

## pedidos

Lo comprado, con su estado y sus sub-órdenes. Un pedido con lotes de tres fincas genera tres sub-órdenes bajo un único número.

**6 endpoints** · 6 con token · 0 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/orders` | sí | Mis pedidos |
| `POST` | `/orders` | sí | Confirmar la compra |
| `POST` | `/orders/sub-orders/{sub_order_id}/cancel` | sí | Cancelar un pedido no despachado |
| `PATCH` | `/orders/sub-orders/{sub_order_id}/status` | sí | Actualizar el estado (vendedor) |
| `GET` | `/orders/{order_id}` | sí | Detalle del pedido |
| `GET` | `/orders/{order_id}/receipt` | sí | Descargar el comprobante en PDF |

## devoluciones

Solicitud, aprobación y seguimiento de una devolución, con los plazos que fijó la revisión legal.

**10 endpoints** · 10 con token · 0 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/orders/sub-orders/{sub_order_id}/return-eligibility` | sí | Qué puede devolverse de este pedido |
| `GET` | `/producer/returns` | sí | Devoluciones de mis ventas |
| `POST` | `/producer/returns/{return_id}/received` | sí | Confirmar que el café volvió |
| `POST` | `/producer/returns/{return_id}/refund` | sí | Registrar el reembolso |
| `POST` | `/producer/returns/{return_id}/resolution` | sí | Responder por escrito a la reclamación |
| `GET` | `/returns` | sí | Mis devoluciones |
| `POST` | `/returns` | sí | Solicitar una devolución |
| `GET` | `/returns/{return_id}` | sí | Constancia de la devolución |
| `POST` | `/returns/{return_id}/evidence` | sí | Adjuntar fotografías |
| `POST` | `/returns/{return_id}/shipped` | sí | Declarar que enviaste el café de vuelta |

## reseñas

Opiniones sobre los lotes y sobre los vendedores, solo de quien compró.

**8 endpoints** · 7 con token · 1 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/admin/reviews/reported` | sí | Cola de moderación de reseñas |
| `GET` | `/products/{product_id}/reviews` | sí | Reseñas de un café |
| `GET` | `/products/{product_id}/reviews/summary` | — | Promedio y reparto de estrellas |
| `POST` | `/reviews` | sí | Reseñar un café comprado |
| `GET` | `/reviews/pending` | sí | Cafés entregados sin reseñar |
| `DELETE` | `/reviews/{review_id}` | sí | Eliminar mi reseña |
| `PUT` | `/reviews/{review_id}` | sí | Editar mi reseña |
| `POST` | `/reviews/{review_id}/report` | sí | Reportar una reseña |

## oferta y demanda

El mercado en su segundo sentido: el comprador publica lo que busca y los caficultores responden con su precio.

**10 endpoints** · 10 con token · 0 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/demands` | sí | Mis solicitudes |
| `POST` | `/demands` | sí | Publicar lo que busco comprar |
| `POST` | `/demands/offers/{offer_id}/respond` | sí | Aceptar o rechazar una postura |
| `GET` | `/demands/{demand_id}` | sí | Detalle de mi solicitud con sus posturas |
| `PATCH` | `/demands/{demand_id}` | sí | Editar mi solicitud |
| `POST` | `/demands/{demand_id}/close` | sí | Cerrar mi solicitud |
| `GET` | `/producer/demands` | sí | Solicitudes de compra vigentes |
| `POST` | `/producer/demands/{demand_id}/offers` | sí | Responder con una postura |
| `GET` | `/producer/offers` | sí | Mis posturas enviadas |
| `POST` | `/producer/offers/{offer_id}/withdraw` | sí | Retirar una postura |

## panel del productor

Todo lo que hace un vendedor con su finca: lotes, variantes, fotos, pedidos recibidos y certificaciones. Es el grupo más grande, y se nota que es donde vive el trabajo diario.

**27 endpoints** · 27 con token · 0 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/producer/catalog` | sí | Mi catálogo, borradores incluidos |
| `POST` | `/producer/catalog` | sí | Publicar un café nuevo |
| `GET` | `/producer/catalog/{product_id}` | sí | Detalle de un café propio |
| `PUT` | `/producer/catalog/{product_id}` | sí | Editar un café propio |
| `GET` | `/producer/catalog/{product_id}/certifications` | sí | Certificaciones declaradas en un café |
| `DELETE` | `/producer/catalog/{product_id}/certifications/{certification_id}` | sí | Quitar una certificación del café |
| `POST` | `/producer/catalog/{product_id}/certifications/{certification_id}` | sí | Asociar una certificación al café |
| `POST` | `/producer/catalog/{product_id}/images` | sí | Subir una fotografía del café |
| `DELETE` | `/producer/catalog/{product_id}/images/{image_id}` | sí | Eliminar una fotografía |
| `POST` | `/producer/catalog/{product_id}/publish` | sí | Sacar el café al catálogo |
| `POST` | `/producer/catalog/{product_id}/unpublish` | sí | Retirar el café del catálogo |
| `POST` | `/producer/catalog/{product_id}/variants` | sí | Agregar una presentación |
| `DELETE` | `/producer/catalog/{product_id}/variants/{variant_id}` | sí | Retirar una presentación |
| `PUT` | `/producer/catalog/{product_id}/variants/{variant_id}` | sí | Editar una presentación |
| `GET` | `/producer/certifications` | sí | Mis certificaciones y su vigencia |
| `POST` | `/producer/certifications` | sí | Registrar una certificación |
| `GET` | `/producer/certifications/catalog` | sí | Certificaciones que puedo declarar |
| `DELETE` | `/producer/certifications/{certification_id}` | sí | Eliminar una certificación |
| `GET` | `/producer/certifications/{certification_id}/document` | sí | Enlace temporal al documento |
| `GET` | `/producer/dashboard` | sí | Resumen del productor |
| `GET` | `/producer/inventory/alerts` | sí | Alertas de bajo inventario |
| `PATCH` | `/producer/inventory/{variant_id}` | sí | Actualizar el stock de una presentación |
| `GET` | `/producer/orders` | sí | Pedidos recibidos |
| `GET` | `/producer/products` | sí | Mis productos |
| `GET` | `/producer/profile` | sí | Datos de mi negocio |
| `PUT` | `/producer/profile` | sí | Actualizar los datos de mi negocio |
| `GET` | `/producer/settlements/summary` | sí | Resumen de liquidación pendiente |

## liquidaciones

El dinero de vuelta al vendedor: cuentas bancarias, cierre de periodo y pago. Es lo más reciente de la API.

**7 endpoints** · 7 con token · 0 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/admin/settlements` | sí | Liquidaciones de todos los vendedores |
| `POST` | `/admin/settlements/close` | sí | Cerrar un periodo y generar las liquidaciones |
| `POST` | `/admin/settlements/{settlement_id}/pay` | sí | Dejar constancia del desembolso |
| `DELETE` | `/producer/bank-account` | sí | Retirar la cuenta registrada |
| `GET` | `/producer/bank-account` | sí | Cuenta registrada, con el número enmascarado |
| `PUT` | `/producer/bank-account` | sí | Registrar o actualizar la cuenta donde cobrar |
| `GET` | `/producer/settlements` | sí | Historial de liquidaciones del vendedor |

## administración

Aprobación de vendedores, moderación y parámetros. Todo exige el permiso explícito, no basta el rol.

**7 endpoints** · 7 con token · 0 públicos

| Método | Ruta | Token | Qué hace |
|---|---|:---:|---|
| `GET` | `/admin/audit-logs` | sí | Registro de auditoría |
| `GET` | `/admin/dashboard` | sí | Panel general |
| `GET` | `/admin/producers/pending` | sí | Vendedores pendientes de aprobación |
| `POST` | `/admin/producers/{producer_id}/review` | sí | Aprobar o rechazar un vendedor |
| `POST` | `/admin/reviews/{review_id}/moderate` | sí | Moderar una reseña |
| `GET` | `/admin/users` | sí | Cuentas de la plataforma |
| `POST` | `/admin/users/{user_id}/suspend` | sí | Suspender o reactivar una cuenta |

---

## Cómo regenerar este archivo

```bash
docker compose up -d
curl -s http://localhost:8000/openapi.json > openapi.json
python3 entregas/GA7/AA5_EV03_APIs_Proyecto/generar_endpoints.py openapi.json \
        entregas/GA7/AA5_EV03_APIs_Proyecto/ENDPOINTS.md
```

La documentación interactiva del mismo documento está en
<http://localhost:8000/docs> (Swagger UI) y <http://localhost:8000/redoc>.
