package co.monkgrain.authentication.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import co.monkgrain.authentication.model.Account;
import co.monkgrain.authentication.model.AccountRole;
import co.monkgrain.authentication.repository.AccountRepository;
import co.monkgrain.authentication.repository.AuthSessionRepository;
import java.time.Duration;
import java.time.Instant;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/**
 * Las reglas del servicio de autenticación.
 *
 * <p>Se prueba el servicio y no los endpoints: lo que hay que fijar son las
 * decisiones —qué se cuenta y qué se calla, cuándo se frena una cuenta— y esas
 * no cambian con la ruta HTTP. Los códigos de estado se prueban aparte, en
 * {@code AuthenticationControllerTest}.
 *
 * <p>{@code @Transactional} deshace cada prueba al terminar: sin esto, la
 * cuenta que crea una prueba haría fallar a la siguiente con «correo ya
 * registrado», y el orden de ejecución pasaría a importar.
 */
@SpringBootTest
@ActiveProfiles("test")
@Transactional
class AuthenticationServiceTest {

    private static final String PASSWORD_VALIDA = "pergamino2026";

    @Autowired
    private AuthenticationService authentication;

    @Autowired
    private AccountRepository accounts;

    @Autowired
    private AuthSessionRepository sessions;

    // ------------------------------------------------------------------
    // Registro
    // ------------------------------------------------------------------

    @Test
    @DisplayName("Registra la cuenta con rol de comprador")
    void registraConRolDeComprador() {
        Account creada = authentication
                .register("Ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo")
                .orElseThrow();

        // El rol no se recibe en la petición: lo decide el servicio. Un
        // vendedor lo obtiene después, cuando un administrador verifica su
        // finca, igual que en el producto.
        assertThat(creada.getRole()).isEqualTo(AccountRole.BUYER);
    }

    @Test
    @DisplayName("Guarda el correo en minúsculas")
    void normalizaElCorreo() {
        authentication.register("  Ana@Finca.CO ", PASSWORD_VALIDA, "Ana Restrepo");

        // Quien escribe «Ana@Finca.CO» al registrarse escribirá «ana@finca.co»
        // al volver, y tiene que encontrar su cuenta.
        assertThat(accounts.findByEmail("ana@finca.co")).isPresent();
    }

    @Test
    @DisplayName("Nunca guarda la contraseña en claro")
    void guardaElResumenYNoLaContrasena() {
        Account creada = authentication
                .register("cafe@finca.co", PASSWORD_VALIDA, "Luis Cardona")
                .orElseThrow();

        assertThat(creada.getPasswordHash())
                .isNotEqualTo(PASSWORD_VALIDA)
                .startsWith("$2a$10$")   // algoritmo y factor de coste
                .hasSize(60);
    }

    @Test
    @DisplayName("Dos cuentas con la misma contraseña no comparten resumen")
    void elResumenLlevaSalPropia() {
        String uno = authentication.register("a@finca.co", PASSWORD_VALIDA, "Uno")
                .orElseThrow().getPasswordHash();
        String otro = authentication.register("b@finca.co", PASSWORD_VALIDA, "Dos")
                .orElseThrow().getPasswordHash();

        // Si fueran iguales, quien robara la tabla sabría de un vistazo qué
        // cuentas comparten contraseña.
        assertThat(uno).isNotEqualTo(otro);
    }

    @Test
    @DisplayName("Un correo repetido no crea una segunda cuenta ni avisa de ello")
    void elCorreoRepetidoNoSeDelata() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");

