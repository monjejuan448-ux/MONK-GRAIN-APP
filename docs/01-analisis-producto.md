# MONK GRAIN — Fase 1: Análisis de Producto

**Equipo:** Analista de negocio · UX/UI · Arquitectura de software · Frontend · Backend · Bases de datos · Ciberseguridad · DevOps · E-commerce/Marketplaces · Café colombiano y trazabilidad agrícola.

---

## 0. Nota de alcance — pivote respecto al análisis académico previo

El trabajo de análisis previo (carpetas GUIA N1-N3) definía MONK GRAIN como un marketplace **B2B exclusivamente internacional** (productor colombiano ↔ comprador internacional). El brief actual **amplía y reemplaza** esa visión: MONK GRAIN pasa a ser un **marketplace multiactor enfocado primero en el mercado colombiano** (COP, departamentos/municipios, operadores logísticos y medios de pago nacionales), que conecta caficultores, fincas, cooperativas, tostadores, distribuidores, cafeterías, empresas y consumidores finales, con expansión internacional como fase futura.

A partir de aquí este documento es la fuente de verdad vigente. Los artefactos académicos (GUIA N1-N3) quedan como insumo histórico de contexto, no como especificación activa.

**Decisiones que quedan resueltas por este mismo brief** (ya no son bloqueantes):
- **Stack tecnológico:** Next.js + TypeScript + Tailwind (web), React Native + Expo (móvil), FastAPI + Python (backend), PostgreSQL + SQLAlchemy + Alembic + Redis (datos), Docker + Nginx + GitHub Actions (infraestructura).
- **Pagos/logística en el MVP:** el MVP incluye checkout **simulado** y creación de órdenes; la integración real con pasarelas de pago (Wompi, Mercado Pago, PayU, PSE) y con operadores logísticos queda **arquitectónicamente preparada pero no activa** hasta una fase posterior.

---

## 1. Público objetivo

MONK GRAIN es una plataforma multilateral: cada segmento tiene necesidades y flujos distintos, unidos por el mismo catálogo y la misma capa de trazabilidad.

| Segmento | Rol en la plataforma | Necesidad principal |
|---|---|---|
| Caficultor individual / finca pequeña-mediana | Productor/vendedor | Vender directo, sin intermediarios, mostrando el origen y la historia de su café |
| Finca establecida / marca propia | Productor/vendedor | Posicionar marca, certificaciones y perfil sensorial ante compradores exigentes |
| Cooperativa de caficultores | Productor/vendedor (perfil multi-finca) | Consolidar oferta de varios asociados bajo un mismo perfil comercial |
| Tostador (roaster) | Comprador empresarial + eventualmente productor de café tostado | Comprar café verde trazable por perfil de taza y altitud; vender café tostado |
| Distribuidor / mayorista | Comprador empresarial | Compra por volumen, precios escalonados, pedidos recurrentes |
| Cafetería / HORECA | Comprador empresarial (volumen medio) | Abastecimiento recurrente con trazabilidad para contar la historia al cliente final |
| Empresa (regalos corporativos, oficinas) | Comprador empresarial o consumidor | Compras ocasionales de volumen medio, factura electrónica |
| Consumidor final | Comprador consumidor | Comprar café de origen con confianza, conocer la historia del productor |
| Visitante no registrado | Visitante | Explorar catálogo, historias y contenido antes de decidir registrarse |

### Propuesta de valor

- **Para productores/cooperativas:** canal de venta directa que reduce intermediación, con perfil público que comunica origen, certificaciones y prácticas sostenibles, y paneles para gestionar inventario, precios y pedidos sin fricción técnica.
- **Para compradores (consumidor, empresa, tostador, distribuidor):** un catálogo confiable con trazabilidad verificable desde la finca, filtros técnicos (altitud, proceso, perfil sensorial, puntaje de catación) y condiciones comerciales adaptadas al volumen que compran (minorista o mayorista/cotización).
- **Para MONK GRAIN como negocio:** comisión por transacción, con arquitectura preparada para escalar a mercados internacionales sin rediseñar el dominio central (multi-moneda y multi-país quedan como extensión, no como reescritura).

