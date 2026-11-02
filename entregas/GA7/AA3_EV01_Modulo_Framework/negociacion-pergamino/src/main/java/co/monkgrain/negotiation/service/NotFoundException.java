package co.monkgrain.negotiation.service;

/** No existe el recurso pedido. Se traduce a un 404. */
public class NotFoundException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public NotFoundException(String message) {
        super(message);
    }
}
