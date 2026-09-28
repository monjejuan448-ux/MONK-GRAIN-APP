# MONK GRAIN — Expediente para revisión jurídica

**Fecha:** 14 de agosto de 2026
**Destinatario:** abogado(a) colombiano(a) en ejercicio, para revisión, ajuste y firma.
**Preparado por:** equipo de desarrollo (análisis de cumplimiento normativo, no asesoría legal).
**Documentos cubiertos:**

- `web/src/app/(public)/legal/terminos/page.tsx` — Términos y condiciones
- `web/src/app/(public)/legal/datos/page.tsx` — Política de tratamiento de datos personales
- `web/src/app/(public)/legal/devoluciones/page.tsx` — Devoluciones y reembolsos
- `web/src/app/(public)/legal/privacidad/page.tsx` — Política de privacidad
- `web/src/app/(public)/legal/layout.tsx` — aviso de borrador (**no debe eliminarse hasta la firma**)

---

## 0. Advertencia sobre el alcance de este trabajo

**Quien preparó este expediente no es abogado y este documento no es asesoría legal.**

Lo que se hizo:

- Se leyó el texto vigente de las normas citadas en fuentes oficiales o en compilaciones normativas de entidades públicas (Ministerio de Comercio, DIAN, SIC, Función Pública, SUIN-Juriscol), no de memoria ni de resúmenes comerciales.
- Se contrastó cada afirmación de los cuatro documentos contra el texto de la norma correspondiente.
- Se corrigieron plazos equivocados, se eliminaron limitaciones de responsabilidad que la ley declara ineficaces y se añadieron obligaciones legales que faltaban por completo.
- Se contrastó lo que los documentos prometen contra lo que el sistema realmente hace (esquema de base de datos, servicios del backend, almacenamiento en el navegador).

Lo que **no** se hizo y sigue pendiente:

- No hay interpretación jurídica de los puntos discutibles. Donde la norma admite lecturas distintas, el documento lo señala y no decide.
- No se verificó la situación societaria, tributaria ni contable de la empresa (constitución, régimen de IVA, activos totales, responsabilidad de facturar). Varias decisiones dependen de eso.
- No se revisaron los contratos con encargados del tratamiento (alojamiento, correo, almacenamiento), que la ley exige por escrito y que hoy no constan en el proyecto.
- No se revisó jurisprudencia ni doctrina de la SIC sobre portales de contacto más allá de identificar que existe una discusión abierta y relevante (ver riesgo R-1).
- No se emite juicio sobre si los documentos «cumplen». Están más completos y más defendibles que antes; **no están aprobados**.

---

## 1. Inventario de normas aplicables

### 1.1 Protección de datos personales

| Norma | Alcance concreto para MONK GRAIN |
|---|---|
| **Ley 1581 de 2012** (estatutaria) | Régimen general. Art. 4 principios; art. 5 datos sensibles (MONK GRAIN no recoge); art. 7 prohibición de tratar datos de menores; art. 8 derechos del titular; art. 9 autorización previa e informada, obtenible por medio consultable después; art. 12 deber de informar al pedir la autorización y de conservar prueba; art. 13 a quién puede suministrarse la información; art. 14 consultas (**10 días hábiles + 5**); art. 15 reclamos (**15 días hábiles + 8**, con requerimiento en 5 días si está incompleto, desistimiento a los 2 meses, traslado en 2 días hábiles si no es competente y leyenda «reclamo en trámite» en 2 días hábiles); **art. 16 requisito de procedibilidad**: no se puede ir a la SIC sin agotar antes la consulta o el reclamo; art. 17 deberes del responsable, incluido el literal n) reporte de incidentes; art. 18 deberes del encargado; **art. 26 prohibición de transferir datos a países sin nivel adecuado**, salvo autorización expresa del titular. |
| **Decreto 1074 de 2015**, Libro 2, Parte 2, Título 2, Cap. 25 (compila el **Decreto 1377 de 2013**) | Art. 5 y 7 autorización y modos de obtenerla (el silencio nunca es autorización); art. 9 revocatoria y supresión, improcedentes si hay deber legal o contractual; art. 10 datos recolectados antes; art. 11 supresión cumplida la finalidad; **art. 13 contenido mínimo obligatorio de la política de tratamiento**, incluido el punto que faltaba: *fecha de entrada en vigencia de la política y período de vigencia de la base de datos*, y el área responsable de atender solicitudes; art. 14 y 15 aviso de privacidad y su contenido mínimo; **art. 25 contrato de transmisión con los encargados**; art. 26 responsabilidad demostrada, proporcional al tamaño de la empresa. |
| **Circular Única de la SIC, Título V** | Instrucciones sobre el RNBD y **reporte de incidentes de seguridad dentro de los 15 días hábiles** siguientes a su detección. Obliga también a quienes no están inscritos en el RNBD y a los encargados. |
| **Decreto 090 de 2018** | Redujo el universo de obligados al **RNBD**: sociedades y entidades sin ánimo de lucro con **activos totales superiores a 100.000 UVT**, y personas jurídicas de naturaleza pública. **No están obligadas las personas naturales ni las micro y pequeñas empresas.** Ver decisión D-4. |
| **Proyecto de ley estatutaria 214 de 2025** | Reforma en trámite de la Ley 1581 (nuevas bases de legitimación, sanciones hasta 10.000 SMMLV o 5 % de ingresos operacionales, régimen especial para menores, perfilamiento y decisiones automatizadas). **No es derecho vigente**; se menciona solo para que la política se diseñe con margen de ajuste. |

