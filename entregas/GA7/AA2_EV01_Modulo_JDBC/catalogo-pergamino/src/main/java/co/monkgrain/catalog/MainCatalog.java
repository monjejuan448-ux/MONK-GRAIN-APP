package co.monkgrain.catalog;

import co.monkgrain.catalog.model.PergaminoLot;
import co.monkgrain.catalog.model.Producer;
import co.monkgrain.catalog.service.CatalogService;
import co.monkgrain.catalog.util.DatabaseConnection;
import co.monkgrain.catalog.util.ValidationException;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/**
 * Demostración por consola de las cuatro operaciones del CRUD.
 *
 * <p>Recorre el ciclo completo —inserción, consulta, actualización y
 * eliminación— sobre el catálogo de lotes de pergamino, mostrando en cada paso
 * qué ocurre y por qué. Al final deja la base como la encontró.
 *
 * <p>Se ejecuta con:
 * <pre>java -jar target/catalogo-pergamino-jar-with-dependencies.jar</pre>
 */
public final class MainCatalog {

    private static final String SEPARADOR = "=".repeat(72);

    private MainCatalog() {
    }

    public static void main(String[] args) {
        CatalogService service = new CatalogService();

        encabezado("MONK GRAIN — Catálogo de pergamino (JDBC)");
        System.out.println("Base de datos: " + DatabaseConnection.url());

        int producerId = demostrarAltaDeVendedor(service);
        int lotId = demostrarInsercion(service, producerId);
        demostrarConsulta(service);
        demostrarConsultaConFiltro(service);
        demostrarActualizacion(service, lotId);
        demostrarValidaciones(service, producerId, lotId);
        demostrarEliminacion(service, producerId, lotId);

        encabezado("Demostración terminada");
    }

    // ------------------------------------------------------------------
    // 1. Alta del vendedor
    // ------------------------------------------------------------------
    private static int demostrarAltaDeVendedor(CatalogService service) {
        encabezado("1. INSERCIÓN — registrar el vendedor");

        Producer producer = new Producer(
                "Finca El Mirador", "Pitalito", "Huila", "SICA-41551-0042");
        int id = service.registerProducer(producer);

        System.out.println("Vendedor registrado: " + producer);
        return id;
    }

    // ------------------------------------------------------------------
    // 2. Inserción de lotes
    // ------------------------------------------------------------------
    private static int demostrarInsercion(CatalogService service, int producerId) {
        encabezado("2. INSERCIÓN — publicar lotes de pergamino");

        PergaminoLot excepcional = new PergaminoLot(
                producerId, "MIR-2026-001", new BigDecimal("24500.00"), 1250);
        excepcional.setVariety("Caturra");
        excepcional.setYieldFactor(new BigDecimal("88.50"));
        excepcional.setMoisturePct(new BigDecimal("11.20"));
        excepcional.setHealthyBeanPct(new BigDecimal("96.40"));
        excepcional.setPasillaPct(new BigDecimal("2.10"));
        excepcional.setBorerDamagePct(new BigDecimal("0.80"));
        excepcional.setHarvestDate(LocalDate.of(2026, 9, 15));
        excepcional.setPublished(true);

        int id = service.registerLot(excepcional);
        System.out.println("Lote registrado: " + excepcional);
        System.out.println("  Lectura del factor : " + excepcional.getYieldFactorLabel());
        System.out.println("  Humedad en rango   : " + (excepcional.isMoistureInRange() ? "sí" : "no"));
        System.out.println("  Valor del lote     : " + excepcional.getTotalValue());

        PergaminoLot estandar = new PergaminoLot(
                producerId, "MIR-2026-002", new BigDecimal("19800.00"), 375);
        estandar.setVariety("Colombia");
        estandar.setYieldFactor(new BigDecimal("94.00"));
        estandar.setMoisturePct(new BigDecimal("11.80"));
        estandar.setPublished(true);
        service.registerLot(estandar);
        System.out.println("Lote registrado: " + estandar);
        System.out.println("  Lectura del factor : " + estandar.getYieldFactorLabel());

        // Sin análisis declarado: es válido, y así se ve en el catálogo.
        PergaminoLot sinAnalisis = new PergaminoLot(
                producerId, "MIR-2026-003", new BigDecimal("17200.00"), 80);
        sinAnalisis.setPublished(true);
        service.registerLot(sinAnalisis);
        System.out.println("Lote registrado: " + sinAnalisis);
        System.out.println("  Sin análisis de laboratorio, y aun así publicable.");

        return id;
    }

