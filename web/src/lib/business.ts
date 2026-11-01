/**
 * Condiciones comerciales que la interfaz anuncia.
 *
 * Están aquí, en un solo sitio, porque aparecen a la vez en la página de
 * vendedores y en los términos y condiciones —donde la cifra es contractual—.
 * Escribirlas dos veces es la forma segura de que un día digan cosas distintas,
 * y un documento legal que promete algo que el sistema no hace es un defecto,
 * no una errata: ya pasó con el cifrado de la cuenta bancaria.
 *
 * **Debe coincidir con `DEFAULT_COMMISSION_RATE` del backend**, que es quien de
 * verdad calcula lo que se cobra. Al cambiar una hay que cambiar la otra.
 */

/** Comisión sobre el valor de los productos, sin incluir el envío. */
export const COMMISSION_RATE = 0.025;

/** La comisión tal como se lee: «2,5 %». */
export const COMMISSION_LABEL = new Intl.NumberFormat(
  process.env.NEXT_PUBLIC_DEFAULT_LOCALE ?? "es-CO",
  { style: "percent", maximumFractionDigits: 2 },
).format(COMMISSION_RATE);