### 1.2 Protección al consumidor y comercio electrónico

| Norma | Alcance concreto para MONK GRAIN |
|---|---|
| **Ley 1480 de 2011** (Estatuto del Consumidor) | Art. 5 definiciones — **num. 11 define «proveedor o expendedor» como quien de manera habitual, directa o *indirectamente*, ofrezca, suministre, distribuya o comercialice productos** (clave para el riesgo R-1); art. 8 **término de la garantía legal: para perecederos, la fecha de vencimiento o expiración; un año para productos nuevos sin término indicado**; art. 10 **responsabilidad solidaria de productor y proveedor** por la garantía; art. 11 contenido de la garantía (reposición o devolución del dinero cuando el bien no admite reparación, y el transporte a cargo del obligado); art. 23 y 24 información mínima; art. 26 precio en pesos con impuestos incluidos y gastos adicionales informados por separado; **arts. 42 y 43 cláusulas abusivas ineficaces de pleno derecho**; art. 46 deberes en ventas a distancia (reclamar y devolver por los mismos medios de la transacción original); **art. 47 retracto**; **art. 50 deberes en comercio electrónico** (los ocho literales); art. 51 **reversión del pago**; art. 52 verificación de edad; **art. 53 portales de contacto**; art. 56 y 58 acciones y procedimiento. |
| **Decreto 587 de 2016** (compilado en el Decreto 1074 de 2015, Cap. 51) | Reglamenta la reversión del pago: cinco causales, queja ante el proveedor y notificación al emisor **dentro de 5 días hábiles**, contenido mínimo de una y otra, **15 días hábiles para hacer efectiva la reversión**, reversión parcial, formulario obligatorio en el sitio web de los participantes del pago. Solo aplica si proveedor y emisor están domiciliados en Colombia y si se usó un instrumento de pago electrónico. |
| **Decreto 735 de 2013** | Efectividad de la garantía: respuesta escrita a la reclamación en **15 días hábiles** indicando procedencia o improcedencia, y devolución del dinero dentro de los **15 días hábiles** siguientes a que el consumidor ponga el bien a disposición. |
| **Ley 527 de 1999** | Equivalencia funcional del mensaje de datos. Sostiene la validez de la aceptación electrónica de los términos y del expediente probatorio que exige el art. 50 lit. e) de la Ley 1480. |
| **Ley 2300 de 2023** | Comunicaciones comerciales: solo por los canales expresamente autorizados, con límites de horario y frecuencia. Aplica a empresas de comercio electrónico. |

### 1.3 Producto, tributario y contable

| Norma | Alcance concreto para MONK GRAIN |
|---|---|
| **Resolución 810 de 2021 (MinSalud)** | Etiquetado nutricional y frontal de alimentos empacados. **El café sin ingredientes añadidos está exceptuado** del etiquetado nutricional; no lo está el café con añadidos. Obligación del vendedor, no de la plataforma, pero conviene verificarlo en el proceso de habilitación. |
| **Denominación de origen «Café de Colombia»** | Administrada por la Federación Nacional de Cafeteros por delegación de la SIC (Resolución 41083 de 2010). Solo puede usarla quien esté autorizado. Relevante porque el catálogo permite declarar origen y certificaciones. |
| **Art. 616-1 E.T. y Resolución DIAN 000165 de 2023** | La obligación de expedir la factura electrónica de venta es **de quien vende**; **la plataforma de comercio electrónico debe poner a disposición un servicio que permita expedirla y entregarla al consumidor final**. Ver riesgo R-6. |
| **Art. 28 de la Ley 962 de 2005 y art. 60 del Código de Comercio** | Libros, papeles y comprobantes del comerciante: **diez (10) años** desde el último asiento, documento o comprobante. Es el plazo al que remite el art. 50 lit. e) de la Ley 1480 para conservar la prueba de la relación comercial. |

