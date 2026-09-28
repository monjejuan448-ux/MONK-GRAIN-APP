# 14 — El dominio: café pergamino seco

**Fecha del pivote:** 28 de septiembre de 2026
**Alcance:** modelo de datos, catálogo, precio, unidades y textos

---

## 1. Qué es el pergamino y por qué cambia todo

El pergamino seco es el café despulpado, fermentado, lavado y secado, que todavía conserva la película que envuelve la almendra —el pergamino— y **no ha pasado por trilla**. Es el producto con el que un caficultor colombiano sale de su finca y el que compran las trilladoras, las cooperativas y los exportadores.

No es café verde: el verde, o almendra, es lo que queda **después** de trillar el pergamino. Y no es café tostado: eso son dos procesos más adelante.

Esa distinción no es terminológica, es económica. Un lote de pergamino no se describe por cómo sabe en taza, sino por **cuánto café exportable rinde al trillarlo**. De ahí que todo el vocabulario del catálogo cambie.

---

## 2. El factor de rendimiento

Es el dato que gobierna el valor de un lote en Colombia: **los kilos de pergamino seco que hay que trillar para obtener un saco de 70 kg de café excelso de exportación**.

- **Más bajo es mejor.** Un factor 88 rinde más que un factor 94 con el mismo peso.
- El **estándar de la Federación Nacional de Cafeteros es 94**. Por debajo se paga sobreprecio; por encima, descuento.
- Fuera del rango 80–130 no existe café comercializable: un valor así es un error de digitación, no un café excepcional.

### Cómo lo trata el sistema

| Decisión | Por qué |
|---|---|
| `NUMERIC(5,2)` | Medio punto de factor mueve el precio de una carga. Redondear a entero borraría esa diferencia. Un `NUMERIC(3,2)` —como proponía el modelo académico para el puntaje de catación— solo admite hasta 9,99. |
| `CHECK` entre 80 y 130 | La base de datos rechaza lo imposible, no solo el schema de entrada. |
| Se filtra por su **máximo** | Menos es mejor, así que lo que un comprador acota es el techo que acepta. Un filtro por mínimo no tendría sentido en este dato. |
| Se ordena **ascendente**, nulos al final | «Mejor factor» es el más bajo. Los lotes sin factor declarado no pueden afirmar que cumplen nada. |
| **No altera el precio** | Ver §5. |
| Se muestra con su lectura al lado | «91,50 · De exportación». El número solo no se interpreta sin saber que 94 es el estándar. |

La lectura en cuatro tramos, que sigue la práctica comercial:

| Factor | Etiqueta | Significado |
|---|---|---|
| ≤ 89 | Excepcional | Rinde mucho más que el estándar; se paga sobreprecio |
| 90 – 92 | De exportación | Por debajo del estándar; apto para trilla de excelso |
| 93 – 96 | Estándar | El rango de la compra corriente |
| ≥ 97 | Bajo rendimiento | Hay que trillar más pergamino para el mismo excelso |

---

## 3. El resto del análisis

| Campo | Columna | Qué decide |
|---|---|---|
| Humedad | `moisture_pct` | Entre 10 % y 12 % es el rango seguro. Por debajo, el grano se quiebra en la trilla; por encima, hay riesgo de hongos y es causal de rechazo en un punto de compra. |
| Almendra sana | `healthy_bean_pct` | Porcentaje de grano apto sobre el peso analizado. |
| Pasilla | `pasilla_pct` | Grano defectuoso que se separa en la trilla. |
| Daño por broca | `borer_damage_pct` | Perforación del insecto. Por encima de cierto umbral descalifica el lote para exportación. |
| Granulometría | `screen_sizes` | Mallas en las que se retiene el grano, de la 14 a la 20. Se guarda como arreglo porque un lote se describe por las mallas que lo componen, no por una sola. |

Todos los porcentajes llevan `CHECK` entre 0 y 100. Las mallas se validan entre 14 y 20 en el schema de entrada, y el mensaje de error nombra la que no existe.

