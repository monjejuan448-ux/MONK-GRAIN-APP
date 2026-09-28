# MONK GRAIN — Fase 2: Historias de Usuario y Criterios de Aceptación

Este documento traduce los requisitos funcionales de la [Fase 1](01-analisis-producto.md) en historias de usuario ejecutables.

**Convenciones**
- **ID:** `HU-<ROL>-<n>` — VIS (Visitante), CC (Comprador consumidor), CE (Comprador empresarial), PRO (Productor/vendedor), ADM (Administrador), TRX (Transversal).
- **Prioridad:** `MVP` = entra al primer release · `F2` = fase 2, preparada pero no implementada.
- **Estimación:** puntos de historia (escala Fibonacci: 1, 2, 3, 5, 8, 13). Son estimaciones reales del equipo, no valores de plantilla.
- **Criterios de aceptación:** formato Dado / Cuando / Entonces. Cada CA debe ser verificable por una prueba automatizada o manual sin ambigüedad.

---

## A. Visitante

### HU-VIS-01 — Explorar la página de inicio
**Como** visitante no registrado **quiero** ver una página de inicio que explique qué es MONK GRAIN y muestre cafés destacados **para** entender la propuesta y decidir si me registro.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-02.1

- **CA1** — Dado que ingreso a la raíz del sitio, cuando carga la página, entonces veo barra de navegación con logo, buscador, y los botones "Comprar café" y "Vender café".
- **CA2** — Dado que la página cargó, entonces veo al menos: banner principal con mensaje de valor, categorías destacadas, productos recomendados, cafés por región, historias de productores, sección de trazabilidad y pie de página completo.
- **CA3** — Dado que pulso "Vender café", entonces soy dirigido al formulario de registro de productor.
- **CA4** — Dado que no hay productos publicados aún, entonces las secciones de catálogo muestran un estado vacío con mensaje explicativo, nunca un bloque roto o en blanco.

### HU-VIS-02 — Consultar el catálogo sin registrarme
**Como** visitante **quiero** navegar el catálogo completo **para** evaluar la oferta antes de crear una cuenta.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-02.1

- **CA1** — Dado que entro al catálogo, entonces veo los productos publicados y aprobados, paginados, con imagen, nombre, productor, región, perfil de taza, precio, presentación, disponibilidad y calificación.
- **CA2** — Dado que estoy en el catálogo, cuando alterno entre vista cuadrícula y vista lista, entonces la preferencia se mantiene mientras navego.
- **CA3** — Dado que pulso "Agregar al carrito" siendo visitante, entonces se me invita a iniciar sesión o registrarme, conservando el producto seleccionado tras autenticarme.
- **CA4** — Dado que un producto está agotado o su vendedor fue suspendido, entonces no aparece como comprable en el catálogo.

### HU-VIS-03 — Buscar y filtrar cafés
**Como** visitante **quiero** buscar por texto y aplicar filtros técnicos **para** encontrar cafés que se ajusten a lo que busco.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-02.2, RF-02.3, RF-02.4

- **CA1** — Dado que escribo en el buscador, entonces obtengo resultados que coincidan con nombre de producto, nombre de productor/marca o región.
- **CA2** — Dado que estoy en el catálogo, cuando aplico filtros de departamento, municipio, variedad, proceso, nivel de tueste, certificación, rango de precio o puntaje de catación, entonces los filtros se combinan entre sí y los resultados se actualizan.
- **CA3** — Dado que apliqué filtros, entonces los filtros activos quedan reflejados en la URL, de modo que puedo compartir o recargar la búsqueda sin perderla.
- **CA4** — Dado que ordeno por precio, popularidad, calificación o novedad, entonces el orden se aplica sobre el conjunto ya filtrado.
- **CA5** — Dado que ninguna combinación de filtros arroja resultados, entonces veo un estado vacío con sugerencia de ampliar criterios y opción de limpiar filtros.

### HU-VIS-04 — Ver el detalle de un café con su trazabilidad
**Como** visitante **quiero** ver toda la información de origen y calidad de un café **para** confiar en lo que estoy considerando comprar.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-03.1, RF-03.2, RF-03.3

- **CA1** — Dado que abro una ficha de producto, entonces veo galería de imágenes, nombre, marca/productor, precio, presentaciones disponibles, tipo (verde/tostado/molido), peso, nivel de tueste, proceso, variedad, altitud, región y municipio.
- **CA2** — Dado que la ficha cargó, entonces veo el perfil sensorial, puntaje de catación, fecha de cosecha y de tueste, certificaciones y prácticas sostenibles del productor.
- **CA3** — Dado que la ficha muestra el origen, entonces la ubicación se presenta a nivel de municipio/vereda aproximada; **nunca** se expone la coordenada exacta de la finca.
- **CA4** — Dado que existen reseñas del producto, entonces veo el promedio de calificación y el listado de reseñas; si no hay ninguna, veo un estado vacío invitando a ser el primero.
- **CA5** — Dado que existen productos similares, entonces veo una sección de productos relacionados de la misma región o variedad.

### HU-VIS-05 — Conocer a los productores
**Como** visitante **quiero** explorar productores y ver su perfil público **para** conocer el origen humano detrás del café.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-02.5, RF-04.1

