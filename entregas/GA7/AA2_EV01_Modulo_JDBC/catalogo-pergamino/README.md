# catalogo-pergamino

Módulo de catálogo de lotes de café pergamino seco con acceso a datos por
**JDBC**. Evidencia **GA7-220501096-AA2-EV01**.

## Qué hace

Las cuatro operaciones del CRUD sobre el catálogo de un vendedor:

| Operación | Dónde |
|---|---|
| Inserción | `PergaminoLotDao.insert()` · `ProducerDao.insert()` |
| Consulta | `findAll()`, `findById()`, `findPublished()` |
| Actualización | `PergaminoLotDao.update()` |
| Eliminación | `PergaminoLotDao.delete()` · `ProducerDao.delete()` |

## Estructura

```
co.monkgrain.catalog
├── MainCatalog          demostración por consola del CRUD completo
├── model/               objetos de dominio, sin dependencias de JDBC
│   ├── Producer
│   └── PergaminoLot
├── dao/                 la única capa que conoce SQL
│   ├── ProducerDao
│   └── PergaminoLotDao
├── service/             reglas de negocio y validación
│   └── CatalogService
└── util/
    ├── DatabaseConnection
    ├── DataAccessException
    └── ValidationException
```

## Requisitos

- Java 17
- Maven 3.9
- PostgreSQL con la base `monkgrain_java` creada a partir de
  `src/main/resources/esquema.sql`

```bash
docker compose exec -T postgres psql -U monkgrain -d postgres -c "CREATE DATABASE monkgrain_java;"
docker compose exec -T postgres psql -U monkgrain -d monkgrain_java \
  < entregas/GA7/AA2_EV01_Modulo_JDBC/catalogo-pergamino/src/main/resources/esquema.sql
```

## Ejecutar

```bash
mvn clean package
java -jar target/catalogo-pergamino-jar-with-dependencies.jar
```

La demostración deja la base como la encontró: se puede ejecutar las veces que
haga falta.

## Configuración

`src/main/resources/database.properties`, o las variables de entorno
`MONKGRAIN_JDBC_URL`, `MONKGRAIN_JDBC_USER` y `MONKGRAIN_JDBC_PASSWORD`, que
tienen prioridad.

## Pruebas

```bash
mvn test
```

13 pruebas sobre las lecturas del dominio —factor de rendimiento, humedad y
conversión a cargas— que no necesitan base de datos.
