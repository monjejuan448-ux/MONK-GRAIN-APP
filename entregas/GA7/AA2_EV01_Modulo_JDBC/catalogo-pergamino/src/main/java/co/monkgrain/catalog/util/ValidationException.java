package co.monkgrain.catalog.util;

/**
 * El dato que llega no cumple una regla del negocio.
 *
 * <p>Se distingue de {@link DataAccessException} a propósito: una es culpa de
 * quien escribe el dato y se corrige cambiándolo; la otra es un fallo del
 * sistema y no hay nada que el usuario pueda hacer. Mezclarlas obligaría a
 * mostrar el mismo mensaje en dos situaciones que no se parecen.
 */
public class ValidationException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public ValidationException(String message) {
        super(message);
    }
}