- **CA1** — Dado que entro a la sección de productores, entonces veo el listado con foto/imagen de finca, nombre, ubicación, descripción breve y calificación, filtrable por departamento, región y tipo de productor (caficultor, finca, cooperativa).
- **CA2** — Dado que abro un perfil de productor, entonces veo portada, logo/fotografía, historia de la finca o marca, ubicación aproximada, tipo de producción, certificaciones, prácticas ambientales, galería, productos publicados y reseñas.
- **CA3** — Dado que veo un perfil de productor, entonces existe un botón de contacto o solicitud comercial que, si no estoy autenticado, me lleva a registro/login.

### HU-VIS-06 — Leer contenido educativo
**Como** visitante **quiero** leer artículos sobre café, regiones y sostenibilidad **para** aprender y ganar confianza en la plataforma.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-12.1, RF-12.2

- **CA1** — Dado que entro al blog, entonces veo artículos publicados con título, imagen, categoría, fecha y extracto.
- **CA2** — Dado que uso el buscador o filtro por categoría (preparación, regiones cafeteras, historias, sostenibilidad, comercio justo, noticias), entonces los resultados se acotan correctamente.
- **CA3** — Dado que abro un artículo, entonces veo su contenido completo y una llamada a la acción para registrarme o explorar el catálogo.

---

## B. Comprador consumidor

### HU-CC-01 — Registrarme con verificación de correo
**Como** persona interesada **quiero** crear una cuenta verificada **para** poder comprar café.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-01.1, RF-01.2

- **CA1** — Dado que envío el formulario con correo válido y contraseña que cumple la política mínima (12+ caracteres), entonces se crea la cuenta en estado `pending_verification` y recibo un correo con enlace de verificación.
- **CA2** — Dado que el correo ya está registrado, entonces recibo un mensaje genérico que no confirma ni niega la existencia de la cuenta (evita enumeración de usuarios).
- **CA3** — Dado que abro el enlace de verificación válido y no expirado, entonces mi cuenta pasa a `active` y puedo iniciar sesión.
- **CA4** — Dado que el enlace expiró (más de 24 h), entonces se me ofrece reenviar la verificación.
- **CA5** — Dado que intento iniciar sesión sin haber verificado, entonces el acceso se bloquea con un mensaje que explica el motivo y permite reenviar el correo.

### HU-CC-02 — Iniciar sesión y recuperar mi contraseña
**Como** usuario registrado **quiero** autenticarme y poder recuperar el acceso si olvido la contraseña **para** no perder mi cuenta.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-01.2

- **CA1** — Dado que ingreso credenciales correctas, entonces recibo access token y refresh token, y accedo a mi panel.
- **CA2** — Dado que fallo la contraseña varias veces consecutivas, entonces se aplica rate limiting con bloqueo temporal creciente.
- **CA3** — Dado que solicito recuperación, entonces recibo un enlace de un solo uso válido por 1 hora; al usarlo puedo fijar una nueva contraseña y todas mis sesiones activas se invalidan.
- **CA4** — Dado que solicito recuperación con un correo no registrado, entonces la respuesta es idéntica a la del caso exitoso (no revela si el correo existe).

### HU-CC-03 — Gestionar mi perfil y mis direcciones
**Como** comprador **quiero** administrar mis datos y direcciones de entrega **para** agilizar mis compras.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-01.6, RF-06.2

- **CA1** — Dado que edito mi perfil, entonces puedo actualizar nombre, teléfono y foto, y los cambios persisten.
- **CA2** — Dado que agrego una dirección, entonces debo seleccionar departamento y municipio de un listado oficial de Colombia (no texto libre), más dirección, barrio, indicaciones y teléfono de contacto.
- **CA3** — Dado que tengo varias direcciones, entonces puedo marcar una como predeterminada y eliminar las que no uso.
- **CA4** — Dado que una dirección está asociada a un pedido en curso, entonces su eliminación es lógica y el pedido conserva la dirección con la que fue creado.

### HU-CC-04 — Guardar cafés en favoritos
**Como** comprador **quiero** guardar cafés que me interesan **para** volver a ellos después.
**Prioridad:** MVP · **Estimación:** 3 · **Trazabilidad:** RF-06.3

- **CA1** — Dado que estoy autenticado, cuando marco un producto como favorito desde el catálogo o la ficha, entonces queda guardado y el ícono refleja el estado.
- **CA2** — Dado que entro a mi lista de favoritos, entonces veo los productos guardados con su disponibilidad actual y puedo agregarlos al carrito o quitarlos de la lista.
- **CA3** — Dado que un producto favorito dejó de estar disponible, entonces se muestra marcado como no disponible en lugar de desaparecer sin explicación.

### HU-CC-05 — Agregar productos al carrito
**Como** comprador **quiero** un carrito que conserve mi selección **para** completar la compra cuando esté listo.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-05.1, RF-05.2

- **CA1** — Dado que selecciono una variante (presentación/peso/molienda) con stock y pulso agregar, entonces el ítem entra al carrito con esa variante y cantidad, y el contador se actualiza.
- **CA2** — Dado que cierro sesión y vuelvo a entrar, entonces mi carrito conserva los ítems (carrito persistente asociado al usuario).
- **CA3** — Dado que agregué como visitante y luego inicio sesión, entonces el carrito anónimo se fusiona con el carrito de mi cuenta sin duplicar ítems.
- **CA4** — Dado que la cantidad solicitada supera el stock disponible, entonces el sistema lo impide y muestra el máximo disponible.
- **CA5** — Dado que veo el carrito, entonces se muestran precio unitario, subtotal por ítem, costo de envío estimado, descuentos aplicados y total.
- **CA6** — Dado que un producto en mi carrito cambió de precio o quedó agotado desde que lo agregué, entonces se me notifica el cambio antes de continuar al checkout.

