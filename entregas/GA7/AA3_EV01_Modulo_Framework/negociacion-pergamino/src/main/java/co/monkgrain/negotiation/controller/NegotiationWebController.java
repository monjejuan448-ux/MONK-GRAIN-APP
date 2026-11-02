package co.monkgrain.negotiation.controller;

import co.monkgrain.negotiation.dto.DemandRequest;
import co.monkgrain.negotiation.dto.OfferRequest;
import co.monkgrain.negotiation.service.BusinessRuleException;
import co.monkgrain.negotiation.service.NegotiationService;
import co.monkgrain.negotiation.service.NotFoundException;
import jakarta.validation.Valid;
import java.math.BigDecimal;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

/**
 * Las pantallas del módulo de negociación.
 *
 * <p>Existe además de la API porque una regla de negocio se demuestra mejor
 * viéndola rechazar un formulario que leyendo un JSON. Comparte el mismo
 * servicio: no hay una segunda copia de las reglas, que es justo lo que la
 * separación en capas permite.
 *
 * <p>Las plantillas son de Thymeleaf. Tras un envío que modifica datos se
 * responde con una redirección, no con el contenido: sin eso, recargar la
 * página vuelve a enviar el formulario.
 */
@Controller
public class NegotiationWebController {

    private final NegotiationService service;

    public NegotiationWebController(NegotiationService service) {
        this.service = service;
    }

    // ------------------------------------------------------------------
    // Comprador
    // ------------------------------------------------------------------

    @GetMapping("/")
    public String inicio() {
        return "redirect:/solicitudes";
    }

    @GetMapping("/solicitudes")
    public String listarSolicitudes(Model modelo,
                                    @RequestParam(required = false) String aviso) {
        modelo.addAttribute("solicitudes", service.listDemands());
        modelo.addAttribute("aviso", aviso);
        return "solicitudes";
    }

    @GetMapping("/solicitudes/nueva")
    public String formularioSolicitud(Model modelo) {
        // Un objeto vacío para que la plantilla pueda enlazar los campos y
        // conservar lo escrito si la validación falla.
        if (!modelo.containsAttribute("solicitud")) {
            modelo.addAttribute("solicitud", new DemandRequest());
        }
        return "solicitud-formulario";
    }

    @PostMapping("/solicitudes")
    public String publicarSolicitud(@Valid @ModelAttribute("solicitud") DemandRequest solicitud,
                                    BindingResult errores,
                                    RedirectAttributes redireccion) {
        // `BindingResult` inmediatamente después del objeto validado: en otro
        // orden Spring lanza la excepción en lugar de entregar los errores, y
        // el formulario no puede mostrarlos junto a cada campo.
        if (errores.hasErrors()) {
            return "solicitud-formulario";
        }

        var creada = service.publishDemand(solicitud.toEntity());
        redireccion.addAttribute("aviso",
                "Solicitud publicada con el número " + creada.getId() + ".");
        return "redirect:/solicitudes";
    }

    @GetMapping("/solicitudes/{id}")
    public String verSolicitud(@PathVariable Long id, Model modelo,
                               @RequestParam(required = false) String aviso) {
        modelo.addAttribute("solicitud", service.findDemand(id));
        modelo.addAttribute("posturas", service.listOffersFor(id));
        modelo.addAttribute("aviso", aviso);
        if (!modelo.containsAttribute("postura")) {
            modelo.addAttribute("postura", new OfferRequest());
        }
        return "solicitud-detalle";
    }

    @PostMapping("/solicitudes/{id}/cerrar")
    public String cerrarSolicitud(@PathVariable Long id,
                                  @RequestParam(required = false) String motivo,
                                  RedirectAttributes redireccion) {
        var cerrada = service.closeDemand(id, motivo);
        redireccion.addAttribute("aviso",
                "La solicitud quedó en estado " + cerrada.getStatus() + ".");
        return "redirect:/solicitudes/" + id;
    }

    // ------------------------------------------------------------------
    // Vendedor
    // ------------------------------------------------------------------

    @PostMapping("/solicitudes/{id}/posturas")
    public String posturar(@PathVariable Long id,
                           @Valid @ModelAttribute("postura") OfferRequest postura,
                           BindingResult errores,
                           Model modelo,
                           RedirectAttributes redireccion) {
        if (errores.hasErrors()) {
            modelo.addAttribute("solicitud", service.findDemand(id));
            modelo.addAttribute("posturas", service.listOffersFor(id));
            return "solicitud-detalle";
        }

        var creada = service.makeOffer(id, postura.toEntity());
        redireccion.addAttribute("aviso",
                "Postura registrada con el número " + creada.getId() + ".");
        return "redirect:/solicitudes/" + id;
    }

    @PostMapping("/posturas/{id}/aceptar")
    public String aceptar(@PathVariable Long id, RedirectAttributes redireccion) {
        var aceptada = service.acceptOffer(id);
        redireccion.addAttribute("aviso",
                "Aceptaste " + aceptada.getOfferedKg() + " kg de " + aceptada.getSellerName() + ".");
        return "redirect:/solicitudes/" + aceptada.getDemandId();
    }

    @PostMapping("/posturas/{id}/rechazar")
    public String rechazar(@PathVariable Long id,
                           @RequestParam(required = false) String motivo,
                           RedirectAttributes redireccion) {
        var rechazada = service.rejectOffer(id, motivo);
        redireccion.addAttribute("aviso", "Postura rechazada.");
        return "redirect:/solicitudes/" + rechazada.getDemandId();
    }

    @GetMapping("/vendedor")
    public String panelVendedor(@RequestParam(required = false) String nombre,
                                @RequestParam(required = false) BigDecimal factor,
                                Model modelo) {
        modelo.addAttribute("nombre", nombre);
        modelo.addAttribute("factor", factor);
        modelo.addAttribute("compatibles", service.findMatchingDemands(factor));
        modelo.addAttribute("misPosturas",
                nombre == null || nombre.isBlank()
                        ? java.util.List.of()
                        : service.listOffersBySeller(nombre));
        return "vendedor";
    }

    // ------------------------------------------------------------------
    // Errores de las pantallas
    // ------------------------------------------------------------------
    //
    // El manejador de la API devuelve JSON; aquí hace falta una página. Son
    // dos traducciones del mismo error, no dos reglas distintas.

    @org.springframework.web.bind.annotation.ExceptionHandler(BusinessRuleException.class)
    public String reglaDeNegocio(BusinessRuleException e, Model modelo) {
        modelo.addAttribute("titulo", "No pudimos continuar");
        modelo.addAttribute("mensaje", e.getMessage());
        return "error";
    }

    @org.springframework.web.bind.annotation.ExceptionHandler(NotFoundException.class)
    public String noEncontrado(NotFoundException e, Model modelo) {
        modelo.addAttribute("titulo", "No encontramos eso");
        modelo.addAttribute("mensaje", e.getMessage());
        return "error";
    }
}