---

## 2. Alcance del MVP

### Incluido en el MVP

- Página de inicio, catálogo, ficha de producto, perfil público de productor.
- Registro/login con verificación de correo; roles: Visitante, Comprador consumidor, Productor/vendedor, Administrador. (El rol Comprador empresarial se modela desde el MVP a nivel de datos — perfil empresarial, precios mayoristas — pero sus flujos avanzados de cotización y negociación quedan para fase 2, ver más abajo).
- Búsqueda y filtros (región, variedad, proceso, certificación, precio, puntaje de catación).
- Carrito persistente, lista de deseos.
- Checkout **simulado** (sin cobro real) y creación de pedidos con estados completos (pendiente → confirmado → preparado → enviado → entregado / cancelado / reembolsado, aunque las transiciones logísticas reales se simulan).
- Panel del comprador (pedidos, direcciones, favoritos, reseñas).
- Panel del productor (productos, inventario, pedidos recibidos, ventas, documentos/certificaciones).
- Panel administrativo (usuarios, aprobación de productores, catálogo, pedidos, reseñas, contenido, métricas básicas).
- Sistema de reseñas y calificaciones.
- Diseño responsive (web) — la app móvil nativa se prepara en fase 2 (ver sección 13 del brief original).
- Datos de prueba realistas (cafés, fincas y regiones colombianas).
- Documentación de instalación local.

### Preparado pero no implementado en el MVP

- Pagos reales (Wompi/Mercado Pago/PayU/PSE) — arquitectura de webhooks e integración de proveedor lista, sin credenciales activas.
- Integración con transportadoras colombianas — modelo de datos de envíos y guías listo, sin conexión real a un operador.
- App móvil completa (React Native/Expo) — se agenda como fase posterior al MVP web.
- Chat en tiempo real comprador-vendedor.
- Sistema de cotizaciones B2B avanzado (negociación, repetición de pedidos, múltiples usuarios por empresa).
- Multiidioma completo (solo español en MVP, inglés preparado a nivel de i18n).
- Analítica avanzada más allá del dashboard básico.
- Trazabilidad con blockchain.

### Explícitamente fuera de alcance (no solo pospuesto)

- Ejecución real de dinero (custodia de fondos, split de pagos entre vendedores) — se resuelve con liquidación manual/reporteada hasta que haya pasarela real activa.
- Logística física operada por MONK GRAIN (no somos transportadora, solo integradores).

---

## 3. Requisitos funcionales

### RF-01 — Cuentas y autenticación
- RF-01.1 Registro de Visitante como Comprador consumidor con verificación de correo electrónico.
- RF-01.2 Inicio de sesión con correo/contraseña; recuperación de contraseña vía correo.
- RF-01.3 Registro diferenciado de Productor/vendedor, con datos de identidad, finca/marca y documentos de validación; el perfil queda en estado `pendiente` hasta aprobación de un Administrador.
- RF-01.4 Registro de perfil empresarial (Comprador empresarial) como extensión del perfil de comprador (NIT/razón social).
- RF-01.5 Control de acceso basado en roles (RBAC) en cada endpoint y vista.
- RF-01.6 Gestión de perfil personal (datos, direcciones, métodos de pago guardados como referencia tokenizada, no datos completos de tarjeta).

### RF-02 — Catálogo y descubrimiento
- RF-02.1 Listado de productos en vista cuadrícula y lista, con paginación.
- RF-02.2 Búsqueda por texto (nombre, productor, región).
- RF-02.3 Filtros combinables: departamento/municipio, variedad, proceso, nivel de tueste, certificación, rango de precio, puntaje de catación.
- RF-02.4 Ordenamiento por precio, popularidad, calificación, novedad.
- RF-02.5 Listado y filtro de productores/fincas por región y tipo de productor.

