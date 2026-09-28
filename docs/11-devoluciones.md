# Devoluciones, retracto y garantía

**Fase 17.** Documento funcional del módulo de devoluciones.

Este módulo existe porque los textos legales publicados en `/legal/devoluciones`
le dicen al comprador: «entra a tu cuenta, abre el pedido y elige *Solicitar
devolución*». Ese botón no existía. Un documento legal que promete un
procedimiento inexistente no es una imprecisión de redacción: es una condición
que el proveedor no está en capacidad de cumplir.

---

## 1. Dos figuras distintas, no una

La interfaz las presenta juntas —«solicitar una devolución»— pero la Ley 1480 de
2011 las trata por separado, y de esa distinción cuelga todo lo demás.

| | **Retracto** (art. 47) | **Garantía legal** (arts. 7, 8 y 11) |
|---|---|---|
| **Motivo** | Ninguno. El comprador se arrepintió. | El producto falló o no corresponde. |
| **Plazo para pedirla** | 5 **días hábiles** desde la entrega | La fecha de vencimiento impresa; a falta de ella, 1 año desde la entrega |
| **Estado del producto** | Debe volver sellado y sin abrir | Procede aunque se haya abierto |
| **Transporte de vuelta** | Lo paga quien compra | Lo paga quien vende |
| **Plazo del reembolso** | 30 días **calendario** desde que se ejerce | 15 días hábiles |
| **Respuesta escrita** | — | 15 días hábiles (Decreto 735 de 2013) |

Mezclarlas en un único «motivo: otro» impedía darle a cada una su trato, y en
particular impedía reconocer que el plazo del retracto ya venció mientras la
garantía sigue perfectamente viva. Por eso `ReturnReason` es un enumerado y no
un texto libre.

### El retracto sobre café es una condición más favorable

El artículo 47 excluye del retracto los bienes perecederos. El café tostado
tiene fecha de vencimiento y podría quedar cubierto por esa excepción. MONK
GRAIN lo reconoce igualmente sobre el café sin abrir, porque una bolsa sellada y
dentro de su vida útil sí puede volver al inventario. Es una condición mejor que
el mínimo legal y como tal se asume: el sistema **repone inventario** solo en
este caso.

---

## 2. Días hábiles colombianos

Casi todos los plazos del Estatuto se cuentan en días hábiles. Contarlos como
días corridos le recorta el plazo al comprador cada vez que cae un festivo, y un
derecho del consumidor es irrenunciable: no puede reducirse por comodidad de
implementación.

`app/core/business_days.py` calcula los festivos en vez de guardarlos en una
tabla que alguien tendría que mantener año a año:

- Seis fechas fijas.
- Siete que la **Ley 51 de 1983** («ley Emiliani») traslada al lunes siguiente.
- Cinco derivadas del Domingo de Pascua, que es determinista.

Verificado contra el calendario oficial: 2025 tiene **17** festivos —San Pedro y
el Sagrado Corazón coinciden el mismo lunes 30 de junio— y 2026 y 2027 tienen
**18**.

> Entrega el viernes 14 de agosto de 2026. El lunes 17 es festivo (Asunción
> trasladada). Los cinco días hábiles son martes, miércoles, jueves, viernes y
> **lunes 24**. Contar días corridos habría vencido el plazo el 19 y le habría
> quitado cinco días al comprador.

---

## 3. Tres decisiones de diseño

**Los plazos se calculan al radicar y se guardan.** Un vencimiento recalculado
en cada lectura cambiaría si mañana alguien toca la fórmula. El comprador tiene
derecho al plazo que corría cuando presentó su reclamación, así que
`response_due_at` y `refund_due_at` son columnas, no propiedades.

**El importe del reembolso no se negocia.** Lo calcula el servidor sumando las
líneas devueltas. El artículo 47 prohíbe descuentos y retenciones, de modo que
el endpoint de reembolso **no recibe ningún importe**: no hay por dónde
rebajarlo. Si la devolución abarca todo el envío, se reintegra también el costo
de envío original; si el comprador se queda con parte, no, porque ese transporte
ya se prestó.

**Rechazar exige motivar.** La respuesta escrita es el documento que el
comprador acompaña a su demanda ante la Superintendencia. Una casilla de
«rechazado» sin razones lo dejaría sin ese soporte, así que `resolution_notes`
tiene un mínimo de diez caracteres y es obligatorio también al aprobar.

