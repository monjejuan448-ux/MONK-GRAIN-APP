package co.monkgrain.catalog.model;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * Lote de café pergamino seco publicado por un vendedor.
 *
 * <p>El pergamino es el café despulpado, fermentado, lavado y secado que todavía
 * conserva la película que envuelve la almendra y <strong>no ha pasado por
 * trilla</strong>. No se describe por cómo sabe en taza, sino por cuánto café
 * exportable rinde al trillarlo: de ahí que el atributo que gobierna su valor
 * sea el factor de rendimiento y no un puntaje de catación.
 *
 * <p>Los importes usan {@link BigDecimal} y nunca {@code double}: en coma
 * flotante, 0,1 + 0,2 no es 0,3, y sobre el precio de una carga de 125 kg ese
 * error se vuelve dinero real.
 */
public class PergaminoLot {

    /** Kilogramos de una carga, la unidad en que se habla del café en Colombia. */
    public static final int KILOS_PER_CARGA = 125;

    /** Estándar de la Federación Nacional de Cafeteros. */
    public static final BigDecimal STANDARD_YIELD_FACTOR = new BigDecimal("94");

    private int lotId;
    private int producerId;
    private String lotCode;
    private String variety;

    // --- Análisis físico. Todo opcional: exigirlo para publicar dejaría fuera
    // --- a la mayoría de caficultores pequeños.
    private BigDecimal yieldFactor;
    private BigDecimal moisturePct;
    private BigDecimal healthyBeanPct;
    private BigDecimal pasillaPct;
    private BigDecimal borerDamagePct;

    // --- Condiciones comerciales ---
    private BigDecimal pricePerKg;
    private int availableKg;
    private LocalDate harvestDate;
    private boolean published;
    private LocalDateTime createdAt;

    public PergaminoLot() {
    }

    public PergaminoLot(int producerId, String lotCode, BigDecimal pricePerKg, int availableKg) {
        this.producerId = producerId;
        this.lotCode = lotCode;
        this.pricePerKg = pricePerKg;
        this.availableKg = availableKg;
    }

    // ------------------------------------------------------------------
    // Lecturas derivadas del dominio
    // ------------------------------------------------------------------

    /**
     * Traduce el factor de rendimiento a la etiqueta que usa el comercio.
     *
     * <p>Un «91,50» no le dice nada a quien no sabe que 94 es el estándar. Los
     * cortes siguen la práctica comercial colombiana: por debajo de 90 se paga
     * sobreprecio; por encima de 96 hay que trillar más pergamino para el mismo
     * excelso.
     *
     * @return la lectura, o {@code "Sin declarar"} si el lote no trae el dato
     */
    public String getYieldFactorLabel() {
        if (yieldFactor == null) {
            return "Sin declarar";
        }
        int factor = yieldFactor.intValue();
        if (factor <= 89) {
            return "Excepcional";
        }
        if (factor <= 92) {
            return "De exportación";
        }
        if (factor <= 96) {
            return "Estándar";
        }
        return "Bajo rendimiento";
    }

    /**
     * Si la humedad está en el rango seguro de almacenamiento.
     *
     * <p>Por debajo del 10 % el grano se quiebra en la trilla; por encima del
     * 12 % hay riesgo de hongos y es causal de rechazo en un punto de compra.
     */
    public boolean isMoistureInRange() {
        if (moisturePct == null) {
            return false;
        }
        return moisturePct.compareTo(new BigDecimal("10")) >= 0
                && moisturePct.compareTo(new BigDecimal("12")) <= 0;
    }

    /** Valor total del lote: precio por kilo por los kilos disponibles. */
    public BigDecimal getTotalValue() {
        if (pricePerKg == null) {
            return BigDecimal.ZERO;
        }
        return pricePerKg.multiply(BigDecimal.valueOf(availableKg));
    }

    /**
     * Los kilos disponibles leídos en cargas.
     *
     * <p>Por debajo de una carga no se convierte: «0,6 cargas» no es como nadie
     * cuenta el café.
     */
    public String getAvailableAsCargas() {
        if (availableKg < KILOS_PER_CARGA) {
            return availableKg + " kg";
        }
        int cargas = availableKg / KILOS_PER_CARGA;
        return String.format("%d kg (%d carga%s)", availableKg, cargas, cargas == 1 ? "" : "s");
    }

    // ------------------------------------------------------------------
    // Accesores
    // ------------------------------------------------------------------

    public int getLotId() {
        return lotId;
    }

    public void setLotId(int lotId) {
        this.lotId = lotId;
    }

    public int getProducerId() {
        return producerId;
    }

    public void setProducerId(int producerId) {
        this.producerId = producerId;
    }

    public String getLotCode() {
        return lotCode;
    }

    public void setLotCode(String lotCode) {
        this.lotCode = lotCode;
    }

    public String getVariety() {
        return variety;
    }

    public void setVariety(String variety) {
        this.variety = variety;
    }

    public BigDecimal getYieldFactor() {
        return yieldFactor;
    }

    public void setYieldFactor(BigDecimal yieldFactor) {
        this.yieldFactor = yieldFactor;
    }

    public BigDecimal getMoisturePct() {
        return moisturePct;
    }

    public void setMoisturePct(BigDecimal moisturePct) {
        this.moisturePct = moisturePct;
    }

    public BigDecimal getHealthyBeanPct() {
        return healthyBeanPct;
    }

    public void setHealthyBeanPct(BigDecimal healthyBeanPct) {
        this.healthyBeanPct = healthyBeanPct;
    }

    public BigDecimal getPasillaPct() {
        return pasillaPct;
    }

    public void setPasillaPct(BigDecimal pasillaPct) {
        this.pasillaPct = pasillaPct;
    }

    public BigDecimal getBorerDamagePct() {
        return borerDamagePct;
    }

    public void setBorerDamagePct(BigDecimal borerDamagePct) {
        this.borerDamagePct = borerDamagePct;
    }

    public BigDecimal getPricePerKg() {
        return pricePerKg;
    }

    public void setPricePerKg(BigDecimal pricePerKg) {
        this.pricePerKg = pricePerKg;
    }

    public int getAvailableKg() {
        return availableKg;
    }

    public void setAvailableKg(int availableKg) {
        this.availableKg = availableKg;
    }

    public LocalDate getHarvestDate() {
        return harvestDate;
    }

    public void setHarvestDate(LocalDate harvestDate) {
        this.harvestDate = harvestDate;
    }

    public boolean isPublished() {
        return published;
    }

    public void setPublished(boolean published) {
        this.published = published;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    @Override
    public String toString() {
        return String.format("[%d] %s — factor %s (%s) — %s a %s/kg",
                lotId,
                lotCode,
                yieldFactor == null ? "—" : yieldFactor.toPlainString(),
                getYieldFactorLabel(),
                getAvailableAsCargas(),
                pricePerKg == null ? "—" : pricePerKg.toPlainString());
    }
}