---

## 2. Qué se corrigió y por qué

Se listan solo los cambios de fondo.

### 2.1 Devoluciones (`devoluciones/page.tsx`)

| # | Antes | Ahora | Fundamento |
|---|---|---|---|
| C-1 | «Puedes reclamar dentro de los **treinta (30) días** siguientes a la entrega» | La garantía legal dura **hasta la fecha de vencimiento** impresa en el empaque; un año si no se indica | Art. 8 Ley 1480. El plazo anterior recortaba la garantía legal por debajo del mínimo: cláusula ineficaz de pleno derecho (art. 43 num. 1 y 2) y conducta sancionable |
| C-2 | «Reembolso, **una vez aprobado**: hasta 30 días calendario» | El retracto se devuelve **completo, sin descuentos ni retenciones, en máximo 30 días calendario desde que se ejerció el derecho** | Art. 47 inc. final Ley 1480. El texto anterior condicionaba a una aprobación que la ley no contempla y corría el plazo desde la fecha equivocada |
| C-3 | Un solo plazo de respuesta de 15 días hábiles, sin distinguir | Se separan: respuesta escrita a la garantía en **15 días hábiles**; devolución por garantía en **15 días hábiles** desde que se pone el bien a disposición; devolución por retracto en **30 días calendario** | Decreto 735 de 2013 y art. 47 Ley 1480 |
| C-4 | La exclusión del café abierto se justificaba solo por sentido común | Se ancla en el art. 47 («devolver por los mismos medios y en las mismas condiciones en que lo recibió») y se explicita que MONK GRAIN **concede** el retracto pese a que los numerales 4 y 6 del art. 47 excluyen los perecederos | Art. 47 Ley 1480. Ver decisión D-1 |
| C-5 | No existía | Sección completa de **reversión del pago**: causales, doble trámite en 5 días hábiles, contenido mínimo, 15 días hábiles de los participantes del pago, reversión parcial, advertencia sobre el cargo definitivo si la controversia se resuelve contra el consumidor | Art. 51 Ley 1480 y Decreto 587 de 2016 |
| C-6 | No existía | Sección **si el pedido no llega o llega tarde**: entrega máxima de 30 días calendario, terminación unilateral y devolución total sin descuentos | Art. 50 lit. h) Ley 1480 |
| C-7 | «La garantía la responde **el vendedor**» a secas | Se mantiene que el vendedor es el obligado directo, **pero se añade que nada limita ni traslada la responsabilidad legal de MONK GRAIN** y se cita expresamente la solidaridad del art. 10 y la ineficacia del art. 43 | Arts. 10, 42 y 43 Ley 1480. El texto anterior era, en la práctica, una cláusula de exoneración |
| C-8 | No existía | Constancia obligatoria de fecha, hora y número de radicación; reclamos y devoluciones por los mismos medios de la compra; enlace visible a la SIC; competencia del juez del domicilio de la relación de consumo; plazo de caducidad de un año | Arts. 46 num. 2, 50 lit. g) y parágrafo, 58 num. 2 y 3 Ley 1480 |

### 2.2 Términos y condiciones (`terminos/page.tsx`)

