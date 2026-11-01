package co.monkgrain.catalog.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import co.monkgrain.catalog.model.PergaminoLot;
import java.math.BigDecimal;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

/**
 * Las lecturas del dominio del pergamino.
 *
 * <p>No tocan la base de datos a propósito: son reglas del negocio y deben poder
 * comprobarse sin levantar PostgreSQL. Lo que verifican es la traducción del
 * análisis físico a una decisión de compra, que es donde más fácil se cuela un
 * error de signo.
 */
class CatalogValidationTest {

    @Nested
    @DisplayName("Lectura del factor de rendimiento")
    class YieldFactorReading {

        @Test
        @DisplayName("por debajo de 90 el café rinde más que el estándar")
        void excepcional() {
            assertEquals("Excepcional", lotConFactor("86.00").getYieldFactorLabel());
            assertEquals("Excepcional", lotConFactor("89.00").getYieldFactorLabel());
        }

        @Test
        @DisplayName("de 90 a 92 es apto para trilla de excelso")
        void deExportacion() {
            assertEquals("De exportación", lotConFactor("90.00").getYieldFactorLabel());
            assertEquals("De exportación", lotConFactor("92.00").getYieldFactorLabel());
        }

        @Test
        @DisplayName("94 es el estándar de la Federación")
        void estandar() {
            assertEquals("Estándar", lotConFactor("94.00").getYieldFactorLabel());
            assertEquals("Estándar", lotConFactor("96.00").getYieldFactorLabel());
        }

        @Test
        @DisplayName("por encima de 96 hay que trillar más para el mismo excelso")
        void bajoRendimiento() {
            assertEquals("Bajo rendimiento", lotConFactor("97.00").getYieldFactorLabel());
            assertEquals("Bajo rendimiento", lotConFactor("110.00").getYieldFactorLabel());
        }

        @Test
        @DisplayName("menos es mejor: es la inversión que más se presta a equivocarse")
        void menosEsMejor() {
            String mejor = lotConFactor("86.00").getYieldFactorLabel();
            String peor = lotConFactor("98.00").getYieldFactorLabel();

            assertEquals("Excepcional", mejor);
            assertEquals("Bajo rendimiento", peor);
        }

        @Test
        @DisplayName("un lote sin factor no afirma que cumple nada")
        void sinDeclarar() {
            PergaminoLot lote = new PergaminoLot(1, "SIN-001", new BigDecimal("20000"), 100);

            assertEquals("Sin declarar", lote.getYieldFactorLabel());
        }
    }

    @Nested
    @DisplayName("Humedad")
    class Moisture {

        @Test
        @DisplayName("entre 10 % y 12 % el pergamino se conserva")
        void enRango() {
            assertTrue(lotConHumedad("10.00").isMoistureInRange());
            assertTrue(lotConHumedad("11.50").isMoistureInRange());
            assertTrue(lotConHumedad("12.00").isMoistureInRange());
        }

        @Test
        @DisplayName("por debajo del 10 % el grano se quiebra en la trilla")
        void muySeco() {
            assertFalse(lotConHumedad("9.50").isMoistureInRange());
        }

        @Test
        @DisplayName("por encima del 12 % hay riesgo de hongos")
        void humedo() {
            assertFalse(lotConHumedad("12.80").isMoistureInRange());
        }

        @Test
        @DisplayName("sin el dato no se puede afirmar que esté en rango")
        void sinDato() {
            PergaminoLot lote = new PergaminoLot(1, "SIN-002", new BigDecimal("20000"), 100);

            assertFalse(lote.isMoistureInRange());
        }
    }

    @Nested
    @DisplayName("Cantidades y valor")
    class Amounts {

        @Test
        @DisplayName("los kilos se leen en cargas de 125 kg")
        void lecturaEnCargas() {
            assertEquals("1250 kg (10 cargas)", lotConKilos(1250).getAvailableAsCargas());
            assertEquals("375 kg (3 cargas)", lotConKilos(375).getAvailableAsCargas());
            assertEquals("125 kg (1 carga)", lotConKilos(125).getAvailableAsCargas());
        }

        @Test
        @DisplayName("por debajo de una carga no se convierte")
        void pordebajoDeUnaCarga() {
            // «0,6 cargas» no es como nadie cuenta el café.
            assertEquals("80 kg", lotConKilos(80).getAvailableAsCargas());
        }

        @Test
        @DisplayName("el valor del lote no usa coma flotante")
        void valorExacto() {
            PergaminoLot lote = new PergaminoLot(1, "VAL-001", new BigDecimal("24500.00"), 1250);

            // 24500,00 × 1250 = 30.625.000,00 exacto. En double daría arrastre.
            assertEquals(0, new BigDecimal("30625000.00").compareTo(lote.getTotalValue()));
        }
    }

    // ------------------------------------------------------------------
    // Auxiliares
    // ------------------------------------------------------------------

    private static PergaminoLot lotConFactor(String factor) {
        PergaminoLot lote = new PergaminoLot(1, "TEST-001", new BigDecimal("20000"), 100);
        lote.setYieldFactor(new BigDecimal(factor));
        return lote;
    }

    private static PergaminoLot lotConHumedad(String humedad) {
        PergaminoLot lote = new PergaminoLot(1, "TEST-002", new BigDecimal("20000"), 100);
        lote.setMoisturePct(new BigDecimal(humedad));
        return lote;
    }

    private static PergaminoLot lotConKilos(int kilos) {
        return new PergaminoLot(1, "TEST-003", new BigDecimal("20000"), kilos);
    }
}
