# 18 — Liquidación y pago al vendedor

**Fecha:** 1 de noviembre de 2026
**Alcance:** tasa de comisión, cuenta bancaria cifrada, cierre de periodo y desembolso

---

## 1. Lo que faltaba

La plataforma cobraba al comprador y calculaba la comisión, pero el dinero no tenía salida. La auditoría de [docs/17](17-auditoria-correcciones.md) lo midió así:

| Pieza | Estado antes |
|---|---|
| `settlements` | 0 filas; ningún código la escribía |
| `Settlement`, `SettlementStatus` | definidos, cero usos |
| permiso `settlement.manage` | sembrado, ningún endpoint lo exigía |
| `bank_account_encrypted` | columna declarada, 0 escrituras y 0 lecturas |
| cifrado | ninguna librería de criptografía en el proyecto |

Era el pendiente de mayor peso del proyecto: un mercado que cobra y no liquida. Y estaba bloqueado por dos decisiones que no podía tomar el desarrollo.

---

## 2. Las dos decisiones que lo desbloquearon

### 2.1 La comisión: del 8 % al 2,5 %

`DEFAULT_COMMISSION_RATE` valía `0.08`. Esa tasa venía del negocio minorista de café tostado —bolsas de unos 40.000 pesos— y **el pivote a pergamino no la revisó**: ni `docs/14` ni `docs/15` la mencionan como decisión.

Sobre los precios reales del catálogo, de 16.800 a 31.000 el kilo:

| Volumen | Al 8 % | Al 2,5 % |
|---|---|---|
| 1 carga (125 kg) | 168.000 – 310.000 | **52.500 – 96.900** |
| 10 cargas (1.250 kg) | 1.680.000 – 3.100.000 | **525.000 – 969.000** |

La intermediación real en pergamino —cooperativas, trilladoras, puntos de compra— opera con márgenes de ese orden. Al 8 % el caficultor vende en el punto de compra del pueblo y no vuelve.

**Lo que no cambió:** `Commission.rate_applied` guarda la tasa vigente al confirmar el pedido, de modo que bajar la comisión **no altera pedidos ya calculados**. Se comprobó en ejecución: un pedido anterior conserva su 8 % (1.075.000 sobre 13.437.500) mientras el siguiente cobra 2,5 % (96.875 sobre 3.875.000).

### 2.2 El flujo del dinero: recaudo centralizado

Decisión D-7 de [docs/10](10-revision-legal.md), que estaba sin resolver. Se optó por **comprador → MONK GRAIN → vendedor**: la plataforma recauda, descuenta su comisión y liquida por periodos.

Es lo que la arquitectura ya hacía —los pagos se registran contra el pedido—, así que construir la liquidación encima es coherente con lo que había. Lo que cambia es que ahora es una decisión tomada y no una consecuencia accidental del código.

> **Sigue pendiente la revisión jurídica.** El recaudo a nombre de terceros tiene implicaciones tributarias y refuerza el riesgo R-1 de la revisión legal. Que el software sepa hacerlo es cosa distinta de que la empresa pueda hacerlo: eso lo dice un abogado, no una prueba.

---

## 3. La cuenta bancaria, cifrada de verdad

La columna `bank_account_encrypted` existía desde el primer esquema y los textos legales prometían el cifrado. No había con qué cifrar: la columna nunca se escribía y el proyecto no tenía ninguna librería de criptografía. La promesa se retiró de los documentos —era falsa— y vuelve ahora que es cierta.

### Por qué Fernet y no AES a mano

Fernet trae autenticación incluida: un valor manipulado en la base **falla al descifrar** en vez de devolver basura que el programa tomaría por buena.

### La clave

`ENCRYPTION_KEY` se configura aparte. Si no está, se deriva de `SECRET_KEY` por HKDF y la aplicación **avisa al arrancar**, porque la derivación tiene una trampa que conviene conocer: `SECRET_KEY` se rota como cosa normal —es la que firma los tokens— y al rotarla los datos ya cifrados dejarían de poder leerse. En desarrollo la derivación basta; en producción no.

La derivación usa `info=b"monkgrain.field-encryption.v1"` para separar este uso de cualquier otro que llegue a derivar de la misma clave: dos propósitos distintos no deben compartir material.

### Qué se devuelve

**Nunca el número completo**, ni al propio dueño. De vuelta viajan el banco, el tipo, el titular y los cuatro últimos dígitos: lo justo para que el vendedor reconozca cuál registró y note si se equivocó de cuenta.

Al administrador **no se le devuelve en absoluto**. Es una decisión que venía del diseño original (HU-ADM-02, CA5) y se mantiene: quien dispersa los fondos consulta el dato por el canal que corresponda, no a través de un listado de la API. El listado solo dice `has_bank_account: true/false`, que es lo que necesita para saber si puede pagar.

El número se guarda limpio de guiones y espacios —así viene en el extracto del banco— para que dos formas de teclear la misma cuenta no parezcan cuentas distintas.

---

## 4. Qué entra en una liquidación

Es la parte que más importa. Pagar de más obliga a pedir dinero de vuelta, que es la situación que ninguna plataforma quiere tener que resolver.

Una comisión entra si cumple **todo** esto:

| Condición | Por qué |
|---|---|
| Está pendiente y sin liquidación asignada | Evita pagar dos veces lo mismo |
| Su sub-orden está **entregada** | No se paga café que no ha llegado. `CONFIRMED` no basta |
| La entrega cae dentro del periodo | Es lo que define un cierre |
| Pasaron **5 días hábiles** desde la entrega | El plazo de retracto del artículo 47 |
| La sub-orden **no tiene devolución viva** | Ese dinero puede tener que devolverse |
| El vendedor **tiene cuenta bancaria** | Una liquidación que nadie puede pagar es peor que ninguna |

