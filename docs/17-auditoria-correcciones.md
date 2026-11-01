# 17 — Auditoría de estado y corrección de sus hallazgos

Registro de la auditoría del 1 de noviembre de 2026 sobre el estado en que quedó el proyecto tras el pivote, y de las correcciones que salieron de ella. Cada corrección tiene su verificación en ejecución y, donde cabe, su prueba de regresión.

**Punto de partida:** commit `00db999`, 401 pruebas, 87 % de cobertura, árbol limpio
**Estado al cierre:** 453 pruebas de backend y 41 de frontend, 87 % de cobertura

---

## 1. El patrón de fondo, otra vez

`docs/16 §1` describió el defecto característico de este proyecto: **endpoints construidos, probados y funcionando, sin forma de alcanzarlos desde la interfaz.** Lo dio por cerrado. No lo estaba: quedaban tres, y dos de ellos el README los anunciaba como funciones del vendedor.

Lo que cambia esta vez es cómo se buscaron. En lugar de revisar pantalla por pantalla, se cruzaron los 100 endpoints declarados contra todo `web/src`. Eso convierte el hallazgo en una comprobación repetible en vez de en un acto de atención.

Y aparecieron dos defectos de una familia nueva, que tampoco detecta ninguna suite: **afirmaciones falsas**. Un documento legal que promete un cifrado que no existe, y una prueba que consagra como correcto un comportamiento que es un agujero. En los dos casos el código hace exactamente lo que dice hacer; lo que está mal es lo que se dice.

---

## 2. Crítico: el límite de intentos de acceso se eludía con una cabecera

**Síntoma.** Doce intentos de inicio de sesión seguidos contra la misma cuenta, todos con credenciales equivocadas, devolvían 401 y ninguno 429. Con la dirección fija, el sexto se bloqueaba.

```
Control  — misma IP:          401 401 401 401 401 429 429 429
Ataque   — rotando la cabecera: 401 ×12, ningún 429
```

**Causa.** `client_identifier()` tomaba el **primer** elemento de `X-Forwarded-For`. Ese elemento lo escribe quien hace la petición. Nginx compone la cabecera con `$proxy_add_x_forwarded_for`, que **añade** la dirección real al final de lo que llegó: el valor falsificado queda delante y es el que se leía. **El salto funcionaba también en producción**, no solo contra el puerto 8000 expuesto en desarrollo.

Rompía el RNF-04 y contradecía lo que `docs/08 §1.9` daba por verificado.

**La prueba que lo protegía.** `test_the_ceiling_is_per_client_and_not_global` comprobaba que cambiar `X-Forwarded-For` daba cupo nuevo. La propiedad que quería fijar es legítima —un cliente pasado de cupo no debe dejar fuera a los demás—, pero la escribía sobre una cabecera falsificable. Arreglar el código sin tocar la prueba la habría puesto en rojo, y era la prueba la que estaba equivocada.

**Corrección, en dos capas.**

1. **Identificar al cliente por lo que no puede escribir.** Se lee `X-Real-IP` —que Nginx *sobreescribe* en cada petición desde `$remote_addr`—, y en su defecto el **último** elemento de `X-Forwarded-For`, que es el que añadió nuestro proxy. Las dos solo se atienden si quien abrió la conexión es nuestro propio proxy: una petición que llega desde una dirección pública no atravesó Nginx y no puede afirmar en nombre de quién viene.
2. **Un segundo tope por cuenta.** `subject_rate_limit` cuenta los intentos contra un mismo correo, sea quien los haga, y no mira ninguna cabecera. Hacen falta los dos porque cada uno deja pasar lo que el otro para: el de cliente no ve mil clientes ensayando contra una cuenta; el de cuenta no ve a un cliente recorriendo el padrón de correos. El asunto se cuenta por su resumen SHA-256, de modo que no quedan correos escritos en las claves de Redis. No distingue si la cuenta existe: hacerlo convertiría el propio límite en una forma de enumerar cuentas.

**Verificación en ejecución.** Veinte intentos rotando `X-Real-IP` y quince rotando `X-Forwarded-For`: en los dos casos el undécimo devuelve 429.