### HU-CC-06 — Aplicar un cupón de descuento
**Como** comprador **quiero** aplicar un código promocional **para** obtener el descuento vigente.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-05.2

- **CA1** — Dado que ingreso un código válido y vigente, entonces el descuento se refleja en el total y se identifica el cupón aplicado.
- **CA2** — Dado que el cupón está expirado, agotado, no aplica a los productos de mi carrito o ya lo usé el máximo de veces permitido, entonces recibo un mensaje que explica el motivo concreto del rechazo.
- **CA3** — Dado que el pedido se confirma con cupón, entonces queda registrado el uso del cupón asociado a mi usuario y a ese pedido.

### HU-CC-07 — Completar el checkout
**Como** comprador **quiero** finalizar mi compra en un flujo claro **para** recibir mi café.
**Prioridad:** MVP · **Estimación:** 13 · **Trazabilidad:** RF-05.3, RF-05.4

- **CA1** — Dado que inicio el checkout, entonces recorro los pasos de datos del comprador, dirección de entrega, método de envío, resumen, método de pago y aceptación de términos.
- **CA2** — Dado que mi carrito contiene productos de más de un productor, entonces el pedido se divide automáticamente en sub-órdenes por vendedor, cada una con su propio envío y estado, bajo un mismo número de pedido principal.
- **CA3** — Dado que confirmo la compra en el MVP, entonces el pago se procesa de forma **simulada**, se crea el pedido en estado `pending` y veo una pantalla de pedido exitoso con su número.
- **CA4** — Dado que no acepto los términos y políticas, entonces no puedo confirmar la compra.
- **CA5** — Dado que ocurre un error durante la confirmación, entonces no se crea un pedido parcial ni se descuenta inventario: la operación es atómica.
- **CA6** — Dado que el pedido se creó, entonces el inventario de cada variante comprada se descuenta y se genera la notificación al comprador y a cada productor involucrado.

### HU-CC-08 — Consultar mis pedidos y su estado
**Como** comprador **quiero** ver el historial y estado de mis pedidos **para** saber cuándo llega mi café.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-05.5, RF-06.1

- **CA1** — Dado que entro a mis pedidos, entonces veo el listado con número, fecha, productos, total y estado actual.
- **CA2** — Dado que abro un pedido, entonces veo el detalle de cada sub-orden por vendedor, con su propio estado e historial de cambios fechado.
- **CA3** — Dado que un pedido cambia de estado, entonces recibo notificación en la aplicación y por correo.

### HU-CC-09 — Seguir mi envío
**Como** comprador **quiero** consultar el estado del envío **para** anticipar la entrega.
**Prioridad:** MVP (simulado) · **Estimación:** 5 · **Trazabilidad:** RF-10.2

- **CA1** — Dado que mi pedido fue despachado, entonces veo el código de seguimiento, el transportador y la fecha estimada de entrega.
- **CA2** — Dado que existen novedades logísticas registradas, entonces las veo en la línea de tiempo del envío.
- **CA3** — Dado que en el MVP no hay integración real con transportadora, entonces los datos de seguimiento provienen de un proveedor simulado, claramente identificado como tal en el entorno de desarrollo.

### HU-CC-10 — Calificar y reseñar un café
**Como** comprador **quiero** dejar mi opinión sobre un café que compré **para** ayudar a otros compradores.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-11.1

- **CA1** — Dado que un pedido mío fue entregado, entonces puedo calificar (1-5) y escribir una reseña de cada producto de ese pedido.
- **CA2** — Dado que no he comprado el producto, entonces no puedo reseñarlo (solo compras verificadas).
- **CA3** — Dado que ya reseñé un producto de un pedido, entonces no puedo duplicar la reseña, pero sí editarla dentro de un plazo definido.
- **CA4** — Dado que publico una reseña, entonces el promedio de calificación del producto y del productor se recalculan automáticamente.

### HU-CC-11 — Descargar comprobantes
**Como** comprador **quiero** descargar el comprobante de mi pedido **para** mis registros.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-05.6

- **CA1** — Dado que mi pedido fue confirmado, entonces puedo descargar un comprobante en PDF con número de pedido, fecha, vendedor, ítems, subtotal, descuentos, envío, total en COP y datos de entrega.
- **CA2** — Dado que solicito el comprobante de un pedido que no es mío, entonces recibo error de autorización.

### HU-CC-12 — Recibir notificaciones
**Como** comprador **quiero** enterarme de lo que pasa con mis pedidos **para** no tener que revisar manualmente.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-11.2

- **CA1** — Dado que ocurre un evento relevante (pedido confirmado, despachado, entregado, cancelado, reembolsado), entonces recibo notificación en la aplicación y por correo.
- **CA2** — Dado que entro a mi configuración de notificaciones, entonces puedo activar o desactivar las notificaciones por correo de tipo comercial, sin poder desactivar las transaccionales críticas.
- **CA3** — Dado que tengo notificaciones sin leer, entonces el indicador refleja la cantidad y puedo marcarlas como leídas.

### HU-CC-13 — Escribir al vendedor
**Como** comprador **quiero** hacer una consulta al productor **para** resolver dudas antes o después de comprar.
**Prioridad:** MVP (asíncrono) · **Estimación:** 8 · **Trazabilidad:** RF-11.3

