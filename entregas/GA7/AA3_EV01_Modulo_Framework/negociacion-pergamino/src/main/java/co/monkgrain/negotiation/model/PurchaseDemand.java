package co.monkgrain.negotiation.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Lo que un comprador busca: el otro sentido del mercado.
 *
 * <p>En el catálogo el vendedor publica lo que tiene; aquí el comprador publica
 * lo que necesita, y los caficultores responden con su precio. Es la diferencia
 * entre esperar a que aparezca el café que uno quiere y pedirlo.
 *
 * <p>Las anotaciones de validación viven sobre el modelo —es lo que aporta el
 * framework frente al módulo anterior, donde la comprobación se escribía a
 * mano—. La regla queda junto al dato que restringe, no en otro archivo que hay
 * que recordar actualizar.
 */
@Entity
@Table(name = "purchase_demands")
public class PurchaseDemand {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "demand_id")
    private Long id;

    @NotBlank(message = "El comprador es obligatorio.")
    @Size(max = 150)
    @Column(name = "buyer_name", nullable = false, length = 150)
    private String buyerName;

    @NotBlank(message = "Indica qué buscas.")
    @Size(max = 200, message = "El título no puede pasar de 200 caracteres.")
    @Column(nullable = false, length = 200)
    private String title;

    @Size(max = 2000)
    @Column(length = 2000)
    private String description;

    /** Kilos que busca el comprador. Una carga son 125 kg. */
    @Min(value = 1, message = "Los kilos que buscas deben ser al menos 1.")
    @Column(name = "wanted_kg", nullable = false)
    private int wantedKg;

    /**
     * Kilos ya cubiertos por posturas aceptadas.
     *
     * <p>No lo fija el comprador: lo calcula el servicio al aceptar cada
     * postura. Dejar que se escriba desde fuera permitiría declarar cubierta
     * una solicitud que no lo está.
     */
    @Column(name = "covered_kg", nullable = false)
    private int coveredKg = 0;

    /**
     * Techo del factor de rendimiento que acepta.
     *
     * <p>Se acota por el máximo porque <strong>menos es mejor</strong>: un
     * filtro por mínimo no tendría sentido en este dato.
     */
    @DecimalMin(value = "80.0", message = "El factor de rendimiento debe estar entre 80 y 130.")
    @Column(name = "max_yield_factor", precision = 5, scale = 2)
    private BigDecimal maxYieldFactor;

    /** Lo máximo que paga por kilo. Los vendedores posturan por debajo. */
    @DecimalMin(value = "0.0", message = "El precio máximo no puede ser negativo.")
    @Column(name = "max_price_per_kg", precision = 14, scale = 2)
    private BigDecimal maxPricePerKg;

    @Future(message = "La fecha de vigencia debe ser futura.")
    @Column(name = "valid_until")
    private LocalDate validUntil;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private DemandStatus status = DemandStatus.OPEN;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    /**
     * Las posturas recibidas.
     *
     * <p>No se serializa en JSON, por dos razones que se refuerzan: es una
     * colección perezosa y, con {@code open-in-view} desactivado —que es lo
     * correcto—, cargarla al escribir la respuesta falla con «could not
     * initialize proxy». Y aunque cargara, cada postura apunta de vuelta a su
     * solicitud, de modo que Jackson entraría en un ciclo.
     *
     * <p>Las posturas de una solicitud se piden a
     * {@code /solicitudes/{id}/posturas}, que además las devuelve en el orden
     * que le sirve al comprador.
     */
    @JsonIgnore
    @OneToMany(mappedBy = "demand", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<SellerOffer> offers = new ArrayList<>();

    // ------------------------------------------------------------------
    // Lecturas derivadas
    // ------------------------------------------------------------------

    /** Kilos que faltan por cubrir. */
    public int getRemainingKg() {
        return Math.max(0, wantedKg - coveredKg);
    }

    /** Porcentaje cubierto, para mostrar el avance. */
    public int getCoveredPercentage() {
        if (wantedKg == 0) {
            return 0;
        }
        return (int) Math.round(coveredKg * 100.0 / wantedKg);
    }

    /** Si ya venció la vigencia que puso el comprador. */
    public boolean isExpired() {
        return validUntil != null && validUntil.isBefore(LocalDate.now());
    }

    /**
     * Si admite posturas ahora mismo.
     *
     * <p>No basta con el estado: una solicitud abierta pero vencida tampoco las
     * admite, y olvidarlo dejaría a los vendedores posturando sobre algo que ya
     * no está vivo.
     */
    public boolean isReceivingOffers() {
        return status.isReceivingOffers() && !isExpired();
    }

    /** Los kilos leídos en cargas, que es como se habla del café. */
    public String getWantedAsCargas() {
        if (wantedKg < 125) {
            return wantedKg + " kg";
        }
        int cargas = wantedKg / 125;
        return String.format("%d kg (%d carga%s)", wantedKg, cargas, cargas == 1 ? "" : "s");
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

    public int getCoveredKg() {
        return coveredKg;
    }

    public void setCoveredKg(int coveredKg) {
        this.coveredKg = coveredKg;
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

    public DemandStatus getStatus() {
        return status;
    }

    public void setStatus(DemandStatus status) {
        this.status = status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public List<SellerOffer> getOffers() {
        return offers;
    }

    public void setOffers(List<SellerOffer> offers) {
        this.offers = offers;
    }
}