| # | Cambio | Fundamento |
|---|---|---|
| C-9 | Identificación del operador ampliada con **dirección de notificación judicial**, teléfono y correo, en lista | Art. 50 lit. a) Ley 1480 |
| C-10 | Se añade el bloque de deberes del art. 50: disponibilidad y plazo de validez de la oferta, medios de pago, **resumen del pedido antes de concluir con derecho a corregir o cancelar**, **acuse de recibo a más tardar el día calendario siguiente**, gastos de envío informados por separado, conservación de la prueba de la relación comercial por el término de los documentos de comercio, mecanismo de PQR con constancia | Art. 50 lit. b) a h) Ley 1480 |
| C-11 | Se reconoce expresamente la condición de **portal de contacto** y los deberes del art. 53, incluida la entrega de los datos del vendedor a quien compró y a la autoridad | Art. 53 Ley 1480 |
| C-12 | La sección de responsabilidad deja de operar como exoneración: se afirma que MONK GRAIN responde por la seguridad de las transacciones realizadas por los medios que dispone, **sean propios o ajenos**, y que ninguna cláusula limita la responsabilidad legal | Art. 50 lit. f) y arts. 42-43 Ley 1480 |
| C-13 | La suspensión de cuenta ya no queda al arbitrio sin consecuencias: se informa el motivo, no afecta el dinero pagado ni los pedidos en curso, no priva de la garantía | Art. 43 num. 5, 6 y 7 Ley 1480 |
| C-14 | Los cambios de términos que impliquen nuevas obligaciones o cobros **requieren aceptación expresa**; el silencio no vale | Art. 43 num. 9 y art. 50 lit. d) inc. final Ley 1480 |
| C-15 | La cláusula de jurisdicción se conserva pero **se subordina expresamente** al derecho del consumidor de acudir a la SIC o al juez del lugar de la relación de consumo | Arts. 43, 56 y 58 Ley 1480. Ver decisión D-5 |
| C-16 | Base de la comisión precisada: 8 % sobre el **valor de los productos**, sin incluir el envío. Verificado contra el código (`backend/app/modules/orders/service.py`: `commission_amount = sub_subtotal * commission_rate`) | Art. 23 Ley 1480 (información veraz y precisa) |
| C-17 | Licencia de contenidos del vendedor acotada: gratuita, no exclusiva, limitada a la plataforma y a la difusión del catálogo, **termina al retirar la publicación o cerrar la cuenta**; el vendedor declara ser titular | El texto anterior («materiales de difusión») era una licencia indefinida y sin límite de alcance |
| C-18 | Se añade la obligación del vendedor de expedir la factura electrónica y de cumplir la normativa sanitaria e INVIMA, y el límite al uso de la denominación de origen | Art. 616-1 E.T. / Res. DIAN 000165 de 2023; Res. 810 de 2021; Res. SIC 41083 de 2010 |
| C-19 | Comunicaciones comerciales solo por canales autorizados, revocables | Ley 2300 de 2023 |
| C-20 | Verificación de mayoría de edad referida a su norma | Art. 52 Ley 1480 |

### 2.3 Tratamiento de datos (`datos/page.tsx`)

| # | Cambio | Fundamento |
|---|---|---|
| C-21 | Se añaden los dos elementos obligatorios que faltaban: **área o cargo responsable** de atender solicitudes y **período de vigencia de la base de datos** con fecha de entrada en vigencia de la política | Art. 13 del Decreto 1377 (Decreto 1074 de 2015, Cap. 25). Su ausencia hacía incompleta la política |
| C-22 | «Presentar quejas ante la SIC» sin más | Se advierte el **requisito de procedibilidad**: hay que agotar antes la consulta o el reclamo | Art. 16 Ley 1581 |
| C-23 | El trámite de reclamos se detalla: requerimiento en 5 días si está incompleto, desistimiento a los 2 meses, traslado en 2 días hábiles, leyenda «reclamo en trámite» | Art. 15 Ley 1581 |
| C-24 | No existía | Apartado de **datos sensibles**: se declara que no se recogen y qué pasaría si se recogieran (carácter facultativo, autorización explícita) | Arts. 5 y 6 Ley 1581; art. 15 Decreto 1377 |
| C-25 | No existía | Apartado de **transferencia internacional** con marcador `[país o países]` y autorización expresa del titular | Art. 26 Ley 1581. Ver riesgo R-3 |
| C-26 | «Lo reportaremos a la autoridad conforme a la ley» | Plazo concreto: **15 días hábiles** a la SIC desde la detección | Circular Única SIC, Título V; art. 17 lit. n) Ley 1581 |
| C-27 | «después durante el plazo que exijan las obligaciones legales aplicables» | Tabla de conservación con **10 años** para soportes contables (verificado) y marcadores `[plazo definido por la empresa]` para lo demás | Art. 28 Ley 962 de 2005 y art. 60 C.Co. Ver decisión D-3 |
| C-28 | No existía | Apartado sobre el **RNBD** con el umbral de 100.000 UVT y marcador para que la empresa declare si está obligada | Decreto 090 de 2018. Ver decisión D-4 |
| C-29 | «La pasarela de pagos procesa el cobro» presentado como hecho | Se añade el recuadro de **estado actual con proveedor simulado**, igual que en términos | El texto afirmaba algo que hoy no ocurre |
| C-30 | Los proveedores de tecnología no aparecían | Se identifican como **encargados del tratamiento** sujetos a contrato escrito con confidencialidad y seguridad | Art. 25 Decreto 1377; art. 18 Ley 1581. Ver riesgo R-4 |
| C-31 | El vendedor aparecía solo como destinatario | Se aclara que al recibir los datos del comprador **se convierte en responsable independiente** con finalidad limitada | Arts. 4, 13 y 17 Ley 1581. Ver riesgo R-5 |
| C-32 | «Contraseña que se guarda cifrada» | «Se transforma con un algoritmo de un solo sentido»: técnicamente exacto sin volverse jerga | Precisión. Verificado: Argon2id |
| C-33 | Inventario de datos incompleto | Se añaden foto de perfil, idioma, preferencia de correos comerciales, dirección de notificaciones y teléfono del vendedor, historia y fotos, solicitudes de devolución | Contrastado con `backend/app/models/user.py` y `producer.py` |