- **CA1** — Dado que estoy autenticado, entonces puedo iniciar una conversación asociada a un producto o a un pedido con su vendedor.
- **CA2** — Dado que envío un mensaje, entonces el vendedor recibe notificación y puede responder desde su panel.
- **CA3** — Dado que el chat en tiempo real está fuera del MVP, entonces la mensajería funciona de forma asíncrona con recarga/consulta, sin conexión persistente.
- **CA4** — Dado que un mensaje contiene contenido con formato o enlaces, entonces se sanitiza antes de almacenarse y renderizarse.

### HU-CC-14 — Cancelar un pedido
**Como** comprador **quiero** cancelar un pedido que aún no fue despachado **para** corregir un error de compra.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-05.5

- **CA1** — Dado que mi sub-orden está en estado `pending` o `confirmed`, entonces puedo solicitar su cancelación indicando un motivo.
- **CA2** — Dado que la sub-orden ya fue despachada, entonces la cancelación no está disponible y se me indica el proceso de devolución.
- **CA3** — Dado que una cancelación se aprueba, entonces el inventario reservado se restituye y el estado pasa a `cancelled` con registro en el historial.

---

## C. Comprador empresarial

### HU-CE-01 — Registrar mi perfil empresarial
**Como** empresa (tostador, distribuidor, cafetería) **quiero** una cuenta empresarial **para** acceder a condiciones comerciales de volumen.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-01.4, RF-13.1

- **CA1** — Dado que me registro como empresa, entonces aporto razón social, NIT, tipo de empresa, datos de contacto comercial, departamento y municipio.
- **CA2** — Dado que mi perfil empresarial se crea, entonces queda en estado `pending` hasta verificación administrativa, conservando mientras tanto las capacidades de comprador consumidor.
- **CA3** — Dado que mi perfil fue verificado, entonces accedo a precios mayoristas y a las funciones B2B habilitadas.

### HU-CE-02 — Ver precios mayoristas
**Como** comprador empresarial verificado **quiero** ver el precio por volumen **para** evaluar la compra.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-04.4, RF-13.1

- **CA1** — Dado que soy empresa verificada y el producto tiene precio mayorista, entonces veo el precio mayorista y la cantidad mínima requerida.
- **CA2** — Dado que soy comprador consumidor o visitante, entonces **no** veo precios mayoristas en ninguna vista ni respuesta de API.
- **CA3** — Dado que alcanzo la cantidad mínima mayorista en el carrito, entonces el precio aplicado es el mayorista y el total lo refleja.

### HU-CE-03 — Solicitar una muestra
**Como** comprador empresarial **quiero** pedir una muestra de un lote **para** catarlo antes de comprar volumen.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-03.4, RF-13.2

- **CA1** — Dado que soy empresa verificada y el producto admite muestras, entonces veo el botón "Solicitar muestra" en la ficha.
- **CA2** — Dado que envío la solicitud, entonces el productor la recibe en su panel con mis datos comerciales y puede aceptarla o rechazarla.
- **CA3** — Dado que no soy comprador empresarial, entonces el botón no está disponible.

### HU-CE-04 — Solicitar una cotización
**Como** comprador empresarial **quiero** solicitar cotización por volumen **para** negociar condiciones.
**Prioridad:** MVP (formulario) · **Estimación:** 8 · **Trazabilidad:** RF-13.2

- **CA1** — Dado que solicito cotización, entonces indico producto, cantidad, presentación, fecha requerida y observaciones.
- **CA2** — Dado que envío la solicitud, entonces el productor la ve en su panel y puede responder con una propuesta de precio y condiciones.
- **CA3** — Dado que en el MVP la negociación conversacional no está implementada, entonces el flujo se limita a solicitud y respuesta única, quedando el ciclo de contraofertas para fase 2.

### HU-CE-05 — Gestionar usuarios de mi empresa y repetir pedidos
**Como** empresa **quiero** varios usuarios en mi cuenta y poder repetir pedidos anteriores **para** operar mi abastecimiento recurrente.
**Prioridad:** **F2** · **Estimación:** 13 · **Trazabilidad:** RF-13.1 (extensión)

- **CA1** — Dado que soy administrador de la cuenta empresarial, entonces puedo invitar usuarios con permisos de compra o solo consulta.
- **CA2** — Dado que tengo un pedido anterior, entonces puedo recrearlo con un clic, ajustando cantidades antes de confirmar.
- **CA3** — Esta historia **no entra al MVP**; el modelo de datos debe dejar previsto el vínculo usuario↔empresa desde el inicio para no requerir migración destructiva.

---

## D. Productor / Vendedor

### HU-PRO-01 — Registrarme como productor
**Como** caficultor, finca o cooperativa **quiero** registrarme como vendedor **para** comercializar mi café.
**Prioridad:** MVP · **Estimación:** 13 · **Trazabilidad:** RF-01.3

