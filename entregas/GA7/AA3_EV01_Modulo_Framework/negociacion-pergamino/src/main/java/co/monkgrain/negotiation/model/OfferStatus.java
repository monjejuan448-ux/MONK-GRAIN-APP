package co.monkgrain.negotiation.model;

/** Estado de la postura de un vendedor sobre una solicitud de compra. */
public enum OfferStatus {

    /** Esperando respuesta del comprador. */
    PENDING,

    /** El comprador la aceptó: esos kilos cuentan como cubiertos. */
    ACCEPTED,

    /** El comprador la rechazó, con su motivo. */
    REJECTED,

    /** El vendedor la retiró antes de que le respondieran. */
    WITHDRAWN;

    /** Si todavía puede responderse o retirarse. */
    public boolean isOpen() {
        return this == PENDING;
    }
}
