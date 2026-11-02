package co.monkgrain.negotiation.model;

/**
 * Estado de una solicitud de compra publicada por un comprador.
 *
 * <p>{@link #PARTIALLY_COVERED} existe por una razón del negocio y no por
 * simetría: en pergamino lo normal es que una solicitud grande no la cubra un
 * solo caficultor —quien busca cinco cargas suele armarlas con tres
 * vendedores—. Marcarla como cumplida al aceptar la primera postura cerraría
 * la solicitud cuando todavía falta café.
 */
public enum DemandStatus {

    /** Admite posturas y no se ha cubierto nada. */
    OPEN,

    /** Admite posturas: se aceptó parte de lo pedido y falta el resto. */
    PARTIALLY_COVERED,

    /** Se cubrieron todos los kilos pedidos. */
    FULFILLED,

    /** El comprador la cerró antes de cubrirla. */
    CLOSED,

    /** El comprador la retiró sin aceptar nada. */
    CANCELLED;

    /** Si todavía admite posturas de los vendedores. */
    public boolean isReceivingOffers() {
        return this == OPEN || this == PARTIALLY_COVERED;
    }
}
