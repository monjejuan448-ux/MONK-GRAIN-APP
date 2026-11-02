package co.monkgrain.authentication.controller;

import static org.assertj.core.api.Assertions.assertThat;

import co.monkgrain.authentication.repository.AccountRepository;
import co.monkgrain.authentication.repository.AuthSessionRepository;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;

/**
 * El servicio por HTTP de verdad, sin {@code @Transactional}.
 *
 * <p><b>Por qué existe esta clase aparte.</b> {@code AuthenticationControllerTest}
 * lleva {@code @Transactional} para que cada prueba se deshaga al terminar, y
 * eso tiene un efecto que no se ve: mantiene abierta la sesión de Hibernate
 * durante toda la prueba. Con la sesión abierta, un sustituto perezoso se
 * resuelve sin problema; en producción, donde {@code open-in-view} está
 * apagado, no hay sesión que lo resuelva y la misma línea termina en error 500.
 *
 * <p>Eso fue justo lo que pasó: las dieciséis pruebas de {@code /api/auth/me}
 * estaban verdes y el endpoint devolvía 500 al llamarlo con {@code curl}.
 * Esta clase reproduce las condiciones de producción —servidor real, puerto
 * real, sin transacción alrededor— para que un fallo así no vuelva a pasar
 * desapercibido.
 *
 * <p>Sin transacción que deshaga nada, la limpieza se hace a mano antes de
 * cada prueba.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class AuthenticationHttpTest {

    private static final String EMAIL = "ana@finca.co";
    private static final String PASSWORD = "pergamino2026";

    @Autowired
    private TestRestTemplate http;

    @Autowired
    private AccountRepository accounts;

    @Autowired
    private AuthSessionRepository sessions;

    @BeforeEach
    void limpiar() {
        // Las sesiones primero: apuntan a las cuentas con una clave ajena.
        sessions.deleteAll();
        accounts.deleteAll();

        // Se cambia el cliente HTTP de serie, que es `HttpURLConnection`.
        // Al recibir un 401, esa clase intenta por su cuenta repetir la
        // petición con credenciales, y como el cuerpo ya salió por el socket
        // falla con «cannot retry due to server authentication» en lugar de
        // entregar la respuesta. Como aquí casi todo lo interesante responde
        // 401, no se puede probar nada con él. El cliente de Java 11 no hace
        // ese reintento y devuelve el 401 tal cual.
        http.getRestTemplate().setRequestFactory(new JdkClientHttpRequestFactory());
    }

    @Test
    @DisplayName("GET /me funciona fuera de una transacción de prueba")
    void elPerfilNoNecesitaUnaSesionDeHibernateAbierta() {
        registrar();
        String token = ingresar();

        ResponseEntity<Map<String, Object>> respuesta = conToken(HttpMethod.GET, "/api/auth/me", token);

        // Aquí es donde aparecía el 500: el controlador leía el correo de la
        // cuenta después de que la transacción del servicio hubiera terminado.
        assertThat(respuesta.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(respuesta.getBody()).containsEntry("email", EMAIL);
    }

    @Test
    @DisplayName("El recorrido completo: registrar, ingresar, consultar, salir")
    void elRecorridoCompleto() {
        assertThat(registrar().getStatusCode()).isEqualTo(HttpStatus.ACCEPTED);

        String token = ingresar();
        assertThat(conToken(HttpMethod.GET, "/api/auth/me", token).getStatusCode())
                .isEqualTo(HttpStatus.OK);

        assertThat(conToken(HttpMethod.POST, "/api/auth/logout", token).getStatusCode())
                .isEqualTo(HttpStatus.OK);

        // Y después de salir, el mismo token ya no abre nada.
        assertThat(conToken(HttpMethod.GET, "/api/auth/me", token).getStatusCode())
                .isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    @DisplayName("Los acentos llegan intactos por HTTP real")
    void losAcentosLleganBien() {
        registrar();

        ResponseEntity<Map<String, Object>> respuesta = http.postForEntity(
                "/api/auth/login",
                Map.of("email", EMAIL, "password", "equivocada-123"),
                mapaDeRespuesta());

        // JSON es UTF-8 por norma (RFC 8259) y la respuesta no declara juego de
        // caracteres. Un cliente real lo decodifica bien; lo que no lo hacía
        // era `getContentAsString()` de MockMvc, que supone ISO-8859-1.
        assertThat(respuesta.getBody())
                .containsEntry("message", "Correo o contraseña incorrectos.");
    }

    @Test
    @DisplayName("El freno por intentos fallidos sobrevive entre peticiones distintas")
    void elFrenoSobreviveEntrePeticiones() {
        registrar();
        for (int intento = 0; intento < 5; intento++) {
            http.postForEntity("/api/auth/login",
                    Map.of("email", EMAIL, "password", "equivocada-123"), String.class);
        }

        ResponseEntity<Map<String, Object>> respuesta = http.postForEntity(
                "/api/auth/login", Map.of("email", EMAIL, "password", PASSWORD), mapaDeRespuesta());

        // El contador vive en la cuenta y no en memoria: cinco peticiones HTTP
        // independientes lo van sumando igual que cinco llamadas al servicio.
        assertThat(respuesta.getStatusCode()).isEqualTo(HttpStatus.TOO_MANY_REQUESTS);
        assertThat(respuesta.getHeaders().getFirst(HttpHeaders.RETRY_AFTER)).isNotNull();
    }

    // ------------------------------------------------------------------
    // Auxiliares
    // ------------------------------------------------------------------

    private ResponseEntity<String> registrar() {
        return http.postForEntity(
                "/api/auth/register",
                Map.of("email", EMAIL, "password", PASSWORD, "fullName", "Ana Restrepo"),
                String.class);
    }

    private String ingresar() {
        ResponseEntity<Map<String, Object>> respuesta = http.postForEntity(
                "/api/auth/login", Map.of("email", EMAIL, "password", PASSWORD), mapaDeRespuesta());
        assertThat(respuesta.getStatusCode()).isEqualTo(HttpStatus.OK);
        return String.valueOf(respuesta.getBody().get("token"));
    }

    private ResponseEntity<Map<String, Object>> conToken(HttpMethod metodo, String ruta, String token) {
        HttpHeaders cabeceras = new HttpHeaders();
        cabeceras.setBearerAuth(token);
        return http.exchange(ruta, metodo, new HttpEntity<>(cabeceras), mapaDeRespuesta());
    }

    /**
     * El tipo de la respuesta.
     *
     * <p>{@code Map.class} en crudo provoca un aviso del compilador en cada
     * llamada; esto lo concentra en un sitio.
     */
    @SuppressWarnings("unchecked")
    private Class<Map<String, Object>> mapaDeRespuesta() {
        return (Class<Map<String, Object>>) (Class<?>) Map.class;
    }
}
