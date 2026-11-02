# negociacion-pergamino

El mercado de pergamino **en su segundo sentido**: el comprador publica lo que
busca y los caficultores responden con su precio.
Evidencia **GA7-220501096-AA3-EV01**.

## Framework

Spring Boot 3.3 · Spring Data JPA · Bean Validation · PostgreSQL

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/negociacion/solicitudes` | Todas las solicitudes |
| GET | `/api/negociacion/solicitudes/{id}` | Una solicitud |
| POST | `/api/negociacion/solicitudes` | Publicar una solicitud |
| GET | `/api/negociacion/solicitudes/compatibles?factor=` | Las que un lote puede atender |
| POST | `/api/negociacion/solicitudes/{id}/cerrar?motivo=` | Cerrarla |
| GET | `/api/negociacion/solicitudes/{id}/posturas` | Posturas, la más barata arriba |
| POST | `/api/negociacion/solicitudes/{id}/posturas` | Posturar |
| POST | `/api/negociacion/posturas/{id}/aceptar` | Aceptar |
| POST | `/api/negociacion/posturas/{id}/rechazar?motivo=` | Rechazar (motivo obligatorio) |
| POST | `/api/negociacion/posturas/{id}/retirar?vendedor=` | Retirar la propia |
| GET | `/api/negociacion/vendedores/{nombre}/posturas` | Las de un vendedor |

## Las reglas que importan

- Una solicitud grande **se cubre con varios vendedores**: por eso existe
  `PARTIALLY_COVERED`.
- Al cubrirse del todo, las posturas pendientes **se rechazan con motivo**:
  dejarlas esperando para siempre es peor que un «no».
- **Cerrar sin cubrir nada es cancelar**, no cerrar.
- El motivo del rechazo es obligatorio: sin él, el caficultor no sabe qué
  corregir en la siguiente.

## Ejecutar

```bash
mvn clean package
java -jar target/negociacion-pergamino.jar
```

Requiere PostgreSQL con la base `monkgrain_java` (la misma que el módulo de
catálogo de AA2-EV01). Las tablas se crean solas.

## Pruebas

```bash
mvn test
```

21 pruebas sobre H2 en memoria: comprobar una regla de negocio no debe exigir
un PostgreSQL vivo.
