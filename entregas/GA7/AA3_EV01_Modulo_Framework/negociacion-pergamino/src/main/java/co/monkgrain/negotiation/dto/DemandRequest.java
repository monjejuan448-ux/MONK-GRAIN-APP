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

/**
 * Lo que un comprador envía para publicar una solicitud.
 *
 * <p>Existe por una razón concreta, no por ceremonia: exponer la entidad como
 * cuerpo de la petición deja que el cliente escriba <em>cualquier</em> campo,
 * incluidos {@code id}, {@code status} y {@code coveredKg}. Un
 * {@code "id": 5} convertiría el alta en una sobrescritura de la solicitud 5, y
 * un {@code "coveredKg"} permitiría declarar cubierta una solicitud que no lo
 * está.
 *
 * <p>Con este objeto, lo que no está aquí no se puede enviar.
 */
public record DemandRequest(

        @NotBlank(message = "El comprador es obligatorio.")
        @Size(max = 150)
        String buyerName,

        @NotBlank(message = "Indica qué buscas.")
        @Size(max = 200, message = "El título no puede pasar de 200 caracteres.")
        String title,

        @Size(max = 2000)
        String description,

        @Min(value = 1, message = "Los kilos que buscas deben ser al menos 1.")
        int wantedKg,

        @DecimalMin(value = "80.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
        @DecimalMax(value = "130.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
        BigDecimal maxYieldFactor,

        @DecimalMin(value = "0.0", inclusive = false,
                message = "El precio máximo debe ser mayor que cero.")
        BigDecimal maxPricePerKg,

        @Future(message = "La fecha de vigencia debe ser futura.")
        LocalDate validUntil) {

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
}