        // Devuelve vacío en lugar de lanzar: el controlador responde el mismo
        // acuse que a un correo nuevo, para que el registro no sirva de
        // buscador de cuentas.
        assertThat(authentication.register("ana@finca.co", PASSWORD_VALIDA, "Otra Persona"))
                .isEmpty();
        assertThat(accounts.count()).isEqualTo(1);
    }

    @Test
    @DisplayName("Rechaza la contraseña débil diciendo todo lo que le falta")
    void enumeraLoQueFaltaALaContrasena() {
        assertThatThrownBy(() -> authentication.register("ana@finca.co", "corta", "Ana Restrepo"))
                .isInstanceOf(WeakPasswordException.class)
                .extracting(failure -> ((WeakPasswordException) failure).getProblems())
                // Corta y sin números: las dos cosas de una vez, no la primera
                // y que lo vuelva a intentar para enterarse de la segunda.
                .asInstanceOf(org.assertj.core.api.InstanceOfAssertFactories.list(String.class))
                .hasSize(2)
                .anySatisfy(problema -> assertThat(problema).contains("12"))
                .anySatisfy(problema -> assertThat(problema).contains("número"));
    }

    @Test
    @DisplayName("Acepta una frase larga sin mayúsculas ni símbolos")
    void aceptaLaFraseLarga() {
        // La política no exige mayúscula ni símbolo a propósito: esas reglas
        // empujan hacia «Contrasena1!», que es peor que una frase larga.
        assertThat(authentication.checkPasswordPolicy("mi finca en el quindio 2026")).isEmpty();
    }

    // ------------------------------------------------------------------
    // Ingreso
    // ------------------------------------------------------------------

    @Test
    @DisplayName("Un ingreso correcto abre sesión y deja constancia de la fecha")
    void elIngresoCorrectoAbreSesion() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();

        AuthenticationService.LoginResult resultado =
                authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora);

        assertThat(resultado.token()).isNotBlank();
        assertThat(resultado.expiresAt()).isEqualTo(ahora.plus(AuthenticationService.SESSION_DURATION));
        assertThat(resultado.account().getLastLoginAt()).isEqualTo(ahora);
    }

    @Test
    @DisplayName("El token viaje en claro una sola vez: en la tabla queda su resumen")
    void laTablaGuardaElResumenDelToken() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        String token = authentication.login("ana@finca.co", PASSWORD_VALIDA, Instant.now()).token();

        // Quien se lleve una copia de la base no debe quedarse con sesiones
        // vivas en la mano.
        assertThat(sessions.findByTokenHash(token)).isEmpty();
        assertThat(sessions.findAll())
                .singleElement()
                .satisfies(sesion -> assertThat(sesion.getTokenHash())
                        .isNotEqualTo(token)
                        .hasSize(64));
    }

    @Test
    @DisplayName("Dos ingresos dan tokens distintos")
    void cadaIngresoDaUnTokenNuevo() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");

        String primero = authentication.login("ana@finca.co", PASSWORD_VALIDA, Instant.now()).token();
        String segundo = authentication.login("ana@finca.co", PASSWORD_VALIDA, Instant.now()).token();

        // Si se repitieran, cerrar sesión en el teléfono cerraría la del
        // computador, y un token filtrado valdría para siempre.
        assertThat(primero).isNotEqualTo(segundo);
    }

    @Test
    @DisplayName("Da el mismo error si el correo no existe que si la contraseña no coincide")
    void elErrorNoDistingueLaCausa() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();

        Throwable correoInexistente = org.assertj.core.api.Assertions
                .catchThrowable(() -> authentication.login("nadie@finca.co", PASSWORD_VALIDA, ahora));
        Throwable contrasenaMala = org.assertj.core.api.Assertions
                .catchThrowable(() -> authentication.login("ana@finca.co", "otra-contrasena-1", ahora));

        // Si los mensajes se diferenciaran, probar un correo con cualquier
        // contraseña diría si esa persona tiene cuenta en MONK GRAIN.
        assertThat(correoInexistente).isInstanceOf(InvalidCredentialsException.class);
        assertThat(contrasenaMala).isInstanceOf(InvalidCredentialsException.class);
        assertThat(correoInexistente.getMessage()).isEqualTo(contrasenaMala.getMessage());
    }

    @Test
    @DisplayName("El ingreso correcto borra los intentos fallidos anteriores")
    void elIngresoCorrectoLimpiaElContador() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();

        for (int intento = 0; intento < 3; intento++) {
            org.assertj.core.api.Assertions.catchThrowable(
                    () -> authentication.login("ana@finca.co", "equivocada-123", ahora));
        }
        authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora);

        // Si no se borrara, tres despistes de hoy más dos de la semana que
        // viene frenarían la cuenta de alguien que nunca fue atacado.
        assertThat(accounts.findByEmail("ana@finca.co").orElseThrow().getFailedAttempts())
                .isZero();
    }

    // ------------------------------------------------------------------
    // Freno por intentos fallidos
    // ------------------------------------------------------------------

    @Test
    @DisplayName("Frena la cuenta al quinto intento fallido")
    void frenaAlQuintoIntento() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();

        for (int intento = 0; intento < AuthenticationService.MAX_FAILED_ATTEMPTS; intento++) {
            org.assertj.core.api.Assertions.catchThrowable(
                    () -> authentication.login("ana@finca.co", "equivocada-123", ahora));
        }

        assertThat(accounts.findByEmail("ana@finca.co").orElseThrow().isLocked(ahora)).isTrue();
    }

    @Test
    @DisplayName("Con la cuenta frenada y la contraseña equivocada, no dice que está frenada")
    void laCuentaFrenadaNoSeDelataAQuienNoSabeLaContrasena() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        frenarLaCuenta(ahora);

        // Es el punto fino del diseño: si el freno se anunciara a cualquiera,
        // provocarlo bastaría para confirmar que el correo existe.
        assertThatThrownBy(() -> authentication.login("ana@finca.co", "equivocada-123", ahora))
                .isInstanceOf(InvalidCredentialsException.class);
    }

    @Test
    @DisplayName("Con la cuenta frenada y la contraseña correcta, dice cuánto falta")
    void alDuenoSiSeLeExplicaElFreno() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        frenarLaCuenta(ahora);

        // Quien acierta la contraseña ya demostró ser el dueño: a él sí se le
        // dice la verdad completa, porque es el único que puede usarla.
        assertThatThrownBy(() -> authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora))
                .isInstanceOf(AccountLockedException.class)
                .hasMessageContaining("15 minutos");
    }

    @Test
    @DisplayName("Insistir con la cuenta frenada no alarga el freno")
    void elFrenoNoSeAlargaInsistiendo() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        frenarLaCuenta(ahora);
        Instant finDelFreno = accounts.findByEmail("ana@finca.co").orElseThrow().getLockedUntil();

        for (int intento = 0; intento < 10; intento++) {
            org.assertj.core.api.Assertions.catchThrowable(
                    () -> authentication.login("ana@finca.co", "equivocada-123", ahora));
        }

        // Si cada intento extendiera el freno, cualquiera podría dejar fuera a
        // un vendedor indefinidamente con solo seguir probando.
        assertThat(accounts.findByEmail("ana@finca.co").orElseThrow().getLockedUntil())
                .isEqualTo(finDelFreno);
    }

    @Test
    @DisplayName("Pasados los quince minutos, la cuenta vuelve a dejar entrar")
    void elFrenoSeLevantaSolo() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        frenarLaCuenta(ahora);

        // El tiempo se pasa como parámetro y no se lee del reloj dentro del
        // servicio: así esta prueba tarda milisegundos en vez de un cuarto de
        // hora, y no depende de cuándo se ejecute.
        Instant despues = ahora.plus(AuthenticationService.LOCK_DURATION).plusSeconds(1);

        assertThat(authentication.login("ana@finca.co", PASSWORD_VALIDA, despues).token())
                .isNotBlank();
    }

    // ------------------------------------------------------------------
    // Sesiones
    // ------------------------------------------------------------------

    @Test
    @DisplayName("El token abre la cuenta a la que pertenece")
    void elTokenIdentificaLaCuenta() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        String token = authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora).token();

        assertThat(authentication.requireAccount(token, ahora).getEmail())
                .isEqualTo("ana@finca.co");
    }

    @Test
    @DisplayName("Un token inventado no abre nada")
    void elTokenInventadoNoSirve() {
        assertThatThrownBy(() -> authentication.requireAccount("token-inventado", Instant.now()))
                .isInstanceOf(InvalidSessionException.class);
    }

    @Test
    @DisplayName("Una sesión vencida no deja pasar aunque su fila siga ahí")
    void laSesionVencidaNoDejaPasar() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        String token = authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora).token();

        Instant pasadoElPlazo = ahora.plus(AuthenticationService.SESSION_DURATION).plusSeconds(1);

        // La caducidad se comprueba en el servicio y no se confía en que algo
        // haya borrado la fila: la limpieza puede no haberse ejecutado.
        assertThat(sessions.count()).isEqualTo(1);
        assertThatThrownBy(() -> authentication.requireAccount(token, pasadoElPlazo))
                .isInstanceOf(InvalidSessionException.class);
    }

    @Test
    @DisplayName("Cerrar sesión invalida el token en el momento")
    void cerrarSesionInvalidaElToken() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        String token = authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora).token();

        authentication.logout(token);

        // Es lo que un JWT no permitiría: su firma seguiría siendo válida.
        assertThatThrownBy(() -> authentication.requireAccount(token, ahora))
                .isInstanceOf(InvalidSessionException.class);
    }

    @Test
    @DisplayName("Cerrar sesión dos veces termina igual de bien")
    void cerrarSesionEsIdempotente() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        String token = authentication.login("ana@finca.co", PASSWORD_VALIDA, Instant.now()).token();

        authentication.logout(token);

        // El usuario quería quedar fuera y queda fuera. Además, un error
        // distinto según si el token existía serviría para adivinar tokens.
        authentication.logout(token);
        authentication.logout("token-que-nunca-existio");
    }

    @Test
    @DisplayName("Cerrar sesión en un dispositivo no cierra la del otro")
    void cadaSesionSeCierraPorSuCuenta() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        String telefono = authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora).token();
        String computador = authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora).token();

        authentication.logout(telefono);

        assertThat(authentication.requireAccount(computador, ahora).getEmail())
                .isEqualTo("ana@finca.co");
    }

    @Test
    @DisplayName("La limpieza borra solo lo vencido")
    void laLimpiezaRespetaLoVivo() {
        authentication.register("ana@finca.co", PASSWORD_VALIDA, "Ana Restrepo");
        Instant ahora = Instant.now();
        String vigente = authentication.login("ana@finca.co", PASSWORD_VALIDA, ahora).token();

        // Se limpia con una fecha anterior a la caducidad de la sesión viva.
        int borradas = sessions.deleteExpired(ahora.plus(Duration.ofHours(1)));

        assertThat(borradas).isZero();
        assertThat(authentication.requireAccount(vigente, ahora)).isNotNull();
    }

    /** Gasta los cinco intentos para dejar la cuenta frenada. */
    private void frenarLaCuenta(Instant ahora) {
        for (int intento = 0; intento < AuthenticationService.MAX_FAILED_ATTEMPTS; intento++) {
            org.assertj.core.api.Assertions.catchThrowable(
                    () -> authentication.login("ana@finca.co", "equivocada-123", ahora));
        }
    }
}
