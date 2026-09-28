# MONK GRAIN — Backend

API REST del marketplace de café MONK GRAIN, construida con FastAPI, SQLAlchemy y PostgreSQL.

La documentación funcional y de arquitectura está en [`../docs/`](../docs/). Este archivo cubre solo lo específico del backend.

## Ejecución

Desde la raíz del monorepo, el backend se levanta junto con el resto del entorno:

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Documentación OpenAPI: `http://localhost:8000/docs`

## Estructura

```
app/
├── main.py         Creación de la aplicación y montaje de routers
├── core/           Configuración, seguridad, permisos, excepciones, logging
├── db/             Sesión, base declarativa, datos iniciales
├── models/         Modelos SQLAlchemy
├── schemas/        Schemas Pydantic
├── modules/        Módulos de dominio (router → service → repository)
├── integrations/   Adaptadores externos: pagos, envíos, almacenamiento, correo
└── workers/        Tareas asíncronas
```

La regla de dependencia es `router → service → repository → models`. Un módulo puede invocar el *service* de otro, nunca su *repository*.

## Comandos frecuentes

```bash
# Pruebas
docker compose exec backend pytest

# Linting y formateo
docker compose exec backend ruff check app
docker compose exec backend ruff format app

# Verificación de tipos
docker compose exec backend mypy app

# Migraciones
docker compose exec backend alembic revision --autogenerate -m "descripcion"
docker compose exec backend alembic upgrade head
```
