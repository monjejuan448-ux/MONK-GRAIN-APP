# MÓDULOS INTEGRADOS — datos de entrada y salida

**GA8-220501096-AA1-EV02**

107 endpoints en 12 módulos. Para cada uno: qué recibe,
qué devuelve y qué pruebas lo cubren.

> **Este archivo se genera.** Sale del documento OpenAPI que publica el
> servicio en marcha y del XML de JUnit que produce `pytest`, con
> `generar_modulos.py`. Ni los campos ni los números de prueba se
> escriben a mano: así no pueden decir una cosa distinta del código.

Convenciones de las tablas:

| | |
|---|---|
| `texto?` | admite vacío (`null`) |
| **ob.** | obligatorio |
| `· campo` | campo dentro del cuerpo |

---

## Resumen

| Módulo | Paquete | Endpoints | Pruebas | Fallos |
|---|---|---:|---:|---:|
| [sistema](#sistema) | `app/main.py` | 1 | 3 | 0 |
| [autenticación](#autenticación) | `app/modules/auth/` | 10 | 38 | 0 |
| [usuarios](#usuarios) | `app/modules/users/` | 7 | 36 | 0 |
| [catálogo](#catálogo) | `app/modules/catalog/` | 5 | 40 | 0 |
| [carrito](#carrito) | `app/modules/cart/` | 9 | 29 | 0 |
| [pedidos](#pedidos) | `app/modules/orders/` | 6 | 29 | 0 |
| [devoluciones](#devoluciones) | `app/modules/returns/` | 10 | 32 | 0 |
| [reseñas](#reseñas) | `app/modules/reviews/` | 8 | 25 | 0 |
| [oferta y demanda](#oferta-y-demanda) | `app/modules/trading/` | 10 | 40 | 0 |
| [panel del productor](#panel-del-productor) | `app/modules/producers/` | 27 | 63 | 0 |
| [liquidaciones](#liquidaciones) | `app/modules/payments/` | 7 | 27 | 0 |
| [administración](#administración) | `app/modules/admin/` | 7 | 21 | 0 |

La columna «Pruebas» suma **383** y las ejecutadas son
**453**. La diferencia tiene dos causas, ninguna de ellas un
error de cuenta:

- `test_checkout.py` (18 pruebas) cuenta en dos módulos —carrito y pedidos— porque recorre el paso de uno al otro. Sumado dos veces, infla la columna en 18.
- 88 pruebas no pertenecen a ningún módulo de dominio: verifican `app/core/` —seguridad, catálogo DANE, archivos, días hábiles— y el mapeo de los modelos. Son `test_business_days.py` (12), `test_divipola.py` (17), `test_files.py` (14), `test_models_mapping.py` (26), `test_security.py` (19).

Cuadra así: 383 − 18 + 88 = 453.

---

## sistema

**Paquete:** `app/main.py`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_performance.py` | 3 | 0 | 0.6 |

### `GET /health`

Comprobación de estado.

**Entrada:** nada.

**Salida** · `200` · `objeto`

## autenticación

**Paquete:** `app/modules/auth/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_auth_flow.py` | 19 | 0 | 3.1 |
| `tests/**/test_rate_limit.py` | 19 | 0 | 13.1 |

### `POST /auth/change-password`

Cambiar la contraseña.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ChangePasswordRequest` | *application/json* | **ob.** |
|   · password | texto | **ob.** |
|   · current_password | texto | **ob.** |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `POST /auth/login`

Iniciar sesión.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `LoginRequest` | *application/json* | **ob.** |
|   · email | texto | **ob.** |
|   · password | texto | **ob.** |

**Salida** · `200` · `TokenResponse`

| Campo | Tipo |
|---|---|
| access_token | texto |
| refresh_token | texto |
| token_type | texto |
| expires_at | texto |

### `POST /auth/logout`

Cerrar sesión.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `RefreshRequest` | *application/json* | **ob.** |
|   · refresh_token | texto | **ob.** |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `GET /auth/me`

Perfil del usuario actual.

**Entrada:** nada.

**Salida** · `200` · `CurrentUserResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| email | texto |
| full_name | texto |
| phone | texto? |
| avatar_key | texto? |
| status | texto |
| locale | texto |
| email_notifications_enabled | sí/no |
| roles | lista de RoleResponse |
| permissions | lista de texto |
| created_at | texto |

### `POST /auth/password-reset`

Solicitar el restablecimiento de la contraseña.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `PasswordResetRequest` | *application/json* | **ob.** |
|   · email | texto | **ob.** |

**Salida** · `202` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `POST /auth/password-reset/confirm`

Confirmar la nueva contraseña.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `PasswordResetConfirm` | *application/json* | **ob.** |
|   · password | texto | **ob.** |
|   · token | texto | **ob.** |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `POST /auth/refresh`

Renovar la sesión.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `RefreshRequest` | *application/json* | **ob.** |
|   · refresh_token | texto | **ob.** |

**Salida** · `200` · `TokenResponse`

| Campo | Tipo |
|---|---|
| access_token | texto |
| refresh_token | texto |
| token_type | texto |
| expires_at | texto |

### `POST /auth/register`

Registrar una cuenta de comprador.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `RegisterRequest` | *application/json* | **ob.** |
|   · password | texto | **ob.** |
|   · email | texto | **ob.** |
|   · full_name | texto | **ob.** |
|   · phone | texto? |  |
|   · data_consent | sí/no | **ob.** |

**Salida** · `202` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `POST /auth/resend-verification`

Reenviar el correo de verificación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ResendVerificationRequest` | *application/json* | **ob.** |
|   · email | texto | **ob.** |

**Salida** · `202` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `POST /auth/verify-email`

Verificar el correo electrónico.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `VerifyEmailRequest` | *application/json* | **ob.** |
|   · token | texto | **ob.** |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

## usuarios

**Paquete:** `app/modules/users/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_profile.py` | 11 | 0 | 2.3 |
| `tests/**/test_addresses.py` | 25 | 0 | 7.6 |

### `GET /users/geo/departments`

Departamentos de Colombia.

**Entrada:** nada.

**Salida** · `200` · `lista de DepartmentResponse`

### `GET /users/geo/departments/{department_id}/municipalities`

Municipios de un departamento.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| department_id *(ruta)* | entero | **ob.** |

**Salida** · `200` · `lista de MunicipalityResponse`

### `PATCH /users/me`

Editar mis datos.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ProfileUpdate` | *application/json* | **ob.** |
|   · full_name | texto? |  |
|   · phone | texto? |  |
|   · email_notifications_enabled | sí/no? |  |

**Salida** · `200` · `ProfileResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| email | texto |
| full_name | texto |
| phone | texto? |
| email_notifications_enabled | sí/no |

### `GET /users/me/addresses`

Mis direcciones de entrega.

**Entrada:** nada.

**Salida** · `200` · `lista de AddressResponse`

### `POST /users/me/addresses`

Agregar una dirección.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `AddressCreate` | *application/json* | **ob.** |
|   · label | texto? |  |
|   · recipient_name | texto | **ob.** |
|   · phone | texto | **ob.** |
|   · municipality_id | entero | **ob.** |
|   · street_address | texto | **ob.** |
|   · neighborhood | texto? |  |
|   · notes | texto? |  |
|   · is_default | sí/no |  |

**Salida** · `201` · `AddressResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| label | texto? |
| recipient_name | texto |
| phone | texto |
| street_address | texto |
| neighborhood | texto? |
| notes | texto? |
| municipality_id | entero |
| department_id | entero |
| is_default | sí/no |

### `PATCH /users/me/addresses/{address_id}`

Editar una dirección.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| address_id *(ruta)* | texto | **ob.** |
| **cuerpo** `AddressUpdate` | *application/json* | **ob.** |
|   · label | texto? |  |
|   · recipient_name | texto? |  |
|   · phone | texto? |  |
|   · municipality_id | entero? |  |
|   · street_address | texto? |  |
|   · neighborhood | texto? |  |
|   · notes | texto? |  |
|   · is_default | sí/no? |  |

**Salida** · `200` · `AddressResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| label | texto? |
| recipient_name | texto |
| phone | texto |
| street_address | texto |
| neighborhood | texto? |
| notes | texto? |
| municipality_id | entero |
| department_id | entero |
| is_default | sí/no |

### `DELETE /users/me/addresses/{address_id}`

Eliminar una dirección.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| address_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

## catálogo

**Paquete:** `app/modules/catalog/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_catalog.py` | 20 | 0 | 3.7 |
| `tests/**/test_pergamino.py` | 20 | 0 | 4.7 |

### `GET /producers`

Listar productores.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| department *(consulta)* | texto? |  |
| region *(consulta)* | texto? |  |
| type *(consulta)* | texto? |  |
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ProducerListItem_`

| Campo | Tipo |
|---|---|
| items | lista de ProducerListItem |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /producers/{producer_id}`

Perfil público de un productor.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| producer_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ProducerDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| legal_name | texto |
| brand_name | texto? |
| type | texto |
| logo_key | texto? |
| cover_key | texto? |
| story | texto? |
| municipality | texto? |
| department | texto? |
| rating_avg | texto |
| rating_count | entero |
| product_count | entero |
| farms | lista de FarmSummary |
| certifications | lista de CertificationResponse |
| *… y 1 más* | |

### `GET /products`

Listar cafés con filtros.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| q *(consulta)* | texto? |  |
| department *(consulta)* | texto? |  |
| municipality *(consulta)* | texto? |  |
| region *(consulta)* | texto? |  |
| variety *(consulta)* | texto? |  |
| process *(consulta)* | CoffeeProcess? |  |
| certification *(consulta)* | texto? |  |
| producer_id *(consulta)* | texto? |  |
| min_price *(consulta)* | decimal? |  |
| max_price *(consulta)* | decimal? |  |
| max_yield_factor *(consulta)* | decimal? |  |
| max_moisture_pct *(consulta)* | decimal? |  |
| min_available_kg *(consulta)* | entero? |  |
| sort *(consulta)* | texto |  |
| *… y 2 más* | | |

**Salida** · `200` · `Page_ProductListItem_`

| Campo | Tipo |
|---|---|
| items | lista de ProductListItem |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /products/{slug}`

Ficha completa de un café.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| slug *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| state | CoffeeState |
| base_price | texto |
| currency | texto |
| primary_image_url | texto? |
| producer | ProducerSummary |
| region | texto? |
| municipality | texto? |
| department | texto? |
| yield_factor | texto? |
| moisture_pct | texto? |
| available_kg | entero |
| *… y 14 más* | |

### `GET /products/{slug}/related`

Cafés relacionados.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| slug *(ruta)* | texto | **ob.** |

**Salida** · `200` · `lista de ProductListItem`

## carrito

**Paquete:** `app/modules/cart/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_checkout.py` | 18 | 0 | 6.2 |
| `tests/**/test_wishlist.py` | 11 | 0 | 3.3 |

### `GET /cart`

Ver el carrito.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| coupon *(consulta)* | texto? |  |

**Salida** · `200` · `CartResponse`

| Campo | Tipo |
|---|---|
| id | texto? |
| groups | lista de CartSellerGroup |
| item_count | entero |
| subtotal | texto |
| shipping_total | texto |
| discount_total | texto |
| grand_total | texto |
| currency | texto |
| coupon | AppliedCoupon? |
| has_warnings | sí/no |

### `DELETE /cart`

Vaciar el carrito.

**Entrada:** nada.

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `POST /cart/items`

Agregar al carrito.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `CartItemAdd` | *application/json* | **ob.** |
|   · variant_id | texto | **ob.** |
|   · quantity | entero | **ob.** |

**Salida** · `201` · `CartResponse`

| Campo | Tipo |
|---|---|
| id | texto? |
| groups | lista de CartSellerGroup |
| item_count | entero |
| subtotal | texto |
| shipping_total | texto |
| discount_total | texto |
| grand_total | texto |
| currency | texto |
| coupon | AppliedCoupon? |
| has_warnings | sí/no |

### `PATCH /cart/items/{item_id}`

Cambiar la cantidad.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| item_id *(ruta)* | texto | **ob.** |
| **cuerpo** `CartItemUpdate` | *application/json* | **ob.** |
|   · quantity | entero | **ob.** |

**Salida** · `200` · `CartResponse`

| Campo | Tipo |
|---|---|
| id | texto? |
| groups | lista de CartSellerGroup |
| item_count | entero |
| subtotal | texto |
| shipping_total | texto |
| discount_total | texto |
| grand_total | texto |
| currency | texto |
| coupon | AppliedCoupon? |
| has_warnings | sí/no |

### `DELETE /cart/items/{item_id}`

Quitar del carrito.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| item_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `CartResponse`

| Campo | Tipo |
|---|---|
| id | texto? |
| groups | lista de CartSellerGroup |
| item_count | entero |
| subtotal | texto |
| shipping_total | texto |
| discount_total | texto |
| grand_total | texto |
| currency | texto |
| coupon | AppliedCoupon? |
| has_warnings | sí/no |

### `POST /cart/merge`

Fusionar el carrito anónimo tras iniciar sesión.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** | lista de CartItemAdd | **ob.** |

**Salida** · `200` · `CartResponse`

| Campo | Tipo |
|---|---|
| id | texto? |
| groups | lista de CartSellerGroup |
| item_count | entero |
| subtotal | texto |
| shipping_total | texto |
| discount_total | texto |
| grand_total | texto |
| currency | texto |
| coupon | AppliedCoupon? |
| has_warnings | sí/no |

### `GET /wishlist`

Ver favoritos.

**Entrada:** nada.

**Salida** · `200` · `lista de WishlistItemResponse`

### `POST /wishlist`

Agregar a favoritos.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `WishlistItemAdd` | *application/json* | **ob.** |
|   · product_id | texto | **ob.** |

**Salida** · `201` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `DELETE /wishlist/{product_id}`

Quitar de favoritos.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

## pedidos

**Paquete:** `app/modules/orders/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_checkout.py` | 18 | 0 | 6.2 |
| `tests/**/test_receipt.py` | 11 | 0 | 8.2 |

### `POST /orders`

Confirmar la compra.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `CheckoutRequest` | *application/json* | **ob.** |
|   · shipping_address_id | texto | **ob.** |
|   · payment_method | PaymentMethod |  |
|   · coupon_code | texto? |  |
|   · customer_notes | texto? |  |
|   · accept_terms | sí/no | **ob.** |

**Salida** · `201` · `CheckoutResponse`

| Campo | Tipo |
|---|---|
| order | OrderDetail |
| payment_reference | texto? |
| payment_redirect_url | texto? |
| message | texto |

### `GET /orders`

Mis pedidos.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_OrderSummary_`

| Campo | Tipo |
|---|---|
| items | lista de OrderSummary |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /orders/sub-orders/{sub_order_id}/cancel`

Cancelar un pedido no despachado.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| sub_order_id *(ruta)* | texto | **ob.** |
| **cuerpo** `OrderCancelRequest` | *application/json* | **ob.** |
|   · reason | texto | **ob.** |

**Salida** · `200` · `SubOrderResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| sub_order_number | texto |
| producer_id | texto |
| producer_name | texto |
| status | SubOrderStatus |
| subtotal | texto |
| shipping_cost | texto |
| items | lista de OrderItemResponse |
| shipment | ShipmentResponse? |
| cancellation_reason | texto? |
| is_cancellable | sí/no |
| created_at | texto |

### `PATCH /orders/sub-orders/{sub_order_id}/status`

Actualizar el estado (vendedor).

**Entrada**

| Dato | Tipo | |
|---|---|---|
| sub_order_id *(ruta)* | texto | **ob.** |
| **cuerpo** `SubOrderStatusUpdate` | *application/json* | **ob.** |
|   · status | SubOrderStatus | **ob.** |
|   · note | texto? |  |
|   · carrier | texto? |  |
|   · tracking_number | texto? |  |

**Salida** · `200` · `SubOrderResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| sub_order_number | texto |
| producer_id | texto |
| producer_name | texto |
| status | SubOrderStatus |
| subtotal | texto |
| shipping_cost | texto |
| items | lista de OrderItemResponse |
| shipment | ShipmentResponse? |
| cancellation_reason | texto? |
| is_cancellable | sí/no |
| created_at | texto |

### `GET /orders/{order_id}`

Detalle del pedido.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| order_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `OrderDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| order_number | texto |
| status | OrderStatus |
| subtotal | texto |
| shipping_total | texto |
| discount_total | texto |
| grand_total | texto |
| currency | texto |
| shipping_address | objeto |
| customer_notes | texto? |
| sub_orders | lista de SubOrderResponse |
| payment | PaymentResponse? |
| placed_at | texto |

### `GET /orders/{order_id}/receipt`

Descargar el comprobante en PDF.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| order_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `—`

## devoluciones

**Paquete:** `app/modules/returns/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_returns.py` | 32 | 0 | 21.9 |

### `GET /orders/sub-orders/{sub_order_id}/return-eligibility`

Qué puede devolverse de este pedido.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| sub_order_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ReturnEligibility`

| Campo | Tipo |
|---|---|
| sub_order_id | texto |
| sub_order_number | texto |
| can_request | sí/no |
| allowed_reasons | lista de ReturnReason |
| withdrawal_deadline | texto? |
| warranty_deadline | texto? |
| delivered_at | texto? |
| items | lista de ReturnableItem |
| blocked_reason | texto? |

### `GET /producer/returns`

Devoluciones de mis ventas.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ReturnSummary_`

| Campo | Tipo |
|---|---|
| items | lista de ReturnSummary |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /producer/returns/{return_id}/received`

Confirmar que el café volvió.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| return_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ReturnDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| return_number | texto |
| sub_order_id | texto |
| sub_order_number | texto |
| order_number | texto |
| producer_name | texto |
| reason | ReturnReason |
| reason_label | texto |
| description | texto? |
| status | ReturnStatus |
| declared_unopened | sí/no |
| refund_amount | texto? |
| return_shipping_paid_by_seller | sí/no |
| response_due_at | texto |
| *… y 8 más* | |

### `POST /producer/returns/{return_id}/refund`

Registrar el reembolso.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| return_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ReturnDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| return_number | texto |
| sub_order_id | texto |
| sub_order_number | texto |
| order_number | texto |
| producer_name | texto |
| reason | ReturnReason |
| reason_label | texto |
| description | texto? |
| status | ReturnStatus |
| declared_unopened | sí/no |
| refund_amount | texto? |
| return_shipping_paid_by_seller | sí/no |
| response_due_at | texto |
| *… y 8 más* | |

### `POST /producer/returns/{return_id}/resolution`

Responder por escrito a la reclamación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| return_id *(ruta)* | texto | **ob.** |
| **cuerpo** `ReturnResolutionInput` | *application/json* | **ob.** |
|   · approve | sí/no | **ob.** |
|   · resolution_notes | texto | **ob.** |

**Salida** · `200` · `ReturnDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| return_number | texto |
| sub_order_id | texto |
| sub_order_number | texto |
| order_number | texto |
| producer_name | texto |
| reason | ReturnReason |
| reason_label | texto |
| description | texto? |
| status | ReturnStatus |
| declared_unopened | sí/no |
| refund_amount | texto? |
| return_shipping_paid_by_seller | sí/no |
| response_due_at | texto |
| *… y 8 más* | |

### `POST /returns`

Solicitar una devolución.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ReturnRequestInput` | *application/json* | **ob.** |
|   · sub_order_id | texto | **ob.** |
|   · reason | ReturnReason | **ob.** |
|   · description | texto? |  |
|   · items | lista de ReturnItemInput | **ob.** |
|   · declared_unopened | sí/no |  |

**Salida** · `201` · `ReturnDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| return_number | texto |
| sub_order_id | texto |
| sub_order_number | texto |
| order_number | texto |
| producer_name | texto |
| reason | ReturnReason |
| reason_label | texto |
| description | texto? |
| status | ReturnStatus |
| declared_unopened | sí/no |
| refund_amount | texto? |
| return_shipping_paid_by_seller | sí/no |
| response_due_at | texto |
| *… y 8 más* | |

### `GET /returns`

Mis devoluciones.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ReturnSummary_`

| Campo | Tipo |
|---|---|
| items | lista de ReturnSummary |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /returns/{return_id}`

Constancia de la devolución.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| return_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ReturnDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| return_number | texto |
| sub_order_id | texto |
| sub_order_number | texto |
| order_number | texto |
| producer_name | texto |
| reason | ReturnReason |
| reason_label | texto |
| description | texto? |
| status | ReturnStatus |
| declared_unopened | sí/no |
| refund_amount | texto? |
| return_shipping_paid_by_seller | sí/no |
| response_due_at | texto |
| *… y 8 más* | |

### `POST /returns/{return_id}/evidence`

Adjuntar fotografías.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| return_id *(ruta)* | texto | **ob.** |
| **cuerpo** `Body_upload_evidence_api_v1_returns__return_id__evidence_post` | *multipart/form-data* | **ob.** |
|   · files | lista de texto | **ob.** |

**Salida** · `201` · `ReturnDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| return_number | texto |
| sub_order_id | texto |
| sub_order_number | texto |
| order_number | texto |
| producer_name | texto |
| reason | ReturnReason |
| reason_label | texto |
| description | texto? |
| status | ReturnStatus |
| declared_unopened | sí/no |
| refund_amount | texto? |
| return_shipping_paid_by_seller | sí/no |
| response_due_at | texto |
| *… y 8 más* | |

### `POST /returns/{return_id}/shipped`

Declarar que enviaste el café de vuelta.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| return_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ReturnDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| return_number | texto |
| sub_order_id | texto |
| sub_order_number | texto |
| order_number | texto |
| producer_name | texto |
| reason | ReturnReason |
| reason_label | texto |
| description | texto? |
| status | ReturnStatus |
| declared_unopened | sí/no |
| refund_amount | texto? |
| return_shipping_paid_by_seller | sí/no |
| response_due_at | texto |
| *… y 8 más* | |

## reseñas

**Paquete:** `app/modules/reviews/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_reviews.py` | 25 | 0 | 16.6 |

### `GET /admin/reviews/reported`

Cola de moderación de reseñas.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ReportedReview_`

| Campo | Tipo |
|---|---|
| items | lista de ReportedReview |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /products/{product_id}/reviews`

Reseñas de un café.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ReviewDetail_`

| Campo | Tipo |
|---|---|
| items | lista de ReviewDetail |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /products/{product_id}/reviews/summary`

Promedio y reparto de estrellas.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ReviewSummary`

| Campo | Tipo |
|---|---|
| rating_avg | decimal |
| rating_count | entero |
| distribution | objeto |

### `POST /reviews`

Reseñar un café comprado.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ReviewInput` | *application/json* | **ob.** |
|   · order_item_id | texto | **ob.** |
|   · rating | entero | **ob.** |
|   · comment | texto? |  |

**Salida** · `201` · `ReviewDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| product_id | texto |
| rating | entero |
| comment | texto? |
| author_name | texto |
| created_at | texto |
| updated_at | texto |
| is_verified_purchase | sí/no |
| can_edit | sí/no |
| is_mine | sí/no |

### `GET /reviews/pending`

Cafés entregados sin reseñar.

**Entrada:** nada.

**Salida** · `200` · `lista de PendingReview`

### `PUT /reviews/{review_id}`

Editar mi reseña.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| review_id *(ruta)* | texto | **ob.** |
| **cuerpo** `ReviewUpdate` | *application/json* | **ob.** |
|   · rating | entero | **ob.** |
|   · comment | texto? |  |

**Salida** · `200` · `ReviewDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| product_id | texto |
| rating | entero |
| comment | texto? |
| author_name | texto |
| created_at | texto |
| updated_at | texto |
| is_verified_purchase | sí/no |
| can_edit | sí/no |
| is_mine | sí/no |

### `DELETE /reviews/{review_id}`

Eliminar mi reseña.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| review_id *(ruta)* | texto | **ob.** |

**Salida** · `204` · `sin cuerpo`

### `POST /reviews/{review_id}/report`

Reportar una reseña.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| review_id *(ruta)* | texto | **ob.** |
| **cuerpo** `ReviewReportInput` | *application/json* | **ob.** |
|   · reason | texto | **ob.** |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

## oferta y demanda

**Paquete:** `app/modules/trading/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_trading.py` | 40 | 0 | 16.1 |

### `POST /demands`

Publicar lo que busco comprar.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `DemandCreate` | *application/json* | **ob.** |
|   · title | texto | **ob.** |
|   · description | texto? |  |
|   · wanted_kg | entero | **ob.** |
|   · max_yield_factor | decimal? |  |
|   · max_moisture_pct | decimal? |  |
|   · variety | texto? |  |
|   · process | CoffeeProcess? |  |
|   · municipality_id | entero? |  |
|   · offered_price_per_kg | decimal? |  |
|   · expires_on | texto | **ob.** |

**Salida** · `201` · `DemandDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| title | texto |
| buyer_name | texto |
| wanted_kg | entero |
| covered_kg | entero |
| remaining_kg | entero |
| max_yield_factor | texto? |
| max_moisture_pct | texto? |
| variety | texto? |
| process | CoffeeProcess? |
| municipality | texto? |
| department | texto? |
| offered_price_per_kg | texto? |
| expires_on | texto |
| *… y 6 más* | |

### `GET /demands`

Mis solicitudes.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_DemandSummary_`

| Campo | Tipo |
|---|---|
| items | lista de DemandSummary |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /demands/offers/{offer_id}/respond`

Aceptar o rechazar una postura.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| offer_id *(ruta)* | texto | **ob.** |
| **cuerpo** `OfferRespond` | *application/json* | **ob.** |
|   · accept | sí/no | **ob.** |
|   · note | texto? |  |

**Salida** · `200` · `DemandDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| title | texto |
| buyer_name | texto |
| wanted_kg | entero |
| covered_kg | entero |
| remaining_kg | entero |
| max_yield_factor | texto? |
| max_moisture_pct | texto? |
| variety | texto? |
| process | CoffeeProcess? |
| municipality | texto? |
| department | texto? |
| offered_price_per_kg | texto? |
| expires_on | texto |
| *… y 6 más* | |

### `GET /demands/{demand_id}`

Detalle de mi solicitud con sus posturas.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| demand_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `DemandDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| title | texto |
| buyer_name | texto |
| wanted_kg | entero |
| covered_kg | entero |
| remaining_kg | entero |
| max_yield_factor | texto? |
| max_moisture_pct | texto? |
| variety | texto? |
| process | CoffeeProcess? |
| municipality | texto? |
| department | texto? |
| offered_price_per_kg | texto? |
| expires_on | texto |
| *… y 6 más* | |

### `PATCH /demands/{demand_id}`

Editar mi solicitud.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| demand_id *(ruta)* | texto | **ob.** |
| **cuerpo** `DemandUpdate` | *application/json* | **ob.** |
|   · title | texto? |  |
|   · description | texto? |  |
|   · offered_price_per_kg | decimal? |  |
|   · expires_on | texto? |  |

**Salida** · `200` · `DemandDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| title | texto |
| buyer_name | texto |
| wanted_kg | entero |
| covered_kg | entero |
| remaining_kg | entero |
| max_yield_factor | texto? |
| max_moisture_pct | texto? |
| variety | texto? |
| process | CoffeeProcess? |
| municipality | texto? |
| department | texto? |
| offered_price_per_kg | texto? |
| expires_on | texto |
| *… y 6 más* | |

### `POST /demands/{demand_id}/close`

Cerrar mi solicitud.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| demand_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `DemandDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| title | texto |
| buyer_name | texto |
| wanted_kg | entero |
| covered_kg | entero |
| remaining_kg | entero |
| max_yield_factor | texto? |
| max_moisture_pct | texto? |
| variety | texto? |
| process | CoffeeProcess? |
| municipality | texto? |
| department | texto? |
| offered_price_per_kg | texto? |
| expires_on | texto |
| *… y 6 más* | |

### `GET /producer/demands`

Solicitudes de compra vigentes.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| only_matching *(consulta)* | sí/no |  |
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_DemandSummary_`

| Campo | Tipo |
|---|---|
| items | lista de DemandSummary |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /producer/demands/{demand_id}/offers`

Responder con una postura.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| demand_id *(ruta)* | texto | **ob.** |
| **cuerpo** `OfferCreate` | *application/json* | **ob.** |
|   · variant_id | texto | **ob.** |
|   · offered_kg | entero | **ob.** |
|   · price_per_kg | decimal | **ob.** |
|   · message | texto? |  |

**Salida** · `201` · `MyOfferSummary`

| Campo | Tipo |
|---|---|
| id | texto |
| demand_id | texto |
| demand_title | texto |
| buyer_name | texto |
| wanted_kg | entero |
| product_name | texto |
| presentation | texto |
| offered_kg | entero |
| price_per_kg | texto |
| line_total | texto |
| status | OfferStatus |
| response_note | texto? |
| demand_expires_on | texto |
| created_at | texto |
| *… y 1 más* | |

### `GET /producer/offers`

Mis posturas enviadas.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_MyOfferSummary_`

| Campo | Tipo |
|---|---|
| items | lista de MyOfferSummary |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /producer/offers/{offer_id}/withdraw`

Retirar una postura.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| offer_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `MyOfferSummary`

| Campo | Tipo |
|---|---|
| id | texto |
| demand_id | texto |
| demand_title | texto |
| buyer_name | texto |
| wanted_kg | entero |
| product_name | texto |
| presentation | texto |
| offered_kg | entero |
| price_per_kg | texto |
| line_total | texto |
| status | OfferStatus |
| response_note | texto? |
| demand_expires_on | texto |
| created_at | texto |
| *… y 1 más* | |

## panel del productor

**Paquete:** `app/modules/producers/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_producer_catalog.py` | 25 | 0 | 7.5 |
| `tests/**/test_certifications.py` | 19 | 0 | 5.2 |
| `tests/**/test_fulfillment.py` | 19 | 0 | 9.7 |

### `GET /producer/catalog`

Mi catálogo, borradores incluidos.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ProducerProductDetail_`

| Campo | Tipo |
|---|---|
| items | lista de ProducerProductDetail |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /producer/catalog`

Publicar un café nuevo.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ProductInput` | *application/json* | **ob.** |
|   · name | texto | **ob.** |
|   · description | texto | **ob.** |
|   · state | CoffeeState |  |
|   · base_price | decimal | **ob.** |
|   · wholesale_price | decimal? |  |
|   · wholesale_min_qty | entero? |  |
|   · farm_id | texto? |  |
|   · category_id | entero? |  |
|   · dispatch_days | entero |  |
|   · storage_conditions | texto? |  |
|   · allows_samples | sí/no |  |
|   · attributes | CoffeeAttributesInput-Input |  |

**Salida** · `201` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `GET /producer/catalog/{product_id}`

Detalle de un café propio.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `PUT /producer/catalog/{product_id}`

Editar un café propio.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| **cuerpo** `ProductInput` | *application/json* | **ob.** |
|   · name | texto | **ob.** |
|   · description | texto | **ob.** |
|   · state | CoffeeState |  |
|   · base_price | decimal | **ob.** |
|   · wholesale_price | decimal? |  |
|   · wholesale_min_qty | entero? |  |
|   · farm_id | texto? |  |
|   · category_id | entero? |  |
|   · dispatch_days | entero |  |
|   · storage_conditions | texto? |  |
|   · allows_samples | sí/no |  |
|   · attributes | CoffeeAttributesInput-Input |  |

**Salida** · `200` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `GET /producer/catalog/{product_id}/certifications`

Certificaciones declaradas en un café.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `lista de CertificationCatalogItem`

### `POST /producer/catalog/{product_id}/certifications/{certification_id}`

Asociar una certificación al café.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| certification_id *(ruta)* | entero | **ob.** |

**Salida** · `200` · `lista de CertificationCatalogItem`

### `DELETE /producer/catalog/{product_id}/certifications/{certification_id}`

Quitar una certificación del café.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| certification_id *(ruta)* | entero | **ob.** |

**Salida** · `200` · `lista de CertificationCatalogItem`

### `POST /producer/catalog/{product_id}/images`

Subir una fotografía del café.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| **cuerpo** `Body_upload_product_image_api_v1_producer_catalog__product_id__images_post` | *multipart/form-data* | **ob.** |
|   · file | texto | **ob.** |
|   · alt_text | texto? |  |

**Salida** · `201` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `DELETE /producer/catalog/{product_id}/images/{image_id}`

Eliminar una fotografía.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| image_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `POST /producer/catalog/{product_id}/publish`

Sacar el café al catálogo.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `POST /producer/catalog/{product_id}/unpublish`

Retirar el café del catálogo.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `POST /producer/catalog/{product_id}/variants`

Agregar una presentación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| **cuerpo** `VariantInput` | *application/json* | **ob.** |
|   · presentation | texto | **ob.** |
|   · min_qty_kg | entero |  |
|   · price | decimal | **ob.** |
|   · wholesale_price | decimal? |  |
|   · stock_qty | entero |  |
|   · low_stock_threshold | entero |  |
|   · is_active | sí/no |  |

**Salida** · `201` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `PUT /producer/catalog/{product_id}/variants/{variant_id}`

Editar una presentación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| variant_id *(ruta)* | texto | **ob.** |
| **cuerpo** `VariantInput` | *application/json* | **ob.** |
|   · presentation | texto | **ob.** |
|   · min_qty_kg | entero |  |
|   · price | decimal | **ob.** |
|   · wholesale_price | decimal? |  |
|   · stock_qty | entero |  |
|   · low_stock_threshold | entero |  |
|   · is_active | sí/no |  |

**Salida** · `200` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `DELETE /producer/catalog/{product_id}/variants/{variant_id}`

Retirar una presentación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| product_id *(ruta)* | texto | **ob.** |
| variant_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `ProducerProductDetail`

| Campo | Tipo |
|---|---|
| id | texto |
| slug | texto |
| name | texto |
| description | texto |
| state | CoffeeState |
| status | ProductStatus |
| base_price | texto |
| wholesale_price | texto? |
| wholesale_min_qty | entero? |
| currency | texto |
| dispatch_days | entero |
| storage_conditions | texto? |
| allows_samples | sí/no |
| images | lista de app__schemas__producer_catalog__ProductImageResponse |
| *… y 3 más* | |

### `GET /producer/certifications`

Mis certificaciones y su vigencia.

**Entrada:** nada.

**Salida** · `200` · `lista de ProducerCertificationResponse`

### `POST /producer/certifications`

Registrar una certificación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `Body_add_certification_api_v1_producer_certifications_post` | *multipart/form-data* | **ob.** |
|   · certification_id | entero | **ob.** |
|   · certificate_number | texto? |  |
|   · issued_at | texto? |  |
|   · expires_at | texto? |  |
|   · file | texto? |  |

**Salida** · `201` · `ProducerCertificationResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| certification_id | entero |
| certification_code | texto |
| certification_name | texto |
| issuing_body | texto? |
| certificate_number | texto? |
| issued_at | texto? |
| expires_at | texto? |
| status | CertStatus |
| has_document | sí/no |
| days_to_expiry | entero? |

### `GET /producer/certifications/catalog`

Certificaciones que puedo declarar.

**Entrada:** nada.

**Salida** · `200` · `lista de CertificationCatalogItem`

### `DELETE /producer/certifications/{certification_id}`

Eliminar una certificación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| certification_id *(ruta)* | texto | **ob.** |

**Salida** · `204` · `sin cuerpo`

### `GET /producer/certifications/{certification_id}/document`

Enlace temporal al documento.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| certification_id *(ruta)* | texto | **ob.** |

**Salida** · `200` · `CertificateDocumentLink`

| Campo | Tipo |
|---|---|
| url | texto |
| expires_in_seconds | entero |

### `GET /producer/dashboard`

Resumen del productor.

**Entrada:** nada.

**Salida** · `200` · `ProducerDashboard`

| Campo | Tipo |
|---|---|
| total_sales | texto |
| commission_paid | texto |
| net_earnings | texto |
| pending_orders | entero |
| orders_to_prepare | entero |
| active_products | entero |
| draft_products | entero |
| low_stock_variants | entero |
| rating_avg | texto |
| rating_count | entero |
| pending_requests | entero |
| top_products | lista de TopProduct |
| sales_by_month | lista de ProducerSalesPoint |

### `GET /producer/inventory/alerts`

Alertas de bajo inventario.

**Entrada:** nada.

**Salida** · `200` · `lista de InventoryAlert`

### `PATCH /producer/inventory/{variant_id}`

Actualizar el stock de una presentación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| variant_id *(ruta)* | texto | **ob.** |
| **cuerpo** `InventoryUpdate` | *application/json* | **ob.** |
|   · stock_qty | entero | **ob.** |
|   · low_stock_threshold | entero? |  |

**Salida** · `200` · `InventoryAlert`

| Campo | Tipo |
|---|---|
| variant_id | texto |
| product_name | texto |
| variant_label | texto |
| available_qty | entero |
| low_stock_threshold | entero |

### `GET /producer/orders`

Pedidos recibidos.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| status *(consulta)* | SubOrderStatus? |  |
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ProducerOrderItem_`

| Campo | Tipo |
|---|---|
| items | lista de ProducerOrderItem |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /producer/products`

Mis productos.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_ProducerProductItem_`

| Campo | Tipo |
|---|---|
| items | lista de ProducerProductItem |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /producer/profile`

Datos de mi negocio.

**Entrada:** nada.

**Salida** · `200` · `ProducerProfileResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| legal_name | texto |
| brand_name | texto? |
| type | texto |
| status | texto |
| story | texto? |
| notification_address | texto? |
| contact_phone | texto? |
| production_capacity_kg | texto? |
| has_notification_data | sí/no |

### `PUT /producer/profile`

Actualizar los datos de mi negocio.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ProducerProfileUpdate` | *application/json* | **ob.** |
|   · brand_name | texto? |  |
|   · story | texto? |  |
|   · notification_address | texto? |  |
|   · contact_phone | texto? |  |
|   · production_capacity_kg | decimal? |  |

**Salida** · `200` · `ProducerProfileResponse`

| Campo | Tipo |
|---|---|
| id | texto |
| legal_name | texto |
| brand_name | texto? |
| type | texto |
| status | texto |
| story | texto? |
| notification_address | texto? |
| contact_phone | texto? |
| production_capacity_kg | texto? |
| has_notification_data | sí/no |

### `GET /producer/settlements/summary`

Resumen de liquidación pendiente.

**Entrada:** nada.

**Salida** · `200` · `SettlementSummary`

| Campo | Tipo |
|---|---|
| gross_amount | texto |
| commission_total | texto |
| net_amount | texto |
| sub_orders_count | entero |

## liquidaciones

**Paquete:** `app/modules/payments/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_settlements.py` | 27 | 0 | 13.7 |

### `GET /admin/settlements`

Liquidaciones de todos los vendedores.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| status *(consulta)* | SettlementStatus? |  |

**Salida** · `200` · `lista de AdminSettlementItem`

### `POST /admin/settlements/close`

Cerrar un periodo y generar las liquidaciones.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `ClosePeriodInput` | *application/json* | **ob.** |
|   · period_start | texto | **ob.** |
|   · period_end | texto | **ob.** |

**Salida** · `201` · `ClosePeriodResult`

| Campo | Tipo |
|---|---|
| settlements_created | entero |
| producers_settled | entero |
| sub_orders_settled | entero |
| net_total | texto |
| skipped_without_bank_account | entero |

### `POST /admin/settlements/{settlement_id}/pay`

Dejar constancia del desembolso.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| settlement_id *(ruta)* | texto | **ob.** |
| **cuerpo** `MarkPaidInput` | *application/json* | **ob.** |
|   · payment_reference | texto | **ob.** |
|   · notes | texto? |  |

**Salida** · `200` · `AdminSettlementItem`

| Campo | Tipo |
|---|---|
| id | texto |
| period_start | texto |
| period_end | texto |
| gross_amount | texto |
| commission_total | texto |
| net_amount | texto |
| status | SettlementStatus |
| paid_at | texto? |
| payment_reference | texto? |
| created_at | texto |
| producer_id | texto |
| producer_name | texto |
| sub_orders_count | entero |
| has_bank_account | sí/no |

### `GET /producer/bank-account`

Cuenta registrada, con el número enmascarado.

**Entrada:** nada.

**Salida** · `200` · `BankAccountView?`

### `PUT /producer/bank-account`

Registrar o actualizar la cuenta donde cobrar.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| **cuerpo** `BankAccountInput` | *application/json* | **ob.** |
|   · bank_name | texto | **ob.** |
|   · account_type | texto | **ob.** |
|   · account_number | texto | **ob.** |
|   · holder_name | texto | **ob.** |
|   · holder_document | texto | **ob.** |

**Salida** · `200` · `BankAccountView`

| Campo | Tipo |
|---|---|
| bank_name | texto |
| account_type | texto |
| holder_name | texto |
| masked_number | texto |
| updated_at | texto? |

### `DELETE /producer/bank-account`

Retirar la cuenta registrada.

**Entrada:** nada.

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `GET /producer/settlements`

Historial de liquidaciones del vendedor.

**Entrada:** nada.

**Salida** · `200` · `lista de ProducerSettlementItem`

## administración

**Paquete:** `app/modules/admin/`

**Pruebas que lo cubren:**

| Archivo | Pruebas | Fallos | Segundos |
|---|---:|---:|---:|
| `tests/**/test_admin.py` | 21 | 0 | 7.7 |

### `GET /admin/audit-logs`

Registro de auditoría.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| action *(consulta)* | texto? |  |
| actor_id *(consulta)* | texto? |  |
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_AuditLogEntry_`

| Campo | Tipo |
|---|---|
| items | lista de AuditLogEntry |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `GET /admin/dashboard`

Panel general.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| days *(consulta)* | entero |  |

**Salida** · `200` · `AdminDashboard`

| Campo | Tipo |
|---|---|
| total_users | entero |
| new_users_period | entero |
| pending_producers | entero |
| approved_producers | entero |
| total_products | entero |
| published_products | entero |
| orders_period | entero |
| revenue_period | texto |
| commission_period | texto |
| orders_by_status | objeto |
| reported_reviews | entero |

### `GET /admin/producers/pending`

Vendedores pendientes de aprobación.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_PendingProducerItem_`

| Campo | Tipo |
|---|---|
| items | lista de PendingProducerItem |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /admin/producers/{producer_id}/review`

Aprobar o rechazar un vendedor.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| producer_id *(ruta)* | texto | **ob.** |
| **cuerpo** `ProducerReviewDecision` | *application/json* | **ob.** |
|   · approve | sí/no | **ob.** |
|   · reason | texto? |  |

**Salida** · `200` · `PendingProducerItem`

| Campo | Tipo |
|---|---|
| id | texto |
| legal_name | texto |
| brand_name | texto? |
| type | texto |
| document_number | texto |
| contact_email | texto |
| contact_name | texto |
| municipality | texto? |
| department | texto? |
| production_capacity_kg | texto? |
| status | ProducerStatus |
| created_at | texto |

### `POST /admin/reviews/{review_id}/moderate`

Moderar una reseña.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| review_id *(ruta)* | texto | **ob.** |
| **cuerpo** `ModerateReviewRequest` | *application/json* | **ob.** |
|   · hide | sí/no | **ob.** |
|   · reason | texto? |  |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

### `GET /admin/users`

Cuentas de la plataforma.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| q *(consulta)* | texto? |  |
| status *(consulta)* | UserStatus? |  |
| role *(consulta)* | RoleCode? |  |
| page *(consulta)* | entero |  |
| page_size *(consulta)* | entero |  |

**Salida** · `200` · `Page_AdminUserItem_`

| Campo | Tipo |
|---|---|
| items | lista de AdminUserItem |
| total | entero |
| page | entero |
| page_size | entero |
| total_pages | entero |
| has_next | sí/no |
| has_previous | sí/no |

### `POST /admin/users/{user_id}/suspend`

Suspender o reactivar una cuenta.

**Entrada**

| Dato | Tipo | |
|---|---|---|
| user_id *(ruta)* | texto | **ob.** |
| **cuerpo** `SuspendRequest` | *application/json* | **ob.** |
|   · suspend | sí/no | **ob.** |
|   · reason | texto? |  |

**Salida** · `200` · `MessageResponse`

| Campo | Tipo |
|---|---|
| message | texto |