    // ------------------------------------------------------------------
    // 3. Consulta
    // ------------------------------------------------------------------
    private static void demostrarConsulta(CatalogService service) {
        encabezado("3. CONSULTA — todos los lotes del vendedor");

        List<PergaminoLot> lotes = service.listAll();
        System.out.println("Lotes registrados: " + lotes.size());
        lotes.forEach(lote -> System.out.println("  " + lote));
    }

    private static void demostrarConsultaConFiltro(CatalogService service) {
        encabezado("4. CONSULTA — catálogo filtrado por factor máximo 92");
        System.out.println("El comprador acota el TECHO que acepta: en el factor de");
        System.out.println("rendimiento, menos es mejor.");
        System.out.println();

        List<PergaminoLot> lotes = service.browseCatalog(new BigDecimal("92"));
        System.out.println("Lotes que cumplen: " + lotes.size());
        lotes.forEach(lote -> System.out.println("  " + lote));
    }

    // ------------------------------------------------------------------
    // 4. Actualización
    // ------------------------------------------------------------------
    private static void demostrarActualizacion(CatalogService service, int lotId) {
        encabezado("5. ACTUALIZACIÓN — corregir el precio y descontar una venta");

        PergaminoLot lote = service.findLot(lotId).orElseThrow();
        System.out.println("Antes : " + lote);

        lote.setPricePerKg(new BigDecimal("25800.00"));
        service.updateLot(lote);
        System.out.println("Después: " + service.findLot(lotId).orElseThrow());

        System.out.println();
        System.out.println("Venta de 2 cargas (250 kg):");
        service.reduceStock(lotId, 250);
        System.out.println("  " + service.findLot(lotId).orElseThrow());
    }

    // ------------------------------------------------------------------
    // 5. Validaciones
    // ------------------------------------------------------------------
    private static void demostrarValidaciones(CatalogService service, int producerId, int lotId) {
        encabezado("6. VALIDACIONES — lo que el módulo rechaza");

        intentarRechazado("Factor de rendimiento imposible (145)", () -> {
            PergaminoLot lote = new PergaminoLot(
                    producerId, "MIR-2026-999", new BigDecimal("20000"), 100);
            lote.setYieldFactor(new BigDecimal("145"));
            service.registerLot(lote);
        });

        intentarRechazado("Código de lote repetido", () -> {
            PergaminoLot lote = new PergaminoLot(
                    producerId, "MIR-2026-001", new BigDecimal("20000"), 100);
            service.registerLot(lote);
        });

        intentarRechazado("Precio negativo", () -> {
            PergaminoLot lote = new PergaminoLot(
                    producerId, "MIR-2026-998", new BigDecimal("-500"), 100);
            service.registerLot(lote);
        });

        intentarRechazado("Humedad del 150 %", () -> {
            PergaminoLot lote = new PergaminoLot(
                    producerId, "MIR-2026-997", new BigDecimal("20000"), 100);
            lote.setMoisturePct(new BigDecimal("150"));
            service.registerLot(lote);
        });

        intentarRechazado("Vender más kilos de los que hay", () ->
                service.reduceStock(lotId, 999_999));
    }

    // ------------------------------------------------------------------
    // 6. Eliminación
    // ------------------------------------------------------------------
    private static void demostrarEliminacion(CatalogService service, int producerId, int lotId) {
        encabezado("7. ELIMINACIÓN — retirar los lotes de la demostración");

        List<PergaminoLot> lotes = service.listAll();
        for (PergaminoLot lote : lotes) {
            service.removeLot(lote.getLotId());
            System.out.println("Eliminado: " + lote.getLotCode());
        }

        // El vendedor también: la demostración promete dejar la base como la
        // encontró, y si no se borra se acumula uno por cada ejecución.
        service.removeProducer(producerId);
        System.out.println("Eliminado el vendedor " + producerId);

        System.out.println();
        System.out.println("Lotes restantes      : " + service.listAll().size());
        System.out.println("Vendedores restantes : " + service.listProducers().size());
        System.out.println("El lote " + lotId + " ya no se encuentra: "
                + service.findLot(lotId).isEmpty());
    }

    // ------------------------------------------------------------------
    // Utilidades de presentación
    // ------------------------------------------------------------------

    /** Ejecuta algo que debe fallar y muestra el mensaje con que se rechaza. */
    private static void intentarRechazado(String descripcion, Runnable accion) {
        try {
            accion.run();
            System.out.println("  [!] " + descripcion + " — NO fue rechazado (revisar)");
        } catch (ValidationException e) {
            System.out.println("  [ok] " + descripcion);
            System.out.println("       → " + e.getMessage());
        }
    }

    private static void encabezado(String titulo) {
        System.out.println();
        System.out.println(SEPARADOR);
        System.out.println(" " + titulo);
        System.out.println(SEPARADOR);
    }
}