### RF-03 — Ficha de producto y trazabilidad
- RF-03.1 Ficha de producto con todos los atributos definidos en la sección 5 del brief (variedad, proceso, altitud, perfil sensorial, puntaje, cosecha, tueste, certificaciones, prácticas sostenibles).
- RF-03.2 Sección de trazabilidad: origen (finca/municipio/departamento), fecha de cosecha, cadena hasta el listado (sin exponer geolocalización exacta de la finca — solo aproximada).
- RF-03.3 Reseñas y productos relacionados en la ficha.
- RF-03.4 Botones "Comprar ahora", "Agregar al carrito" y "Solicitar muestra" (este último visible solo para Comprador empresarial).

### RF-04 — Perfil de productor/finca
- RF-04.1 Perfil público editable por el productor: historia, ubicación, certificaciones, prácticas ambientales, galería.
- RF-04.2 Publicación y edición de productos, con múltiples imágenes y variantes (presentación, peso, molienda).
- RF-04.3 Gestión de inventario con stock por variante y alertas de bajo inventario.
- RF-04.4 Gestión de precios minorista y mayorista por producto.
- RF-04.5 Carga de certificados y documentos (PDF/imagen) asociados al perfil o a productos específicos.

### RF-05 — Carrito, checkout y pedidos
- RF-05.1 Carrito persistente por usuario (sobrevive a cierre de sesión).
- RF-05.2 Cálculo de subtotal, envío estimado, descuentos por cupón y total.
- RF-05.3 Checkout con selección de dirección, método de envío y método de pago (en MVP: pago simulado).
- RF-05.4 Separación automática del pedido en sub-órdenes cuando hay productos de más de un productor.
- RF-05.5 Ciclo de estados del pedido completo (pendiente, confirmado, preparado, enviado, entregado, cancelado, reembolsado) con historial de cambios.
- RF-05.6 Generación de comprobante de pedido descargable (PDF).

### RF-06 — Panel del comprador
- RF-06.1 Resumen de actividad, pedidos recientes y su estado.
- RF-06.2 Gestión de direcciones y métodos de pago guardados (tokenizados).
- RF-06.3 Lista de favoritos.
- RF-06.4 Reseñas pendientes de escribir tras un pedido entregado.

### RF-07 — Panel del productor
- RF-07.1 Dashboard con ventas totales, pedidos pendientes, productos activos, productos más vendidos.
- RF-07.2 Gestión de productos, inventario y pedidos recibidos.
- RF-07.3 Gestión de documentos/certificaciones y su estado de vigencia.
- RF-07.4 Configuración de datos de pago para liquidación (cuenta bancaria de referencia).

### RF-08 — Panel administrativo
- RF-08.1 Aprobación/rechazo de productores pendientes, con motivo registrado.
- RF-08.2 Gestión de usuarios, categorías, productos, pedidos, reseñas reportadas, contenido/banners y cupones.
- RF-08.3 Configuración de comisión de MONK GRAIN por venta.
- RF-08.4 Métricas generales (ventas, usuarios activos, productos publicados) y exportación de reportes en CSV/PDF.
- RF-08.5 Log de auditoría de acciones administrativas sensibles (aprobar/rechazar, cambios de comisión, cambios de rol).

### RF-09 — Pagos (arquitectura preparada)
- RF-09.1 Creación de orden de pago desacoplada del proveedor concreto (interfaz común para Wompi/Mercado Pago/PayU/PSE).
- RF-09.2 Confirmación de pago vía webhook con validación de firma/origen.
- RF-09.3 Manejo de pagos rechazados y reembolsos, con registro de cada evento de pago.
- RF-09.4 Registro de comisión de plataforma y cálculo de liquidación a productores (aunque el pago real no esté activo en MVP, el cálculo sí debe ser correcto sobre datos simulados).

