package co.monkgrain.negotiation.controller;

import co.monkgrain.negotiation.service.BusinessRuleException;
import co.monkgrain.negotiation.service.NotFoundException;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;

/**
 * Traduce las excepciones del dominio a respuestas HTTP.
 *
 * <p>Está en un solo sitio y no repartido por cada controlador: eso es lo que
 * evita que un endpoint devuelva 500 donde otro devuelve 400 para el mismo tipo
 * de error.
 *
 * <p>Los códigos no son intercambiables. Un dato mal escrito es culpa de quien
 * lo escribe y se corrige cambiándolo —400—; un 500 diría que el fallo es del
 * servidor y que no hay nada que el usuario pueda hacer.
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(NotFoundException e) {
        return build(HttpStatus.NOT_FOUND, "no_encontrado", e.getMessage());
    }

    @ExceptionHandler(BusinessRuleException.class)
    public ResponseEntity<Map<String, Object>> handleBusinessRule(BusinessRuleException e) {
        return build(HttpStatus.UNPROCESSABLE_ENTITY, "regla_de_negocio", e.getMessage());
    }

    /**
     * Fallo de validación del modelo.
     *
     * <p>Se devuelven <strong>todos</strong> los campos que fallan, no el
     * primero: corregir de uno en uno obligaría al usuario a reenviar el
     * formulario tantas veces como errores tenga.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(
            MethodArgumentNotValidException e) {

        Map<String, String> campos = new LinkedHashMap<>();
        e.getBindingResult().getFieldErrors()
                .forEach(error -> campos.put(error.getField(), error.getDefaultMessage()));

        Map<String, Object> cuerpo = baseBody("validacion", "Revisa los datos enviados.");
        cuerpo.put("campos", campos);

        return ResponseEntity.unprocessableEntity().body(cuerpo);
    }

    /**
     * Un parámetro de la dirección incumple su restricción.
     *
     * <p>Sin este manejador, Spring devolvía un 400 con un cuerpo que decía
     * <em>«Validation failed for method=…​ Error count: 0»</em> y la firma
     * completa del método Java: delata la estructura interna y no le dice al
     * usuario qué corregir.
     *
     * <p>Se captura {@link HandlerMethodValidationException} y no
     * {@code ConstraintViolationException}: desde Spring Framework 6.1 la
     * validación de parámetros de método produce la primera. Esperar la
     * segunda —que es lo que enseñan casi todos los ejemplos— deja el
     * manejador sin efecto y el error sin explicación.
     */
    @ExceptionHandler(HandlerMethodValidationException.class)
    public ResponseEntity<Map<String, Object>> handleParameterValidation(
            HandlerMethodValidationException e) {

        // `getAllValidationResults()` y no `getParameterValidationResults()`:
        // el segundo llegó en Spring Framework 6.2 y aquí corre 6.1.
        Map<String, String> campos = new LinkedHashMap<>();
        e.getAllValidationResults().forEach(resultado -> {
            String parametro = resultado.getMethodParameter().getParameterName();
            resultado.getResolvableErrors().forEach(error ->
                    campos.put(parametro == null ? "parámetro" : parametro,
                            error.getDefaultMessage()));
        });

        Map<String, Object> cuerpo = baseBody("parametro_invalido", "Revisa los parámetros.");
        cuerpo.put("campos", campos);
        return ResponseEntity.badRequest().body(cuerpo);
    }

    /** Falta un parámetro obligatorio en la dirección. */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<Map<String, Object>> handleMissingParam(
            MissingServletRequestParameterException e) {
        return build(HttpStatus.BAD_REQUEST, "parametro_faltante",
                "Falta el parámetro «" + e.getParameterName() + "».");
    }

    private ResponseEntity<Map<String, Object>> build(
            HttpStatus estado, String codigo, String mensaje) {
        return ResponseEntity.status(estado).body(baseBody(codigo, mensaje));
    }

    private Map<String, Object> baseBody(String codigo, String mensaje) {
        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("momento", LocalDateTime.now().toString());
        cuerpo.put("codigo", codigo);
        cuerpo.put("mensaje", mensaje);
        return cuerpo;
    }
}
