package co.monkgrain.catalog.util;

/**
 * Error al hablar con la base de datos.
 *
 * <p>Envuelve a {@link java.sql.SQLException}, que es comprobada, para que las
 * capas superiores no tengan que declararla en cada firma. El DAO es el único
 * que conoce JDBC; el servicio y la interfaz no deberían saber siquiera que
 * detrás hay SQL.
 *
 * <p>Se conserva siempre la causa original: sin ella, el mensaje de error dice
 * que algo falló pero no qué, y depurar se vuelve adivinar.
 */
public class DataAccessException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public DataAccessException(String message, Throwable cause) {
        super(message, cause);
    }

    public DataAccessException(String message) {
        super(message);
    }
}
