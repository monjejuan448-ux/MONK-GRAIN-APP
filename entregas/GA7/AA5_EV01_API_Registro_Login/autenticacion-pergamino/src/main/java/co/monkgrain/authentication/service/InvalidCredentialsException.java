package co.monkgrain.authentication.service;

/**
 * El ingreso falló.
 *
 * <p>Una sola excepción para «ese correo no está registrado» y para «la
 * contraseña no coincide», y no dos: distinguirlas convertiría el endpoint de
 * ingreso en un buscador de correos registrados. Quien quisiera saber si
 * alguien tiene cuenta en MONK GRAIN solo tendría que probar su correo con
 * cualquier contraseña y mirar cuál de los dos mensajes vuelve.
 */
public class InvalidCredentialsException extends RuntimeException {

    public InvalidCredentialsException() {
        super("Correo o contraseña incorrectos.");
    }
}
