# 15 — Oferta y demanda: el mercado de dos lados

**Módulo:** `app/modules/trading/`
**Tablas:** `demand_requests`, `demand_offers`, y dos columnas en `cart_items`

---

## 1. El problema

El catálogo resuelve un solo sentido del negocio: el vendedor publica y el comprador elige. En pergamino eso deja fuera la mitad de cómo funciona la compra.

Una trilladora que necesita cinco cargas con factor 93 o menos no recorre el catálogo cada semana esperando que aparezca. Publica lo que busca —cuántos kilos, qué factor acepta, qué paga— y espera que los caficultores le respondan. Y un caficultor pequeño con 620 kg en bodega no compite por aparecer en un listado: responde a quien ya dijo que lo necesita.

---

## 2. Las dos entidades

### `DemandRequest` — lo que un comprador busca

| Campo | Notas |
|---|---|
| `wanted_kg`, `covered_kg` | Los cubiertos se mantienen como columna, no se calculan al vuelo: deciden si la solicitud sigue recibiendo posturas, y esa pregunta se hace en cada listado. |
| `max_yield_factor`, `max_moisture_pct` | **Techos**, no valores exactos: en estos dos datos menos es mejor, así que lo que se declara es el máximo aceptable. Un lote con factor 88 satisface una solicitud que pide «92 o menos». |
| `variety`, `process` | Preferencias. Nulo es «cualquiera». |
| `department_id`, `municipality_id` | Origen preferido. El departamento se deriva del municipio, igual que en las direcciones: recibirlo aparte permitiría una pareja imposible. |
| `offered_price_per_kg` | Referencia, no compromiso: la postura del vendedor lleva su propio precio. |
| `expires_on` | Vigencia, **máximo 90 días**. Más allá, el precio ofrecido ya no corresponde a la cosecha. |

### `DemandOffer` — la postura de un vendedor

Va **siempre respaldada por una oferta concreta de un lote publicado**. Su análisis, su origen y su trazabilidad son los del lote, no datos que se escriban de nuevo aquí.

Esa es la decisión de diseño central del módulo: sin ese respaldo, una postura sería una promesa sin ficha técnica detrás, y el comprador estaría aceptando algo que no puede inspeccionar. Por eso se exige que el lote esté **publicado**: un borrador dejaría al comprador aceptando algo cuya ficha no puede ver.

---

## 3. El recorrido

```
  COMPRADOR                                          VENDEDOR
      │
      │ publica solicitud
      │   625 kg · factor ≤ 93 · ofrece 21.000/kg
      │   vigencia 45 días
      ├──────────────────────────────────────────────────►
      │                                    la ve en su bandeja,
      │                                    filtrada a lo que sus
      │                                    lotes pueden cumplir
      │                                                  │
      │                    responde con una postura      │
      │   ◄──────────────────────────────────────────────┤
      │     625 kg a 21.500/kg, sobre el lote
      │     «Nariño Altura Lavado» (factor 91,50)
      │
      │ ve el análisis de ese lote y acepta
      ├──────────────►  CARRITO  (625 kg × 21.500, precio acordado)
      │                    │
      │                    └──► CHECKOUT ──► PEDIDO ──► sub-orden
      │                                                 del vendedor
```

---

## 4. La decisión que evita duplicar el sistema de pedidos

**Aceptar una postura no crea un pedido: crea una línea de carrito al precio acordado.**

La alternativa —cerrar el pedido en el momento de aceptar— habría cobrado **un envío por cada vendedor**, y en pergamino lo normal es armar una carga con tres. También habría exigido un segundo camino hacia el pedido, con su propio cálculo de comisión y su propia reserva de inventario, que es exactamente donde aparecen las discrepancias.

Con esta decisión, el comprador acepta posturas de varios caficultores, revisa su carrito y paga una vez. El sistema arma una sub-orden por vendedor, como siempre.

### Cómo se sostiene el precio acordado

Dos columnas nuevas en `cart_items`:

