# ENDPOINTS ejercitados — colección AA5-EV04

**GA7-220501096-AA5-EV04**

La colección hace **28 peticiones**. No cubre los 107 endpoints de la
API: recorre tres caminos completos —comprador, vendedor y autorización—
tocando los grupos principales.

> El catálogo **completo** de los 107 endpoints está en
> `entregas/GA7/AA5_EV03_APIs_Proyecto/ENDPOINTS.md`, y se genera desde el
> documento OpenAPI del servicio en marcha.

**Base:** `http://localhost:8000`

---

## 1. Salud y autenticación

| # | Método | Ruta | Qué comprueba |
|---|---|---|---|
| 1.1 | `GET` | `/health` | GET /health → 200 |
| 1.2 | `POST` | `/api/v1/auth/login` | Ingreso del comprador → 200 |
| 1.3 | `POST` | `/api/v1/auth/login` | Ingreso del vendedor → 200 |
| 1.4 | `GET` | `/api/v1/auth/me` | GET /auth/me → 200 |
| 1.5 | `GET` | `/api/v1/auth/me` | Sin token → 401 |

## 2. Catálogo

| # | Método | Ruta | Qué comprueba |
|---|---|---|---|
| 2.1 | `GET` | `/api/v1/products?page=1&page_size=5` | GET /products → 200 paginado |
| 2.2 | `GET` | `/api/v1/products?max_yield_factor=92&page_size=20` | Filtro por factor de rendimiento → 200 |
| 2.3 | `GET` | `/api/v1/products/{var}` | GET /products/{slug} → 200 con variantes |
| 2.4 | `GET` | `/api/v1/products/lote-que-no-existe-jamas` | Slug inexistente → 404 |

## 3. Carrito

| # | Método | Ruta | Qué comprueba |
|---|---|---|---|
| 3.1 | `DELETE` | `/api/v1/cart` | Vaciar el carrito |
| 3.2 | `POST` | `/api/v1/cart/items` | Un kilo suelto en el carrito vacío → 422 |
| 3.3 | `POST` | `/api/v1/cart/items` | Añadir el mínimo → 201 |
| 3.4 | `GET` | `/api/v1/cart` | GET /cart → 200, con el renglón dentro |
| 3.5 | `POST` | `/api/v1/cart/items` | Un kilo más sobre el mínimo → 201 |
| 3.6 | `PATCH` | `/api/v1/cart/items/{var}` | Bajar por debajo del mínimo → 422 |
| 3.7 | `POST` | `/api/v1/cart/items` | Variante inventada → 404 o 422 |
| 3.8 | `GET` | `/api/v1/cart` | Carrito sin token → 401 |

## 4. Oferta y demanda

| # | Método | Ruta | Qué comprueba |
|---|---|---|---|
| 4.1 | `POST` | `/api/v1/demands` | Publicar una solicitud de compra → 201 |
| 4.2 | `GET` | `/api/v1/demands?page_size=10` | GET /demands → 200 |
| 4.3 | `GET` | `/api/v1/demands/{var}` | GET /demands/{id} → 200 con cobertura |
| 4.4 | `GET` | `/api/v1/producer/demands?page_size=10` | El vendedor ve la solicitud → 200 |
| 4.5 | `POST` | `/api/v1/demands/{var}/close` | Cerrar la solicitud → 200 |

## 5. Autorización

| # | Método | Ruta | Qué comprueba |
|---|---|---|---|
| 5.1 | `GET` | `/api/v1/producer/products?page_size=5` | El comprador entra al panel del productor → 403 |
| 5.2 | `GET` | `/api/v1/admin/users?page_size=5` | El comprador entra a administración → 403 |
| 5.3 | `GET` | `/api/v1/admin/producers/pending?page_size=5` | El vendedor entra a administración → 403 |
| 5.4 | `GET` | `/api/v1/orders/00000000-0000-0000-0000-000000000000` | Un pedido ajeno → 404, no 403 |
| 5.5 | `GET` | `/api/v1/auth/me` | Token manipulado → 401 |
| 5.6 | `GET` | `/api/v1/auth/me` | Esquema que no es Bearer → 401 |

---

## Endpoints distintos tocados: 20

| Método | Ruta |
|---|---|
| `GET` | `/api/v1/admin/producers/pending?page_size=5` |
| `GET` | `/api/v1/admin/users?page_size=5` |
| `POST` | `/api/v1/auth/login` |
| `GET` | `/api/v1/auth/me` |
| `DELETE` | `/api/v1/cart` |
| `GET` | `/api/v1/cart` |
| `POST` | `/api/v1/cart/items` |
| `PATCH` | `/api/v1/cart/items/{var}` |
| `POST` | `/api/v1/demands` |
| `GET` | `/api/v1/demands/{var}` |
| `POST` | `/api/v1/demands/{var}/close` |
| `GET` | `/api/v1/demands?page_size=10` |
| `GET` | `/api/v1/orders/00000000-0000-0000-0000-000000000000` |
| `GET` | `/api/v1/producer/demands?page_size=10` |
| `GET` | `/api/v1/producer/products?page_size=5` |
| `GET` | `/api/v1/products/lote-que-no-existe-jamas` |
| `GET` | `/api/v1/products/{var}` |
| `GET` | `/api/v1/products?max_yield_factor=92&page_size=20` |
| `GET` | `/api/v1/products?page=1&page_size=5` |
| `GET` | `/health` |

---

## Cómo ejecutarla

```bash
docker compose up -d
npx newman run entregas/GA7/AA5_EV04_Postman_Proyecto/postman/\
    MONK_GRAIN_API_Proyecto.postman_collection.json
```

O en Postman: **File → Import**, y luego **Run** sobre la colección.
Las carpetas se ejecutan en orden y cada una depende de la anterior.

**Si el ingreso responde 429**, espera un minuto: admite 10 intentos por
minuto y por cuenta, y la colección está agotando ese tope. No hay nada
que arreglar.