### RF-10 — Envíos y logística (arquitectura preparada)
- RF-10.1 Cálculo estimado de costo de envío según dirección y peso (con reglas simples en MVP, integrables a un proveedor real después).
- RF-10.2 Generación de guía y código de seguimiento (simulado en MVP).
- RF-10.3 Registro de novedades logísticas y gestión de devoluciones.

### RF-11 — Reseñas, mensajería y notificaciones
- RF-11.1 Calificación y reseña de producto tras pedido entregado, con promedio recalculado automáticamente.
- RF-11.2 Notificaciones dentro de la aplicación y por correo (cambios de estado de pedido, aprobación de productor, nuevas solicitudes).
- RF-11.3 Mensajería básica comprador-vendedor asociada a un producto o pedido (chat en tiempo real queda para fase posterior; en MVP puede ser asíncrona).

### RF-12 — Contenido / Blog
- RF-12.1 Publicación de artículos por categoría (preparación, regiones, sostenibilidad, comercio justo, noticias).
- RF-12.2 Buscador y filtro de contenido por categoría.

### RF-13 — Comercio B2B (Comprador empresarial)
- RF-13.1 Perfil empresarial con datos fiscales y precios mayoristas visibles solo para este rol.
- RF-13.2 Solicitud de muestra y solicitud de cotización sobre un producto (formulario estructurado; negociación conversacional queda para fase 2).

---

## 4. Requisitos no funcionales

| ID | Requisito | Criterio medible |
|---|---|---|
| RNF-01 | Rendimiento | Tiempo de respuesta de API &lt; 300 ms p95 en operaciones de lectura; carga de página inicial &lt; 2.5 s en conexión 4G |
| RNF-02 | Disponibilidad | 99% mensual para el MVP (no se exige alta disponibilidad multi-región todavía) |
| RNF-03 | Escalabilidad | Backend stateless detrás de balanceador; catálogo y búsqueda deben soportar crecimiento a 10.000 productos sin rediseño de esquema |
| RNF-04 | Seguridad | Contraseñas con Argon2/bcrypt, JWT con access+refresh token revocable, HTTPS obligatorio, rate limiting en endpoints de autenticación y pagos |
| RNF-05 | Protección de datos | Cumplimiento de la Ley 1581 de 2012 (Colombia): consentimiento explícito, política de tratamiento de datos, no exposición de ubicación exacta de fincas ni datos financieros completos |
| RNF-06 | Usabilidad | Diseño responsive verificado en viewport móvil (360px) a escritorio (1920px); mensajes de error comprensibles; estados de carga y vacío en toda vista con datos remotos |
| RNF-07 | Accesibilidad | Cumplimiento de contraste WCAG AA como mínimo, navegación por teclado en flujos críticos (checkout, registro) |
| RNF-08 | Compatibilidad | Web responsive en navegadores modernos (Chrome, Safari, Firefox, Edge); app móvil preparada para Android e iOS vía Expo |
| RNF-09 | Internacionalización | Arquitectura de i18n activa desde el MVP aunque solo se publique contenido en español; moneda y localización (COP, departamentos/municipios) parametrizadas, no hardcodeadas, para permitir expansión futura |
| RNF-10 | Mantenibilidad | Cobertura de pruebas en módulos críticos (auth, pedidos, pagos) ≥ 70%; linting y formateo automatizados en CI |
| RNF-11 | Auditabilidad | Toda acción administrativa sensible y todo evento de pago quedan registrados con actor, fecha y detalle, sin posibilidad de edición retroactiva |
| RNF-12 | Observabilidad | Logs estructurados y captura de errores en backend y frontend desde el primer despliegue, no como mejora posterior |

---

## 5. Próximo paso

Con el alcance del MVP y los requisitos fijados, la Fase 2 traduce cada RF en historias de usuario por rol (Visitante, Comprador consumidor, Comprador empresarial, Productor/vendedor, Administrador) con criterios de aceptación verificables, listas para convertirse en backlog de sprint.
