package co.monkgrain.negotiation.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import jakarta.persistence.UniqueConstraint;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * La respuesta de un caficultor a una solicitud de compra.
 *
 * <p>Dice cuántos kilos puede poner, a qué precio y con qué factor de
 * rendimiento. El comprador acepta, rechaza con motivo, o deja pasar la
 * vigencia.
 */
@Entity
@Table(
        name = "seller_offers",
        // Un vendedor no postura dos veces sobre la misma solicitud con el
        // mismo lote: sería competir consigo mismo y duplicaría los kilos
        // comprometidos si se aceptaran las dos.
        uniqueConstraints = @UniqueConstraint(
                name = "uq_offer_seller_lot_per_demand",
                columnNames = {"demand_id", "seller_name", "lot_code"}))
public class SellerOffer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "offer_id")
    private Long id;

    /**
     * La solicitud a la que responde.
     *
     * <p><strong>Sin anotación de validación a propósito.</strong> Este campo
     * no lo envía el vendedor: lo establece el servicio a partir de la ruta.
     * Un {@code @NotNull} aquí se evaluaría antes de que el servicio lo
     * asignara y rechazaría toda postura válida con un «must not be null» que
     * no dice nada a quien la envió. La integridad la garantiza
     * {@code nullable = false} en la columna.
     */
    @JsonIgnore
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "demand_id", nullable = false)
    private PurchaseDemand demand;

    @NotBlank(message = "El vendedor es obligatorio.")
    @Size(max = 150)
    @Column(name = "seller_name", nullable = false, length = 150)
    private String sellerName;

    @NotBlank(message = "El código del lote es obligatorio.")
    @Size(max = 60)
    @Column(name = "lot_code", nullable = false, length = 60)
    private String lotCode;

    @Min(value = 1, message = "Los kilos ofrecidos deben ser al menos 1.")
    @Column(name = "offered_kg", nullable = false)
    private int offeredKg;

    @NotNull(message = "El precio por kilogramo es obligatorio.")
    @DecimalMin(value = "0.0", inclusive = false,
            message = "El precio por kilogramo debe ser mayor que cero.")
    @Column(name = "price_per_kg", nullable = false, precision = 14, scale = 2)
    private BigDecimal pricePerKg;

    @DecimalMin(value = "80.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
    @Column(name = "yield_factor", precision = 5, scale = 2)
    private BigDecimal yieldFactor;

    @Size(max = 1000)
    @Column(length = 1000)
    private String note;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private OfferStatus status = OfferStatus.PENDING;

    /** Motivo del rechazo. Obligatorio al rechazar, y por eso no va aquí validado. */
    @Size(max = 1000)
    @Column(name = "response_note", length = 1000)
    private String responseNote;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "responded_at")
    private LocalDateTime respondedAt;

    // ------------------------------------------------------------------
    // Lecturas derivadas
    // ------------------------------------------------------------------

    /**
     * Identificador de la solicitud a la que responde.
     *
     * <p>Se expone esto y no la solicitud entera: devolverla completa dentro de
     * cada postura repetiría los mismos datos en cada elemento de la lista y,
     * al ser perezosa, fallaría al serializar fuera de la transacción.
     */
    @Transient
    public Long getDemandId() {
        return demand == null ? null : demand.getId();
    }

    /** Lo que costaría aceptar esta postura entera. */
    public BigDecimal getTotalValue() {
        if (pricePerKg == null) {
            return BigDecimal.ZERO;
        }
        return pricePerKg.multiply(BigDecimal.valueOf(offeredKg));
    }

    /** La lectura comercial del factor, la misma que usa el catálogo. */
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

    // ------------------------------------------------------------------
    // Accesores
    // ------------------------------------------------------------------

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public PurchaseDemand getDemand() {
        return demand;
    }

    public void setDemand(PurchaseDemand demand) {
        this.demand = demand;
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

    public OfferStatus getStatus() {
        return status;
    }

    public void setStatus(OfferStatus status) {
        this.status = status;
    }

    public String getResponseNote() {
        return responseNote;
    }

    public void setResponseNote(String responseNote) {
        this.responseNote = responseNote;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getRespondedAt() {
        return respondedAt;
    }

    public void setRespondedAt(LocalDateTime respondedAt) {
        this.respondedAt = respondedAt;
    }
}
