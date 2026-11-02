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
 *
 * <p>Clase mutable y no {@code record}, por la misma razón que
 * {@link DemandRequest}: el formulario debe poder devolver al usuario lo que
 * tecleó aunque una conversión falle, y un {@code record} se construye entero
 * o no se construye.
 */
public class OfferRequest {

    @NotBlank(message = "El vendedor es obligatorio.")
    @Size(max = 150, message = "El nombre del vendedor no puede pasar de 150 caracteres.")
    private String sellerName;

    @NotBlank(message = "El código del lote es obligatorio.")
    @Size(max = 60, message = "El código del lote no puede pasar de 60 caracteres.")
    private String lotCode;

    @Min(value = 1, message = "Los kilos ofrecidos deben ser al menos 1.")
    private int offeredKg;

    @NotNull(message = "El precio por kilogramo es obligatorio.")
    @DecimalMin(value = "0.0", inclusive = false,
            message = "El precio por kilogramo debe ser mayor que cero.")
    private BigDecimal pricePerKg;

    @DecimalMin(value = "80.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
    @DecimalMax(value = "130.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
    private BigDecimal yieldFactor;

    @Size(max = 1000, message = "La nota no puede pasar de 1000 caracteres.")
    private String note;

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

    public String getSellerName() {
        return sellerName;
    }

    public void setSellerName(String sellerName) {
        this.sellerName = sellerName;
    }

    public String getLotCode() {
        return lotCode;
    }

    public void setLotCode(String lotCode) {
        this.lotCode = lotCode;
    }

    public int getOfferedKg() {
        return offeredKg;
    }

    public void setOfferedKg(int offeredKg) {
        this.offeredKg = offeredKg;
    }

    public BigDecimal getPricePerKg() {
        return pricePerKg;
    }

    public void setPricePerKg(BigDecimal pricePerKg) {
        this.pricePerKg = pricePerKg;
    }

    public BigDecimal getYieldFactor() {
        return yieldFactor;
    }

    public void setYieldFactor(BigDecimal yieldFactor) {
        this.yieldFactor = yieldFactor;
    }

    public String getNote() {
        return note;
    }

    public void setNote(String note) {
        this.note = note;
    }
}
