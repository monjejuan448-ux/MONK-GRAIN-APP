package co.monkgrain.catalog.util;

import java.io.IOException;
import java.io.InputStream;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Properties;

/**
 * Fábrica de conexiones JDBC contra la base de datos del módulo.
 *
 * <p>Los datos de conexión se leen de {@code database.properties} y no se
 * escriben en el código: una credencial dentro de una clase viaja al
 * repositorio y no se puede cambiar sin recompilar. Las variables de entorno
 * tienen prioridad sobre el archivo, que es como se configura en un despliegue
 * real.
 *
 * <p>La clase no guarda ninguna conexión abierta. Cada llamada a
 * {@link #open()} devuelve una nueva, y es responsabilidad de quien la pide
 * cerrarla —en la práctica, con {@code try-with-resources}—. Un
 * {@code Connection} compartido entre hilos es una fuente de errores difíciles
 * de reproducir.
 */
public final class DatabaseConnection {

    private static final String ARCHIVO_CONFIGURACION = "database.properties";

    /**
     * Nombre del controlador, que se carga explícitamente.
     *
     * <p>Desde JDBC 4.0 el controlador se registra solo, y en una aplicación de
     * consola basta con tenerlo en el classpath. <strong>Dentro de un contenedor
     * de servlets no basta</strong>: {@code DriverManager} hace su búsqueda
     * automática una sola vez, con el cargador de clases que esté activo en ese
     * momento, y si Tomcat lo tocó primero esa búsqueda ya ocurrió sin ver el
     * controlador que vive en {@code WEB-INF/lib}. El síntoma es un
     * «No suitable driver found» con el controlador presente en el WAR.
     *
     * <p>{@code Class.forName} fuerza el registro desde el cargador de la
     * aplicación web y resuelve el caso. En consola es inofensivo.
     */
    private static final String CONTROLADOR = "org.postgresql.Driver";

    private static final String URL;
    private static final String USUARIO;
    private static final String CLAVE;

    static {
        try {
            Class.forName(CONTROLADOR);
        } catch (ClassNotFoundException e) {
            throw new DataAccessException(
                    "No se encontró el controlador JDBC " + CONTROLADOR
                            + ". Verifica que el jar de PostgreSQL esté en el classpath.", e);
        }

        Properties propiedades = cargarPropiedades();
        URL = resolver("MONKGRAIN_JDBC_URL", propiedades, "db.url");
        USUARIO = resolver("MONKGRAIN_JDBC_USER", propiedades, "db.user");
        CLAVE = resolver("MONKGRAIN_JDBC_PASSWORD", propiedades, "db.password");
    }

    /** Clase de utilidad: no se instancia. */
    private DatabaseConnection() {
    }

    /**
     * Abre una conexión nueva.
     *
     * @return conexión lista para usar, que el llamador debe cerrar
     * @throws DataAccessException si la base de datos no está disponible
     */
    public static Connection open() {
        try {
            return DriverManager.getConnection(URL, USUARIO, CLAVE);
        } catch (SQLException e) {
            throw new DataAccessException(
                    "No fue posible conectar con la base de datos en " + URL, e);
        }
    }

    /** Dirección configurada, para poder mostrarla en los mensajes de arranque. */
    public static String url() {
        return URL;
    }

    private static Properties cargarPropiedades() {
        Properties propiedades = new Properties();
        try (InputStream entrada = DatabaseConnection.class.getClassLoader()
                .getResourceAsStream(ARCHIVO_CONFIGURACION)) {
            if (entrada != null) {
                propiedades.load(entrada);
            }
        } catch (IOException e) {
            throw new DataAccessException(
                    "No fue posible leer " + ARCHIVO_CONFIGURACION, e);
        }
        return propiedades;
    }

    /**
     * Toma el valor del entorno si existe y, si no, el del archivo.
     *
     * <p>Ese orden es el que permite que el mismo artefacto funcione en el
     * equipo del desarrollador y en un servidor sin recompilar nada.
     */
    private static String resolver(String variableEntorno, Properties propiedades, String clave) {
        String delEntorno = System.getenv(variableEntorno);
        if (delEntorno != null && !delEntorno.isBlank()) {
            return delEntorno;
        }
        String delArchivo = propiedades.getProperty(clave);
        if (delArchivo == null || delArchivo.isBlank()) {
            throw new DataAccessException(
                    "Falta la configuración '" + clave + "'. Defínela en "
                            + ARCHIVO_CONFIGURACION + " o en la variable " + variableEntorno + ".");
        }
        return delArchivo;
    }
}
