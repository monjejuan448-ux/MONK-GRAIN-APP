package co.monkgrain.authentication.model;

/**
 * Para qué entra cada quien a MONK GRAIN.
 *
 * <p>Un enumerado y no una cadena libre: el rol decide qué puede hacer la
 * cuenta, y una errata de escritura en «vendedor» se convertiría en un permiso
 * que nadie concedió. Con el enumerado, el error se ve al compilar.
 */
public enum AccountRole {

    /** Compra café pergamino. Es el rol que se asigna al registrarse. */
    BUYER,

    /**
     * Vende su café. No se obtiene al registrarse: un administrador lo concede
     * después de verificar la finca, igual que en el producto.
     */
    SELLER,

    /** Administra la plataforma. Se concede a mano, nunca por la API. */
    ADMIN
}