- **CA1** — Dado que inicio el registro, entonces indico tipo de vendedor (caficultor, finca, cooperativa, tostador), nombre o razón social, número de identificación (cédula/NIT), datos de contacto, departamento y municipio.
- **CA2** — Dado que continúo, entonces registro información de la finca o empresa, capacidad de producción, tipo de café y certificaciones que poseo.
- **CA3** — Dado que cargo documentos de validación, entonces solo se aceptan PDF/JPG/PNG dentro del límite de tamaño configurado, validados por tipo real de archivo y no solo por extensión.
- **CA4** — Dado que registro información bancaria para liquidación, entonces se almacena de forma cifrada y nunca se devuelve completa en respuestas de API.
- **CA5** — Dado que completo el registro y acepto los términos comerciales, entonces mi cuenta queda en estado `pending_approval` y no puedo publicar productos hasta ser aprobado.
- **CA6** — Dado que mi solicitud es aprobada o rechazada, entonces recibo notificación por correo con el resultado y, si fue rechazada, el motivo.

### HU-PRO-02 — Construir el perfil público de mi finca o marca
**Como** productor aprobado **quiero** contar la historia de mi finca **para** diferenciarme y generar confianza.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-04.1

- **CA1** — Dado que edito mi perfil, entonces puedo cargar portada, logo/foto, historia, tipo de producción, prácticas ambientales y galería de imágenes.
- **CA2** — Dado que indico la ubicación de mi finca, entonces el sistema almacena el municipio y una ubicación aproximada; la coordenada exacta **no** se publica.
- **CA3** — Dado que guardo cambios, entonces el perfil público se actualiza y es visible para visitantes.

### HU-PRO-03 — Publicar un café
**Como** productor **quiero** publicar mi café con toda su información técnica **para** que los compradores lo evalúen.
**Prioridad:** MVP · **Estimación:** 13 · **Trazabilidad:** RF-04.2, RF-03.1

- **CA1** — Dado que creo un producto, entonces registro nombre comercial, descripción, marca, finca, departamento, municipio, región cafetera, tipo de café, estado (verde/tostado/molido), variedad, proceso, nivel de tueste, altitud, perfil sensorial, puntaje de catación, fecha de cosecha, fecha de tueste, condiciones de almacenamiento y tiempo de despacho.
- **CA2** — Dado que subo imágenes, entonces se exige al menos una, con validación de tipo y tamaño, y puedo ordenarlas eligiendo la principal.
- **CA3** — Dado que defino presentaciones, entonces puedo crear variantes por peso y molienda, cada una con su propio precio e inventario.
- **CA4** — Dado que faltan campos obligatorios, entonces el formulario indica exactamente cuáles y no permite publicar.
- **CA5** — Dado que publico un producto, entonces queda visible en el catálogo si mi cuenta está aprobada; si la moderación de catálogo está activa, queda en revisión.

### HU-PRO-04 — Editar y despublicar mis productos
**Como** productor **quiero** actualizar o retirar mis publicaciones **para** mantener la oferta al día.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-04.2

- **CA1** — Dado que edito un producto, entonces los cambios se reflejan en el catálogo tras guardar.
- **CA2** — Dado que despublico un producto, entonces deja de ser comprable pero se conserva en los pedidos históricos que lo incluyen.
- **CA3** — Dado que intento editar un producto de otro productor, entonces recibo error de autorización.

### HU-PRO-05 — Gestionar mi inventario
**Como** productor **quiero** controlar el stock de cada presentación **para** no vender lo que no tengo.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-04.3

- **CA1** — Dado que actualizo el stock de una variante, entonces el catálogo refleja la disponibilidad inmediatamente.
- **CA2** — Dado que una variante llega a cero, entonces se marca como agotada y no puede añadirse al carrito.
- **CA3** — Dado que el stock cae por debajo del umbral que definí, entonces recibo una alerta de bajo inventario.
- **CA4** — Dado que se confirma un pedido, entonces el stock se descuenta de forma consistente incluso ante compras simultáneas del mismo lote (control de concurrencia).

### HU-PRO-06 — Definir precios minoristas y mayoristas
**Como** productor **quiero** fijar precios distintos según el tipo de comprador **para** atender minoristas y volumen.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-04.4

- **CA1** — Dado que edito un producto, entonces puedo definir precio minorista y, opcionalmente, precio mayorista con cantidad mínima.
- **CA2** — Dado que defino precio mayorista, entonces solo es visible para compradores empresariales verificados.
- **CA3** — Dado que cambio un precio, entonces los pedidos ya creados conservan el precio con el que fueron confirmados.

### HU-PRO-07 — Gestionar los pedidos que recibo
**Como** productor **quiero** administrar mis pedidos **para** despachar a tiempo.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-07.2, RF-05.5

- **CA1** — Dado que recibo un pedido, entonces lo veo en mi panel con comprador, ítems, cantidades, total y dirección de entrega, y recibo notificación.
- **CA2** — Dado que gestiono una sub-orden, entonces puedo avanzar su estado (confirmado → preparado → enviado) registrando la información correspondiente.
- **CA3** — Dado que marco como enviado, entonces registro transportador y código de seguimiento, y el comprador recibe la notificación.
- **CA4** — Dado que intento saltar estados de forma inválida (por ejemplo de `pending` a `delivered`), entonces el sistema lo rechaza.

### HU-PRO-08 — Ver mis ventas y estadísticas
**Como** productor **quiero** ver cómo va mi negocio **para** tomar decisiones.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-07.1

- **CA1** — Dado que entro a mi panel, entonces veo ventas totales, pedidos pendientes, productos activos, ingresos del periodo y productos más vendidos.
- **CA2** — Dado que filtro por rango de fechas, entonces las métricas se recalculan para ese periodo.
- **CA3** — Dado que veo mis ingresos, entonces se distingue el monto bruto, la comisión de MONK GRAIN y el neto a liquidar.

