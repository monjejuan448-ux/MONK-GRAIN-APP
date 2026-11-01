package co.monkgrain.catalog.web;

import co.monkgrain.catalog.model.PergaminoLot;
import co.monkgrain.catalog.model.Producer;
import co.monkgrain.catalog.service.CatalogService;
import co.monkgrain.catalog.util.ValidationException;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;

/**
 * Gestión de lotes del vendedor: el formulario y su procesamiento.
 *
 * <p>Demuestra los dos métodos HTTP que pide la evidencia:
 *
 * <ul>
 *   <li><strong>GET</strong> — muestra el listado, el formulario de alta o el
 *       detalle de un lote, según la acción.</li>
 *   <li><strong>POST</strong> — recibe el formulario, da de alta o elimina.</li>
 * </ul>
 *
 * <p>Tras un POST que modifica datos se responde con una
 * <strong>redirección</strong> y no con el contenido directamente. Es el patrón
 * <em>POST-Redirect-GET</em>: sin él, recargar la página reenvía el formulario y
 * el lote se publica dos veces.
 */
@WebServlet(name = "LotServlet", urlPatterns = {"/lotes"})
public class LotServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    private transient CatalogService service;

    @Override
    public void init() throws ServletException {
        this.service = new CatalogService();
    }

    // ------------------------------------------------------------------
    // GET
    // ------------------------------------------------------------------

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        String accion = request.getParameter("accion");
        if (accion == null) {
            accion = "listar";
        }

        try {
            switch (accion) {
                case "nuevo" -> mostrarFormulario(request, response);
                case "detalle" -> mostrarDetalle(request, response);
                default -> listar(request, response);
            }
        } catch (ValidationException e) {
            reenviarAError(request, response, e.getMessage(),
                    HttpServletResponse.SC_BAD_REQUEST);
        }
    }

    /** Todos los lotes del vendedor, publicados o no. */
    private void listar(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        request.setAttribute("lotes", service.listAll());
        request.setAttribute("mensaje", request.getParameter("mensaje"));
        request.getRequestDispatcher("/WEB-INF/jsp/lotes.jsp").forward(request, response);
    }

    /** Formulario de alta, con la lista de vendedores para elegir. */
    private void mostrarFormulario(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        request.setAttribute("productores", service.listProducers());
        request.getRequestDispatcher("/WEB-INF/jsp/lote-formulario.jsp")
               .forward(request, response);
    }

    private void mostrarDetalle(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        int lotId = parsearEntero(request.getParameter("id"), "identificador del lote");
        PergaminoLot lote = service.findLot(lotId)
                .orElseThrow(() -> new ValidationException("No existe el lote " + lotId + "."));

        request.setAttribute("lote", lote);
        request.getRequestDispatcher("/WEB-INF/jsp/lote-detalle.jsp").forward(request, response);
    }

    // ------------------------------------------------------------------
    // POST
    // ------------------------------------------------------------------

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        // Sin esto, los acentos del formulario llegan como caracteres rotos:
        // «Nariño» se convierte en «NariÃ±o» en la base de datos.
        request.setCharacterEncoding("UTF-8");

        String accion = request.getParameter("accion");
        if (accion == null) {
            accion = "crear";
        }

        try {
            switch (accion) {
                case "eliminar" -> eliminar(request, response);
                case "productor" -> crearProductor(request, response);
                default -> crear(request, response);
            }
        } catch (ValidationException e) {
            reenviarAError(request, response, e.getMessage(),
                    HttpServletResponse.SC_BAD_REQUEST);
        }
    }

    /** Da de alta un lote con los datos del formulario. */
    private void crear(HttpServletRequest request, HttpServletResponse response)
            throws IOException {

        PergaminoLot lote = new PergaminoLot();
        lote.setProducerId(parsearEntero(request.getParameter("productor"), "vendedor"));
        lote.setLotCode(textoObligatorio(request.getParameter("codigo"), "código del lote"));
        lote.setVariety(textoOpcional(request.getParameter("variedad")));

        lote.setYieldFactor(parsearDecimalOpcional(
                request.getParameter("factor"), "factor de rendimiento"));
        lote.setMoisturePct(parsearDecimalOpcional(
                request.getParameter("humedad"), "humedad"));
        lote.setHealthyBeanPct(parsearDecimalOpcional(
                request.getParameter("almendraSana"), "almendra sana"));
        lote.setPasillaPct(parsearDecimalOpcional(
                request.getParameter("pasilla"), "pasilla"));
        lote.setBorerDamagePct(parsearDecimalOpcional(
                request.getParameter("broca"), "daño por broca"));

        lote.setPricePerKg(parsearDecimalObligatorio(
                request.getParameter("precio"), "precio por kilogramo"));
        lote.setAvailableKg(parsearEntero(
                request.getParameter("kilos"), "kilos disponibles"));
        lote.setHarvestDate(parsearFechaOpcional(request.getParameter("cosecha")));
        lote.setPublished("on".equals(request.getParameter("publicado")));

        int id = service.registerLot(lote);

        // POST-Redirect-GET: recargar no debe publicar el lote dos veces.
        response.sendRedirect(request.getContextPath()
                + "/lotes?mensaje=" + codificar("Lote " + lote.getLotCode()
                + " publicado con el identificador " + id + "."));
    }

    private void crearProductor(HttpServletRequest request, HttpServletResponse response)
            throws IOException {

        Producer productor = new Producer(
                textoObligatorio(request.getParameter("finca"), "nombre de la finca"),
                textoObligatorio(request.getParameter("municipio"), "municipio"),
                textoObligatorio(request.getParameter("departamento"), "departamento"),
                textoOpcional(request.getParameter("sica")));

        service.registerProducer(productor);

        response.sendRedirect(request.getContextPath()
                + "/lotes?accion=nuevo&mensaje="
                + codificar("Vendedor " + productor.getFarmName() + " registrado."));
    }

    private void eliminar(HttpServletRequest request, HttpServletResponse response)
            throws IOException {

        int lotId = parsearEntero(request.getParameter("id"), "identificador del lote");
        service.removeLot(lotId);

        response.sendRedirect(request.getContextPath()
                + "/lotes?mensaje=" + codificar("Lote " + lotId + " eliminado."));
    }

    // ------------------------------------------------------------------
    // Conversión y validación de la entrada
    // ------------------------------------------------------------------
    //
    // Toda la entrada llega como texto. Convertirla aquí, con un mensaje que
    // nombra el campo, evita que el usuario reciba un «NumberFormatException»
    // que no le dice qué corregir.

    private String textoObligatorio(String valor, String campo) {
        if (valor == null || valor.isBlank()) {
            throw new ValidationException("El " + campo + " es obligatorio.");
        }
        return valor.trim();
    }

    private String textoOpcional(String valor) {
        return (valor == null || valor.isBlank()) ? null : valor.trim();
    }

    private int parsearEntero(String valor, String campo) {
        if (valor == null || valor.isBlank()) {
            throw new ValidationException("El " + campo + " es obligatorio.");
        }
        try {
            return Integer.parseInt(valor.trim());
        } catch (NumberFormatException e) {
            throw new ValidationException(
                    "El " + campo + " debe ser un número entero. Recibimos: «" + valor + "».");
        }
    }

    private BigDecimal parsearDecimalObligatorio(String valor, String campo) {
        BigDecimal resultado = parsearDecimalOpcional(valor, campo);
        if (resultado == null) {
            throw new ValidationException("El " + campo + " es obligatorio.");
        }
        return resultado;
    }

    private BigDecimal parsearDecimalOpcional(String valor, String campo) {
        if (valor == null || valor.isBlank()) {
            return null;
        }
        try {
            // Se admite la coma decimal: es como se escribe en Colombia.
            return new BigDecimal(valor.trim().replace(',', '.'));
        } catch (NumberFormatException e) {
            throw new ValidationException(
                    "El " + campo + " debe ser un número. Recibimos: «" + valor + "».");
        }
    }

    private LocalDate parsearFechaOpcional(String valor) {
        if (valor == null || valor.isBlank()) {
            return null;
        }
        try {
            return LocalDate.parse(valor.trim());
        } catch (DateTimeParseException e) {
            throw new ValidationException(
                    "La fecha de cosecha debe tener el formato AAAA-MM-DD. "
                    + "Recibimos: «" + valor + "».");
        }
    }

    private String codificar(String mensaje) {
        return java.net.URLEncoder.encode(mensaje, java.nio.charset.StandardCharsets.UTF_8);
    }

    private void reenviarAError(HttpServletRequest request, HttpServletResponse response,
                                String mensaje, int codigo)
            throws ServletException, IOException {
        response.setStatus(codigo);
        request.setAttribute("mensajeError", mensaje);
        request.getRequestDispatcher("/WEB-INF/jsp/error.jsp").forward(request, response);
    }
}