### El plazo de retracto, y por qué no se retiene

Pagarle al vendedor antes de que venza el retracto obligaría a reclamarle el dinero cuando un comprador desiste. Esa es justo la situación que la **facultad de retención de la decisión D-6** intenta resolver, y que todavía no tiene respaldo contractual. Esperar cinco días hábiles la evita sin necesidad de retener nada.

La fecha de entrega se toma del **historial de estados**, no de la guía logística, por la misma razón que en devoluciones: el plazo no puede depender de que exista un envío bien diligenciado.

### El vendedor sin cuenta no se omite en silencio

El cierre devuelve `skipped_without_bank_account` y la pantalla lo dice con nombre: *«N vendedores quedaron fuera por no tener cuenta bancaria registrada. Su dinero sigue acumulado y entrará en el próximo cierre.»* Omitirlo callando sería la forma de que alguien dejara de cobrar sin que nadie se enterase.

### Cerrar dos veces no paga dos veces

Es el error más caro posible aquí y el más fácil de cometer: un administrador que no está seguro de haber cerrado vuelve a darle. La idempotencia es estructural, no un control añadido: al marcar cada comisión con su `settlement_id`, la segunda pasada no las encuentra.

---

## 5. El desembolso

`POST /admin/settlements/{id}/pay` marca la liquidación pagada y **cierra las comisiones que cubre** (`PENDING → SETTLED`). Sin ese último paso seguirían pendientes y el resumen del vendedor diría que se le debe dos veces.

La **referencia del pago es obligatoria**: un pago sin constancia de por dónde salió el dinero no es un pago registrado, es una casilla marcada.

Pagar dos veces se rechaza nombrando la referencia del primero, para que quien lo intente vea de inmediato que ya estaba hecho y con qué soporte.

### Auditoría

`settlement.created` y `settlement.paid` quedan en el registro inmutable con quién lo hizo, su dirección y los importes. La auditoría es de solo inserción —no hay endpoint que la edite y el rol de aplicación en PostgreSQL tampoco puede—, que es justo lo que se le pide a un registro de pagos.

**La cuenta bancaria no aparece en la auditoría.** Hay una prueba que lo comprueba.

---

## 6. Lo que ve cada quien

### El vendedor — `/productor/liquidaciones`

Lo pendiente de liquidar, la cuenta donde se le consigna y el historial con su estado y su referencia de pago. Sin cuenta registrada, el formulario se abre solo y un aviso dice lo que está en juego: *«Sin una cuenta registrada no podemos liquidarte. Tus ventas se siguen acumulando, pero el dinero no tiene a dónde ir.»*

### El administrador — `/admin/liquidaciones`

Cierre de periodo —con el mes anterior precargado, que es el caso de casi siempre— y el listado de todas las liquidaciones con su importe y su estado. Registrar un pago pide la referencia antes de dejar confirmar.

### Lo que no se promete

El resumen del panel del vendedor dice explícitamente qué es la cifra: lo acumulado, no un pago en curso. Mientras un periodo no se cierre, esa cifra solo crece, y presentarla sin más daría a entender un desembolso en camino.

---

## 7. Verificación en ejecución

El recorrido completo del dinero, contra el sistema en marcha:

```
1. El vendedor registra su cuenta       → ••••6789 de vuelta, nada más
2. Lo que quedó en PostgreSQL           → gAAAAABq54aGNXt-K6--EKMh1aln…  ilegible
3. Una compradora de Bogotá pide        → 125 kg · 3.875.000 COP
4. Comisión al 2,5 %                    → 96.875  (el pedido anterior conserva su 8 %)
5. El vendedor confirma → prepara →
   despacha con guía → entrega
6. El administrador cierra el periodo   → 1 liquidación · neto 3.778.125
7. Registra el pago                     → TRF-BA-2026-88123
8. Lo pendiente del vendedor            → 0
9. Su historial                         → pagada, con fecha y referencia
10. Auditoría                           → settlement.created · settlement.paid
11. ¿Se coló la cuenta en algún registro?  0 coincidencias
```

**27 pruebas** en `test_settlements.py`. Entre ellas: que el número no vuelva nunca completo; que lo guardado en la base no sea legible; que un pedido dentro del plazo de retracto espere; que uno sin entregar no se pague; que una reclamación viva lo retenga; que cerrar dos veces no duplique; que pagar cierre las comisiones; que pagar dos veces se rechace; que un vendedor no vea liquidaciones ajenas; y que ni el listado del administrador ni la auditoría lleven la cuenta bancaria.

---

## 8. Lo que queda

- **La revisión jurídica del recaudo** (D-7) y la **facultad de retención** (D-6), que hoy solo está escrita de cara al consumidor y sin contrato que la respalde.
- **El cierre no es automático.** Lo dispara un administrador. Automatizarlo mensualmente depende del proceso en segundo plano, que sigue sin existir (`app/workers/` está vacío).
- **No hay dispersión real de fondos.** La transferencia la hace una persona y aquí se registra su referencia. Integrarla con la pasarela es un paso posterior, y la interfaz para ello —el proveedor tras una interfaz común— ya está.
- **`SettlementStatus.DRAFT` y `CANCELLED` no se usan todavía.** Una liquidación nace en `PENDING_PAYMENT`. Quedan para cuando haya revisión previa al desembolso o haya que anular una.
