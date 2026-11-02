package co.monkgrain.negotiation.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import co.monkgrain.negotiation.model.DemandStatus;
import co.monkgrain.negotiation.model.OfferStatus;
import co.monkgrain.negotiation.model.PurchaseDemand;
import co.monkgrain.negotiation.model.SellerOffer;
import java.math.BigDecimal;
import java.time.LocalDate;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/**
 * Las reglas del mercado de dos sentidos.
 *
 * <p>Se prueban contra el servicio real y una base H2 en memoria, no con
 * simulacros: lo que importa verificar aquí es que los kilos cubiertos y el
 * estado de la solicitud queden consistentes tras cada operación, y eso solo se
 * ve si las escrituras ocurren de verdad.
 */
@SpringBootTest
@ActiveProfiles("test")
@Transactional
class NegotiationServiceTest {

    @Autowired
    private NegotiationService service;

    private PurchaseDemand solicitud;

    @BeforeEach
    void publicarSolicitud() {
        PurchaseDemand nueva = new PurchaseDemand();
        nueva.setBuyerName("Trilladora del Huila");
        nueva.setTitle("Pergamino factor 92 o mejor");
        nueva.setWantedKg(1250); // 10 cargas
        nueva.setMaxYieldFactor(new BigDecimal("92.00"));
        nueva.setMaxPricePerKg(new BigDecimal("26000.00"));
        nueva.setValidUntil(LocalDate.now().plusDays(30));
        solicitud = service.publishDemand(nueva);
    }

    private SellerOffer postura(String vendedor, String lote, int kilos, String precio) {
        SellerOffer oferta = new SellerOffer();
        oferta.setSellerName(vendedor);
        oferta.setLotCode(lote);
        oferta.setOfferedKg(kilos);
        oferta.setPricePerKg(new BigDecimal(precio));
        oferta.setYieldFactor(new BigDecimal("89.00"));
        return oferta;
    }

    // ------------------------------------------------------------------

    @Nested
    @DisplayName("Publicar una solicitud")
    class Publicar {

        @Test
        @DisplayName("nace abierta y sin nada cubierto")
        void naceAbierta() {
            assertThat(solicitud.getStatus()).isEqualTo(DemandStatus.OPEN);
            assertThat(solicitud.getCoveredKg()).isZero();
            assertThat(solicitud.getRemainingKg()).isEqualTo(1250);
        }

        @Test
        @DisplayName("los kilos cubiertos no los pone quien publica")
        void noSePuedeDeclararCubierta() {
            PurchaseDemand tramposa = new PurchaseDemand();
            tramposa.setBuyerName("Comprador");
            tramposa.setTitle("Intento");
            tramposa.setWantedKg(500);
            tramposa.setCoveredKg(500);          // se intenta declarar cubierta
            tramposa.setStatus(DemandStatus.FULFILLED);

            PurchaseDemand creada = service.publishDemand(tramposa);

            assertThat(creada.getCoveredKg()).isZero();
            assertThat(creada.getStatus()).isEqualTo(DemandStatus.OPEN);
        }

        @Test
        @DisplayName("los kilos se leen en cargas")
        void lecturaEnCargas() {
            assertThat(solicitud.getWantedAsCargas()).isEqualTo("1250 kg (10 cargas)");
        }
    }

    @Nested
    @DisplayName("Posturar")
    class Posturar {

        @Test
        @DisplayName("un vendedor responde con su precio")
        void posturaValida() {
            SellerOffer creada = service.makeOffer(
                    solicitud.getId(), postura("Finca El Mirador", "MIR-001", 375, "24500"));

            assertThat(creada.getStatus()).isEqualTo(OfferStatus.PENDING);
            assertThat(creada.getTotalValue())
                    .isEqualByComparingTo(new BigDecimal("9187500.00"));
        }

        @Test
        @DisplayName("no se puede ofrecer más de lo que falta")
        void masDeLoQueFalta() {
            assertThatThrownBy(() -> service.makeOffer(
                    solicitud.getId(), postura("Finca", "L-1", 2000, "24000")))
                    .isInstanceOf(BusinessRuleException.class)
                    .hasMessageContaining("Solo faltan 1250 kg");
        }

        @Test
        @DisplayName("no se postura por encima del precio máximo del comprador")
        void porEncimaDelPrecio() {
            assertThatThrownBy(() -> service.makeOffer(
                    solicitud.getId(), postura("Finca", "L-2", 125, "30000")))
                    .isInstanceOf(BusinessRuleException.class)
                    .hasMessageContaining("paga como máximo");
        }