**Todo el análisis es opcional.** Exigirlo para poder publicar dejaría fuera a la mayoría de los caficultores pequeños, que no han mandado su café a un laboratorio. La interfaz dice qué falta y explica que un lote con factor y humedad declarados se vende mejor.

**El análisis lo declara el vendedor y MONK GRAIN no lo verifica.** La ficha lo dice, los términos y condiciones lo dicen, y la pantalla recomienda pedir muestra y hacer análisis propio antes de una compra por volumen. Toda medición sobre muestra tiene tolerancia, y eso también quedó escrito en la política de devoluciones: medio punto de factor no es un incumplimiento, tres puntos sí.

---

## 4. Trazabilidad del lote

| Campo | Para qué |
|---|---|
| `lot_code` | El código con el que el productor identifica el lote en su finca. Permite que una reclamación apunte a un lote concreto y no al café «en general» de esa finca. |
| `sica_code` | Código del predio en el Sistema de Información Cafetera. **No se contrasta con la Federación** —no hay integración—, así que se publica tal como lo declara el vendedor y la ficha lo presenta como declarado. |
| `drying_method` | Marquesina, patio de cemento, camas africanas, secador mecánico, silo. Texto libre con sugerencias: cada finca seca a su manera. |

---

## 5. El precio

**Precio libre por kilogramo, puesto por el vendedor.** El factor queda informativo al lado.

La alternativa era indexarlo al precio interno de referencia de la Federación más una bonificación por calidad, que es como funciona el negocio real. Se descartó para esta fase por una razón concreta: exige **una fuente del precio diario** y decidir quién la actualiza. Sin eso, la indexación produce precios de una cosecha anterior presentados como vigentes, que es peor que no indexar.

La tabla `FncPriceReference` está diseñada y anotada, sin implementar. Cuando se decida quién mantiene el precio diario, el cambio es aditivo: el precio por kilo pasa a calcularse como `(precio_carga / 125) + bonificacion_kg`, y nada del pedido, el pago ni la comisión se toca.

### Precio por volumen

`wholesale_price` es el precio por kilo a partir de una cantidad. Se valida que sea **menor** que el precio corriente: un «precio por volumen» más alto no es un descuento.

---

## 6. Unidades

**La unidad del sistema es el kilogramo.** Precio por kilo, inventario en kilos, cantidad del carrito en kilos.

La decisión alternativa era modelar carga (125 kg), arroba (12,5 kg) y bulto (70 kg) como unidades de primera clase. Se descartó porque obliga a convertir en cada comparación de precios y multiplica los caminos por donde puede colarse un error de redondeo.

Lo que sí se conserva es la **lectura** en cargas, porque es como se habla del precio del café en Colombia:

```
1.250 kg (10 cargas)
375 kg (3 cargas)
80 kg              ← por debajo de una carga no se convierte:
                     «0,6 cargas» no es como nadie cuenta
```

### El mínimo de compra

Cada oferta de un lote lleva su `min_qty_kg`. Un caficultor no despacha 3 kg: el costo del flete se come la venta.

- Se hace cumplir **en el servidor**, al agregar y al editar la línea del carrito. Solo al agregar habría dejado abierta la vía obvia: agregar el mínimo y bajarlo después.
- Se juzga sobre **el total de la línea**, no sobre cada clic: el carrito suma, y 100 kg más 25 kg son los 125 exigidos.
- Al publicar se rechaza un mínimo mayor que las existencias: esa oferta sería incomprable y el comprador solo lo descubriría en el carrito.
- Los botones de más y menos del carrito **saltan en la unidad del mínimo**. De kilo en kilo harían falta 125 clics para llegar a la siguiente cantidad que el vendedor acepta.
- Un lote cuyo remanente no alcanza el mínimo se marca como tal en lugar de ofrecer un botón que va a fallar.

---

## 7. Qué se retiró

