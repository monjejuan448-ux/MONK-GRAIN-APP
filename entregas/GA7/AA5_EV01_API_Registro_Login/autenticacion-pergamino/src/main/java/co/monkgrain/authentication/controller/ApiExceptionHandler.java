package co.monkgrain.authentication.controller;

import co.monkgrain.authentication.service.AccountLockedException;
import co.monkgrain.authentication.service.InvalidCredentialsException;
import co.monkgrain.authentication.service.InvalidSessionException;
import co.monkgrain.authentication.service.WeakPasswordException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Convierte los fallos en respuestas HTTP.
 *
 * <p>En un solo sitio y no repartido por los endpoints: si cada método
 * tradujera sus propios errores, el formato se iría separando y el cliente
 * tendría que saber leer varios.
 *
 * <p>Todas las respuestas tienen la misma forma —{@code error}, {@code message}
 * y a veces {@code details}— para que el cliente pueda mostrar
 * {@code message} sin mirar nada más.
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    /**
     * Credenciales incorrectas: 401.
     *
     * <p>No 404 aunque el correo no exista: un 404 diría «ese usuario no está
     * aquí», que es exactamente el dato que no se quiere dar. El 401 significa
     * «no te identificaste», sin aclarar por qué.
     */
    @ExceptionHandler(InvalidCredentialsException.class)
    public ResponseEntity<Map<String, Object>> onInvalidCredentials(InvalidCredentialsException failure) {
        return build(HttpStatus.UNAUTHORIZED, "authentication_failed", failure.getMessage(), null);
    }

    /** Sesión inválida o caducada: 401. */
    @ExceptionHandler(InvalidSessionException.class)
    public ResponseEntity<Map<String, Object>> onInvalidSession(InvalidSessionException failure) {
        return build(HttpStatus.UNAUTHORIZED, "invalid_session", failure.getMessage(), null);
    }

    /**
     * Cuenta frenada: 429 con {@code Retry-After}.
     *
     * <p>429 y no 403: el 403 dice «no puedes, y no insistas», mientras que el
     * 429 dice «ahora no, vuelve después», que es la verdad. La cabecera
     * {@code Retry-After} va en segundos porque así la entienden los clientes
     * que reintentan solos, sin tener que leer el mensaje.
     */
    @ExceptionHandler(AccountLockedException.class)
    public ResponseEntity<Map<String, Object>> onAccountLocked(AccountLockedException failure) {
        long seconds = Math.max(1, failure.getRetryAfter().toSeconds());
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                .header(HttpHeaders.RETRY_AFTER, String.valueOf(seconds))
                .body(body("account_locked", failure.getMessage(), null));
    }

    /**
     * Contraseña débil: 422.
     *
     * <p>422 y no 400: el cuerpo llegó bien formado y con los tipos correctos
     * —un 400 sería mentira—, lo que no cumple es una regla del negocio.
     */
    @ExceptionHandler(WeakPasswordException.class)
    public ResponseEntity<Map<String, Object>> onWeakPassword(WeakPasswordException failure) {
        return build(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "weak_password",
                failure.getMessage(),
                failure.getProblems());
    }

    /**
     * Validación de forma: 400, con el campo y el motivo de cada fallo.
     *
     * <p>Se devuelven todos los campos a la vez y no el primero: quien llena
     * un formulario merece ver los tres errores juntos en lugar de
     * descubrirlos de uno en uno.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> onValidation(MethodArgumentNotValidException failure) {
        List<String> details = failure.getBindingResult().getFieldErrors().stream()
                .map(error -> fieldName(error) + ": " + error.getDefaultMessage())
                .toList();
        return build(HttpStatus.BAD_REQUEST, "validation_error", "Revisa los datos enviados.", details);
    }

    /**
     * JSON ilegible: 400.
     *
     * <p>Sin este manejador, un cuerpo con una coma de más saldría como 500 y
     * parecería un fallo del servidor cuando el problema está en la petición.
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, Object>> onUnreadableBody(HttpMessageNotReadableException failure) {
        return build(
                HttpStatus.BAD_REQUEST,
                "malformed_body",
                "El cuerpo de la petición no es un JSON válido.",
                null);
    }

    /**
     * Lo imprevisto: 500 con un mensaje genérico.
     *
     * <p>La excepción se escribe en la bitácora del servidor, no en la
     * respuesta: el texto de un fallo de base de datos suele llevar dentro el
     * nombre de la tabla, la consulta y la versión del motor.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> onUnexpected(Exception failure) {
        log.error("Fallo no previsto en el servicio de autenticación", failure);
        return build(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "internal_error",
                "Ocurrió un error inesperado. Inténtalo de nuevo.",
                null);
    }

    /**
     * El nombre del campo tal como lo envió el cliente.
     *
     * <p>Bean Validation sobre un {@code record} informa el nombre del
     * componente, que aquí coincide con el del JSON. Si algún día se renombrara
     * con {@code @JsonProperty}, este es el sitio donde habría que traducirlo.
     */
    private String fieldName(FieldError error) {
        return error.getField();
    }

    private ResponseEntity<Map<String, Object>> build(
            HttpStatus status, String code, String message, List<String> details) {
        return ResponseEntity.status(status).body(body(code, message, details));
    }

    private Map<String, Object> body(String code, String message, List<String> details) {
        // LinkedHashMap y no Map.of: el orden de las claves se conserva, y una
        // respuesta que siempre sale igual es mucho más fácil de leer en
        // Postman y de comparar entre una prueba y otra.
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("error", code);
        payload.put("message", message);
        if (details != null && !details.isEmpty()) {
            payload.put("details", details);
        }
        payload.put("timestamp", Instant.now().toString());
        return payload;
    }
}