### 2.4 Privacidad (`privacidad/page.tsx`)

| # | Cambio | Fundamento |
|---|---|---|
| C-34 | **Contradicción resuelta.** El documento prometía que «nunca» se hacen públicos el correo y el teléfono del vendedor, promesa que chocaba de frente con el deber del art. 53 de entregar sus datos de identificación a quien compró | Se conserva la reserva frente al catálogo y se explica la excepción legal: los datos se entregan a quien tiene un reclamo concreto y a la autoridad, no se publican | Art. 53 Ley 1480 |
| C-35 | Se omitía el **carrito anónimo**, que sí sobrevive al cierre de la pestaña (`localStorage`) mientras la sesión no (`sessionStorage`) | Se declara y se explica la diferencia | Verificado en `web/src/lib/session.ts`. La afirmación anterior era incompleta |
| C-36 | No existía | Ley 2300 de 2023 sobre mensajes comerciales, con límites de canal, horario y frecuencia | Ley 2300 de 2023 |
| C-37 | No existía | Enlace a la SIC y advertencia del requisito de procedibilidad | Art. 50 par. Ley 1480; art. 16 Ley 1581 |
| C-38 | No existía | Regla de prelación: si esta página contradice la política de tratamiento de datos, prevalece aquella | Evita que un texto «en lenguaje llano» genere obligaciones distintas de las de la política formal |

---

## 3. Decisiones de negocio pendientes

Ninguna puede resolverla el equipo de desarrollo. Cada una cambia el texto de los documentos.

1. **D-1 — ¿Se concede el retracto sobre café?**
   El art. 47 num. 4 y 6 de la Ley 1480 excluye los bienes perecederos y los que pueden deteriorarse o caducar con rapidez. El café tostado tiene fecha de vencimiento y podría quedar cubierto. El borrador **opta por conceder el retracto** sobre café sin abrir, por ser más favorable al consumidor y comercialmente sensato. La empresa debe confirmar esa decisión y el abogado validar que la redacción no genere una obligación mayor de la querida. Si se decide invocar la excepción, hay que reescribir toda la sección 2 de devoluciones.

2. **D-2 — ¿Quién asume el transporte de la devolución por retracto?**
   Por ley lo asume el consumidor (art. 47 inc. 2), y así está redactado. La empresa puede decidir asumirlo como política comercial. Si lo hace, hay que decir quién lo paga entre MONK GRAIN y el vendedor, y reflejarlo en la liquidación.

3. **D-3 — Plazos de conservación.**
   Los soportes contables quedan en 10 años (verificado). Faltan dos: **registros de auditoría y seguridad** y **datos de cuenta tras el cierre**. Ambos figuran como `[plazo definido por la empresa]` en la sección 10 de la política de datos.

4. **D-4 — ¿Aplica el RNBD?**
   Depende de los **activos totales** de la sociedad frente al umbral de 100.000 UVT del Decreto 090 de 2018. Si no supera el umbral y no es persona jurídica pública, no está obligada a inscribirse — pero **el deber de reportar incidentes de seguridad a la SIC en 15 días hábiles subsiste igual**. Debe completarse el marcador de la sección 12 de la política de datos.

5. **D-5 — Cláusula de jurisdicción.**
   Está redactada acotada para no chocar con el art. 58 de la Ley 1480. La empresa debe elegir la ciudad y el abogado confirmar si conviene mantener la cláusula o suprimirla, dado que frente a un consumidor tiene efecto limitado.

6. **D-6 — Retención de fondos al vendedor.**
   La sección 9 de devoluciones dice que MONK GRAIN «puede retener o descontar el valor en su liquidación» cuando una reclamación procede y el vendedor no responde. Eso es una **facultad de retención sobre dinero ajeno** y necesita: criterio jurídico sobre su validez, definición de en qué momento y con qué prueba se activa, y consagración expresa en el contrato con el vendedor. Hoy solo está en el documento de cara al consumidor.

