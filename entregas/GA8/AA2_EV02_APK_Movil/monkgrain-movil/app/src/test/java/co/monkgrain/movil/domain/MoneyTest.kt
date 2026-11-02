package co.monkgrain.movil.domain

import java.math.BigDecimal
import kotlin.test.assertEquals
import kotlin.test.assertNull
import org.junit.Test

/** El dinero: pesos colombianos, sin coma flotante en ningún momento. */
class MoneyTest {

    @Test
    fun `los pesos van sin decimales y con miles separados`() {
        assertEquals("$ 1.850.000", Money.texto(BigDecimal("1850000.00")))
    }

    @Test
    fun `el precio por kilo lleva su unidad`() {
        // Es como se negocia el pergamino: por kilo, no por bulto.
        assertEquals("$ 20.500 / kg", Money.porKilo(BigDecimal("20500.00")))
    }

    @Test
    fun `redondea como la gente espera`() {
        // HALF_UP: el 0,5 sube. Es lo que cualquiera hace de cabeza.
        assertEquals("$ 21", Money.texto(BigDecimal("20.5")))
        assertEquals("$ 20", Money.texto(BigDecimal("20.4")))
    }

    @Test
    fun `sin precio se dice con palabras`() {
        assertEquals("Precio sin declarar", Money.texto(null))
        assertEquals("Precio sin declarar", Money.porKilo(null))
    }

    @Test
    fun `un texto ilegible deja el campo vacio y no lanza`() {
        assertNull(Money.desdeTexto("veinte mil"))
        assertNull(Money.desdeTexto(null))
        assertEquals(BigDecimal("20500.00"), Money.desdeTexto("20500.00"))
    }

    @Test
    fun `la precision no se pierde en el camino`() {
        // Si en algún momento esto pasara por Double, 0.1 + 0.2 dejaría de
        // ser 0.3 y el total de una carga saldría descuadrado.
        val precio = Money.desdeTexto("20500.10")!!
        assertEquals(BigDecimal("20500.10"), precio)
        assertEquals("$ 20.500", Money.texto(precio))
    }
}