### HU-PRO-09 — Gestionar mis certificaciones y documentos
**Como** productor **quiero** mantener mis certificados vigentes **para** respaldar la calidad de mi café.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-04.5

- **CA1** — Dado que cargo un certificado, entonces registro tipo, entidad emisora, número, fecha de emisión y fecha de vencimiento, adjuntando el archivo.
- **CA2** — Dado que un certificado está próximo a vencer, entonces recibo una alerta con anticipación configurable.
- **CA3** — Dado que un certificado venció, entonces deja de mostrarse como vigente en mi perfil público y en mis productos.

### HU-PRO-10 — Responder solicitudes comerciales
**Como** productor **quiero** atender solicitudes de muestra y cotización **para** cerrar negocios con empresas.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-13.2, RF-11.3

- **CA1** — Dado que recibo una solicitud de muestra o cotización, entonces la veo en mi panel con los datos del solicitante y del producto.
- **CA2** — Dado que respondo una cotización, entonces indico precio propuesto, condiciones y vigencia de la oferta, y el comprador es notificado.
- **CA3** — Dado que una solicitud lleva más del tiempo definido sin respuesta, entonces se marca como vencida.

### HU-PRO-11 — Configurar mis datos de liquidación
**Como** productor **quiero** registrar dónde recibir mi dinero **para** cobrar mis ventas.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-07.4, RF-09.4

- **CA1** — Dado que configuro mi cuenta bancaria, entonces registro banco, tipo de cuenta, número y titular, almacenados de forma cifrada.
- **CA2** — Dado que consulto mis liquidaciones, entonces veo el detalle por periodo con ventas, comisión descontada y monto neto.
- **CA3** — Dado que en el MVP no hay dispersión real de fondos, entonces las liquidaciones se calculan y registran, pero se marcan como pendientes de pago manual.

---

## E. Administrador

### HU-ADM-01 — Aprobar o rechazar productores
**Como** administrador **quiero** validar a los vendedores antes de que publiquen **para** garantizar la confianza de la plataforma.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-08.1

- **CA1** — Dado que entro a la bandeja de aprobaciones, entonces veo los productores pendientes con sus datos, documentos cargados y fecha de solicitud.
- **CA2** — Dado que apruebo un productor, entonces su cuenta pasa a `approved`, puede publicar y recibe notificación.
- **CA3** — Dado que rechazo un productor, entonces debo registrar un motivo obligatorio que se le comunica.
- **CA4** — Dado que apruebo o rechazo, entonces la acción queda en el log de auditoría con administrador, fecha, decisión y motivo.

### HU-ADM-02 — Gestionar usuarios y roles
**Como** administrador **quiero** administrar cuentas y permisos **para** operar la plataforma con seguridad.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-08.2, RF-01.5

- **CA1** — Dado que busco un usuario, entonces puedo filtrar por rol, estado y fecha de registro.
- **CA2** — Dado que gestiono un usuario, entonces puedo suspender, reactivar o cambiar su rol.
- **CA3** — Dado que suspendo a un vendedor, entonces sus productos dejan de ser comprables sin borrarse.
- **CA4** — Dado que cambio un rol o suspendo una cuenta, entonces queda registrado en auditoría.
- **CA5** — Dado que soy administrador, entonces **no** puedo ver contraseñas ni datos bancarios completos de ningún usuario.

### HU-ADM-03 — Gestionar categorías y catálogo
**Como** administrador **quiero** organizar y moderar el catálogo **para** mantener la calidad de la oferta.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-08.2

- **CA1** — Dado que gestiono categorías, entonces puedo crear, editar, reordenar y desactivar categorías sin romper los productos asociados.
- **CA2** — Dado que reviso productos, entonces puedo despublicar uno que incumpla las políticas, registrando el motivo y notificando al productor.
- **CA3** — Dado que la moderación previa está activada, entonces los productos nuevos requieren aprobación antes de aparecer en el catálogo.

### HU-ADM-04 — Supervisar pedidos y pagos
**Como** administrador **quiero** ver toda la operación transaccional **para** resolver incidencias.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-08.2, RF-09.3

- **CA1** — Dado que consulto pedidos, entonces puedo filtrar por estado, vendedor, comprador y rango de fechas.
- **CA2** — Dado que abro un pedido, entonces veo su trazabilidad completa: sub-órdenes, eventos de pago, envíos y cambios de estado con su autor.
- **CA3** — Dado que un pago fue rechazado o reembolsado, entonces el evento queda visible con su motivo.

### HU-ADM-05 — Configurar comisiones y liquidaciones
**Como** administrador **quiero** definir la comisión de la plataforma **para** operar el modelo de negocio.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-08.3, RF-09.4

- **CA1** — Dado que configuro la comisión, entonces puedo definir un porcentaje global y, opcionalmente, excepciones por categoría o vendedor.
- **CA2** — Dado que cambio la comisión, entonces el nuevo valor aplica solo a pedidos futuros; los pedidos existentes conservan la comisión con la que se calcularon.
- **CA3** — Dado que consulto liquidaciones, entonces veo por vendedor y periodo: ventas brutas, comisión y neto a pagar.
- **CA4** — Dado que modifico la comisión, entonces la acción queda auditada.

### HU-ADM-06 — Moderar reseñas y contenido
**Como** administrador **quiero** atender reportes de contenido **para** mantener un espacio confiable.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-08.2

