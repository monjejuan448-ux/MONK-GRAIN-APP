# Reseñas y calificaciones

**Fase 18.** Documento funcional del módulo de reseñas.

El sistema de reseñas figuraba en el alcance del MVP desde la primera fase, la
ficha del café prometía mostrarlas y el panel administrativo ya sabía moderarlas.
Lo único que faltaba era que alguien pudiera escribir una: no existía ningún
endpoint para ello, así que la ficha las mostraba vacías de forma permanente y la
cola de moderación no podía llenarse nunca.

---

## 1. Lo que una reseña acredita

Una reseña vale por lo que garantiza: que quien la escribe compró ese café y lo
recibió. Esa garantía no descansa en una comprobación del código, sino en la
forma de la tabla. `reviews.order_item_id` es **único** y apunta a una línea de
pedido concreta, de modo que ni un error de validación ni una petición
malintencionada pueden colar una opinión sobre un café que nunca se compró.

De ahí salen las tres reglas del módulo:

**Solo se reseña lo entregado.** No basta con haber pagado (HU-CC-10, CA1).

**Una reseña por línea de pedido.** Quien compra el mismo café dos veces puede
reseñarlo dos veces, y es correcto: son dos experiencias distintas. Lo que no
puede es reseñar dos veces la misma compra (CA3).

**Se corrige, no se reescribe indefinidamente.** La edición está abierta
**treinta días**. Después la reseña queda como está: otros compradores ya
decidieron con ella a la vista. Eliminarla, en cambio, se admite siempre: lleva
el nombre de quien la escribió y la política de datos le reconoce el derecho a
suprimir lo que publicó sobre sí mismo.

---

## 2. Quién firma

La reseña se publica como **«Lucía R.»**: nombre de pila y la inicial del primer
apellido. La ficha del café es pública y la indexan los buscadores; el apellido
completo de quien compra no aporta nada a la reseña y sí expone un dato personal
más de lo necesario.

---

## 3. Reportar no es silenciar

`ReviewStatus` distingue tres situaciones, y la diferencia entre las dos últimas
es la decisión de diseño central del módulo:

| Estado | Visible en la ficha | Cuenta para el promedio |
|---|---|---|
| `published` | sí | sí |
| `reported` | **sí** | **sí** |
| `hidden` | no | no |

Una denuncia sin resolver **no es una decisión de moderación**. Si bastara con
reportar una reseña para que dejara de verse —o incluso solo para que dejara de
pesar en la calificación—, el botón de denunciar sería un modo indirecto de
silenciar cualquier opinión incómoda. La reseña sigue donde está hasta que un
administrador decida; lo único que cambia el reporte es que la solicitud entra en
la cola.

El motivo de la denuncia se guarda en `review_reports`, aparte de
`reviews.moderation_reason`. Son cosas distintas: el primero lo da quien reporta
y es lo que la cola necesita mostrar (HU-ADM-06, CA1); el segundo lo da el
administrador al decidir. Una clave única sobre `(review_id, reported_by)` impide
que una misma persona reporte varias veces e infle el recuento.

---

## 4. Endpoints

| Método | Ruta | Quién |
|---|---|---|
| `GET` | `/products/{id}/reviews` | público |
| `GET` | `/products/{id}/reviews/summary` | público |
| `POST` | `/reviews` | comprador |
| `GET` | `/reviews/pending` | comprador |
| `PUT` | `/reviews/{id}` | autor, dentro del plazo |
| `DELETE` | `/reviews/{id}` | autor |
| `POST` | `/reviews/{id}/report` | cualquier usuario, salvo el autor |
| `GET` | `/admin/reviews/reported` | administrador |

El listado público acepta sesión opcional: si quien consulta la tiene, sus
propias reseñas vienen marcadas con `is_mine` y `can_edit`. Sin sesión, ambos
son falsos.

Intentar reseñar la compra de otra persona devuelve **404 y no 403**: distinguir
ambos casos permitiría averiguar qué identificadores de línea existen de verdad.

---

## 5. Interfaz

| Ruta | Qué hace |
|---|---|
| `/catalogo/[slug]` | Promedio junto al título, reparto de estrellas y listado. Estado vacío que invita a ser el primero (HU-VIS-04, CA4). |
| `/mi-cuenta/resenas` | Cafés entregados sin reseñar, con el formulario en línea (RF-06.4). |

