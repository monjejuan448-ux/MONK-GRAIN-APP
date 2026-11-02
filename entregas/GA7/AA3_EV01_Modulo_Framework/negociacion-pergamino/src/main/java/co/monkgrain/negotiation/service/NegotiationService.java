package co.monkgrain.negotiation.service;

import co.monkgrain.negotiation.model.DemandStatus;
import co.monkgrain.negotiation.model.OfferStatus;
import co.monkgrain.negotiation.model.PurchaseDemand;
import co.monkgrain.negotiation.model.SellerOffer;
import co.monkgrain.negotiation.repository.PurchaseDemandRepository;
import co.monkgrain.negotiation.repository.SellerOfferRepository;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Las reglas del mercado de dos sentidos.
 *
 * <p>Aquí vive lo que no se puede expresar con una anotación sobre el modelo:
 * cuándo una solicitud admite posturas, qué pasa con las pendientes al cubrirse
 * los kilos, y por qué aceptar media postura no es aceptar la postura.
 *
 * <p>Las operaciones que tocan varias filas van en una transacción. Aceptar una
 * postura cambia la postura, los kilos cubiertos de la solicitud y quizá su
 * estado: si falla a la mitad, lo peor que puede pasar es que la solicitud diga
 * que tiene kilos cubiertos que nadie se comprometió a poner.
 */
@Service
public class NegotiationService {

    private final PurchaseDemandRepository demandRepository;
    private final SellerOfferRepository offerRepository;

    /**
     * Las dependencias llegan por el constructor y no por campo.
     *
     * <p>Así el objeto no puede existir a medio construir, y en las pruebas se
     * sustituyen sin necesidad del contenedor de Spring.
     */
    public NegotiationService(PurchaseDemandRepository demandRepository,
                              SellerOfferRepository offerRepository) {
        this.demandRepository = demandRepository;
        this.offerRepository = offerRepository;
    }

    // ------------------------------------------------------------------
    // Solicitudes de compra
    // ------------------------------------------------------------------

    @Transactional
    public PurchaseDemand publishDemand(PurchaseDemand demand) {
        // Los kilos cubiertos y el estado no los pone quien publica: se
        // derivan de las posturas aceptadas. Admitirlos desde fuera permitiría
        // declarar cubierta una solicitud que no lo está.
        demand.setCoveredKg(0);
        demand.setStatus(DemandStatus.OPEN);
        demand.setCreatedAt(LocalDateTime.now());
        return demandRepository.save(demand);
    }

    @Transactional(readOnly = true)
    public List<PurchaseDemand> listDemands() {
        return demandRepository.findAllByOrderByCreatedAtDesc();
    }

