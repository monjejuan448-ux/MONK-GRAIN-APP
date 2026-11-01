package co.monkgrain.catalog.web;

import co.monkgrain.catalog.model.PergaminoLot;
import co.monkgrain.catalog.service.CatalogService;
import co.monkgrain.catalog.util.ValidationException;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.math.BigDecimal;
import java.util.List;

/**
 * Catálogo público de lotes de pergamino. Responde a <strong>GET</strong>.
 *
 * <p>Es la vista del comprador: solo lo publicado y con existencias, con el
 * filtro por factor de rendimiento máximo. El servlet no consulta la base de
 * datos ni contiene reglas: recoge los parámetros, los valida mínimamente y
 * delega en {@link CatalogService}, que es el módulo de la evidencia anterior.
 *
 * <p>Esa delegación es el punto de la separación en capas: si mañana cambia la
 * regla del filtro, cambia en un solo sitio y las dos interfaces —consola y
 * web— la heredan.
 */
@WebServlet(name = "CatalogServlet", urlPatterns = {"/catalogo"})
public class CatalogServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    private transient CatalogService service;

    @Override
    public void init() throws ServletException {
        // Una sola instancia por servlet: crear el servicio en cada petición
        // abriría y cerraría recursos sin necesidad.
        this.service = new CatalogService();
    }

    /**
     * Muestra el catálogo, opcionalmente filtrado.
     *
     * <p>Parámetro {@code factorMaximo}: techo del factor de rendimiento que
     * acepta el comprador. Se acota por el máximo porque <strong>menos es
     * mejor</strong>: un filtro por mínimo no tendría sentido en este dato.
     */
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        String parametro = request.getParameter("factorMaximo");

        try {
            BigDecimal factorMaximo = parsearFactor(parametro);
            List<PergaminoLot> lotes = service.browseCatalog(factorMaximo);

            request.setAttribute("lotes", lotes);
            request.setAttribute("factorMaximo", parametro == null ? "" : parametro);
            request.setAttribute("total", lotes.size());

            request.getRequestDispatcher("/WEB-INF/jsp/catalogo.jsp")
                   .forward(request, response);

        } catch (ValidationException e) {
            // Un filtro mal escrito es culpa de quien lo escribe y se corrige
            // cambiándolo: 400, no 500.
            reenviarAError(request, response, e.getMessage(),
                    HttpServletResponse.SC_BAD_REQUEST);
        }
    }

    /**
     * Convierte el parámetro del filtro, tolerando que venga vacío.
     *
     * @return el factor, o {@code null} si no se filtró
     * @throws ValidationException si el texto no es un número
     */
    private BigDecimal parsearFactor(String valor) {
        if (valor == null || valor.isBlank()) {
            return null;
        }
        try {
            return new BigDecimal(valor.trim());
        } catch (NumberFormatException e) {
            throw new ValidationException(
                    "El factor de rendimiento debe ser un número. Recibimos: «" + valor + "».");
        }
    }

    private void reenviarAError(HttpServletRequest request, HttpServletResponse response,
                                String mensaje, int codigo)
            throws ServletException, IOException {
        response.setStatus(codigo);
        request.setAttribute("mensajeError", mensaje);
        request.getRequestDispatcher("/WEB-INF/jsp/error.jsp").forward(request, response);
    }
}
