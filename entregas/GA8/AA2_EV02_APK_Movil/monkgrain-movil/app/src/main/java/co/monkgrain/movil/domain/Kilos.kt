package co.monkgrain.movil.domain

import java.util.Locale

/**
 * El peso del café pergamino.
 *
 * Se almacena y se transporta siempre en **kilogramos**. La *carga* de 125 kg
 * es una **lectura**, no una unidad de almacenamiento: guardar cargas
 * obligaría a representar «media carga y catorce kilos», que es exactamente
 * el tipo de dato que se redondea mal.
 *
 * Puerto de `formatKilosWithCargas` del frontend web.
 */
object Kilos {

    /** Una carga son 125 kilos. Es la unidad con la que se habla en el gremio. */
    const val KG_POR_CARGA = 125

    /**
     * El formato de números de Colombia, fijado a propósito.
     *
     * El peso de un lote no debe cambiar de significado según el idioma en
     * que esté configurado el teléfono.
     */
    private val COLOMBIA: Locale = Locale.forLanguageTag("es-CO")

    /**
     * Los kilos con su equivalente en cargas, cuando alcanza para una.
     *
     * Por debajo de una carga no se menciona: «0,4 cargas» no es como habla
     * nadie, y añadiría ruido en lugar de información.
     */
    fun texto(kg: Int): String {
        val base = "${separarMiles(kg)} kg"
        if (kg < KG_POR_CARGA) return base

        val cargas = kg.toDouble() / KG_POR_CARGA
        val lectura = if (cargas % 1.0 == 0.0) {
            val enteras = cargas.toInt()
            "$enteras ${if (enteras == 1) "carga" else "cargas"}"
        } else {
            // Una cifra decimal basta: «3,2 cargas» informa, «3,24» no añade
            // nada que el caficultor vaya a usar.
            //
            // El `Locale` es explícito y NO el del dispositivo. Sin él,
            // `String.format` usa la configuración del teléfono y «3,2
            // cargas» se convierte en «3.2 cargas» en un teléfono en inglés
            // —donde el punto es el decimal—, justo al lado de un número de
            // kilos que sigue usando el punto como separador de miles. Las
            // dos lecturas juntas serían contradictorias.
            String.format(COLOMBIA, "%.1f cargas", cargas)
        }
        return "$base ($lectura)"
    }

    /**
     * Separador de miles con punto, como se escribe en Colombia.
     *
     * Se calcula a mano en lugar de usar `NumberFormat` con la configuración
     * del dispositivo: un teléfono configurado en inglés mostraría «1,250 kg»,
     * y en Colombia la coma es el separador decimal. El número de kilos de un
     * lote no debe cambiar de significado según el idioma del teléfono.
     */
    fun separarMiles(valor: Int): String =
        valor.toString()
            .reversed()
            .chunked(3)
            .joinToString(".")
            .reversed()
}