        @Test
        @DisplayName("el mismo vendedor no postura dos veces con el mismo lote")
        void mismoLoteDosVeces() {
            service.makeOffer(solicitud.getId(), postura("Finca", "L-3", 125, "24000"));

            assertThatThrownBy(() -> service.makeOffer(
                    solicitud.getId(), postura("Finca", "L-3", 125, "23000")))
                    .isInstanceOf(BusinessRuleException.class)
                    .hasMessageContaining("Ya posturaste");
        }

        @Test
        @DisplayName("una solicitud vencida no admite posturas")
        void solicitudVencida() {
            PurchaseDemand vencida = new PurchaseDemand();
            vencida.setBuyerName("Comprador");
            vencida.setTitle("Vencida");
            vencida.setWantedKg(500);
            PurchaseDemand creada = service.publishDemand(vencida);
            creada.setValidUntil(LocalDate.now().minusDays(1));

            assertThatThrownBy(() -> service.makeOffer(
                    creada.getId(), postura("Finca", "L-4", 125, "24000")))
                    .isInstanceOf(BusinessRuleException.class)
                    .hasMessageContaining("venció");
        }
    }

    @Nested
    @DisplayName("Responder a una postura")
    class Responder {

        @Test
        @DisplayName("aceptar parte deja la solicitud parcialmente cubierta")
        void aceptarParte() {
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca A", "A-1", 500, "24000"));

            service.acceptOffer(oferta.getId());
            PurchaseDemand actualizada = service.findDemand(solicitud.getId());

            assertThat(actualizada.getStatus()).isEqualTo(DemandStatus.PARTIALLY_COVERED);
            assertThat(actualizada.getCoveredKg()).isEqualTo(500);
            assertThat(actualizada.getRemainingKg()).isEqualTo(750);
            assertThat(actualizada.getCoveredPercentage()).isEqualTo(40);
        }

        @Test
        @DisplayName("cubrirla entera la marca cumplida y rechaza lo pendiente")
        void cubrirEntera() {
            // Es la razón de que exista PARTIALLY_COVERED: una solicitud
            // grande se arma con varios caficultores.
            SellerOffer primera = service.makeOffer(
                    solicitud.getId(), postura("Finca A", "A-1", 750, "24000"));
            SellerOffer segunda = service.makeOffer(
                    solicitud.getId(), postura("Finca B", "B-1", 500, "25000"));
            SellerOffer tercera = service.makeOffer(
                    solicitud.getId(), postura("Finca C", "C-1", 125, "25500"));

            service.acceptOffer(primera.getId());
            service.acceptOffer(segunda.getId());

            PurchaseDemand actualizada = service.findDemand(solicitud.getId());
            assertThat(actualizada.getStatus()).isEqualTo(DemandStatus.FULFILLED);
            assertThat(actualizada.getRemainingKg()).isZero();

            // La que quedó pendiente se rechaza: dejarla esperando para
            // siempre es peor que un «no».
            SellerOffer restante = service.listOffersFor(solicitud.getId()).stream()
                    .filter(o -> o.getId().equals(tercera.getId()))
                    .findFirst().orElseThrow();
            assertThat(restante.getStatus()).isEqualTo(OfferStatus.REJECTED);
            assertThat(restante.getResponseNote()).contains("se cubrió");
        }

        @Test
        @DisplayName("se puede rechazar sin motivo: exigirlo produce «no» a secas")
        void rechazarSinMotivo() {
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca", "L-5", 125, "24000"));

            SellerOffer rechazada = service.rejectOffer(oferta.getId(), null);

            assertThat(rechazada.getStatus()).isEqualTo(OfferStatus.REJECTED);
            assertThat(rechazada.getResponseNote()).isNull();
        }

        @Test
        @DisplayName("una nota de espacios no se guarda como explicación")
        void notaEnBlanco() {
            // Se puede no explicar; lo que no se puede es simular que se
            // explicó, que dejaría un recuadro vacío con aspecto de fallo.
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca", "L-7", 125, "24000"));

            SellerOffer rechazada = service.rejectOffer(oferta.getId(), "     ");

            assertThat(rechazada.getResponseNote()).isNull();
        }

        @Test
        @DisplayName("el motivo se guarda sin espacios sobrantes")
        void motivoRecortado() {
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca", "L-8", 125, "24000"));

            SellerOffer rechazada = service.rejectOffer(
                    oferta.getId(), "   El factor no cumple.   ");

            assertThat(rechazada.getResponseNote()).isEqualTo("El factor no cumple.");
        }