El bloque de reseñas se carga en el cliente y no en el servidor porque cambia
según quién mire: la propia reseña trae el botón de eliminarla y las ajenas el de
reportarlas. Renderizarlo en el servidor obligaría a variar la caché de la ficha
por usuario para un bloque que está por debajo del pliegue.

Las estrellas son decorativas —`aria-hidden`— y el valor va en texto: un lector
de pantalla que enumerase cinco iconos no diría nada útil, y quien no distingue el
relleno del contorno necesita el número.

---

## 6. Dos fallos encontrados en producción, no en la suite

La suite pasaba en verde mientras el código estaba mal. Los dos fallos salieron
al ejercitar el sistema en ejecución.

### El promedio del productor nunca se actualizaba

`recalculate_product_rating` asignaba el promedio del café y, acto seguido,
calculaba el del productor con una agregación sobre `products`. Esa consulta no
veía el valor recién asignado, así que el promedio del productor se quedaba en
cero mientras el del café ya figuraba correcto.

**Por qué la suite no lo vio.** La sesión de la aplicación se crea con
`autoflush=False`; la de las pruebas usaba el valor por defecto, `True`. Con
autoflush cualquier consulta arrastra los cambios pendientes, de modo que la
prueba pasaba aunque el código dependiera de un `flush` que en producción nunca
ocurría.

La corrección tiene dos partes. La primera, un `flush` explícito en el
repositorio. La segunda y más importante: **la sesión de pruebas ahora replica la
configuración real** (`tests/conftest.py`). En cuanto se alineó, la suite
descubrió por su cuenta **dos casos más del mismo fallo** —eliminar una reseña y
ocultarla desde moderación tampoco recalculaban bien—, que estaban ahí desde
antes de esta fase.

Es la lección metodológica de esta fase: *una prueba que corre con una
configuración más permisiva que la de producción no prueba producción.*

### Denunciar rebajaba la calificación

Diseñé el reporte para que no ocultara la reseña, pero `recalculate_product_rating`
solo contaba las `published`. El resultado era incoherente: la reseña seguía
visible y sin embargo dejaba de pesar en el promedio. Denunciar funcionaba como
un silenciador a medias, exactamente lo que se quería evitar.

Corregido con `VISIBLE_REVIEW_STATUSES`, compartida entre el listado y la
agregación para que no puedan volver a discrepar.

---

## 7. Verificación

**Suite:** 227 pruebas en verde (202 previas + 25 nuevas).

Validadas reintroduciendo los defectos:

| Defecto reintroducido | Pruebas que fallaron |
|---|---|
| No comprobar que el pedido fue entregado | 1 |
| No comprobar que la línea es de quien reseña | 1 |
| Ocultar la reseña al reportarla | 3 |
| Quitar el `flush` del recálculo | 2 |

**Ciclo completo contra el entorno en ejecución:**

```
Sin comprar                          → 0 cafés por reseñar
Pagado sin entregar                  → 422
Entregado                            → aparece en «cafés por reseñar»
Reseñar la compra de otro            → 404
Sin sesión                           → 401
9 estrellas                          → 422
Publicar                             → 201, firmada «Lucía R.»
Reseñar dos veces la misma compra    → 409
Editar / borrar reseña ajena         → 403 / 403
Reportar la propia                   → 422
Reportar dos veces                   → 409
Vendedor entrando a la cola          → 403
Cola de moderación (admin)           → motivo de la denuncia visible
Reseña denunciada                    → sigue en la ficha y en el promedio
Admin la oculta                      → fuera de la ficha y del promedio (0 reseñas)
Admin la restablece                  → café 5,00 · productor 5,00
```

Ruff, Ruff format, Mypy, TypeScript, ESLint y Prettier sin hallazgos.
`alembic check` sin migraciones pendientes; la migración `2840b05b463c`
verificada de ida y vuelta.

---

## 8. Lo que este módulo no incluye

**Respuesta del vendedor a una reseña.** No figura en ninguna historia de
usuario. Es una función habitual en otros marketplaces y probablemente valga la
pena, pero es alcance nuevo y no una deuda de esta fase.

**Fotografías en la reseña.** Tampoco está en el alcance. La infraestructura
existe —validación por contenido y almacenamiento privado, de la fase 13—, así
que añadirla sería barato si el negocio lo pide.

**Aviso para reseñar.** `NotificationType.REVIEW_REMINDER` existe y se usa hoy
para avisar al vendedor de una reseña nueva, pero nadie recuerda al comprador que
tiene cafés pendientes. Hace falta una tarea programada, la misma que reclama la
vigilancia de plazos de devoluciones.
