package co.monkgrain.negotiation.controller;

import co.monkgrain.negotiation.dto.DemandRequest;
import co.monkgrain.negotiation.dto.OfferRequest;
import co.monkgrain.negotiation.model.PurchaseDemand;
import co.monkgrain.negotiation.model.SellerOffer;
import co.monkgrain.negotiation.service.NegotiationService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.math.BigDecimal;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * API del módulo de negociación.
 *
 * <p>El controlador no contiene reglas: valida la entrada con
 * {@code @Valid} —que dispara las anotaciones del modelo— y delega en el
 * servicio. Es la misma separación del módulo anterior, con la diferencia de
 * que aquí la validación es declarativa en vez de escrita a mano.
 */
// Sin `@Validated` a propósito. Desde Spring Framework 6.1 el controlador
// valida por sí solo las restricciones puestas sobre sus parámetros, y lanza
// `HandlerMethodValidationException`. Añadir `@Validated` activa además el
// interceptor AOP heredado, que lanza `ConstraintViolationException`: con los
// dos activos la validación ocurre dos veces y el error llega por el camino
// que el manejador no espera, devolviendo un 500 en lugar de un 400.
@RestController
@RequestMapping("/api/negociacion")
public class NegotiationApiController {

    private final NegotiationService service;

    public NegotiationApiController(NegotiationService service) {
        this.service = service;
    }

    // ------------------------------------------------------------------
    // Solicitudes de compra
    // ------------------------------------------------------------------

    @GetMapping("/solicitudes")
    public List<PurchaseDemand> listarSolicitudes() {
        return service.listDemands();
    }

    @GetMapping("/solicitudes/{id}")
    public PurchaseDemand verSolicitud(@PathVariable Long id) {
        return service.findDemand(id);
    }

    @PostMapping("/solicitudes")
    public ResponseEntity<PurchaseDemand> publicarSolicitud(
            @Valid @RequestBody DemandRequest solicitud) {
        PurchaseDemand creada = service.publishDemand(solicitud.toEntity());
        return ResponseEntity.status(HttpStatus.CREATED).body(creada);
    }

    /**
     * Las solicitudes que un vendedor puede atender con un lote.
     *
     * @param factor factor de rendimiento del lote; si no se envía, no se filtra
     */
    @GetMapping("/solicitudes/compatibles")
    public List<PurchaseDemand> solicitudesCompatibles(
            @RequestParam(required = false) BigDecimal factor) {
        return service.findMatchingDemands(factor);
    }

    @PostMapping("/solicitudes/{id}/cerrar")
    public PurchaseDemand cerrarSolicitud(
            @PathVariable Long id,
            @RequestParam(required = false) String motivo) {
        return service.closeDemand(id, motivo);
    }

    // ------------------------------------------------------------------
    // Posturas
    // ------------------------------------------------------------------

    @GetMapping("/solicitudes/{id}/posturas")
    public List<SellerOffer> listarPosturas(@PathVariable Long id) {
        return service.listOffersFor(id);
    }

    @PostMapping("/solicitudes/{id}/posturas")
    public ResponseEntity<SellerOffer> posturar(
            @PathVariable Long id,
            @Valid @RequestBody OfferRequest postura) {
        SellerOffer creada = service.makeOffer(id, postura.toEntity());
        return ResponseEntity.status(HttpStatus.CREATED).body(creada);
    }

    @PostMapping("/posturas/{id}/aceptar")
    public SellerOffer aceptar(@PathVariable Long id) {
        return service.acceptOffer(id);
    }

    @PostMapping("/posturas/{id}/rechazar")
    public SellerOffer rechazar(
            @PathVariable Long id,
            @RequestParam(required = false) String motivo) {
        return service.rejectOffer(id, motivo);
    }

    @PostMapping("/posturas/{id}/retirar")
    public SellerOffer retirar(
            @PathVariable Long id,
            @RequestParam
            @NotBlank(message = "Indica qué vendedor retira la postura.")
            String vendedor) {
        return service.withdrawOffer(id, vendedor);
    }

    @GetMapping("/vendedores/{vendedor}/posturas")
    public List<SellerOffer> posturasDelVendedor(@PathVariable String vendedor) {
        return service.listOffersBySeller(vendedor);
    }
}