- **CA1** — Dado que una reseña fue reportada, entonces aparece en la cola de moderación con el motivo del reporte.
- **CA2** — Dado que modero una reseña, entonces puedo ocultarla o mantenerla, registrando la decisión.
- **CA3** — Dado que oculto una reseña, entonces el promedio de calificación del producto se recalcula excluyéndola.

### HU-ADM-07 — Gestionar contenido, banners y cupones
**Como** administrador **quiero** administrar la vitrina y las promociones **para** impulsar las ventas.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-08.2, RF-12.1

- **CA1** — Dado que gestiono banners y secciones destacadas de la página de inicio, entonces puedo publicarlos, programarlos y despublicarlos.
- **CA2** — Dado que creo un cupón, entonces defino código, tipo de descuento, valor, vigencia, límite de usos, monto mínimo y alcance (global, categoría o vendedor).
- **CA3** — Dado que publico un artículo del blog, entonces defino título, contenido, categoría, imagen y estado de publicación.

### HU-ADM-08 — Consultar métricas y exportar reportes
**Como** administrador **quiero** medir el desempeño de la plataforma **para** tomar decisiones.
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RF-08.4

- **CA1** — Dado que entro al dashboard, entonces veo usuarios registrados, productores pendientes, ventas del periodo, comisiones generadas, pedidos por estado y productos publicados.
- **CA2** — Dado que filtro por rango de fechas, entonces todas las métricas se recalculan.
- **CA3** — Dado que exporto un reporte, entonces obtengo el archivo en CSV o PDF con los mismos datos y filtros aplicados en pantalla.

### HU-ADM-09 — Auditar la actividad del sistema
**Como** administrador **quiero** revisar quién hizo qué **para** responder ante incidentes.
**Prioridad:** MVP · **Estimación:** 5 · **Trazabilidad:** RF-08.5, RNF-11

- **CA1** — Dado que consulto el log de auditoría, entonces veo actor, acción, entidad afectada, fecha/hora y detalle del cambio.
- **CA2** — Dado que filtro por usuario, tipo de acción o fecha, entonces obtengo el subconjunto correspondiente.
- **CA3** — Dado que un registro de auditoría existe, entonces **no** puede editarse ni eliminarse desde la aplicación, por ningún rol.

---

## F. Transversales

### HU-TRX-01 — Experiencia responsive y accesible
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RNF-06, RNF-07

- **CA1** — Dado que uso la plataforma entre 360 px y 1920 px de ancho, entonces la navegación, el catálogo y el checkout son plenamente usables sin desbordes horizontales.
- **CA2** — Dado que navego solo con teclado, entonces puedo completar registro, login y checkout, con foco visible en cada control.
- **CA3** — Dado que se evalúa el contraste de texto y controles, entonces cumple WCAG AA como mínimo.
- **CA4** — Dado que una vista depende de datos remotos, entonces tiene definidos sus estados de carga, error y vacío.

### HU-TRX-02 — Seguridad de la sesión y los datos
**Prioridad:** MVP · **Estimación:** 8 · **Trazabilidad:** RNF-04, RNF-05

- **CA1** — Dado que se almacena una contraseña, entonces se cifra con Argon2 o bcrypt; nunca en texto plano ni con hash reversible.
- **CA2** — Dado que mi access token expira, entonces el refresh token permite renovar la sesión, y puede ser revocado individualmente.
- **CA3** — Dado que cierro sesión, entonces el refresh token queda invalidado del lado del servidor.
- **CA4** — Dado que un endpoint requiere un rol específico, entonces se valida en el backend, no solo ocultando la opción en la interfaz.
- **CA5** — Dado que se registra un usuario, entonces se solicita consentimiento explícito de tratamiento de datos conforme a la Ley 1581 de 2012, y queda registrado.

### HU-TRX-03 — Internacionalización preparada
**Prioridad:** MVP (infraestructura) · **Estimación:** 5 · **Trazabilidad:** RNF-09

- **CA1** — Dado que la interfaz muestra texto, entonces proviene de archivos de traducción, no de literales incrustados en los componentes.
- **CA2** — Dado que el MVP se publica solo en español, entonces la estructura permite añadir inglés sin refactorizar componentes.
- **CA3** — Dado que se muestran precios, entonces el formato de moneda (COP) y de fecha se resuelven por configuración regional, no hardcodeados.

---

## G. Matriz de trazabilidad RF ↔ HU

