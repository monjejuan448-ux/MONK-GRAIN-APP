# MONK GRAIN — Fase 4: Estructura del Proyecto

Define cómo se organiza el repositorio, dónde vive cada tipo de archivo y qué convenciones se respetan. El objetivo es que cualquier integrante encuentre el código sin preguntar y que el proyecto arranque en local con un solo comando.

---

## 1. Organización general

Se adopta un **monorepo** con tres aplicaciones y la infraestructura compartida.

```
MONK-GRAIN-APP/
├── README.md                  Punto de entrada del proyecto
├── .gitignore
├── .env.example               Plantilla de variables compartidas
├── docker-compose.yml         Entorno de desarrollo completo
├── docs/                      Documentación funcional y técnica (español)
├── backend/                   API FastAPI
├── web/                       Aplicación web Next.js
├── infra/                     Nginx, inicialización de PostgreSQL
└── .github/workflows/         Integración continua
```

**Por qué monorepo:** el contrato entre frontend y backend cambia constantemente durante el MVP. Tenerlos en repositorios separados obliga a coordinar dos pull requests por cada cambio de API y a versionar tipos compartidos antes de que el dominio esté estable. Cuando la API se asiente, separarlos es trivial; hacerlo ahora solo añade fricción.

---

## 2. Backend

```
backend/
├── pyproject.toml             Dependencias y configuración de herramientas
├── Dockerfile
├── alembic.ini                Configuración de migraciones (Fase 5)
├── app/
│   ├── main.py                Creación de la app, montaje de routers, middleware
│   ├── core/                  Infraestructura transversal
│   │   ├── config.py          Settings tipados desde variables de entorno
│   │   ├── security.py        Hash de contraseñas, emisión y validación de JWT
│   │   ├── permissions.py     Dependencias de autorización (RBAC)
│   │   ├── exceptions.py      Excepciones de dominio y sus manejadores HTTP
│   │   ├── logging.py         Logs estructurados en JSON
│   │   └── pagination.py      Utilidades de paginación reutilizables
│   ├── db/
│   │   ├── base.py            Base declarativa y mixins (timestamps, soft delete)
│   │   ├── session.py         Motor y sesión de SQLAlchemy
│   │   └── seed.py            Carga de datos iniciales y de prueba
│   ├── models/                Modelos SQLAlchemy, un archivo por dominio
│   ├── schemas/               Schemas Pydantic de entrada y salida
│   ├── modules/               Un paquete por módulo de dominio
│   │   └── <modulo>/
│   │       ├── router.py      Endpoints HTTP, validación y autorización
│   │       ├── service.py     Reglas de negocio y transacciones
│   │       └── repository.py  Acceso a datos
│   ├── integrations/          Adaptadores a servicios externos
│   │   ├── payments/          Contrato PaymentProvider + implementaciones
│   │   ├── shipping/          Contrato de operador logístico
│   │   ├── storage/           Cliente de almacenamiento S3
│   │   └── mail/              Envío de correo
│   └── workers/               Tareas asíncronas (correos, PDF, recálculos)
├── migrations/versions/       Migraciones de Alembic
└── tests/
    ├── unit/                  Lógica de negocio aislada
    └── integration/           Endpoints contra base de datos real de prueba
```

### Regla de dependencias

`router → service → repository → models`

- El **router** no consulta la base de datos ni contiene reglas de negocio. Valida la entrada, resuelve autorización y delega.
- El **service** es el único lugar donde se abren y confirman transacciones. Ahí vive el checkout atómico.
- El **repository** no conoce HTTP ni schemas Pydantic; solo entidades y consultas.
- Los **models** no importan nada de `modules/`.

Un módulo puede llamar al *service* de otro módulo, nunca a su *repository*. Esa restricción es la que permite extraer un módulo a un servicio independiente sin desenredar consultas cruzadas (ADR-01).

### Módulos definidos

| Módulo | Responsabilidad |
|---|---|
| `auth` | Registro, verificación, login, refresh, recuperación de contraseña |
| `users` | Perfil, direcciones, preferencias de notificación |
| `producers` | Perfiles de productor, fincas, certificaciones, aprobación |
| `catalog` | Categorías, productos, variantes, atributos de café, inventario, búsqueda |
| `cart` | Carrito, ítems, lista de deseos, cupones |
| `orders` | Checkout, pedidos, sub-órdenes, estados, comprobantes |
| `payments` | Intenciones de pago, webhooks, reembolsos, comisiones, liquidaciones |
| `shipments` | Envíos, seguimiento, novedades, devoluciones |
| `reviews` | Reseñas, calificaciones, moderación |
| `messaging` | Conversaciones, mensajes, notificaciones, solicitudes comerciales |
| `content` | Blog, banners, páginas estáticas |
| `admin` | Panel administrativo, reportes, auditoría, configuración |

---

## 3. Frontend web

```
web/
├── package.json
├── Dockerfile
├── next.config.ts             Configuración de Next.js
├── tsconfig.json
├── tailwind.config.ts         Tokens de la identidad visual
├── src/
│   ├── app/                   App Router
│   │   ├── (public)/          Rutas públicas: inicio, catálogo, productores, blog
│   │   ├── (auth)/            Login, registro, recuperación
│   │   ├── (buyer)/           Panel del comprador
│   │   ├── (producer)/        Panel del productor
│   │   ├── (admin)/           Panel administrativo
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                Primitivas de shadcn/ui
│   │   └── shared/            Componentes propios reutilizables
│   ├── features/              Lógica por dominio, en espejo con el backend
│   │   └── <dominio>/
│   │       ├── api.ts         Llamadas al backend
│   │       ├── schemas.ts     Validación con Zod
│   │       ├── hooks.ts       Hooks de TanStack Query
│   │       └── components/    Componentes específicos del dominio
│   ├── lib/                   Cliente HTTP, formateo de moneda y fechas, utilidades
│   ├── hooks/                 Hooks transversales
│   ├── types/                 Tipos compartidos
│   └── styles/
└── tests/
```