7. **D-7 — ¿Quién recibe el dinero del comprador?**
   Si MONK GRAIN recauda y luego liquida al vendedor, hay implicaciones de recaudo a nombre de terceros, tributarias y —muy probablemente— de refuerzo del riesgo R-1. Debe definirse el flujo real antes de activar la pasarela.

8. **D-8 — Régimen de IVA e impuestos en el precio.**
   Los documentos afirman que los precios incluyen los impuestos aplicables. Debe confirmarse con el contador qué impuestos aplican al café en cada presentación y quién es responsable de recaudarlos.

9. **D-9 — Alcance del uso de contenidos del vendedor.**
   La licencia se acotó a la plataforma y a la difusión del catálogo, y termina al retirar la publicación. Si mercadeo pretende usar fotos de fincas en campañas después de que el productor se retire, hay que decirlo y remunerarlo o acordarlo aparte.

10. **D-10 — Plazo de validez de la oferta.**
    El art. 50 lit. b) obliga a informarlo y el documento ya lo promete. Debe definirse un valor y mostrarlo en la ficha de producto.

11. **D-11 — Fechas de entrada en vigencia.**
    Cada documento tiene «Vigente desde [fecha]». Deben ser posteriores a la firma del abogado y anteriores al primer usuario real. La política de datos, además, requiere fecha de entrada en vigencia como contenido obligatorio (art. 13 Decreto 1377).

---

## 4. Datos a completar

Todos los marcadores entre corchetes que quedan en los cuatro documentos.

### 4.1 Identificación de la empresa (aparece en varios documentos)

- `[Razón social]` — términos §1, datos §1
- `[número]` (NIT) — términos §1, datos §1
- `[dirección]` y `[ciudad]` — términos §1 y §14, datos §1
- `[teléfono]` — términos §1 y §15, datos §1, devoluciones §5
- `[correo]` — términos §1, §8, §12 y §15; datos §1 y §8; privacidad §6 y §8; devoluciones §5

> El correo aparece con tres funciones distintas (datos personales, PQR, comunicaciones comerciales). Puede ser el mismo o pueden ser tres; decidirlo antes de reemplazar.

### 4.2 Fechas

- `[fecha]` de vigencia y de última actualización — **en los cuatro documentos**, dos por documento.

### 4.3 Protección de datos

- `[área o cargo designado]` — datos §1. Persona o área que tramita peticiones, consultas y reclamos.
- `[país o países]` — datos §6, alojamiento de la información fuera de Colombia.
- `[plazo definido por la empresa]` — datos §10, dos ocurrencias (auditoría/seguridad y datos de cuenta tras el cierre).
- `[Indicar si la empresa está o no obligada y, si lo está, la fecha de inscripción.]` — datos §12, RNBD.

---

## 5. Puntos de riesgo que requieren criterio jurídico

**R-1 — ¿Es MONK GRAIN un simple portal de contacto o también un «proveedor»? (riesgo alto)**
El art. 5 num. 11 de la Ley 1480 define proveedor como quien de manera habitual, **directa o indirectamente**, ofrezca, suministre, distribuya o comercialice productos, con o sin ánimo de lucro. MONK GRAIN exhibe el catálogo, gestiona el carrito y el checkout, confirma el pedido, interviene en el flujo del pago, cobra una comisión del 8 % y liquida al vendedor. Un consumidor que demande ante la SIC puede sostener que la plataforma comercializa indirectamente, y en tal caso el art. 10 la haría **solidariamente responsable de la garantía legal**, y el art. 43 num. 1, 2 y 4 haría ineficaz cualquier cláusula que lo niegue. Existe discusión doctrinal y decisiones de la SIC sobre este punto que **no se analizaron aquí**. Los documentos se redactaron para no depender de esa exoneración: afirman que el vendedor es el obligado directo, pero no niegan la responsabilidad legal de la plataforma. **El abogado debe decidir si esa posición es la correcta o si conviene asumir explícitamente la solidaridad**, y en función de eso revisar el contrato con vendedores, el seguro y la provisión contable.

**R-2 — El art. 53 exige datos que el sistema no guarda (riesgo alto, es también un defecto técnico)**
El art. 53 obliga a llevar un registro con **nombre o razón social, documento de identificación, dirección física de notificaciones y teléfono** de cada oferente. El modelo `ProducerProfile` (`backend/app/models/producer.py`) guarda `legal_name` y `document_number`, pero **no tiene campo de dirección física** —solo departamento y municipio— y el teléfono vive en `users.phone`, que es **opcional** (`nullable=True`). Los documentos ya prometen ese registro. Hay que crear el campo de dirección de notificaciones, hacer obligatorio el teléfono del vendedor, y habilitar el mecanismo por el que un comprador consulta esos datos. **Publicar los textos sin ese desarrollo es prometer algo que el sistema no puede cumplir.**