| RF | Descripción breve | Historias que lo cubren |
|---|---|---|
| RF-01.1 / 01.2 | Registro, verificación, login, recuperación | HU-CC-01, HU-CC-02 |
| RF-01.3 | Registro y validación de productor | HU-PRO-01, HU-ADM-01 |
| RF-01.4 | Perfil empresarial | HU-CE-01 |
| RF-01.5 | Control de acceso por roles | HU-ADM-02, HU-TRX-02 |
| RF-01.6 | Gestión de perfil | HU-CC-03 |
| RF-02.1 / 02.2 / 02.3 / 02.4 | Catálogo, búsqueda, filtros, orden | HU-VIS-01, HU-VIS-02, HU-VIS-03 |
| RF-02.5 | Listado de productores | HU-VIS-05 |
| RF-03.1 / 03.2 / 03.3 | Ficha de producto y trazabilidad | HU-VIS-04 |
| RF-03.4 | Acciones de compra y muestra | HU-CC-05, HU-CE-03 |
| RF-04.1 | Perfil público del productor | HU-PRO-02, HU-VIS-05 |
| RF-04.2 | Publicación y edición de productos | HU-PRO-03, HU-PRO-04 |
| RF-04.3 | Inventario | HU-PRO-05 |
| RF-04.4 | Precios minorista/mayorista | HU-PRO-06, HU-CE-02 |
| RF-04.5 | Certificaciones y documentos | HU-PRO-09 |
| RF-05.1 / 05.2 | Carrito y totales | HU-CC-05, HU-CC-06 |
| RF-05.3 / 05.4 | Checkout y sub-órdenes | HU-CC-07 |
| RF-05.5 | Estados del pedido | HU-CC-08, HU-CC-14, HU-PRO-07 |
| RF-05.6 | Comprobantes | HU-CC-11 |
| RF-06.1 / 06.2 / 06.3 | Panel del comprador | HU-CC-03, HU-CC-04, HU-CC-08 |
| RF-07.1 / 07.2 | Panel del productor | HU-PRO-07, HU-PRO-08 |
| RF-07.4 | Datos de liquidación | HU-PRO-11 |
| RF-08.1 | Aprobación de productores | HU-ADM-01 |
| RF-08.2 | Gestión administrativa | HU-ADM-02, HU-ADM-03, HU-ADM-04, HU-ADM-06, HU-ADM-07 |
| RF-08.3 | Comisiones | HU-ADM-05 |
| RF-08.4 | Métricas y exportación | HU-ADM-08 |
| RF-08.5 | Auditoría | HU-ADM-09 |
| RF-09.x | Pagos (arquitectura) | HU-CC-07, HU-ADM-04, HU-PRO-11 |
| RF-10.1 / 10.2 / 10.3 | Envíos y seguimiento | HU-CC-09, HU-PRO-07 |
| RF-11.1 | Reseñas | HU-CC-10, HU-ADM-06 |
| RF-11.2 | Notificaciones | HU-CC-12 |
| RF-11.3 | Mensajería | HU-CC-13, HU-PRO-10 |
| RF-12.1 / 12.2 | Blog y contenido | HU-VIS-06, HU-ADM-07 |
| RF-13.1 / 13.2 | Comercio B2B | HU-CE-01, HU-CE-02, HU-CE-03, HU-CE-04, HU-CE-05 (F2) |

**Cobertura:** todos los RF de la Fase 1 tienen al menos una historia asociada. Toda historia tiene al menos un RF de origen. No existen historias huérfanas ni requisitos sin cubrir.

---

## H. Agrupación propuesta en sprints

Total estimado del MVP: **~330 puntos** (excluyendo las historias marcadas F2).

| Sprint | Foco | Historias | Puntos |
|---|---|---|---|
| 1 | Cimientos: autenticación, roles, perfiles | HU-CC-01, HU-CC-02, HU-CC-03, HU-TRX-02, HU-PRO-01, HU-ADM-01 | ~47 |
| 2 | Catálogo y descubrimiento | HU-VIS-01, HU-VIS-02, HU-VIS-03, HU-VIS-04, HU-VIS-05, HU-PRO-02 | ~39 |
| 3 | Publicación e inventario del productor | HU-PRO-03, HU-PRO-04, HU-PRO-05, HU-PRO-06, HU-PRO-09 | ~36 |
| 4 | Carrito, checkout y pedidos | HU-CC-04, HU-CC-05, HU-CC-06, HU-CC-07, HU-CC-14 | ~34 |
| 5 | Operación de pedidos y envíos | HU-PRO-07, HU-PRO-08, HU-CC-08, HU-CC-09, HU-CC-11 | ~31 |
| 6 | Paneles administrativos y comisiones | HU-ADM-02, HU-ADM-03, HU-ADM-04, HU-ADM-05, HU-ADM-09 | ~37 |
| 7 | Confianza y comunidad | HU-CC-10, HU-CC-12, HU-CC-13, HU-ADM-06, HU-ADM-07 | ~34 |
| 8 | B2B, contenido y cierre de calidad | HU-CE-01, HU-CE-02, HU-CE-03, HU-CE-04, HU-VIS-06, HU-ADM-08, HU-PRO-10, HU-PRO-11, HU-TRX-01, HU-TRX-03 | ~65 |

El orden respeta las dependencias reales: no hay catálogo sin cuentas y roles, no hay carrito sin productos publicados, no hay panel administrativo de pedidos sin pedidos existentes.

---

## I. Definition of Ready y Definition of Done

**Una historia entra a sprint solo si:**
- Tiene criterios de aceptación redactados y verificables.
- Tiene trazabilidad a un RF de la Fase 1.
- Tiene estimación acordada por el equipo.
- Tiene definidos sus estados de interfaz (carga, error, vacío) cuando aplica.
- Sus dependencias técnicas están disponibles o mockeadas.

**Una historia se considera terminada solo si:**
- Todos sus criterios de aceptación pasan.
- Tiene pruebas automatizadas en la lógica crítica (autenticación, pedidos, pagos, inventario).
- Pasa linting y formateo en CI.
- La documentación funcional y de API afectada quedó actualizada.
- Fue revisada en viewport móvil y escritorio.
- No introduce datos sensibles en logs ni en respuestas de API.

---

## Próximo paso

La Fase 3 traduce estas historias en arquitectura: diagrama de componentes, modelo entidad-relación completo sobre las entidades definidas en el brief, diagrama de secuencia del flujo de compra y decisiones técnicas registradas.
