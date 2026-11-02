package co.monkgrain.negotiation.dto;

import co.monkgrain.negotiation.model.SellerOffer;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

/**
 * Lo que un vendedor envía para posturar sobre una solicitud.
 *
 * <p>No incluye la solicitud: esa la establece el servidor a partir de la ruta.
 * Tenerla en el cuerpo permitiría posturar sobre una solicitud distinta de la
 * que dice la dirección, y dejaría la petición con dos fuentes de verdad.
 */
public record OfferRequest(

        @NotBlank(message = "El vendedor es obligatorio.")
        @Size(max = 150)
        String sellerName,

        @NotBlank(message = "El código del lote es obligatorio.")
        @Size(max = 60)
        String lotCode,

        @Min(value = 1, message = "Los kilos ofrecidos deben ser al menos 1.")
        int offeredKg,

        @NotNull(message = "El precio por kilogramo es obligatorio.")
        @DecimalMin(value = "0.0", inclusive = false,
                message = "El precio por kilogramo debe ser mayor que cero.")
        BigDecimal pricePerKg,

        @DecimalMin(value = "80.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
        @DecimalMax(value = "130.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
        BigDecimal yieldFactor,

        @Size(max = 1000)
        String note) {

    /** Construye la entidad con lo que el vendedor sí puede decidir. */
    public SellerOffer toEntity() {
        SellerOffer offer = new SellerOffer();
        offer.setSellerName(sellerName);
        offer.setLotCode(lotCode);
        offer.setOfferedKg(offeredKg);
        offer.setPricePerKg(pricePerKg);
        offer.setYieldFactor(yieldFactor);
        offer.setNote(note);
        return offer;
    }
}