        @Test
        @DisplayName("responder dos veces se rechaza")
        void responderDosVeces() {
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca", "L-6", 125, "24000"));
            service.rejectOffer(oferta.getId(), "El factor no cumple.");

            assertThatThrownBy(() -> service.acceptOffer(oferta.getId()))
                    .isInstanceOf(BusinessRuleException.class)
                    .hasMessageContaining("ya fue respondida");
        }

        @Test
        @DisplayName("una postura que ya no cabe no se puede aceptar")
        void yaNoCabe() {
            // Entre postura y respuesta, otras pueden haberse aceptado.
            SellerOffer grande = service.makeOffer(
                    solicitud.getId(), postura("Finca A", "A-1", 1000, "24000"));
            SellerOffer otra = service.makeOffer(
                    solicitud.getId(), postura("Finca B", "B-1", 250, "24500"));

            service.acceptOffer(grande.getId());
            service.acceptOffer(otra.getId());   // cubre justo los 1250

            SellerOffer tardia = new SellerOffer();
            tardia.setSellerName("Finca C");
            tardia.setLotCode("C-1");
            tardia.setOfferedKg(125);
            tardia.setPricePerKg(new BigDecimal("23000"));

            assertThatThrownBy(() -> service.makeOffer(solicitud.getId(), tardia))
                    .isInstanceOf(BusinessRuleException.class);
        }
    }

    @Nested
    @DisplayName("Retirar y cerrar")
    class RetirarYCerrar {

        @Test
        @DisplayName("el vendedor retira su propia postura")
        void retirarPropia() {
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca A", "A-1", 125, "24000"));

            SellerOffer retirada = service.withdrawOffer(oferta.getId(), "Finca A");

            assertThat(retirada.getStatus()).isEqualTo(OfferStatus.WITHDRAWN);
        }

        @Test
        @DisplayName("nadie retira la postura de otro")
        void retirarAjena() {
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca A", "A-1", 125, "24000"));

            assertThatThrownBy(() -> service.withdrawOffer(oferta.getId(), "Finca B"))
                    .isInstanceOf(BusinessRuleException.class)
                    .hasMessageContaining("no es tuya");
        }

        @Test
        @DisplayName("cerrar sin haber cubierto nada es cancelar")
        void cerrarSinCubrir() {
            PurchaseDemand cerrada = service.closeDemand(solicitud.getId(), null);

            assertThat(cerrada.getStatus()).isEqualTo(DemandStatus.CANCELLED);
        }

        @Test
        @DisplayName("cerrar con algo cubierto es cerrar, no cancelar")
        void cerrarConParte() {
            SellerOffer oferta = service.makeOffer(
                    solicitud.getId(), postura("Finca A", "A-1", 500, "24000"));
            service.acceptOffer(oferta.getId());

            PurchaseDemand cerrada = service.closeDemand(solicitud.getId(), "Ya completé.");

            assertThat(cerrada.getStatus()).isEqualTo(DemandStatus.CLOSED);
        }

        @Test
        @DisplayName("cerrar rechaza las posturas que seguían esperando")
        void cerrarRechazaPendientes() {
            SellerOffer pendiente = service.makeOffer(
                    solicitud.getId(), postura("Finca A", "A-1", 125, "24000"));

            service.closeDemand(solicitud.getId(), "Conseguí el café por otro lado.");

            SellerOffer tras = service.listOffersFor(solicitud.getId()).get(0);
            assertThat(tras.getId()).isEqualTo(pendiente.getId());
            assertThat(tras.getStatus()).isEqualTo(OfferStatus.REJECTED);
            assertThat(tras.getResponseNote()).isEqualTo("Conseguí el café por otro lado.");
        }
    }

    @Nested
    @DisplayName("Compatibilidad con el lote del vendedor")
    class Compatibilidad {

        @Test
        @DisplayName("un lote con mejor factor del pedido entra")
        void factorMejor() {
            assertThat(service.findMatchingDemands(new BigDecimal("88.00")))
                    .extracting(PurchaseDemand::getId)
                    .contains(solicitud.getId());
        }

        @Test
        @DisplayName("un lote con peor factor del pedido no entra")
        void factorPeor() {
            // El comprador pidió 92 o mejor; 96 rinde menos.
            assertThat(service.findMatchingDemands(new BigDecimal("96.00")))
                    .extracting(PurchaseDemand::getId)
                    .doesNotContain(solicitud.getId());
        }

        @Test
        @DisplayName("un lote sin factor declarado entra: lo decide el comprador")
        void sinFactor() {
            assertThat(service.findMatchingDemands(null))
                    .extracting(PurchaseDemand::getId)
                    .contains(solicitud.getId());
        }
    }
}
