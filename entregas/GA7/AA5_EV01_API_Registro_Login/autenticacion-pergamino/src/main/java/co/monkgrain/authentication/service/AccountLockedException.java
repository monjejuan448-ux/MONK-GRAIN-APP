package co.monkgrain.authentication.service;

import java.time.Duration;

/**
 * La cuenta está frenada por intentos fallidos.
 *
 * <p>Solo se lanza cuando la contraseña <b>sí</b> era correcta. Con la
 * contraseña equivocada se responde lo mismo que en cualquier otro fallo, para
 * no confirmarle a nadie que el correo existe. Ver {@code AuthenticationService}.
 */
public class AccountLockedException extends RuntimeException {

    private final Duration retryAfter;

    public AccountLockedException(Duration retryAfter) {
        super("Demasiados intentos fallidos. Vuelve a intentarlo en "
                + minutosRedondeadosHaciaArriba(retryAfter) + " minutos.");
        this.retryAfter = retryAfter;
    }

    /**
     * Minutos hacia arriba, no {@code toMinutes()}.
     *
     * <p>{@code toMinutes()} trunca: con catorce minutos y cincuenta y nueve
     * segundos restantes diría «14 minutos», y quien volviera a los catorce se
     * encontraría otra vez con la puerta cerrada. Redondeando hacia arriba, el
     * plazo que se anuncia siempre alcanza.
     */
    private static long minutosRedondeadosHaciaArriba(Duration retryAfter) {
        long segundos = Math.max(1, retryAfter.toSeconds());
        return (segundos + 59) / 60;
    }

    public Duration getRetryAfter() {
        return retryAfter;
    }
}
