# MONK GRAIN

Marketplace digital de café colombiano que conecta caficultores, fincas y cooperativas con tostadores, distribuidores, cafeterías y consumidores finales.

Cada café publicado indica su finca, municipio, altitud, variedad, proceso y puntaje de catación: el comprador sabe exactamente de dónde viene lo que compra, y el productor vende sin intermediarios.

Orientado al mercado colombiano: pesos colombianos, departamentos y municipios con códigos DANE, operadores logísticos nacionales y medios de pago disponibles en el país.

---

## Índice

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

---

## Estado del proyecto

| Fase | Entregable | Estado |
|---|---|---|
| 1 | Análisis de producto, alcance del MVP, requisitos | ✅ [docs/01](docs/01-analisis-producto.md) |
| 2 | Historias de usuario y criterios de aceptación | ✅ [docs/02](docs/02-historias-usuario.md) |
| 3 | Arquitectura y base de datos | ✅ [docs/03](docs/03-arquitectura-y-datos.md) |
| 4 | Estructura del proyecto | ✅ [docs/04](docs/04-estructura-proyecto.md) |
| 5 | Backend: 48 tablas, migraciones, datos iniciales | ✅ |
| 6 | Frontend: identidad visual y páginas públicas | ✅ [docs/05](docs/05-diseno-visual.md) |
| 7 | Autenticación y control de acceso por roles | ✅ |
| 8 | Catálogo, carrito y pedidos | ✅ |
| 9 | Paneles de comprador, productor y administrador | ✅ |
| 10 | Pruebas y documentación | ✅ [docs/06](docs/06-api.md) · [docs/07](docs/07-despliegue.md) |
| 11 | Seguridad, rendimiento y accesibilidad | ✅ [docs/08](docs/08-auditoria.md) |
| 12 | Integración continua y despliegue | ✅ [docs/07 §6](docs/07-despliegue.md) |

**Las 12 fases están completas.** 98 pruebas automatizadas, 82 % de cobertura, verificado en
ejecución contra PostgreSQL real. Auditoría de seguridad, rendimiento y accesibilidad superada.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Web | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Móvil (fase posterior) | React Native con Expo |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2, Pydantic 2, Alembic |
| Datos | PostgreSQL 16, Redis 7, almacenamiento compatible con S3 |
| Infraestructura | Docker, Docker Compose, Nginx |

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

Carga roles, permisos y la geografía cafetera de Colombia:

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

Carga 5 productores y 9 cafés colombianos verosímiles para explorar la plataforma:

```bash
docker compose exec backend python -m app.db.demo_data
```

Incluye una finca del Huila, una cooperativa de Nariño, una hacienda del Quindío, una tostadora del Cauca y un caficultor de Antioquia, con variedades, procesos, altitudes y perfiles sensoriales reales de la caficultura colombiana. Las fincas y personas son ficticias.

