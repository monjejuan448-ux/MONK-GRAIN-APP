# catalogo-web

Capa web del catálogo de pergamino: **servlets + JSP**.
Evidencia **GA7-220501096-AA2-EV02**.

## Qué demuestra

| Requisito de la guía | Dónde |
|---|---|
| Formularios HTML con servlets | `lote-formulario.jsp` → `LotServlet` |
| Método **GET** | `CatalogServlet.doGet()`, `LotServlet.doGet()` |
| Método **POST** | `LotServlet.doPost()` — crear, eliminar, registrar vendedor |
| Elementos de JSP | directivas, `jsp:include`, EL `${...}`, JSTL `c:` y `fmt:` |

## Reutiliza, no repite

Depende del módulo `catalogo-pergamino` de AA2-EV01. Los servlets **no**
contienen SQL ni reglas de negocio: delegan en `CatalogService`.

## Rutas

| Ruta | Método | Qué hace |
|---|---|---|
| `/catalogo` | GET | Catálogo público, con filtro por factor máximo |
| `/lotes` | GET | Bandeja del vendedor |
| `/lotes?accion=nuevo` | GET | Formulario de publicación |
| `/lotes?accion=detalle&id=N` | GET | Ficha del lote |
| `/lotes` | POST | Crear lote, eliminar lote o registrar vendedor |

## Desplegar

```bash
# 1. el módulo del que depende
cd ../AA2_EV01_Modulo_JDBC/catalogo-pergamino && mvn clean install

# 2. el WAR
cd ../../AA2_EV02_Modulo_Servlets_JSP/catalogo-web && mvn clean package

# 3. Tomcat 10
cp target/catalogo-pergamino.war $CATALINA_HOME/webapps/
$CATALINA_HOME/bin/startup.sh
```

→ http://localhost:8080/catalogo-pergamino/catalogo

## Requisitos

- Java 17, Maven 3.9, **Tomcat 10** (Jakarta Servlet 6; con Tomcat 9 no funciona:
  cambió el espacio de nombres de `javax` a `jakarta`)
- PostgreSQL con la base `monkgrain_java`