**Pruebas.** Nueve nuevas en `test_rate_limit.py`, que pasa de 10 a 19. Entre ellas: que el último salto es el que cuenta, que falsificar el primero no cambia la identidad, que las cabeceras se ignoran cuando el par no es nuestro proxy, que rotar la identidad no compra más intentos, y que agotar el cupo de una cuenta no deja fuera a las demás —porque si no, ensayar contra el correo de alguien sería una forma de impedirle entrar—.

---

## 3. Crítico: la política de privacidad afirmaba un hecho falso

**Síntoma.** Dos documentos legales publicados decían al titular que su cuenta bancaria se almacena cifrada:

> «La cuenta bancaria, que además se almacena cifrada.» — `legal/privacidad`
> «Cuenta bancaria de referencia para la liquidación, que se almacena **cifrada**» — `legal/datos`

**Realidad.** No se recoge ninguna cuenta bancaria y no hay cifrado en el proyecto. La columna `bank_account_encrypted` existe en el modelo, nunca se escribe ni se lee, y no hay ninguna librería de cifrado en las dependencias. La afirmación era falsa de principio a fin.

No es un defecto cosmético: la Ley 1581 exige que la información que se da al titular sobre el tratamiento de sus datos sea veraz, y este texto estaba publicado.

**Corrección.** Se retiró la mención de los dos documentos, y también de la lista de «qué información no se publica», donde nombrar un dato que no se recoge sobraba. Cuando exista la cuenta bancaria con su cifrado real, la cláusula vuelve —con el cifrado detrás.

---

## 4. Crítico: no había camino de pago al vendedor — **resuelto**

> **Actualización del mismo día.** Estaba bloqueado por dos decisiones de negocio. El dueño del proyecto las tomó —comisión al 2,5 % y recaudo centralizado— y la liquidación está construida y verificada de punta a punta. El detalle está en **[18 — Liquidaciones](18-liquidaciones.md)**. Lo que sigue describe el estado en que la auditoría lo encontró.

La plataforma cobra al comprador y calcula la comisión, pero el dinero no tiene salida:

| Pieza | Estado |
|---|---|
| `settlements` | 0 filas; ningún código la escribe |
| `Settlement`, `SettlementStatus` | definidos, cero usos |
| permiso `settlement.manage` | sembrado, ningún endpoint lo exige |
| `bank_account_encrypted` | columna declarada, 0 escrituras y 0 lecturas |
| cifrado | sin `fernet`, `cryptography` ni equivalente en el proyecto |

Lo único que existe es `GET /producer/settlements/summary`, que agrega comisiones pendientes —y que no se llamaba desde ninguna parte (§6)—.

**Lo que bloquea construirlo:**

- **La tasa de comisión** (§5). Define sobre qué se liquida.
- **La decisión legal D-7 de [docs/10](10-revision-legal.md): quién recauda el dinero del comprador.** Si MONK GRAIN recauda y después liquida, hay implicaciones de recaudo a nombre de terceros y tributarias, y refuerza el riesgo R-1. La arquitectura actual ya recauda —los pagos se registran contra el pedido—, así que construir la liquidación sobre esa premisa es coherente con lo que hay; pero conviene que sea una decisión tomada y no una consecuencia accidental del código.
- **La decisión D-6**, la facultad de retener fondos al vendedor, que hoy solo está escrita de cara al consumidor y sin contrato que la respalde.

**Qué haría falta, cuando se decida:** cuenta bancaria en el perfil del vendedor con cifrado real y gestión de clave; cierre de periodo que escriba la fila de `settlements`; pantalla de administración que la marque pagada con su referencia; y la vista del vendedor, que ahora sí tiene dónde encajar.

---

## 5. Alto: la comisión del 8 % era la del negocio anterior — **resuelta**

> **Actualización.** Se fijó en **2,5 %**. `Commission.rate_applied` guarda la tasa vigente al confirmar, de modo que los pedidos anteriores conservan su 8 %: se comprobó en ejecución. Ver [18 §2.1](18-liquidaciones.md).

`DEFAULT_COMMISSION_RATE = 0.08` se fijó cuando MONK GRAIN vendía bolsas de café tostado de unos 40.000 pesos. El pivote cambió el producto, la unidad y el precio, y **no revisó la tasa**: ni `docs/14` ni `docs/15` la mencionan como decisión.

Sobre los precios que hoy tiene el catálogo —de 16.800 a 31.000 el kilo—:

| Volumen | Comisión al 8 % |
|---|---|
| 1 carga (125 kg) | 168.000 – 310.000 COP |
| 10 cargas (1.250 kg) | 1.680.000 – 3.100.000 COP |