**Credenciales de los productores de prueba:**

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
docker compose exec backend ruff check app && docker compose exec backend mypy app
```

```bash
docker compose exec backend alembic revision --autogenerate -m "descripcion del cambio"
```

### Frontend

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
│   │   ├── models/        48 modelos SQLAlchemy por dominio
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
Navegar el catálogo, buscar y filtrar por región, variedad, proceso, tueste, certificación, precio y puntaje de catación; consultar la ficha completa con la trazabilidad del café y los perfiles públicos de los productores.

### Comprador
Registro con verificación de correo, carrito persistente que se conserva al iniciar sesión, checkout con división automática por vendedor, historial de pedidos, seguimiento de envíos, favoritos y reseñas de compras verificadas.

### Comprador empresarial
Perfil empresarial verificado, acceso a precios mayoristas, solicitud de muestras y cotizaciones.

### Productor
Registro con validación administrativa, perfil de finca, publicación de cafés con ficha técnica completa, control de inventario con alertas de bajo stock, gestión de pedidos recibidos y resumen de liquidaciones.

### Administrador
Aprobación de vendedores, métricas de la plataforma, moderación de reseñas, suspensión de cuentas y registro de auditoría inmutable.

---

## Documentación

| Documento | Contenido |
|---|---|
| [01 — Análisis del producto](docs/01-analisis-producto.md) | Público objetivo, propuesta de valor, alcance del MVP, requisitos |
| [02 — Historias de usuario](docs/02-historias-usuario.md) | 47 historias con criterios de aceptación y matriz de trazabilidad |
| [03 — Arquitectura y datos](docs/03-arquitectura-y-datos.md) | Decisiones de arquitectura, diagramas, modelo de 51 tablas |
| [04 — Estructura del proyecto](docs/04-estructura-proyecto.md) | Organización de carpetas y convenciones de código |
| [05 — Diseño visual](docs/05-diseno-visual.md) | Identidad de marca, paleta, decisiones de accesibilidad |
| [06 — API](docs/06-api.md) | Los endpoints con sus parámetros, respuestas y errores |
| [07 — Despliegue](docs/07-despliegue.md) | Instalación detallada, producción, CI/CD, respaldos, escalabilidad |
| [08 — Auditoría](docs/08-auditoria.md) | Seguridad, rendimiento y accesibilidad verificados en ejecución |
| [09 — Auditoría de QA](docs/09-auditoria-qa.md) | Auditoría independiente de QA, seguridad y confiabilidad, con sus hallazgos y remediación |
| [10 — Revisión legal](docs/10-revision-legal.md) | Contraste de los documentos legales con la normativa colombiana, riesgos y decisiones de negocio pendientes |
| [11 — Devoluciones](docs/11-devoluciones.md) | Retracto, garantía legal, plazos en días hábiles y reembolso |
| [12 — Reseñas](docs/12-resenas.md) | Compra verificada, promedios, reporte y moderación |
| [13 — Comprobante](docs/13-comprobante.md) | Constancia del pedido en PDF, con los datos del artículo 53 |

---

## Decisiones de diseño destacadas

Las decisiones completas están en [docs/03](docs/03-arquitectura-y-datos.md). Estas son las que más condicionan el comportamiento del sistema:

**Sub-órdenes por vendedor.** Un pedido con cafés de tres fincas genera tres sub-órdenes con estado, envío, comisión y liquidación independientes, bajo un único número de pedido. Cada productor despacha y cobra por separado.

**El inventario se reserva, no se descuenta.** El checkout retiene las unidades; solo se descuentan cuando el pago se confirma. Un pago rechazado devuelve el stock al catálogo automáticamente.

**Los importes nunca usan punto flotante.** `NUMERIC(14,2)` en PostgreSQL, `Decimal` en Python y cadenas en JSON. Los errores de redondeo son inaceptables en comisiones y liquidaciones.

**La ubicación exacta de las fincas no sale del servidor.** Se publica el municipio y una coordenada aproximada. Exponer la coordenada real de una finca rural es un riesgo de seguridad física para el productor, no solo de privacidad.

**Ningún endpoint revela qué correos están registrados.** Registro, inicio de sesión y recuperación de contraseña responden igual exista o no la cuenta.

**La auditoría es inmutable.** No existe endpoint para editarla ni borrarla, y el rol de aplicación en PostgreSQL solo tiene permisos de inserción y lectura sobre esa tabla.

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

**98 pruebas:** 62 de integración contra PostgreSQL real y 36 unitarias. Cobertura global del 82 %; en los módulos críticos: seguridad 96 %, repositorio de autenticación 98 %, servicio de catálogo 90 %.

Las pruebas de integración usan PostgreSQL, no SQLite: el esquema depende de tipos específicos (CITEXT, JSONB, ENUM nativos, índices parciales) que SQLite no reproduce, y una prueba que pase contra otro motor daría una falsa sensación de seguridad.

Entre lo que verifican: que el checkout sea atómico, que el stock se reserve y se libere correctamente, que reprocesar un webhook no descuente dos veces, que la coordenada exacta de las fincas nunca aparezca en una respuesta, que los precios mayoristas no lleguen a quien no debe verlos, y que los mensajes de error no permitan averiguar si un correo está registrado.

---

## Licencia

Proyecto privado. Todos los derechos reservados.
