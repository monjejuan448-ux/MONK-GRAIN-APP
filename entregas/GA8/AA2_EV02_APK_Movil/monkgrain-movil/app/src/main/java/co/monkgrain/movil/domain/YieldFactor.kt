package co.monkgrain.movil.domain

import java.math.BigDecimal

/**
 * El factor de rendimiento del café pergamino seco.
 *
 * Es el atributo que gobierna el precio, y tiene una propiedad que
 * desconcierta a quien llega de otro dominio: **menos es mejor**. El factor
 * dice cuántos kilos de pergamino hacen falta para obtener 70 kg de café
 * excelso, así que un número bajo significa que el grano rinde más.
 *
 * El estándar de la Federación Nacional de Cafeteros es **94**.
 *
 * Esta clase es un puerto de la regla ya verificada en el frontend web
 * (`YieldFactorReading.tsx`, 3 pruebas). Se repite aquí en lugar de pedirle
 * al servidor que mande la lectura hecha, porque es una regla de
 * presentación y viaja mejor el número: así la aplicación puede ordenar y
 * comparar, que con una cadena de texto no podría.
 */
object YieldFactor {

    /** El estándar de la Federación. Por debajo, el café rinde más. */
    val ESTANDAR_FNC: BigDecimal = BigDecimal("94")

    /** Los límites que admite el dominio. Fuera de ellos, el dato está mal. */
    val MINIMO: BigDecimal = BigDecimal("80")
    val MAXIMO: BigDecimal = BigDecimal("130")

    /**
     * La lectura comercial del número.
     *
     * Nunca se muestra el factor solo: un «88,50» no le dice nada a quien no
     * sabe que el estándar es 94 y que menos es mejor.
     */
    enum class Lectura(val etiqueta: String) {
        EXCEPCIONAL("Excepcional"),
        SOBRE_EL_ESTANDAR("Sobre el estándar"),
        ESTANDAR("Estándar FNC"),
        BAJO_EL_ESTANDAR("Bajo el estándar"),
        FUERA_DE_RANGO("Fuera de rango"),
    }

    /**
     * Traduce el factor a su lectura.
     *
     * Los cortes están en 90 y 94. Un factor de 94 exacto es el estándar, no
     * «bajo el estándar»: la comparación es estricta a propósito, porque
     * marcar como deficiente justo el valor de referencia confundiría a
     * cualquier caficultor.
     */
    fun leer(factor: BigDecimal?): Lectura? {
        if (factor == null) return null
        if (factor < MINIMO || factor > MAXIMO) return Lectura.FUERA_DE_RANGO
        return when {
            factor < BigDecimal("90") -> Lectura.EXCEPCIONAL
            factor < ESTANDAR_FNC -> Lectura.SOBRE_EL_ESTANDAR
            factor.compareTo(ESTANDAR_FNC) == 0 -> Lectura.ESTANDAR
            else -> Lectura.BAJO_EL_ESTANDAR
        }
    }

    /**
     * El texto que se muestra en pantalla: el número y su lectura, juntos.
     *
     * Cuando no hay factor declarado se dice con palabras, porque un hueco
     * vacío parece un fallo de la aplicación.
     */
    fun texto(factor: BigDecimal?): String {
        val lectura = leer(factor) ?: return "Factor sin declarar"
        return "Factor $factor · ${lectura.etiqueta}"
    }

    /**
     * Convierte el texto que manda la API a un número.
     *
     * La API envía el factor como **cadena** —igual que el dinero— para no
     * perder precisión en el camino. Un texto que no sea un número devuelve
     * `null` en lugar de lanzar: un dato raro no debe tumbar la pantalla
     * entera, solo ese campo.
     */
    fun desdeTexto(valor: String?): BigDecimal? =
        valor?.let { runCatching { BigDecimal(it) }.getOrNull() }
}