| Se retiró | Por qué |
|---|---|
| `RoastLevel` y la columna `roast` | El pergamino no está tostado. |
| `GrindType`, `GRIND_LABELS` y la columna `grind` | Tampoco está molido. |
| `cupping_score` | El puntaje de catación describe una taza; aquí se vende grano sin trillar. |
| `tasting_notes` | Idem. |
| `sensory_profile` | Su contenido se trasladó a `notes` del lote antes de eliminar la columna. |
| `roast_date` | No hay tostión. |
| `weight_grams` de las variantes | Media tonelada son 500.000 g. |
| `CoffeeState.GREEN`, `ROASTED`, `GROUND` | Queda un único valor: `PERGAMINO`. |
| `shipments.weight_grams` | Pasa a `weight_kg`, con su valor convertido. |

`CoffeeState` **se conserva con un solo valor** en lugar de eliminar la columna, por dos razones: deja constancia explícita de qué se vendió en un pedido de hace un año, y admite un segundo estado el día que se decida sin tocar el esquema.

## Qué se conservó

Reseñas, favoritos y el derecho de retracto. Fue una decisión: la plataforma admite compradores **persona natural** además de empresas, y para ellos el Estatuto del Consumidor aplica.

Eso obligó a revisar el razonamiento de la política de devoluciones. El café tostado podía quedar excluido del retracto por ser perecedero; el pergamino seco, guardado en bodega ventilada y con humedad entre 10 % y 12 %, se conserva meses. **El retracto sí aplica**, y lo que puede hacer que un lote deje de ser devolvible es su manejo: pergamino que se mojó, que tomó olores o que ya pasó por trilla no vuelve al inventario del vendedor.

---

## 8. Las categorías

Agrupan por lo que decide una compra —el factor— y no por presentación:

| Categoría | Criterio |
|---|---|
| Pergamino de exportación | Factor 92 o menor |
| Pergamino estándar | Factor entre 93 y 96 |
| Microlotes | Variedades y beneficios especiales, en lotes pequeños |
| Pergamino certificado | Con certificación orgánica, Fairtrade, Rainforest o UTZ vigente |

---

## 9. La migración

`99716e5f6986_pivote_a_cafe_pergamino.py`, escrita a mano. El autogenerado de Alembic tenía tres fallos que la habrían roto:

1. **No detecta el cambio de valores de un ENUM.** La columna `products.state` habría quedado con el tipo antiguo, sin admitir `pergamino`: ningún lote nuevo se habría podido insertar. PostgreSQL no permite retirar valores de un ENUM, así que se construye el tipo nuevo, se convierte la columna con un `USING` y se descarta el viejo.
2. **Añadía `presentation` y `min_qty_kg` como `NOT NULL` sin valor por defecto** sobre una tabla con filas. Ahora entran con defecto, se rellenan y el defecto se retira, porque la aplicación siempre envía ambos campos.
3. **Dejaba huérfanos los tipos `roast_level` y `grind_type`** tras eliminar sus columnas.

### Advertencia sobre los datos anteriores

La conversión preserva la estructura, no el significado. Un precio de 40.000 que era el costo de **una bolsa de 500 g** queda como «40.000 **por kilogramo**», y unas existencias de 100 bolsas quedan como «100 kg». La migración marca la presentación de esas filas con `Revisar: antes N g` para que no pase inadvertido, y lo correcto es **recargar los datos sobre una base limpia**.

Probada de ida, de vuelta y de ida otra vez contra la base con datos.

---

## 10. Las tres visiones que había en el repositorio

Vale la pena dejarlo escrito, porque es la causa de fondo del pivote: cuando empezó esta fase, el repositorio contenía **cuatro** definiciones distintas del producto.

| Fuente | Producto |
|---|---|
| GUIA N1–N3 (artefactos académicos) | Gestión agrícola con calendario lunar y sensores IoT, más marketplace |
| `plan pre-desarrollo/analisis_monk_grain.md` | Marketplace B2B de **exportación** a compradores internacionales |
| `docs/01-analisis-producto.md` | Minorista nacional multiactor de café **tostado** ← lo construido |
| El brief vigente | Compra y venta de **pergamino** ← lo que se construyó en esta fase |

El alcance nunca se había cerrado. Esta fase lo cierra: **pergamino seco, por kilo, en los dos sentidos del mercado.**