    @Transactional(readOnly = true)
    public PurchaseDemand findDemand(Long id) {
        return demandRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("No existe la solicitud " + id + "."));
    }

    /**
     * Las solicitudes que un vendedor puede atender con un lote concreto.
     *
     * @param lotYieldFactor factor del lote, o {@code null} si no lo ha declarado
     */
    @Transactional(readOnly = true)
    public List<PurchaseDemand> findMatchingDemands(BigDecimal lotYieldFactor) {
        return demandRepository.findMatchingForSeller(LocalDate.now(), lotYieldFactor);
    }

    /**
     * El comprador cierra la solicitud antes de cubrirla.
     *
     * <p>Las posturas que seguían esperando se rechazan con un motivo: dejarlas
     * pendientes para siempre es peor que un «no», porque el vendedor sigue
     * contando con esos kilos.
     */
    @Transactional
    public PurchaseDemand closeDemand(Long demandId, String reason) {
        PurchaseDemand demand = findDemand(demandId);

        if (demand.getStatus() == DemandStatus.CLOSED
                || demand.getStatus() == DemandStatus.CANCELLED) {
            throw new BusinessRuleException("Esta solicitud ya está cerrada.");
        }

        // Cerrar sin haber cubierto nada es cancelar; con algo cubierto, es
        // cerrar. La distinción importa en el historial del comprador.
        demand.setStatus(demand.getCoveredKg() > 0
                ? DemandStatus.CLOSED
                : DemandStatus.CANCELLED);

        rejectPendingOffers(demand, reason == null || reason.isBlank()
                ? "El comprador cerró la solicitud."
                : reason);

        return demandRepository.save(demand);
    }

    // ------------------------------------------------------------------
    // Posturas
    // ------------------------------------------------------------------

    /**
     * Un vendedor responde a una solicitud con su precio.
     *
     * @throws BusinessRuleException si la solicitud no admite posturas, si ya
     *     posturó con ese lote, o si ofrece más kilos de los que faltan
     */
    @Transactional
    public SellerOffer makeOffer(Long demandId, SellerOffer offer) {
        PurchaseDemand demand = findDemand(demandId);

        if (!demand.isReceivingOffers()) {
            throw new BusinessRuleException(demand.isExpired()
                    ? "Esta solicitud venció el " + demand.getValidUntil() + "."
                    : "Esta solicitud ya no admite posturas.");
        }

        if (offerRepository.existsByDemand_IdAndSellerNameAndLotCode(
                demandId, offer.getSellerName(), offer.getLotCode())) {
            throw new BusinessRuleException(
                    "Ya posturaste sobre esta solicitud con el lote " + offer.getLotCode() + ".");
        }

        // Ofrecer más de lo que falta no es generosidad: el comprador tendría
        // que aceptar de más o rechazar entera una postura que le servía.
        if (offer.getOfferedKg() > demand.getRemainingKg()) {
            throw new BusinessRuleException(
                    "Solo faltan " + demand.getRemainingKg() + " kg por cubrir.");
        }

        if (demand.getMaxPricePerKg() != null
                && offer.getPricePerKg().compareTo(demand.getMaxPricePerKg()) > 0) {
            throw new BusinessRuleException(
                    "El comprador paga como máximo " + demand.getMaxPricePerKg() + " por kilo.");
        }

        offer.setDemand(demand);
        offer.setStatus(OfferStatus.PENDING);
        offer.setCreatedAt(LocalDateTime.now());
        return offerRepository.save(offer);
    }

    @Transactional(readOnly = true)
    public List<SellerOffer> listOffersFor(Long demandId) {
        findDemand(demandId);
        return offerRepository.findForDemandOrdered(demandId);
    }

    @Transactional(readOnly = true)
    public List<SellerOffer> listOffersBySeller(String sellerName) {
        return offerRepository.findBySellerNameOrderByCreatedAtDesc(sellerName);
    }

    /**
     * El comprador acepta una postura.
     *
     * <p>Sumar los kilos puede cubrir la solicitud entera, y entonces las
     * posturas que seguían pendientes se rechazan: el vendedor tiene derecho a
     * saber que ya no le van a comprar.
     */
    @Transactional
    public SellerOffer acceptOffer(Long offerId) {
        SellerOffer offer = findOffer(offerId);
        PurchaseDemand demand = offer.getDemand();

        requireOpen(offer);

        // Entre que se hizo la postura y se responde, otras pueden haberse
        // aceptado. Volver a comprobar aquí evita cubrir de más.
        if (offer.getOfferedKg() > demand.getRemainingKg()) {
            throw new BusinessRuleException(
                    "Ya solo faltan " + demand.getRemainingKg() + " kg: "
                    + "se aceptaron otras posturas mientras tanto.");
        }

        offer.setStatus(OfferStatus.ACCEPTED);
        offer.setRespondedAt(LocalDateTime.now());

        demand.setCoveredKg(demand.getCoveredKg() + offer.getOfferedKg());

        if (demand.getRemainingKg() == 0) {
            demand.setStatus(DemandStatus.FULFILLED);
            rejectPendingOffers(demand, "La solicitud se cubrió con otras posturas.");
        } else {
            demand.setStatus(DemandStatus.PARTIALLY_COVERED);
        }

        demandRepository.save(demand);
        return offerRepository.save(offer);
    }

    /**
     * El comprador rechaza una postura.
     *
     * <p>El motivo es obligatorio. Un «no» sin explicación no le dice al
     * caficultor si el problema fue el precio, el factor o la cantidad, de modo
     * que no puede corregir nada en la siguiente.
     */
    @Transactional
    public SellerOffer rejectOffer(Long offerId, String reason) {
        SellerOffer offer = findOffer(offerId);
        requireOpen(offer);

        if (reason == null || reason.isBlank()) {
            throw new BusinessRuleException(
                    "Indica por qué rechazas la postura: sin un motivo, el vendedor no "
                    + "sabe qué corregir en la siguiente.");
        }

        offer.setStatus(OfferStatus.REJECTED);
        offer.setResponseNote(reason.trim());
        offer.setRespondedAt(LocalDateTime.now());
        return offerRepository.save(offer);
    }

    /** El vendedor retira su postura antes de que le respondan. */
    @Transactional
    public SellerOffer withdrawOffer(Long offerId, String sellerName) {
        SellerOffer offer = findOffer(offerId);

        if (!offer.getSellerName().equals(sellerName)) {
            throw new BusinessRuleException("Esta postura no es tuya.");
        }
        requireOpen(offer);

        offer.setStatus(OfferStatus.WITHDRAWN);
        offer.setRespondedAt(LocalDateTime.now());
        return offerRepository.save(offer);
    }

    // ------------------------------------------------------------------
    // Utilidades internas
    // ------------------------------------------------------------------

    private SellerOffer findOffer(Long id) {
        return offerRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("No existe la postura " + id + "."));
    }

    /** Una postura ya respondida o retirada no vuelve a tocarse. */
    private void requireOpen(SellerOffer offer) {
        if (!offer.getStatus().isOpen()) {
            throw new BusinessRuleException(
                    "Esta postura ya fue respondida: está en estado " + offer.getStatus() + ".");
        }
    }

    private void rejectPendingOffers(PurchaseDemand demand, String reason) {
        for (SellerOffer pending : offerRepository.findForDemandOrdered(demand.getId())) {
            if (pending.getStatus().isOpen()) {
                pending.setStatus(OfferStatus.REJECTED);
                pending.setResponseNote(reason);
                pending.setRespondedAt(LocalDateTime.now());
                offerRepository.save(pending);
            }
        }
    }
}