```sql
negotiated_price   NUMERIC(14,2)   -- el precio acordado
demand_offer_id    UUID            -- la postura que lo respalda

CHECK ((negotiated_price IS NULL) = (demand_offer_id IS NULL))
```

Ese `CHECK` es lo que impide que exista un precio distinto del de catálogo sin rastro de dónde salió. Un precio arbitrario en una línea de carrito, sin nada que lo justifique, es justo lo que alguien preguntaría al auditar un pedido.

El precio efectivo se resuelve en **un solo sitio**, una propiedad del modelo:

```python
@property
def effective_price(self) -> Decimal:
    return self.negotiated_price if self.negotiated_price is not None else self.variant.price
```

Lo usan el carrito y el checkout. Importa que sea el checkout y no solo la vista: **la comisión se calcula sobre el subtotal**, de modo que un precio equivocado ahí se arrastraría hasta la liquidación del vendedor.

Y el aviso de «el precio cambió» se suprime en las líneas negociadas: lo acordado no cambia porque el vendedor mueva su lista, y advertirlo asustaría sin motivo.

---

## 5. Las reglas que hace cumplir el servidor

### Sobre la solicitud

- Vigencia de 90 días como máximo y no en el pasado.
- Los **kilos buscados y los techos de calidad no se editan**: cambiarlos invalidaría las posturas que ya respondieron a otras condiciones. Para pedir otra cosa se cierra esta solicitud y se abre otra.
- El vencimiento **se juzga al consultar**, no con un estado guardado. Mantenerlo al día exigiría un proceso que recorra la tabla cada noche, y una solicitud vencida se comporta igual si simplemente se deja de considerar vigente.
- Cerrar una solicitud **sin compras la cancela; con compras hechas la cierra**. Mezclarlo borraría del historial que hubo negocio.
- Al cerrar, las posturas pendientes se rechazan en bloque con su motivo. Dejarlas colgando haría que un caficultor siguiera esperando una respuesta que no va a llegar.

### Sobre la postura

- No se puede ofrecer más de los kilos disponibles, ni menos del mínimo de la propia oferta del lote.
- No se puede ofrecer un lote de otro vendedor (404) ni un lote sin publicar (422 con el motivo).
- **Una postura por vendedor y lote sobre la misma solicitud**, garantizado por un `UNIQUE` en la base de datos. Sin eso, un vendedor inundaría la solicitud repitiendo la misma oferta para aparecer primero en la lista.
- El vendedor retira una postura que aún no fue respondida; una ya respondida, no.

### Sobre la respuesta

- **Al aceptar se vuelve a comprobar el inventario.** Entre que el vendedor ofreció y el comprador respondió pudo vender ese café a otro. El error dice cuántos kilos quedan.
- Cubrir parte de lo buscado deja la solicitud en `partially_covered` y **sigue recibiendo posturas**: quien busca 250 kg y consigue 125 necesita los otros 125.
- Cubrirlo todo la marca `fulfilled` y **rechaza lo pendiente** con el motivo «La solicitud se completó con otras posturas».
- Una nota de rechazo en blanco no se guarda como explicación. No se exige el motivo —obligar a escribir algo produce «no» a secas—, pero sí se impide simular una explicación con espacios.

### Sobre quién ve qué

- Las solicitudes **no son públicas**: dicen qué busca alguien y a qué precio, que es información comercial suya. Solo las ve un vendedor aprobado.
- Una solicitud ajena responde **404 y no 403**: distinguirlos revelaría que existe.
- El filtro `only_matching` acota el listado del vendedor a lo que sus lotes pueden satisfacer, comparando contra su mejor lote —menor factor, menor humedad— y sus kilos vendibles. Un requisito que el comprador no puso (`NULL`) no excluye a nadie.

---

## 6. Detalles de la interfaz que son decisiones