La intermediación real en pergamino —cooperativas, trilladoras, puntos de compra— opera con márgenes de un orden de magnitud menor. A estos números el caficultor vende en el punto de compra del pueblo y no vuelve.

El cálculo está bien hecho; lo que nadie volvió a mirar es la tasa. Es una decisión del dueño del negocio: contrastar con lo que cobra hoy la intermediación y decidir si la comisión sigue siendo un porcentaje, si se escalona por volumen o si pasa a ser una tarifa fija por carga.

---

## 6. Funciones construidas e inalcanzables, las que quedaban

| Función | Endpoint | Qué faltaba |
|---|---|---|
| Alertas de inventario | `GET /producer/inventory/alerts` | El panel mostraba *cuántos* lotes estaban bajos, nunca *cuáles*. El README anunciaba «control de inventario con alertas». |
| Resumen de liquidación | `GET /producer/settlements/summary` | Ninguna pantalla. El README anunciaba «resumen de liquidaciones». |
| Ajuste de inventario | `PATCH /producer/inventory/{variant_id}` | Sin llamador, pero **no bloqueaba nada**: el vendedor cambia sus kilos editando la oferta, que persiste `stock_qty` y respeta lo reservado. Es un endpoint redundante, no un camino cortado. Se deja, anotado. |

`POST /payments/webhook` también sale en el cruce y es correcto que no tenga llamador: lo invoca la pasarela, no el navegador.

**Corrección.**

- **`SettlementSummary` como schema.** El endpoint devolvía `dict[str, Decimal | int]`, sin contrato: el frontend no tenía forma de saber qué campos esperar, y de hecho nunca llegó a llamarlo. Ahora tiene schema, con su docstring explicando que es **lo acumulado y no el estado de un pago**.
- **Panel del vendedor.** Sección «Liquidación pendiente» con ventas acumuladas, comisión y neto, y sección «Lotes por reponer» con el lote, los kilos libres y el umbral que el propio vendedor fijó.
- **Se dice lo que la cifra no es.** Mientras no exista el cierre de periodo (§4), la cifra solo crece: presentarla sin más daría a entender un desembolso en camino. La pantalla lo dice con esas palabras.

**Verificación en ejecución.** Con el vendedor que tiene el lote agotado a propósito, `/producer/inventory/alerts` devuelve «La Esperanza Lote de Traspatio», 0 kg libres, umbral 124.

---

## 7. El catálogo geográfico dejaba sin comprar a media Colombia

**Síntoma.** `addresses.municipality_id` es `NOT NULL` y apunta al catálogo sembrado. Ese catálogo tenía **10 departamentos y 54 municipios**: solo la geografía cafetera. Quien no estuviera en la lista no podía crear una dirección, y sin dirección no hay checkout.

```
presentes: Medellín · Bucaramanga
ausentes:  Bogotá · Cali · Barranquilla · Cartagena
```

Es el lado equivocado del mercado. El catálogo cubría bien de dónde **sale** el pergamino y dejaba fuera dónde **está** quien lo compra: las trilladoras, las exportadoras y las comercializadoras de las capitales y los puertos. El README, además, prometía «departamentos y municipios con códigos DANE», que se lee como cobertura nacional.

**Corrección.** El catálogo completo, en un módulo aparte: `app/db/divipola.py`, con los **33 departamentos y las 1.122 entidades municipales** del DANE y su centroide. Está fuera de `seed.py` porque son mil cien líneas de datos de referencia, no lógica.

Incluye las 18 áreas no municipalizadas y la isla de San Andrés: son direcciones válidas de gente que existe, y excluirlas habría repetido el mismo error a menor escala.

**Fuente.** Conjunto `gdxc-w37w` del portal de datos abiertos del Estado colombiano, consultado el 1 de noviembre de 2026. Los nombres llegan en mayúsculas y se pasan a capitalización española conservando las partículas en minúscula. El seed sigue siendo idempotente: salta los municipios que ya existen, de modo que los 54 originales conservan sus datos.

**Verificación en ejecución.** Una compradora se registra desde cero, lee su token de verificación en Mailpit, inicia sesión y **crea su dirección en Bogotá**: `Calle 72 # 10-34, oficina 501`. Antes era imposible.

