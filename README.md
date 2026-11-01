# MONK GRAIN

Plataforma de compra y venta de **café pergamino seco** en Colombia: el café ya beneficiado y secado que todavía conserva el pergamino y aún no ha pasado por trilla.

Conecta a los caficultores, fincas y cooperativas del país con quienes compran por volumen —trilladoras, exportadoras, cooperativas, tostadoras— y funciona en los dos sentidos: el vendedor publica sus lotes, y el comprador publica lo que busca para que le respondan.

Cada lote se publica con lo que decide su valor: **factor de rendimiento**, humedad, almendra sana, pasilla, daño por broca y granulometría, además de su origen y su código de lote. Los precios son **por kilogramo** y las cantidades, kilos.

Orientado al mercado colombiano: pesos colombianos, los 33 departamentos y las 1.122 entidades municipales del DANE, operadores logísticos nacionales y medios de pago disponibles en el país.

---

## Índice

- [Qué es y qué no es](#qué-es-y-qué-no-es)
- [Estado del proyecto](#estado-del-proyecto)
- [Stack tecnológico](#stack-tecnológico)
- [Instalación](#instalación)
- [Datos de prueba](#datos-de-prueba)
- [Comandos frecuentes](#comandos-frecuentes)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Funcionalidades](#funcionalidades)
- [Documentación](#documentación)
- [Decisiones de diseño destacadas](#decisiones-de-diseño-destacadas)
- [Integraciones simuladas](#integraciones-simuladas)
- [Pruebas](#pruebas)
- [Lo que falta](#lo-que-falta)

---

## Qué es y qué no es

**Es** un mercado de pergamino seco. Un solo producto, en un solo estado, vendido por kilo.

**No es** una tienda de café tostado. No hay nivel de tueste, ni molienda, ni puntaje de catación, ni notas de cata: son atributos de un café que ya pasó por trilla y tostión, y aquí no se vende eso. Lo que describe un lote de pergamino es su análisis físico.

El proyecto **fue** un marketplace minorista de café tostado hasta el pivote del 28 de septiembre de 2026. Las decisiones de ese pivote —qué se retiró, qué se conservó y por qué— están en [docs/14](docs/14-pergamino.md).

---

## Estado del proyecto

| Fase | Entregable | Estado |
|---|---|---|
| 1 | Análisis de producto, alcance del MVP, requisitos | ✅ [docs/01](docs/01-analisis-producto.md) |
| 2 | Historias de usuario y criterios de aceptación | ✅ [docs/02](docs/02-historias-usuario.md) |
| 3 | Arquitectura y base de datos | ✅ [docs/03](docs/03-arquitectura-y-datos.md) |
| 4 | Estructura del proyecto | ✅ [docs/04](docs/04-estructura-proyecto.md) |
| 5 | Backend: modelos, migraciones, datos iniciales | ✅ |
| 6 | Frontend: identidad visual y páginas públicas | ✅ [docs/05](docs/05-diseno-visual.md) |
| 7 | Autenticación y control de acceso por roles | ✅ |
| 8 | Catálogo, carrito y pedidos | ✅ |
| 9 | Paneles de comprador, productor y administrador | ✅ |
| 10 | Pruebas y documentación | ✅ [docs/06](docs/06-api.md) · [docs/07](docs/07-despliegue.md) |
| 11 | Seguridad, rendimiento y accesibilidad | ✅ [docs/08](docs/08-auditoria.md) |
| 12 | Integración continua y despliegue | ✅ [docs/07 §6](docs/07-despliegue.md) |
| 13 | Desbloqueo de compra y despacho | ✅ [docs/16](docs/16-correcciones.md) |
| 14 | Pivote del dominio a pergamino | ✅ [docs/14](docs/14-pergamino.md) |
| 15 | Oferta y demanda entre comprador y vendedor | ✅ [docs/15](docs/15-oferta-demanda.md) |
| 16 | Panel de administración completo | ✅ |
| 17 | Pruebas del frontend y límite de peticiones | ✅ |
| 18 | Auditoría de estado y corrección de sus hallazgos | ✅ [docs/17](docs/17-auditoria-correcciones.md) |
| 19 | Liquidación y pago al vendedor | ✅ [docs/18](docs/18-liquidaciones.md) |

**453 pruebas del backend con 87 % de cobertura, más 41 del frontend**, verificado en ejecución contra PostgreSQL real el 1 de noviembre de 2026.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Web | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2, Pydantic 2, Alembic |
| Datos | PostgreSQL 16, Redis 7, almacenamiento compatible con S3 |
| Infraestructura | Docker, Docker Compose, Nginx |

Dimensión: 18.400 líneas de Python, 17.700 de TypeScript, 107 operaciones de API, 43 páginas, 54 tablas.

---

## Instalación

### Requisitos

- Docker y Docker Compose
- Git

No hace falta instalar Python ni Node.js: todo corre en contenedores.

### Puesta en marcha

```bash
git clone <url-del-repositorio>
cd MONK-GRAIN-APP
cp .env.example .env
```

Genera una clave real para firmar los tokens y reemplázala en tu `.env`:

```bash
openssl rand -hex 32
```

> La aplicación **rechaza arrancar** si `SECRET_KEY` conserva el valor de ejemplo. Es deliberado: evita que una clave de plantilla llegue a producción por descuido.

Levanta el entorno:

```bash
docker compose up --build
```

Crea el esquema de la base de datos:

```bash
docker compose exec backend alembic upgrade head
```

Carga roles, permisos y la división político-administrativa completa del país (33 departamentos, 1.122 municipios):

```bash
docker compose exec backend python -m app.db.seed
```

### Servicios disponibles

| Servicio | URL |
|---|---|
| Aplicación web | http://localhost:3000 |
| API | http://localhost:8000 |
| Documentación interactiva (OpenAPI) | http://localhost:8000/docs |
| Correos de desarrollo (Mailpit) | http://localhost:8025 |
| Consola de almacenamiento (MinIO) | http://localhost:9001 |

---

## Datos de prueba

Carga 5 vendedores y 9 lotes de pergamino verosímiles para explorar la plataforma:

```bash
docker compose exec backend python -m app.db.demo_data
docker compose exec backend python -m app.db.demo_images
```

Incluye una finca del Huila, una cooperativa de Nariño, una hacienda del Quindío, un centro de acopio del Cauca y un caficultor de Antioquia, con factores de rendimiento de 86 a 96, humedades de 10,5 % a 11,8 %, análisis físico completo, códigos de lote y precios de 16.800 a 31.000 el kilo. **Las fincas, las personas, los lotes y los precios son inventados**: sirven para recorrer la plataforma, no como referencia de mercado. Un lote queda sin existencias a propósito, para poder ver cómo se muestra un lote agotado.

**Credenciales de los vendedores de prueba:**

| Correo | Contraseña |
|---|---|
| `finca.elmirador@ejemplo.co` | `MonkGrain2026Demo` |
| `coop.narino@ejemplo.co` | `MonkGrain2026Demo` |
| `hacienda.altavista@ejemplo.co` | `MonkGrain2026Demo` |
| `tostaduria.monje@ejemplo.co` | `MonkGrain2026Demo` |
| `finca.laesperanza@ejemplo.co` | `MonkGrain2026Demo` |

Para crear un administrador:

```bash
docker compose exec backend python -m app.db.create_admin
```

Los datos de prueba **no incluyen cuentas de comprador**. Para probar el lado de la compra conviene registrar una: el correo de verificación llega a Mailpit, en http://localhost:8025.

---

## Comandos frecuentes

### Backend

```bash
docker compose exec backend pytest
```

```bash
docker compose exec backend pytest --cov=app --cov-report=term-missing
```

```bash
docker compose exec backend ruff check app tests && docker compose exec backend mypy app
```

```bash
docker compose exec backend alembic revision --autogenerate -m "descripcion del cambio"
```

> Las pruebas usan una base de datos propia (`monkgrain_test`) que se borra y se recrea en cada sesión. **Dos ejecuciones simultáneas de `pytest` se estorban** y producen cientos de errores que no son defectos del producto.
>
> `pyproject.toml` está montado por *bind* en el contenedor, así que **cambiar una dependencia exige `docker compose build backend`**: la declaración se ve desde dentro sin que la instalación exista. Es lo que hizo que `pytest` no pudiera ni recolectar `test_receipt.py` tras recrear el contenedor.

### Frontend

```bash
docker compose exec web npm test
```

```bash
docker compose exec web npm run lint
```

```bash
docker compose exec web npx tsc --noEmit
```

```bash
docker compose exec web npm run format
```

### Base de datos

```bash
docker compose exec postgres psql -U monkgrain -d monkgrain
```

---

## Estructura del repositorio

```
MONK-GRAIN-APP/
├── docs/          Documentación funcional y técnica (español)
├── backend/       API FastAPI
│   ├── app/
│   │   ├── core/          Configuración, seguridad, permisos, excepciones
│   │   ├── db/            Sesión, base declarativa, datos iniciales
│   │   ├── models/        53 modelos SQLAlchemy por dominio
│   │   ├── schemas/       Schemas Pydantic de entrada y salida
│   │   ├── modules/       Módulos de dominio (router → service → repository)
│   │   └── integrations/  Pagos, envíos, almacenamiento, correo
│   ├── migrations/        Migraciones de Alembic
│   └── tests/             Pruebas unitarias y de integración
├── web/           Aplicación Next.js
│   └── src/
│       ├── app/           Rutas agrupadas por área
│       ├── components/    Primitivas de interfaz y componentes compartidos
│       ├── features/      Lógica por dominio, en espejo con el backend
│       └── lib/           Cliente HTTP, formateo, sesión
├── infra/         Nginx e inicialización de PostgreSQL
└── .github/       Integración continua
```

El detalle de la organización y las convenciones está en [docs/04-estructura-proyecto.md](docs/04-estructura-proyecto.md).

---

## Funcionalidades

### Visitante
Navegar el catálogo de lotes y filtrarlos por región, variedad, proceso, certificación, precio por kilo, **factor de rendimiento máximo**, **humedad máxima** y **kilos disponibles**; consultar la ficha completa con el análisis del pergamino y los perfiles públicos de los vendedores.

### Comprador
Registro con verificación de correo, carrito en kilogramos que se conserva al iniciar sesión, checkout con división automática por vendedor, historial de pedidos, seguimiento de envíos, favoritos, reseñas de compras verificadas, y **solicitudes de compra**: publicar lo que busca para que los caficultores le respondan con su precio.

### Comprador empresarial
Perfil empresarial verificado, acceso a precios por volumen, solicitud de muestras.

### Vendedor
Registro con validación administrativa, perfil de finca, publicación de lotes con su análisis del pergamino y su trazabilidad, control de inventario en kilos con alertas, **bandeja de pedidos recibidos** con avance de estado y guía de despacho, **posturas** sobre las solicitudes de compra que sus lotes pueden atender, **detalle de los lotes por reponer**, **cuenta bancaria cifrada** y **liquidaciones con su estado y su referencia de pago**.

### Administrador
Aprobación de vendedores, métricas de la plataforma, **búsqueda y suspensión de cuentas**, **moderación de reseñas denunciadas**, **cierre de periodos y registro de los pagos a vendedores**, y **registro de auditoría inmutable**.

---

## Documentación

| Documento | Contenido |
|---|---|
| [01 — Análisis del producto](docs/01-analisis-producto.md) | Público objetivo, propuesta de valor, alcance del MVP, requisitos |
| [02 — Historias de usuario](docs/02-historias-usuario.md) | Historias con criterios de aceptación y matriz de trazabilidad |
| [03 — Arquitectura y datos](docs/03-arquitectura-y-datos.md) | Decisiones de arquitectura, diagramas, modelo de datos |
| [04 — Estructura del proyecto](docs/04-estructura-proyecto.md) | Organización de carpetas y convenciones de código |
| [05 — Diseño visual](docs/05-diseno-visual.md) | Identidad de marca, paleta, decisiones de accesibilidad |
| [06 — API](docs/06-api.md) | Los endpoints con sus parámetros, respuestas y errores |
| [07 — Despliegue](docs/07-despliegue.md) | Instalación detallada, producción, CI/CD, respaldos, escalabilidad |
| [08 — Auditoría](docs/08-auditoria.md) | Seguridad, rendimiento y accesibilidad verificados en ejecución |
| [09 — Auditoría de QA](docs/09-auditoria-qa.md) | Auditoría independiente de QA, con sus hallazgos y remediación |
| [10 — Revisión legal](docs/10-revision-legal.md) | Contraste con la normativa colombiana, riesgos y decisiones pendientes |
| [11 — Devoluciones](docs/11-devoluciones.md) | Retracto, garantía legal, plazos en días hábiles y reembolso |
| [12 — Reseñas](docs/12-resenas.md) | Compra verificada, promedios, reporte y moderación |
| [13 — Comprobante](docs/13-comprobante.md) | Constancia del pedido en PDF, con los datos del artículo 53 |
| [14 — Pergamino](docs/14-pergamino.md) | **El dominio: factor de rendimiento, análisis, unidades y el pivote** |
| [15 — Oferta y demanda](docs/15-oferta-demanda.md) | **El mercado de dos lados: solicitudes, posturas y precio acordado** |
| [16 — Correcciones](docs/16-correcciones.md) | Los defectos del desbloqueo de compra y despacho, con su verificación |
| [17 — Auditoría y correcciones](docs/17-auditoria-correcciones.md) | La auditoría del 1-nov-2026: lo medido, lo corregido y lo que queda |
| [18 — Liquidaciones](docs/18-liquidaciones.md) | **El pago al vendedor: comisión, cuenta cifrada, cierre de periodo y desembolso** |

---

## Decisiones de diseño destacadas

**Todo se cuenta en kilogramos.** El precio es por kilo, el inventario son kilos y la cantidad del carrito son kilos. Es lo que hace comparables dos lotes de tamaño distinto de un vistazo. La conversión a cargas de 125 kg se muestra al lado —«1.250 kg (10 cargas)»— porque es la unidad en la que se habla del precio del café en Colombia, pero el sistema no calcula en ella.

**El factor de rendimiento no altera el precio.** Lo pone el vendedor y el factor va al lado, informativo. Automatizar el cálculo exigiría una fuente del precio interno de referencia del día, que no existe en el sistema; la tabla para ello está diseñada pero no implementada.

**Cada oferta de un lote tiene su mínimo de compra.** Un caficultor no despacha 3 kg: el flete se come la venta. El mínimo se hace cumplir en el servidor al agregar y al editar la línea del carrito, no solo al agregarla, porque bajar la cantidad después sería la forma obvia de esquivarlo.

**Una postura aceptada se convierte en línea de carrito, no en pedido.** Así el comprador arma su carga con varios vendedores y paga una sola vez, en vez de un envío por cada trato. El precio acordado manda sobre el del catálogo y la base de datos exige que venga acompañado de la postura que lo respalda.

**Sub-órdenes por vendedor.** Un pedido con lotes de tres fincas genera tres sub-órdenes con estado, envío, comisión y liquidación independientes, bajo un único número de pedido.

**El inventario se reserva, no se descuenta.** El checkout retiene los kilos; solo se descuentan cuando el pago se confirma. Un pago rechazado, o una cancelación de cualquiera de las dos partes, los devuelve al catálogo.

**Los importes nunca usan punto flotante.** `NUMERIC(14,2)` en PostgreSQL, `Decimal` en Python y cadenas en JSON.

**La ubicación exacta de las fincas no sale del servidor.** Se publica el municipio y una coordenada aproximada. Exponer la coordenada real de una finca rural es un riesgo de seguridad física para el vendedor.

**Ningún endpoint revela qué correos están registrados.** Registro, inicio de sesión y recuperación de contraseña responden igual exista o no la cuenta.

**El inicio de sesión tiene dos topes, no uno.** Uno por cliente y otro por cuenta. El segundo existe porque el primero no basta: el cliente se identifica por una cabecera que pone el proxy, y quien rotaba esa cabecera estrenaba cupo en cada intento. Contar también por cuenta pone techo al ensayo de contraseñas sin depender de ninguna cabecera. El cliente se identifica por `X-Real-IP` —que Nginx sobreescribe— y nunca por el primer elemento de `X-Forwarded-For`, que lo escribe quien hace la petición.

**La auditoría es inmutable.** No existe endpoint para editarla ni borrarla, y el rol de aplicación en PostgreSQL solo tiene permisos de inserción y lectura sobre esa tabla. Hay una prueba que recorre las rutas declaradas para que añadir un endpoint de escritura sobre la auditoría la rompa.

---

## Integraciones simuladas

La pasarela de pago y el operador logístico están implementados tras una interfaz común, con un proveedor **simulado** activo por defecto.

- **No se realizan cobros reales.** El checkout crea pedidos y registra pagos de prueba, identificados como `simulated` en la base de datos y en la respuesta de la API.
- La validación de firma de los webhooks **sí se ejerce de verdad**, de modo que el camino que se usará en producción queda probado desde ahora.

Activar un proveedor real (Wompi, Mercado Pago, PayU o PSE) consiste en añadir su implementación en `app/integrations/payments/` y cambiar `PAYMENT_PROVIDER` en el entorno. El módulo de pedidos no se toca.

En ningún caso se almacenan datos completos de tarjetas: solo referencias y tokens del proveedor.

---

## Pruebas

```bash
docker compose exec backend pytest
```

**Backend — 453 pruebas:** 365 de integración contra PostgreSQL real y 88 unitarias. Cobertura global del **87 %**.

```bash
docker compose exec web npm test
```

**Frontend — 41 pruebas** con Vitest y Testing Library, sobre el formateo del dominio, la lectura del análisis, el componente de compra y la navegación global. Consultan por lo que el usuario percibe —texto accesible, estado deshabilitado— y no por la estructura interna que React produjo.

Las pruebas de integración usan PostgreSQL, no SQLite: el esquema depende de tipos específicos (CITEXT, JSONB, ENUM nativos, índices parciales) que SQLite no reproduce, y una prueba que pase contra otro motor daría una falsa sensación de seguridad.

Entre lo que verifican: que el checkout sea atómico; que los kilos se reserven y se liberen correctamente, incluso cuando cancela el vendedor; que el mínimo de compra no se pueda esquivar editando la línea del carrito; que el precio acordado en una negociación sea el que se cobra y no el del catálogo; que reprocesar un webhook no descuente dos veces; que la coordenada exacta de las fincas nunca aparezca en una respuesta; que los precios por volumen no lleguen a quien no debe verlos; que un factor de rendimiento imposible lo rechace la base de datos; y que los mensajes de error no permitan averiguar si un correo está registrado.

---

## Lo que falta

Lo que sigue pendiente, sin adornos. El pago al vendedor —que encabezaba esta lista tras la auditoría del 1 de noviembre de 2026— **ya está construido**: ver [docs/18](docs/18-liquidaciones.md). El detalle de lo corregido está en [docs/17](docs/17-auditoria-correcciones.md).

- **Los tokens viven en `sessionStorage`**, no en cookies `httpOnly`. Aceptable para el MVP, no para producción: quedan expuestos a cualquier script que se cuele en la página. Migrarlos exige además protección CSRF y middleware: es un cambio de arquitectura, no una corrección puntual.
- **No hay proceso en segundo plano.** Nada vigila el vencimiento de las certificaciones ni los plazos de las devoluciones, que la revisión legal dejó anotado.
- **Ocho páginas de contenido sin escribir:** `/regiones`, `/blog`, `/nosotros`, `/trazabilidad`, `/sostenibilidad`, `/ayuda`, `/contacto` y `/envios`. **Ya no están enlazadas**, porque prometerlas en las 41 páginas del sitio era peor que no tenerlas; sus enlaces vuelven cuando exista el texto. Una prueba vigila que no reaparezcan antes.
- **Hay esquema sin código detrás:** `conversations` y `messages` (mensajería), `blog_posts` y los cupones, que el carrito consume pero ningún endpoint crea. Construirlo o retirarlo es una decisión de alcance.
- **Los textos legales son un borrador sin revisión jurídica**, con los datos de la empresa entre corchetes, y además fueron redactados para el negocio anterior: requieren una segunda revisión tras el pivote a pergamino. Quedan once decisiones de negocio sin resolver en [docs/10](docs/10-revision-legal.md); la que más urge es **D-7**, quién recauda el dinero, porque condiciona el punto primero de esta lista.
- **El repositorio no tiene remoto.** Todo el historial vive en un solo disco, y el CI nunca se ha ejecutado: está escrito, no probado.
- **El precio no está indexado al precio interno de referencia de la FNC.** Fue una decisión, no un olvido: exigía una fuente del precio diario y decidir quién la mantiene.

---

## Licencia

Proyecto privado. Todos los derechos reservados.
