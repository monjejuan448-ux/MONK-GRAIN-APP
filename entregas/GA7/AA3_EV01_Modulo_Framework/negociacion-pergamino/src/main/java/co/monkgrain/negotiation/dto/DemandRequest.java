package co.monkgrain.negotiation.dto;

import co.monkgrain.negotiation.model.PurchaseDemand;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.LocalDate;
import org.springframework.format.annotation.DateTimeFormat;

/**
 * Lo que un comprador envía para publicar una solicitud.
 *
 * <p>Existe por una razón concreta, no por ceremonia: exponer la entidad como
 * cuerpo de la petición deja que el cliente escriba <em>cualquier</em> campo,
 * incluidos {@code id}, {@code status} y {@code coveredKg}. Un
 * {@code "id": 5} convertiría el alta en una sobrescritura de la solicitud 5, y
 * un {@code "coveredKg"} permitiría declarar cubierta una solicitud que no lo
 * está. Con este objeto, lo que no está aquí no se puede enviar.
 *
 * <p><strong>Es una clase mutable y no un {@code record}.</strong> Empezó
 * siéndolo, y con JSON funcionaba bien. En el formulario HTML, en cambio,
 * escribir «abc» donde van los kilos devolvía un <strong>500</strong>: un
 * {@code record} se construye entero o no se construye, de modo que al fallar
 * una conversión Spring no puede entregar un objeto a medias y la plantilla
 * recibía {@code null} al intentar reponer lo escrito. Un formulario que debe
 * devolver al usuario lo que tecleó necesita un objeto que admita quedar
 * incompleto.
 */
public class DemandRequest {

    @NotBlank(message = "El comprador es obligatorio.")
    @Size(max = 150, message = "El comprador no puede pasar de 150 caracteres.")
    private String buyerName;

    @NotBlank(message = "Indica qué buscas.")
    @Size(max = 200, message = "El título no puede pasar de 200 caracteres.")
    private String title;

    @Size(max = 2000, message = "Los detalles no pueden pasar de 2000 caracteres.")
    private String description;

    @Min(value = 1, message = "Los kilos que buscas deben ser al menos 1.")
    private int wantedKg;

    @DecimalMin(value = "80.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
    @DecimalMax(value = "130.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
    private BigDecimal maxYieldFactor;

    @DecimalMin(value = "0.0", inclusive = false,
            message = "El precio máximo debe ser mayor que cero.")
    private BigDecimal maxPricePerKg;

    /**
     * Vigencia de la solicitud.
     *
     * <p>{@code @DateTimeFormat} fija el formato esperado. Sin él, una fecha
     * escrita como «15/09/2026» produce un error de conversión cuyo mensaje
     * menciona clases de Java en lugar de decir qué formato se espera.
     */
    @Future(message = "La fecha de vigencia debe ser futura.")
    @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
    private LocalDate validUntil;

    /** Construye la entidad con lo que el cliente sí puede decidir. */
    public PurchaseDemand toEntity() {
        PurchaseDemand demand = new PurchaseDemand();
        demand.setBuyerName(buyerName);
        demand.setTitle(title);
        demand.setDescription(description);
        demand.setWantedKg(wantedKg);
        demand.setMaxYieldFactor(maxYieldFactor);
        demand.setMaxPricePerKg(maxPricePerKg);
        demand.setValidUntil(validUntil);
        return demand;
    }

    public String getBuyerName() {
        return buyerName;
    }

    public void setBuyerName(String buyerName) {
        this.buyerName = buyerName;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public int getWantedKg() {
        return wantedKg;
    }

    public void setWantedKg(int wantedKg) {
        this.wantedKg = wantedKg;
    }

    public BigDecimal getMaxYieldFactor() {
        return maxYieldFactor;
    }

    public void setMaxYieldFactor(BigDecimal maxYieldFactor) {
        this.maxYieldFactor = maxYieldFactor;
    }

    public BigDecimal getMaxPricePerKg() {
        return maxPricePerKg;
    }

    public void setMaxPricePerKg(BigDecimal maxPricePerKg) {
        this.maxPricePerKg = maxPricePerKg;
    }

    public LocalDate getValidUntil() {
        return validUntil;
    }

    public void setValidUntil(LocalDate validUntil) {
        this.validUntil = validUntil;
    }
}
