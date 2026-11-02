package co.monkgrain.movil.domain

import java.math.BigDecimal
import kotlin.test.assertEquals
import kotlin.test.assertNull
import org.junit.Test

/**
 * La regla que gobierna el precio del pergamino.
 *
 * Estas pruebas corren en la **JVM**, sin emulador ni dispositivo, porque el
 * dominio no depende de Android. Es la razón de haber dejado `YieldFactor`,
 * `Kilos` y `Money` fuera de la capa de interfaz: lo que se puede probar sin
 * un teléfono, conviene poder probarlo sin un teléfono.
 *
 * Son las mismas verificaciones que ya pasan en el frontend web
 * (`TradingComponents.test.tsx`), portadas.
 */
class YieldFactorTest {

    @Test
    fun `nunca muestra el numero solo`() {
        // Un «88.50» no le dice nada a quien no sabe que el estándar es 94.
        val texto = YieldFactor.texto(BigDecimal("88.50"))
        assertEquals("Factor 88.50 · Excepcional", texto)
    }

    @Test
    fun `menos es mejor`() {
        // La propiedad que desconcierta a quien llega de otro dominio: el
        // número bajo es el bueno. Si alguien invierte la comparación, esta
        // prueba lo detecta.
        assertEquals(YieldFactor.Lectura.EXCEPCIONAL, YieldFactor.leer(BigDecimal("86")))
        assertEquals(YieldFactor.Lectura.BAJO_EL_ESTANDAR, YieldFactor.leer(BigDecimal("102")))
    }

    @Test
    fun `el 94 exacto es el estandar y no esta por debajo`() {
        // La comparación es estricta a propósito: marcar como deficiente
        // justo el valor de referencia de la Federación confundiría a
        // cualquier caficultor.
        assertEquals(YieldFactor.Lectura.ESTANDAR, YieldFactor.leer(BigDecimal("94")))
        assertEquals(YieldFactor.Lectura.ESTANDAR, YieldFactor.leer(BigDecimal("94.00")))
    }

    @Test
    fun `el 93 queda sobre el estandar`() {
        assertEquals(YieldFactor.Lectura.SOBRE_EL_ESTANDAR, YieldFactor.leer(BigDecimal("93")))
    }

    @Test
    fun `fuera de 80 a 130 el dato esta mal`() {
        assertEquals(YieldFactor.Lectura.FUERA_DE_RANGO, YieldFactor.leer(BigDecimal("79")))
        assertEquals(YieldFactor.Lectura.FUERA_DE_RANGO, YieldFactor.leer(BigDecimal("131")))
    }

    @Test
    fun `sin factor se dice con palabras`() {
        // Un hueco vacío parece un fallo de la aplicación.
        assertNull(YieldFactor.leer(null))
        assertEquals("Factor sin declarar", YieldFactor.texto(null))
    }

    @Test
    fun `un texto que no es numero no tumba la pantalla`() {
        // La API manda el factor como cadena. Un dato raro debe dejar ese
        // campo vacío, no reventar la lista entera.
        assertNull(YieldFactor.desdeTexto("no-es-un-numero"))
        assertNull(YieldFactor.desdeTexto(null))
        assertEquals(BigDecimal("88.50"), YieldFactor.desdeTexto("88.50"))
    }
}
