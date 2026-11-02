package co.monkgrain.authentication.service;

/** El token no corresponde a ninguna sesión viva. */
public class InvalidSessionException extends RuntimeException {

    public InvalidSessionException() {
        super("Tu sesión no es válida o ya caducó. Vuelve a iniciar sesión.");
    }
}
