package co.monkgrain.movil.domain

import java.math.BigDecimal

/**
 * El dinero, en pesos colombianos.
 *
 * **Nunca `Double`.** Un número de coma flotante no representa exactamente
 * 0,1; sobre una carga de 125 kg, un redondeo mal hecho son miles de pesos de
 * diferencia entre lo que el comprador ve y lo que el vendedor cobra. La API
 * lo envía como cadena por el mismo motivo, y aquí se lee a `BigDecimal`.
 */
object Money {

    /**
     * Formato de pesos sin decimales.
     *
     * El peso colombiano no usa centavos en la práctica, así que mostrarlos
     * añade dos dígitos que nadie lee. El redondeo es `HALF_UP`, el que la
     * gente espera: 0,5 sube.
     */
    fun texto(valor: BigDecimal?): String {
        if (valor == null) return "Precio sin declarar"
        val entero = valor.setScale(0, java.math.RoundingMode.HALF_UP).toInt()
        return "$ ${Kilos.separarMiles(entero)}"
    }

    /** El precio por kilo, con su unidad, que es como se negocia el pergamino. */
    fun porKilo(valor: BigDecimal?): String =
        if (valor == null) "Precio sin declarar" else "${texto(valor)} / kg"

    /**
     * Lee el texto que manda la API.
     *
     * Devuelve `null` si no es un número, en lugar de lanzar: un precio
     * ilegible debe dejar ese campo vacío, no tumbar la lista entera.
     */
    fun desdeTexto(valor: String?): BigDecimal? =
        valor?.let { runCatching { BigDecimal(it) }.getOrNull() }
}