**Pruebas.** 12 nuevas en `tests/unit/test_divipola.py`: que estén los 33 departamentos, que haya más de 1.100 municipios, que no falten las cuatro ciudades que bloqueaban la compra, que **sigan estando** los municipios cafeteros originales, que no haya códigos repetidos, que el código del municipio empiece por el de su departamento, que ningún nombre llegue en mayúsculas y que las coordenadas caigan dentro de Colombia —una latitud y una longitud invertidas pasarían desapercibidas hasta que un mapa pusiera una finca en mitad del océano—.

---

## 8. Ocho enlaces muertos, en las 41 páginas del sitio

**Síntoma.** `docs/16 §5.3` dejó ocho enlaces pendientes en `Navbar` y `Footer`. Seguían ahí, y como esos dos componentes salen en todas las páginas, no eran ocho enlaces rotos: eran ocho en cada página del sitio. Dos estaban en la navegación principal.

```
404  /regiones  /blog  /nosotros  /trazabilidad
404  /sostenibilidad  /ayuda  /contacto  /envios
200  /catalogo  /vender          ← control
```

**Corrección.** Se retiraron los ocho. Las secciones «Conocer» y «Ayuda» del pie desaparecen —todos sus enlaces menos uno eran muertos— y el que sobrevivía, «Cambios y devoluciones», pasa a una sección «Mi cuenta» con rutas que sí existen. En la barra, «Regiones» y «Blog» se van; el catálogo ya filtra por región, que era lo que «Regiones» prometía.

**Escribir las ocho páginas depende del alcance del producto; quitar un `href` no.** Prometerlas en todas las páginas era peor que no tenerlas. Sus enlaces vuelven cuando exista el texto.

**Prueba.** `web/tests/navigation.test.ts`, nueva: lee los `href` de los dos componentes y los contrasta contra los `page.tsx` del árbol de rutas, resolviendo los grupos `(public)` y `(auth)`. Una tercera comprobación nombra las ocho rutas, de modo que si alguien devuelve un enlace antes que su página, la prueba lo dice por su nombre. Lleva además una comprobación de que encuentra lo que va a comparar: si se mueve un archivo, la prueba no debe pasar en vacío.

---

## 9. Las dependencias no tenían techo, y ya habían cruzado versiones mayores

**Síntoma.** Todo estaba declarado con `>=`. La imagen en uso, construida semanas antes, corría con versiones mayores distintas de las que se escribieron:

| Declarado | Instalado |
|---|---|
| `sqlalchemy>=2.0.36` | 2.1.1 |
| `mypy>=1.13` | 2.3.1 |
| `pytest>=8.3` | 9.1.1 |
| `fastapi>=0.115` | 0.141.1 |

Todo pasaba en verde, pero eso era suerte comprobada, no una garantía: cada reconstrucción volvía a tirar el dado. Ya había cobrado una vez, cuando SQLAlchemy 2.1 cambió la firma de `select()` y rompió el tipado de nueve archivos a la vez. Y el `bind-mount` de `pyproject.toml` esconde el problema, porque la declaración se ve desde dentro del contenedor sin que la instalación exista.

**Corrección, en dos capas, porque resuelven cosas distintas.**

1. **Techo de versión mayor en `pyproject.toml`**, en las 25 dependencias. En los paquetes 0.x el techo va en la minor, porque ahí es donde rompen. Esto evita el salto silencioso para quien instale de cero.
2. **`backend/requirements.lock`**, con las 77 versiones exactas del árbol completo, transitivas incluidas. Es el equivalente del `package-lock.json` que el frontend ya tenía y el backend no. El `Dockerfile` lo usa como fichero de restricciones (`pip install -c`) en las dos etapas, desarrollo y producción, y el CI también: así el CI valida lo mismo que corre en la imagen.

**Verificación en ejecución.** Se reconstruyó la imagen y se recreó el contenedor: las 77 versiones instaladas coinciden exactamente con el lock, y las 426 pruebas siguen en verde. Es la comprobación que importaba —que el techo reproduce lo que funciona, no solo que está escrito—.

**Al cambiar una dependencia** hay que subir su techo, reconstruir y regenerar el lock en el mismo cambio. El procedimiento está anotado en la cabecera del propio archivo.

---

## 10. Rastros del café tostado en mensajes que el usuario lee