- El formulario de postura **no pide factor ni humedad**: ya están en la ficha del lote que la respalda. Pedirlos otra vez invitaría a declarar algo distinto de lo publicado.
- Propone de entrada **los kilos que faltan por cubrir**, acotados al mínimo y a las existencias de la oferta elegida, para que el caso corriente salga válido sin corregirlo.
- Si el vendedor pide más de lo que el comprador ofreció, el aviso lo señala y sugiere explicarlo en el mensaje.
- Las posturas se ordenan **lo pendiente primero, y de eso lo más barato por kilo**: es el orden en que un comprador quiere revisar.
- Las posturas retiradas **no se cuentan**. Anunciar «3 posturas» y listar una sola resta credibilidad.
- El motivo de un rechazo se le muestra completo al vendedor: es lo que le dice qué ajustar en la siguiente.

---

## 7. Los endpoints

| Método | Ruta | Quién |
|---|---|---|
| `POST` | `/demands` | Comprador |
| `GET` | `/demands` | Comprador (las suyas) |
| `GET` | `/demands/{id}` | Comprador (la suya, con posturas) |
| `PATCH` | `/demands/{id}` | Comprador |
| `POST` | `/demands/{id}/close` | Comprador |
| `POST` | `/demands/offers/{id}/respond` | Comprador |
| `GET` | `/producer/demands` | Vendedor aprobado |
| `POST` | `/producer/demands/{id}/offers` | Vendedor aprobado |
| `GET` | `/producer/offers` | Vendedor aprobado |
| `POST` | `/producer/offers/{id}/withdraw` | Vendedor aprobado |

Las rutas están separadas **por lado del mercado y no por entidad**. Mezclarlas en un solo recurso habría obligado a que cada endpoint decidiera, según el rol de quien llama, qué es lo que devuelve.

---

## 8. La migración

`4ad7359adcf8_oferta_y_demanda_entre_comprador_y_.py`. Dos fallos del autogenerado, corregidos a mano:

1. **Intentaba recrear el tipo `coffee_process`**, que ya existía desde la migración inicial: fallaba con «type already exists». Se reutiliza con `create_type=False`.
2. **El `downgrade` no retiraba los tipos `demand_status` ni `offer_status`**, de modo que volver a aplicar la migración fallaba. Es el mismo error que tenía la migración del pivote a pergamino, en el otro sentido.

Probada de ida, de vuelta y de ida otra vez.

---

## 9. Verificación

40 pruebas en `tests/integration/test_trading.py`. Las que más importan:

- El precio acordado es el que queda en el carrito **y el que cobra el pedido**, con el catálogo a otro precio.
- El precio acordado **sobrevive a un cambio del precio de catálogo** y no dispara el aviso de cambio.
- Unos kilos vendidos entre la postura y la respuesta **bloquean la aceptación**.
- Un precio negociado sin su postura **lo rechaza la base de datos**.
- La misma pareja de vendedor y lote **no puede repetirse** en una solicitud, también a nivel de base de datos.

Comprobado además contra el entorno en ejecución: un comprador nuevo publica 625 kg con factor ≤ 93; la cooperativa de Nariño la ve en su bandeja filtrada y ofrece 625 kg a 21.500 el kilo sobre un lote que lista a 23.000; el comprador ve el factor 91,50 y la humedad 10,50 %, acepta, y el pedido cobra 625 × 21.500 = 13.437.500.

De paso quedó demostrada una de las reglas: un primer intento de ofrecer 625 kg sobre una oferta con mínimo de 700 kg fue rechazado con «Esta oferta se vende desde 700 kg».

---

## 10. Lo que no incluye

- **No hay contraoferta.** El comprador acepta o rechaza; no propone otro precio sobre la misma postura. El vendedor puede retirar la suya y enviar otra, que cubre el caso sin un estado más en el grafo.
- **No hay notificaciones.** Los tipos `DEMAND_OFFER_RECEIVED`, `DEMAND_OFFER_ACCEPTED` y `DEMAND_OFFER_REJECTED` están declarados en el enum, pero nada las emite todavía: hace falta el proceso en segundo plano que el proyecto no tiene.
- **No hay chat.** El mensaje de la postura y la nota de la respuesta son un intercambio de una sola vuelta, a propósito.
