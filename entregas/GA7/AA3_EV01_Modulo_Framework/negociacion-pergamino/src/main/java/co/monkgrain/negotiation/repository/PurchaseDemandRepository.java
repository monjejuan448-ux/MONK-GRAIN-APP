package co.monkgrain.negotiation.repository;

import co.monkgrain.negotiation.model.DemandStatus;
import co.monkgrain.negotiation.model.PurchaseDemand;
import java.time.LocalDate;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/**
 * Acceso a datos de las solicitudes de compra.
 *
 * <p>Spring Data genera la implementación a partir de la firma de cada método:
 * no hay una línea de JDBC, a diferencia del módulo de la evidencia AA2-EV01.
 * Es lo que aporta el framework —y también lo que oculta, de ahí que las
 * consultas con reglas de negocio se escriban explícitas con {@code @Query}, en
 * lugar de confiarlas a un nombre de método de cuarenta caracteres.
 */
@Repository
public interface PurchaseDemandRepository extends JpaRepository<PurchaseDemand, Long> {

    /** Derivada del nombre: Spring Data la traduce a un WHERE sobre el estado. */
    List<PurchaseDemand> findByStatusOrderByCreatedAtDesc(DemandStatus status);

    /**
     * Las que un vendedor puede atender hoy.
     *
     * <p>Tres condiciones que van juntas y por eso se escriben juntas: que el
     * estado admita posturas, que no haya vencido la vigencia, y que el factor
     * del lote entre dentro del techo que pide el comprador. Un lote sin factor
     * declarado también entra: el comprador decidirá.
     */
    @Query("""
            SELECT d FROM PurchaseDemand d
            WHERE d.status IN (co.monkgrain.negotiation.model.DemandStatus.OPEN,
                               co.monkgrain.negotiation.model.DemandStatus.PARTIALLY_COVERED)
              AND (d.validUntil IS NULL OR d.validUntil >= :hoy)
              AND (:factorDelLote IS NULL
                   OR d.maxYieldFactor IS NULL
                   OR d.maxYieldFactor >= :factorDelLote)
            ORDER BY d.createdAt DESC
            """)
    List<PurchaseDemand> findMatchingForSeller(
            @Param("hoy") LocalDate hoy,
            @Param("factorDelLote") java.math.BigDecimal factorDelLote);

    /** Todas, con la más reciente primero. */
    List<PurchaseDemand> findAllByOrderByCreatedAtDesc();
}