El pivote limpió el modelo de datos a fondo, pero quedaron residuos en la capa que se lee. En un producto que se define por vender **solo** pergamino **solo** por kilo, cada uno resta credibilidad.

| Dónde | Decía | Dice |
|---|---|---|
| Checkout, sin existencias | «Solo quedan 40 **unidades** disponibles.» | «Solo quedan 40 **kg** disponibles.» |
| Editar una oferta | «...las 3 **unidades** ya reservadas.» | «...los 3 **kg** ya reservados.» |
| Ajustar inventario | «**unidades** reservadas por pedidos en curso» | «**kg** reservados por pedidos en curso» |
| Devoluciones | «3 de las 5 **unidades**» | «3 de los 5 **kg**» |
| Retirar una oferta | «Esta presentación tiene **unidades** reservadas» | «Esta oferta tiene **kilos** reservados» |
| Panel del vendedor, más vendidos | «1.250 **unidades**» | «1.250 **kg**» |
| `producers/router.py` | «Peso, **molienda**, precio y stock» | «Precio por kilo, mínimo de compra y kilos disponibles» |

Una prueba afirmaba sobre el texto exacto de uno de esos mensajes y se puso en rojo con el cambio. Se reescribió para comprobar **el número y la unidad** en lugar de la frase: que la redacción pueda cambiar está bien; que el vendedor sepa cuántos kilos tiene comprometidos es lo que no puede perderse.

**Lo que se deja anotado.** `ProducerType.ROASTER` sigue existiendo como tipo de *vendedor*, y entre los datos de demostración hay una tostaduría que se describe tostando café y fechando su tueste. En el comercio de pergamino una tostadora **compra**, no vende. Los datos de demostración son inventados a propósito y no pretenden ser realistas, así que no se tocaron; pero si el enum se queda, conviene que sea una decisión y no un resto.

---

## 11. Lo que se deja sin corregir, con su motivo

- **Los tokens en `sessionStorage`.** Migrarlos a cookies `httpOnly` exige protección CSRF, middleware de sesión y revisar cada pantalla que lee el token. Es cambio de arquitectura. El acceso sigue aislado en `web/src/lib/session.ts` a propósito, para que toque un solo archivo.
- **El proceso en segundo plano.** `app/workers/` sigue vacío: nada vigila el vencimiento de certificaciones, los plazos de devolución (decisión D-6) ni emite las notificaciones `DEMAND_OFFER_*`, que ya están en el enum.
- **El esquema sin código detrás:** `conversations`, `messages`, `blog_posts` y los cupones, que el carrito consume pero ningún endpoint crea. Construirlo o retirarlo es una decisión de alcance; mientras figure, un esquema promete una función que no existe.
- **La aplicación móvil** quedó **retirada del alcance** el mismo día, por decisión del dueño del proyecto: la web responsive —verificada de 360 px a 1920 px— cubre el uso desde el teléfono. `docs/01` lo recoge y `mobile/` se eliminó.
- **El remoto del repositorio.** Todo el historial vive en un solo disco y el CI nunca se ha ejecutado. Es la corrección más barata que queda y la de mayor pérdida evitada, pero crear el repositorio remoto es una acción sobre una cuenta ajena.
- **`SIM103` en `migrations/env.py`**, anterior a todo este trabajo. El CI solo revisa `app` y `tests`, de modo que no lo detecta.
- **El precio indexado al precio interno de referencia de la FNC.** Decisión consciente: exige una fuente del precio diario y decidir quién la mantiene. `FncPriceReference` está diseñada y anotada.

---

## 12. Lo medido, antes y después

| | Antes | Después |
|---|---|---|
| Pruebas de backend | 401 | **453** |
| Pruebas de frontend | 38 | **41** |
| Cobertura | 87 % | 87 % |
| Municipios en el catálogo | 54 | **1.122** |
| Departamentos | 10 | **33** |
| Enlaces muertos en la navegación | 8 | **0** |
| Endpoints sin llamador | 3 | **1**, redundante y anotado |
| Dependencias sin techo | 25 | **0** |
| Intentos de login rotando la cabecera | ilimitados | **10 por cuenta y minuto** |
| Liquidaciones generadas | imposible | **cierre, pago y auditoría** |
| Comisión por venta | 8 % (del minorista) | **2,5 %** |

`ruff`, `ruff format`, `mypy`, `tsc` y `eslint` siguen sin hallazgos.