**R-3 — Transferencia internacional de datos (riesgo medio)**
El proyecto se declara sin operación internacional, pero eso se refiere al comercio, no al alojamiento. Si el hosting, el correo transaccional o el almacenamiento de archivos están fuera de Colombia, hay transferencia internacional y aplica el art. 26 de la Ley 1581. El texto ya incluye la autorización expresa del titular —la excepción del literal a)— y un marcador de país. **Debe verificarse dónde reside realmente cada servicio antes de publicar**, y el abogado debe valorar si la autorización dentro de la política es suficiente o si conviene un consentimiento separado.

**R-4 — No hay contratos de transmisión con los encargados (riesgo medio)**
El art. 25 del Decreto 1377 exige contrato escrito con cada encargado, con alcance, actividades y obligaciones de seguridad y confidencialidad. La política ya afirma que existen. **Hoy no constan en el proyecto.** Es una afirmación que hay que respaldar antes de publicar.

**R-5 — El vendedor como responsable independiente (riesgo medio)**
El vendedor recibe nombre, teléfono y dirección del comprador. Los documentos ahora dicen que a partir de ese momento responde por su cuenta y con finalidad limitada, pero **eso debe quedar pactado en el contrato con el vendedor**, no solo declarado frente al consumidor. Sin ese pacto, un uso indebido por parte del vendedor puede escalar hacia MONK GRAIN.

**R-6 — Facturación electrónica (riesgo medio)**
El art. 616-1 del E.T. y la Resolución DIAN 000165 de 2023 obligan a las plataformas de comercio electrónico a **poner a disposición un servicio que permita al vendedor expedir y entregar la factura electrónica al consumidor final**. Los términos ya lo prometen. No se verificó que ese servicio exista en el producto. Debe confirmarse con el contador y con el equipo técnico.

**R-7 — El flujo de devoluciones no distingue retracto de garantía (riesgo medio, defecto técnico) — ✅ RESUELTO**
El enum `ReturnReason` (`backend/app/models/enums.py`) admitía `DAMAGED`, `WRONG_ITEM`, `QUALITY` y `OTHER`. **No existía una causal de retracto**, pese a que el documento instruye al comprador a elegir entre retractarse y reclamar por defecto. Las dos vías tienen plazos, costos de transporte y consecuencias distintas, y no podían compartir un mismo `OTHER`.

> **Remediación (fase 17).** Se añadió `WITHDRAWAL` y se construyó el módulo completo: plazos calculados en **días hábiles colombianos** (Ley 51 de 1983 y Pascua, sin tabla que mantener), cinco días para el retracto y quince para la respuesta escrita; treinta días calendario para el reembolso del retracto contados **desde que se ejerce**, no desde la aprobación; transporte de vuelta a cargo de quien corresponda según el motivo; importe del reembolso calculado por el servidor sin campo por donde rebajarlo; rechazo obligatoriamente motivado; y constancia con número de radicación, fecha y hora. Detalle en [docs/11](11-devoluciones.md). Queda pendiente, y anotado allí, la vigilancia automática del vencimiento de los quince días hábiles, que depende de la decisión **D-6**.

**R-8 — Obligaciones de interfaz que los documentos ya prometen (riesgo medio)**
Al añadir los deberes del art. 50 se prometieron comportamientos que deben existir en la aplicación antes de publicar: resumen del pedido descargable e imprimible antes de concluir, **acuse de recibo enviado a más tardar el día calendario siguiente**, constancia de radicación de PQR con fecha y hora, disponibilidad y plazo de validez de la oferta en la ficha, gastos de envío informados por separado, y **enlace visible a la SIC** (exigido por el parágrafo del art. 50; hoy solo aparece dentro de los textos legales, y conviene evaluar si debe ir también en el pie de página del sitio). Cada una es un requisito legal, no un detalle de producto.

**R-9 — La reversión del pago exige infraestructura (riesgo bajo hoy, alto al activar la pasarela)**
El Decreto 587 exige un **formulario de solicitud de reversión disponible en el sitio web** de los participantes del proceso de pago, y que el proveedor emita constancia de la queja con fecha y causal. Mientras el proveedor de pago sea simulado no aplica, y así se advierte en el documento. **Debe volver a revisarse antes de activar cobro real.**