---

## 4. La constancia

Cada solicitud recibe un **número de radicación legible** (`DEV-2026-000123`) y
conserva su fecha y hora. Sale de una secuencia de PostgreSQL por la misma razón
que el número de pedido: un `SELECT count(*) + 1` no es atómico.

La constancia es lo que el comprador lleva a la autoridad. La ven su autor,
quien vende y un administrador; cualquier otro recibe `403`.

---

## 5. Recorrido de una devolución

```
                    ┌── aprobada ──┬─→ en camino ─→ recibida ─┐
  radicada ─────────┤              ├──────────────────────────┴─→ reembolsada
                    └── rechazada (terminal)
```

`aprobada` puede saltar directo a `reembolsada`: un café que llegó dañado no
siempre tiene sentido devolverlo físicamente. `rechazada` es terminal —no se
reabre— y la constancia le dice al comprador que su camino es la
Superintendencia.

**Quién hace qué.** Declarar que el café va de vuelta es lo único que le
corresponde al comprador: es el único que sabe si lo entregó al transportador.
Responder, confirmar la recepción y reembolsar le tocan a quien vende. Un
administrador puede hacer ambas cosas, porque el artículo 10 hace solidaria la
responsabilidad por la garantía: si quien vende no responde dentro del plazo,
alguien tiene que hacerlo.

El servidor devuelve en `available_actions` lo que el usuario que consulta puede
ejecutar ahora. La interfaz lo pinta, pero la autorización sigue estando en el
servidor: ocultar un botón no es control de acceso.

---

## 6. Efectos del reembolso

| Efecto | Cuándo |
|---|---|
| **Reposición de inventario** | Solo en el retracto. Un café devuelto por venir dañado o vencido no vuelve al escaparate. |
| **Rebaja de la base de comisión** | Siempre, en proporción a lo devuelto. Nadie paga comisión sobre dinero que ya reintegró. Solo se toca si la comisión sigue pendiente; si ya se liquidó, queda registrado en el log para regularizarlo. |
| **Sub-orden a `refunded`** | Solo cuando ya no queda nada por devolver. Una devolución parcial no cierra la venta. |
| **Pedido y pago a `refunded`** | Solo cuando ninguna sub-orden sigue viva. En un pedido con varios vendedores, devolver el café de uno no significa recuperar todo lo pagado. |

`OrderStatus` incorpora `refunded`, distinto de `cancelled`: un pedido
reembolsado se entregó y luego se devolvió, y confundirlos borraba esa
diferencia en el historial del comprador y en las métricas del vendedor. La
regla que deriva el estado del pedido vive en una única función,
`derive_order_status`, porque ahora hay dos módulos que cierran pedidos y dos
lecturas distintas de la misma regla acabarían discrepando.

---

## 7. Las fotografías del reclamo

**No son obligatorias.** Exigirlas para admitir el reclamo sería imponer una
condición que la ley no impone, y el artículo 43 declara ineficaz de pleno
derecho lo que dificulte el ejercicio de la garantía.

Se tratan como material privado, con el mismo criterio que los certificados:

- Se validan por su **contenido**, no por la extensión ni el `Content-Type`.
- Se reescriben con Pillow como JPEG, lo que descarta cualquier carga incrustada
  y elimina los metadatos EXIF —incluida la ubicación GPS de la casa de quien
  fotografía.
- Se guardan bajo `returns/`, **fuera de los prefijos públicos** del almacén.
- Se entregan con enlaces firmados que caducan en cinco minutos.

Verificado en el entorno: la misma clave devuelve **403 sin firma** y **200 con
firma**.

---

## 8. Endpoints

| Método | Ruta | Quién |
|---|---|---|
| `GET` | `/orders/sub-orders/{id}/return-eligibility` | comprador |
| `POST` | `/returns` | comprador |
| `GET` | `/returns` | comprador |
| `GET` | `/returns/{id}` | autor, vendedor, admin |
| `POST` | `/returns/{id}/evidence` | autor, vendedor, admin |
| `POST` | `/returns/{id}/shipped` | comprador |
| `GET` | `/producer/returns` | vendedor |
| `POST` | `/producer/returns/{id}/resolution` | vendedor, admin |
| `POST` | `/producer/returns/{id}/received` | vendedor, admin |
| `POST` | `/producer/returns/{id}/refund` | vendedor, admin |

