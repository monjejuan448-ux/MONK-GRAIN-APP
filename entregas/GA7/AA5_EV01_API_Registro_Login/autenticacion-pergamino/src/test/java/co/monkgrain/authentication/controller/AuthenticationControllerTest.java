package co.monkgrain.authentication.controller;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

/**
 * Los cuatro endpoints, por HTTP.
 *
 * <p>Aquí se fija lo que el servicio no puede fijar: los códigos de estado, el
 * contenido de las respuestas de error y las cabeceras. Un 401 donde debía ir
 * un 429 es un fallo que no se ve probando solo el servicio, porque la
 * excepción lanzada es la correcta y lo que está mal es su traducción.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class AuthenticationControllerTest {

    private static final String PASSWORD_VALIDA = "pergamino2026";

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper json;

    // ------------------------------------------------------------------
    // Registro
    // ------------------------------------------------------------------

    @Test
    @DisplayName("POST /register responde 202")
    void elRegistroResponde202() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"))
                // 202 y no 201: un 201 anunciaría «se creó un recurso», y la
                // gracia de esta respuesta es no decir si se creó o no.
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.message", containsString("Ya puedes iniciar sesión")));
    }

    @Test
    @DisplayName("Un correo repetido responde exactamente lo mismo que uno nuevo")
    void elCorreoRepetidoRespondeIgual() throws Exception {
        String primera = cuerpoDe(mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo")));

        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Otra Persona"))
                .andExpect(status().isAccepted())
                // Mismo código y mismo cuerpo, byte por byte: si se
                // diferenciaran, el registro serviría de buscador de cuentas.
                .andExpect(content().json(primera, true));
    }

    @Test
    @DisplayName("Una contraseña débil responde 422 con la lista de lo que falta")
    void laContrasenaDebilResponde422() throws Exception {
        mockMvc.perform(registro("ana@finca.co", "corta", "Ana Restrepo"))
                // 422 y no 400: el cuerpo llegó bien formado, lo que no cumple
                // es una regla del negocio.
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.error").value("weak_password"))
                .andExpect(jsonPath("$.details", hasSize(2)));
    }

    @Test
    @DisplayName("Un correo mal formado responde 400 con el nombre del campo")
    void elCorreoInvalidoResponde400() throws Exception {
        mockMvc.perform(registro("no-es-un-correo", PASSWORD_VALIDA, "Ana Restrepo"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("validation_error"))
                .andExpect(jsonPath("$.details[0]", containsString("email")));
    }

    @Test
    @DisplayName("Un JSON roto responde 400 y no 500")
    void elJsonRotoResponde400() throws Exception {
        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\": \"ana@finca.co\",,}"))
                // Sin el manejador correspondiente esto saldría como 500 y
                // parecería un fallo del servidor.
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("malformed_body"));
    }

    @Test
    @DisplayName("El rol enviado en la petición se ignora")
    void noSePuedeElegirElRol() throws Exception {
        // La petición pide ser administrador. El objeto de entrada no tiene
        // ese campo, así que Jackson lo descarta y el servicio asigna BUYER.
        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"ana@finca.co","password":"pergamino2026",
                                 "fullName":"Ana Restrepo","role":"ADMIN","id":1}
                                """))
                .andExpect(status().isAccepted());

        mockMvc.perform(get("/api/auth/me").header("Authorization", "Bearer " + ingresar()))
                .andExpect(jsonPath("$.role").value("BUYER"));
    }

    // ------------------------------------------------------------------
    // Ingreso
    // ------------------------------------------------------------------

    @Test
    @DisplayName("POST /login devuelve el mensaje de autenticación satisfactoria y el token")
    void elIngresoCorrectoResponde200() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));

        mockMvc.perform(login("ana@finca.co", PASSWORD_VALIDA))
                .andExpect(status().isOk())
                // Es el mensaje que pide la evidencia.
                .andExpect(jsonPath("$.message").value("Autenticación satisfactoria."))
                .andExpect(jsonPath("$.token").isNotEmpty())
                .andExpect(jsonPath("$.expiresAt").isNotEmpty())
                .andExpect(jsonPath("$.account.email").value("ana@finca.co"));
    }

    @Test
    @DisplayName("La respuesta no lleva el resumen de la contraseña")
    void laRespuestaNoPublicaElResumen() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));

        mockMvc.perform(login("ana@finca.co", PASSWORD_VALIDA))
                .andExpect(jsonPath("$.account.passwordHash").doesNotExist())
                // Tampoco los intentos fallidos: le dirían a un atacante
                // cuántos le quedan antes de que la cuenta se frene.
                .andExpect(jsonPath("$.account.failedAttempts").doesNotExist())
                .andExpect(jsonPath("$.account.lockedUntil").doesNotExist())
                .andExpect(content().string(not(containsString("$2a$"))));
    }

    @Test
    @DisplayName("Un ingreso fallido responde 401")
    void elIngresoFallidoResponde401() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));

        mockMvc.perform(login("ana@finca.co", "equivocada-123"))
                // 401 y no 404 aunque el correo no existiera: un 404 diría «ese
                // usuario no está aquí», que es el dato que no se quiere dar.
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error").value("authentication_failed"))
                .andExpect(jsonPath("$.message").value("Correo o contraseña incorrectos."));
    }

    @Test
    @DisplayName("El correo inexistente responde lo mismo que la contraseña equivocada")
    void losDosFallosRespondenIgual() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));

        String contrasenaMala = cuerpoDe(mockMvc.perform(login("ana@finca.co", "equivocada-123")));
        String correoInexistente = cuerpoDe(mockMvc.perform(login("nadie@finca.co", PASSWORD_VALIDA)));

        // Se comparan sin la marca de tiempo, que es lo único que cambia.
        org.assertj.core.api.Assertions.assertThat(sinMarcaDeTiempo(correoInexistente))
                .isEqualTo(sinMarcaDeTiempo(contrasenaMala));
    }

    @Test
    @DisplayName("La cuenta frenada responde 429 con Retry-After")
    void laCuentaFrenadaResponde429() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));
        for (int intento = 0; intento < 5; intento++) {
            mockMvc.perform(login("ana@finca.co", "equivocada-123"));
        }

        mockMvc.perform(login("ana@finca.co", PASSWORD_VALIDA))
                // 429 y no 403: el 403 dice «no puedes y no insistas», el 429
                // dice «ahora no, vuelve después», que es la verdad.
                .andExpect(status().isTooManyRequests())
                .andExpect(header().exists("Retry-After"))
                .andExpect(jsonPath("$.error").value("account_locked"));
    }

    // ------------------------------------------------------------------
    // Sesión
    // ------------------------------------------------------------------

    @Test
    @DisplayName("GET /me con el token devuelve la cuenta")
    void elTokenAbreElPerfil() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));

        mockMvc.perform(get("/api/auth/me").header("Authorization", "Bearer " + ingresar()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value("ana@finca.co"))
                .andExpect(jsonPath("$.fullName").value("Ana Restrepo"));
    }

    @Test
    @DisplayName("GET /me sin cabecera responde 401")
    void sinCabeceraNoHayPerfil() throws Exception {
        mockMvc.perform(get("/api/auth/me"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error").value("invalid_session"));
    }

    @Test
    @DisplayName("GET /me con un esquema que no es Bearer responde 401")
    void soloSeAceptaBearer() throws Exception {
        mockMvc.perform(get("/api/auth/me").header("Authorization", "Basic YW5hOjEyMw=="))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("«bearer» en minúsculas también vale")
    void elEsquemaNoDistingueMayusculas() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));

        // La norma dice que el esquema no distingue mayúsculas, y hay clientes
        // que envían «bearer».
        mockMvc.perform(get("/api/auth/me").header("Authorization", "bearer " + ingresar()))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("Después de cerrar sesión, el token ya no abre nada")
    void elLogoutCierraDeVerdad() throws Exception {
        mockMvc.perform(registro("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo"));
        String token = ingresar();

        mockMvc.perform(post("/api/auth/logout").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/auth/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isUnauthorized());
    }

    // ------------------------------------------------------------------
    // Auxiliares
    // ------------------------------------------------------------------

    private org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder registro(
            String email, String password, String fullName) throws Exception {
        return post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsString(
                        new java.util.LinkedHashMap<>(java.util.Map.of(
                                "email", email, "password", password, "fullName", fullName))));
    }

    private org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder login(
            String email, String password) throws Exception {
        return post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsString(
                        new java.util.LinkedHashMap<>(java.util.Map.of(
                                "email", email, "password", password))));
    }

    /** Ingresa con la cuenta de prueba y devuelve el token. */
    private String ingresar() throws Exception {
        String cuerpo = cuerpoDe(mockMvc.perform(login("ana@finca.co", PASSWORD_VALIDA))
                .andExpect(status().isOk()));
        return json.readTree(cuerpo).get("token").asText();
    }

    /**
     * El cuerpo de la respuesta, leído como UTF-8.
     *
     * <p>No se usa {@code getContentAsString()} sin argumentos: MockMvc
     * decodifica con ISO-8859-1 cuando la respuesta no declara juego de
     * caracteres, y «sesión» se lee entonces como «sesiÃ³n». Es un defecto de
     * la prueba y no del servicio —la cabecera {@code application/json} no
     * lleva juego de caracteres porque JSON es UTF-8 por norma (RFC 8259), y
     * un cliente real lo decodifica bien—, pero comparar dos cuerpos leídos de
     * formas distintas hacía fallar la prueba por el motivo equivocado.
     */
    private String cuerpoDe(org.springframework.test.web.servlet.ResultActions resultado)
            throws Exception {
        return resultado.andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
    }

    /** El cuerpo sin la marca de tiempo, que es lo único que varía entre dos fallos. */
    private String sinMarcaDeTiempo(String cuerpo) throws Exception {
        JsonNode arbol = json.readTree(cuerpo);
        ((com.fasterxml.jackson.databind.node.ObjectNode) arbol).remove("timestamp");
        return arbol.toString();
    }
}
