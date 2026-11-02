package co.monkgrain.negotiation.repository;

import co.monkgrain.negotiation.model.OfferStatus;
import co.monkgrain.negotiation.model.SellerOffer;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/** Acceso a datos de las posturas de los vendedores. */
@Repository
public interface SellerOfferRepository extends JpaRepository<SellerOffer, Long> {

    /**
     * Las posturas de una solicitud, en el orden en que le sirven al comprador.
     *
     * <p>Primero las pendientes —son las que exigen una decisión— y dentro de
     * ellas, la más barata arriba. Ordenar por fecha pondría primero la que
     * llegó antes, que no es la que más le conviene.
     */
    @Query("""
            SELECT o FROM SellerOffer o
            WHERE o.demand.id = :demandaId
            ORDER BY CASE WHEN o.status = co.monkgrain.negotiation.model.OfferStatus.PENDING
                          THEN 0 ELSE 1 END,
                     o.pricePerKg ASC
            """)
    List<SellerOffer> findForDemandOrdered(@Param("demandaId") Long demandaId);

    List<SellerOffer> findBySellerNameOrderByCreatedAtDesc(String sellerName);

    /**
     * Si ese vendedor ya posturó con ese lote sobre esa solicitud.
     *
     * <p>El guion bajo de {@code Demand_Id} no es decorativo: le dice a Spring
     * Data que recorra la relación {@code demand} y tome su {@code id}. Sin él,
     * {@code DemandId} se interpreta primero como un atributo llamado
     * «demandId» —que existe como método derivado pero no como columna— y la
     * consulta falla al arrancar con «Could not resolve attribute 'demandId'».
     */
    boolean existsByDemand_IdAndSellerNameAndLotCode(
            Long demandId, String sellerName, String lotCode);

    /** Cuántas posturas siguen esperando respuesta. */
    long countByDemand_IdAndStatus(Long demandId, OfferStatus status);
}