### Agrupación de rutas

Los paréntesis en `(public)`, `(buyer)`, `(producer)` y `(admin)` son grupos de rutas de Next.js: **no aparecen en la URL** pero permiten aplicar un layout y una guarda de autorización distintos a cada área. Un usuario sin rol de productor no llega a renderizar el panel del productor.

La carpeta `features/` refleja los módulos del backend. Cuando alguien trabaja en pedidos, encuentra `web/src/features/orders/` y `backend/app/modules/orders/` con la misma frontera de responsabilidad.

---

## 4. Convenciones

### Idioma
- **Código en inglés:** variables, funciones, clases, tablas, columnas, endpoints, ramas y mensajes de commit.
- **Documentación y textos de interfaz en español:** archivos de `docs/`, comentarios explicativos de negocio y cadenas de traducción.

Motivo: el código en inglés es la convención universal y evita nombres híbridos como `getProductosDestacados`. La documentación en español responde al contexto real del proyecto y sus lectores.

### Nombres
| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos y módulos Python | `snake_case` | `order_service.py` |
| Clases Python | `PascalCase` | `OrderService` |
| Funciones y variables Python | `snake_case` | `create_sub_orders()` |
| Tablas y columnas | `snake_case`, tabla en plural | `sub_orders`, `producer_id` |
| Componentes React | `PascalCase` | `ProductCard.tsx` |
| Hooks | `camelCase` con prefijo `use` | `useCart.ts` |
| Rutas de API | plural, en minúscula | `/api/v1/products` |
| Variables de entorno | `SCREAMING_SNAKE_CASE` | `DATABASE_URL` |

### Commits
Formato *Conventional Commits*: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.

---

## 5. Entorno de desarrollo

`docker-compose.yml` levanta el entorno completo:

| Servicio | Imagen | Puerto | Propósito |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Base de datos principal |
| `redis` | redis:7-alpine | 6379 | Caché, rate limiting, colas |
| `minio` | minio/minio | 9000 / 9001 | Almacenamiento S3 compatible en local |
| `mailpit` | axllent/mailpit | 1025 / 8025 | Captura de correos salientes en desarrollo |
| `backend` | build local | 8000 | API FastAPI con recarga automática |
| `web` | build local | 3000 | Next.js en modo desarrollo |

MinIO y Mailpit son servicios reales configurados en el compose, no integraciones simuladas: los correos se ven en `http://localhost:8025` y los archivos subidos en `http://localhost:9001`. La pasarela de pago y el operador logístico sí son adaptadores simulados en código, porque no hay credenciales reales que configurar (ADR-03).

### Arranque

```bash
cp .env.example .env
docker compose up --build
```

Servicios disponibles tras el arranque:
- Web: `http://localhost:3000`
- API y documentación OpenAPI: `http://localhost:8000/docs`
- Correos de desarrollo: `http://localhost:8025`
- Consola de almacenamiento: `http://localhost:9001`

---

## 6. Calidad de código

| Herramienta | Ámbito | Función |
|---|---|---|
| Ruff | Backend | Linting y formateo (reemplaza flake8, isort y black) |
| Mypy | Backend | Verificación de tipos |
| Pytest | Backend | Pruebas unitarias y de integración |
| ESLint | Web | Linting |
| Prettier | Web | Formateo |
| TypeScript | Web | Verificación de tipos en modo estricto |
| Vitest | Web | Pruebas de componentes y utilidades |

Toda la configuración vive en `backend/pyproject.toml` y en los archivos de configuración de `web/`, no en archivos dispersos por el repositorio.

---

## 7. Variables de entorno

`.env.example` documenta cada variable con un valor de ejemplo seguro. Reglas:

- **Ningún secreto real se versiona.** El `.env` está en `.gitignore`.
- Las credenciales de ejemplo son evidentemente de desarrollo (`change_me_in_production`), para que un valor de ejemplo nunca llegue a producción por descuido.
- El backend valida las variables al arrancar con Pydantic Settings: si falta una obligatoria, la aplicación falla de inmediato con un mensaje claro en vez de romperse más tarde en tiempo de ejecución.

---

## 8. Archivos creados en esta fase

| Archivo | Contenido |
|---|---|
| `README.md` | Descripción, requisitos, arranque rápido y estructura |
| `.gitignore` | Exclusiones de Python, Node, Docker, entornos y editores |
| `.env.example` | Todas las variables del proyecto documentadas |
| `docker-compose.yml` | Los seis servicios del entorno de desarrollo |
| `backend/pyproject.toml` | Dependencias y configuración de Ruff, Mypy y Pytest |
| `backend/Dockerfile` | Imagen del backend con etapas de desarrollo y producción |
| `backend/.dockerignore` | Exclusiones del contexto de build |
| `web/package.json` | Dependencias y scripts del frontend |
| `web/Dockerfile` | Imagen del frontend con etapas de desarrollo y producción |
| `web/.dockerignore` | Exclusiones del contexto de build |
| `infra/nginx/nginx.conf` | Proxy reverso y cabeceras de seguridad |

---

## Próximo paso

La Fase 5 construye el backend: configuración, modelos SQLAlchemy de las 48 tablas, migraciones de Alembic, y los módulos de dominio empezando por autenticación y catálogo.
