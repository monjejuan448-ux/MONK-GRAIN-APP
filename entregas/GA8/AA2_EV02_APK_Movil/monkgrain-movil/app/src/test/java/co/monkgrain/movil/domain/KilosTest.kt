package co.monkgrain.movil.domain

import kotlin.test.assertEquals
import org.junit.Test

/** El peso del pergamino, y su lectura en cargas de 125 kg. */
class KilosTest {

    @Test
    fun `una carga exacta se dice en singular`() {
        assertEquals("125 kg (1 carga)", Kilos.texto(125))
    }

    @Test
    fun `varias cargas exactas van en plural`() {
        assertEquals("1.250 kg (10 cargas)", Kilos.texto(1250))
    }

    @Test
    fun `las cargas incompletas llevan un decimal`() {
        // Una cifra basta: «3,2 cargas» informa, «3,24» no añade nada que el
        // caficultor vaya a usar.
        assertEquals("400 kg (3,2 cargas)", Kilos.texto(400))
    }

    @Test
    fun `por debajo de una carga no se menciona`() {
        // «0,4 cargas» no es como habla nadie en el gremio.
        assertEquals("50 kg", Kilos.texto(50))
        assertEquals("124 kg", Kilos.texto(124))
    }

    @Test
    fun `los miles se separan con punto`() {
        // Punto y no coma: en Colombia la coma es el separador decimal. Esto
        // se calcula a mano justamente para que no cambie con el idioma del
        // teléfono.
        assertEquals("1.000", Kilos.separarMiles(1000))
        assertEquals("12.500", Kilos.separarMiles(12500))
        assertEquals("999", Kilos.separarMiles(999))
        assertEquals("1.234.567", Kilos.separarMiles(1234567))
    }

    @Test
    fun `el cero no se rompe`() {
        assertEquals("0 kg", Kilos.texto(0))
    }
}
