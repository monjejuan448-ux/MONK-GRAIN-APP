package co.monkgrain.negotiation.service;

/**
 * Una regla del negocio impide la operación.
 *
 * <p>Se distingue de un error de validación de formato: aquí el dato está bien
 * escrito, lo que no cuadra es la situación —posturar sobre una solicitud
 * cerrada, responder dos veces, ofrecer más kilos de los que faltan—.
 */
public class BusinessRuleException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public BusinessRuleException(String message) {
        super(message);
    }
}