**R-10 — Menores de edad (riesgo bajo)**
El art. 52 de la Ley 1480 obliga a «tomar las medidas posibles» para verificar la edad del consumidor. Hoy solo hay una declaración del usuario. El abogado debe valorar si eso basta para el riesgo del producto (café) o si se requiere algo más.

**R-11 — Reforma en trámite (informativo)**
El proyecto de ley estatutaria 214 de 2025 reformaría la Ley 1581 con sanciones sustancialmente mayores. No es derecho vigente. Conviene fijar una fecha de revisión de la política.

---

## 6. Checklist previo a la publicación

**Jurídico**

- [ ] Un abogado colombiano en ejercicio revisó, ajustó y aprobó los cuatro documentos.
- [ ] Se resolvieron las once decisiones de la sección 3.
- [ ] Se tomó posición expresa sobre R-1 (portal de contacto frente a proveedor) y se ajustó el contrato con vendedores en consecuencia.
- [ ] Existe contrato con el vendedor que recoge: deberes del art. 53, condición de responsable independiente de datos (R-5), obligación de facturar y la facultad de retención de D-6.
- [ ] Existen contratos de transmisión firmados con cada encargado del tratamiento (R-4).

**Datos personales**

- [ ] Todos los marcadores de la sección 4.3 están completos.
- [ ] Se verificó en qué país reside cada servicio de tecnología y se completó `[país o países]`.
- [ ] Se designó formalmente el área o cargo responsable de atender solicitudes de titulares.
- [ ] Se definió si aplica el RNBD y, de aplicar, se hizo la inscripción.
- [ ] Existe un procedimiento interno documentado para consultas (10+5) y reclamos (15+8) y para reportar incidentes a la SIC en 15 días hábiles.
- [ ] La casilla de autorización en el registro es **una acción afirmativa**, no una casilla premarcada, y queda prueba consultable de la autorización con fecha y hora.

**Producto y comercio electrónico**

- [ ] El registro del art. 53 está completo: dirección física de notificaciones y teléfono obligatorios para todo vendedor (R-2), con mecanismo de consulta para el comprador.
- [x] El flujo de devoluciones distingue retracto de garantía (R-7). *Hecho en la fase 17; ver [docs/11](11-devoluciones.md).*
- [ ] Están implementados el resumen del pedido descargable, el acuse de recibo del día siguiente, la constancia de PQR y la disponibilidad y validez de la oferta en la ficha (R-8).
- [ ] El enlace a la SIC es visible y fácilmente identificable.
- [ ] Existe el servicio que permite al vendedor expedir y entregar la factura electrónica (R-6).

**Cierre**

- [ ] Las fechas de vigencia son posteriores a la firma y anteriores al primer usuario real.
- [ ] Se retiró el aviso de borrador de `legal/layout.tsx` — **y solo entonces**.
- [ ] Se archivó la versión firmada y se fijó fecha de revisión periódica.

---

## 7. Fuentes consultadas

- Ley 1480 de 2011, texto completo publicado en el normograma del Ministerio de Comercio, Industria y Turismo.
- Ley 1581 de 2012, texto completo (copia publicada por entidad pública, contrastada con el Gestor Normativo de Función Pública).
- Decreto 1377 de 2013 (compilado en el Decreto 1074 de 2015, Cap. 25), compilación normativa pública.
- Decreto 587 de 2016, texto completo publicado en el normograma del Ministerio de Comercio, Industria y Turismo.
- Decreto 735 de 2013 y Decreto 090 de 2018, a través de fuentes oficiales de MinCIT y SIC.
- Circular Única de la SIC, Título V (protección de datos personales), publicación de la SIC.
- Resolución DIAN 000165 de 2023, normograma de la DIAN.
- Ley 962 de 2005 art. 28 y art. 60 del Código de Comercio, sobre conservación de libros y papeles.
- Resolución 810 de 2021 (MinSalud) y Resolución SIC 41083 de 2010 (denominación de origen «Café de Colombia»).

**Limitación de la verificación:** los portales de la SIC, Función Pública y SUIN-Juriscol presentaron fallos de certificado o de conexión durante esta revisión, por lo que parte del texto normativo se tomó de compilaciones publicadas por otras entidades públicas (MinCIT, DIAN, ICBF). El contenido citado se contrastó entre al menos dos fuentes cuando fue posible, **pero conviene que el abogado confirme el texto vigente en la fuente oficial**, en especial la Circular Única de la SIC, que se modifica con frecuencia y de la que aquí solo se pudo consultar una síntesis.