La lista del vendedor viene ordenada por vencimiento: el orden de la pantalla es
el orden en que hay que responder para no incumplir los quince días hábiles.

---

## 9. Interfaz

| Ruta | Qué hace |
|---|---|
| `/mi-cuenta/pedidos/[id]` | Detalle del pedido. **No existía**: las notificaciones apuntaban a un 404. Es desde donde se cancela antes del despacho y se solicita la devolución después. |
| `/mi-cuenta/devoluciones` | Listado del comprador |
| `/mi-cuenta/devoluciones/nueva?envio=` | Formulario de solicitud |
| `/mi-cuenta/devoluciones/[id]` | Constancia |
| `/productor/devoluciones` | Listado del vendedor, por vencimiento |
| `/productor/devoluciones/[id]` | Constancia y respuesta escrita |

El formulario **solo ofrece los motivos que el servidor declara vivos**. Si el
retracto venció, no aparece, y la pantalla lo explica en lugar de callarlo:
«el plazo para retractarte venció el …, pero la garantía sigue vigente».

---

## 10. Verificación

**Suite:** 202 pruebas en verde (170 previas + 32 nuevas).

Las pruebas se validaron **reintroduciendo los defectos**, no solo comprobando
que pasan:

| Defecto reintroducido | Pruebas que fallaron |
|---|---|
| Ignorar las unidades ya reclamadas | 2 |
| No rebajar la base de comisión | 3 |
| Quitar `populate_existing` al releer la constancia | 1 |

**Un defecto real encontrado por la prueba manual, no por la suite.** Al
adjuntar una fotografía la respuesta salía sin ella: la solicitud ya estaba en
el mapa de identidad de la sesión y SQLAlchemy devolvía el objeto en memoria con
su colección vacía. Es el mismo patrón que apareció en la fase 14 con las
variantes. Corregido con `populate_existing=True` y **cubierto ahora por una
prueba** que falla si se retira.

**Ciclo completo verificado en el entorno en ejecución:**

```
Antes del despacho   → can_request=False, «puedes cancelarlo sin costo»
Entregado            → retracto vence 2026-08-24 · garantía 2027-08-16
Retracto con bolsa abierta          → 422
Devolver 99 de 2 unidades           → 422
Radicación                          → DEV-2026-000001, 150.000 COP
Otro vendedor lee la constancia     → 403
Otro vendedor la aprueba            → 403
Otro vendedor la reembolsa          → 403
Sin autenticar                      → 401
Rechazo sin motivar                 → 422
Reembolsar antes de responder       → 422
El vendedor declara el envío        → 403   (solo el comprador)
Ciclo completo                      → sub-orden, pedido y pago en `refunded`
                                       comisión 0.00, estado `reversed`
                                       inventario intacto (motivo: dañado)
Foto sin firma / con firma          → 403 / 200
```

Ruff, Ruff format, Mypy, TypeScript, ESLint y Prettier sin hallazgos.
`alembic check` sin migraciones pendientes; la migración `6cd4b72f44fd`
verificada de ida y vuelta.

---

## 11. Lo que este módulo no resuelve

**La reversión del pago (artículo 51)** no se implementa porque no puede: el
proveedor de pago es simulado y no hay instrumento electrónico que reversar. El
documento legal ya lo advierte expresamente. Cuando se active una pasarela con
cobro efectivo habrá que construir el flujo de queja al vendedor y notificación
al emisor, ambos dentro de cinco días hábiles.

**La fecha de vencimiento del empaque** no se captura hoy, así que la garantía
rige siempre por el término supletorio de un año desde la entrega —el más
favorable al comprador—. Capturarla permitiría ajustar el plazo al que
efectivamente corresponde a cada café.

**El plazo de respuesta no se vigila solo.** El sistema calcula el vencimiento,
lo muestra y ordena la lista del vendedor por él, pero nadie escala una
reclamación que se pasó de los quince días hábiles. Hace falta una tarea
programada y la decisión de negocio D-6 del expediente legal —la potestad de
retener fondos, hoy anunciada al consumidor pero no pactada contractualmente con
el vendedor.

**La revisión del abogado sigue pendiente**, como todo lo demás en `10-revision-legal.md`.
