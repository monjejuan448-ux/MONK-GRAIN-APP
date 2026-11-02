package co.monkgrain.authentication.service;

import co.monkgrain.authentication.model.Account;
import co.monkgrain.authentication.model.AuthSession;
import co.monkgrain.authentication.repository.AccountRepository;
import co.monkgrain.authentication.repository.AuthSessionRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Registro, ingreso, salida y validación de sesión.
 *
 * <p>Toda la lógica vive aquí y no en el controlador: el controlador traduce
 * HTTP, el servicio decide. Así las reglas se pueden probar sin levantar un
 * servidor, que es lo que hace {@code AuthenticationServiceTest}.
 */
@Service
public class AuthenticationService {

    private static final Logger log = LoggerFactory.getLogger(AuthenticationService.class);

    /** Mínimo de caracteres. El mismo que exige el producto. */
    private static final int MIN_PASSWORD_LENGTH = 12;

    /** Intentos fallidos seguidos antes de frenar la cuenta. */
    static final int MAX_FAILED_ATTEMPTS = 5;

    /** Cuánto dura el freno. */
    static final Duration LOCK_DURATION = Duration.ofMinutes(15);

    /** Cuánto dura una sesión sin volver a pedir la contraseña. */
    static final Duration SESSION_DURATION = Duration.ofHours(8);

    /**
     * Resumen de una contraseña que nadie tiene.
     *
     * <p>Sirve para gastar el mismo tiempo cuando el correo no existe que
     * cuando sí. Sin esto, un correo desconocido respondería en un milisegundo
     * y uno registrado en cien, y esa diferencia es medible desde fuera: basta
     * cronometrar las respuestas para separar los correos que existen de los
     * que no, aunque el mensaje sea idéntico en los dos casos.
     *
     * <p>Se calcula una sola vez al arrancar, con la misma configuración de
     * BCrypt que usan las contraseñas reales.
     */
    private final String dummyHash;

    private final AccountRepository accounts;
    private final AuthSessionRepository sessions;
    private final PasswordEncoder passwordEncoder;
    private final SecureRandom random = new SecureRandom();

    public AuthenticationService(
            AccountRepository accounts,
            AuthSessionRepository sessions,
            PasswordEncoder passwordEncoder) {
        this.accounts = accounts;
        this.sessions = sessions;
        this.passwordEncoder = passwordEncoder;
        this.dummyHash = passwordEncoder.encode("contrasena-que-nadie-usa-" + System.nanoTime());
    }

    // ------------------------------------------------------------------
    // Registro
    // ------------------------------------------------------------------

    /**
     * Crea una cuenta.
     *
     * <p><b>No avisa si el correo ya estaba registrado.</b> Decirlo convertiría
     * el registro en lo mismo que se evitó en el ingreso: un formulario para
     * averiguar quién tiene cuenta. Quien ya está registrado y lo intenta otra
     * vez recibe el mismo acuse que un recién llegado, y descubre su situación
     * al ir a iniciar sesión o al pedir una contraseña nueva.
     *
     * <p>Es la misma decisión que tomó el producto en {@code auth/router.py}.
     * No es gratis: un usuario despistado se queda sin saber por qué «no se
     * creó» su cuenta. El precio se paga en el correo de confirmación, que es
     * donde se le explica.
     *
     * @return la cuenta creada, o vacío si el correo ya existía
     */
    @Transactional
    public Optional<Account> register(String email, String password, String fullName) {
        String normalizedEmail = normalizeEmail(email);

        // La política se comprueba antes de mirar la base: si la contraseña no
        // sirve, el correo da igual.
        List<String> problems = checkPasswordPolicy(password);
        if (!problems.isEmpty()) {
            throw new WeakPasswordException(problems);
        }

        if (accounts.existsByEmail(normalizedEmail)) {
            // Se registra en la bitácora del servidor, no en la respuesta: aquí
            // sí interesa saber que ocurrió, al cliente no.
            log.info("Registro repetido sobre un correo ya existente; se responde igual que a uno nuevo.");
            return Optional.empty();
        }

        Account account = new Account(normalizedEmail, passwordEncoder.encode(password), fullName.trim());
        return Optional.of(accounts.save(account));
    }

    /**
     * Devuelve las reglas que la contraseña incumple; vacía si está bien.
     *
     * <p>Longitud, una letra y un número. No se exige mayúscula ni símbolo a
     * propósito: esas reglas empujan a la gente hacia «Contrasena1!», que es
     * peor que una frase larga, y el producto ya tomó esa decisión.
     */
    List<String> checkPasswordPolicy(String password) {
        List<String> problems = new ArrayList<>();
        if (password.length() < MIN_PASSWORD_LENGTH) {
            problems.add("Debe tener al menos " + MIN_PASSWORD_LENGTH + " caracteres.");
        }
        if (password.chars().noneMatch(Character::isLetter)) {
            problems.add("Debe incluir al menos una letra.");
        }
        if (password.chars().noneMatch(Character::isDigit)) {
            problems.add("Debe incluir al menos un número.");
        }
        return problems;
    }

    // ------------------------------------------------------------------
    // Ingreso
    // ------------------------------------------------------------------

    /**
     * Autentica y abre una sesión.
     *
     * <p>El orden importa: primero se verifica la contraseña y después se mira
     * si la cuenta está frenada. Al revés, un atacante sabría que el correo
     * existe con solo provocar el freno, sin acertar nunca la contraseña.
     * Haciéndolo en este orden, quien no sabe la contraseña recibe siempre la
     * misma respuesta, y solo el dueño legítimo llega a enterarse de que su
     * cuenta está frenada y de cuánto le falta para poder entrar.
     *
     * <p><b>{@code noRollbackFor} no es un detalle.</b> Spring deshace la
     * transacción cuando el método lanza una excepción no comprobada, y eso
     * incluye el {@code InvalidCredentialsException} de un intento fallido:
     * sin esta cláusula, el contador de intentos se sumaba en memoria y se
     * borraba al salir, de modo que la cuenta no se frenaba nunca y el freno
     * entero era decorativo.
     *
     * <p>Las pruebas con {@code @Transactional} no lo veían, porque leían el
     * contador desde la misma sesión de Hibernate donde seguía sumado. Lo
     * descubrió {@code AuthenticationHttpTest}, que va por HTTP real y sin
     * transacción alrededor.
     *
     * @return la cuenta y el token de la sesión recién abierta
     */
    @Transactional(noRollbackFor = InvalidCredentialsException.class)
    public LoginResult login(String email, String password, Instant now) {
        String normalizedEmail = normalizeEmail(email);
        Optional<Account> found = accounts.findByEmail(normalizedEmail);

        if (found.isEmpty()) {
            // Se compara contra un resumen inventado para gastar el mismo
            // tiempo que si la cuenta existiera. El resultado se descarta.
            passwordEncoder.matches(password, dummyHash);
            throw new InvalidCredentialsException();
        }

        Account account = found.get();
        boolean passwordMatches = passwordEncoder.matches(password, account.getPasswordHash());

        if (!passwordMatches) {
            registerFailedAttempt(account, now);
            throw new InvalidCredentialsException();
        }

        if (account.isLocked(now)) {
            // Contraseña correcta, pero la cuenta sigue frenada. Es el único
            // caso en que se dice la verdad completa, porque quien llega aquí
            // ya demostró ser el dueño.
            throw new AccountLockedException(Duration.between(now, account.getLockedUntil()));
        }

        account.setFailedAttempts(0);
        account.setLockedUntil(null);
        account.setLastLoginAt(now);
        accounts.save(account);

        return openSession(account, now);
    }

    /**
     * Suma un intento fallido y frena la cuenta al llegar al tope.
     *
     * <p>Mientras está frenada no se suman más: si cada intento extendiera el
     * freno, cualquiera podría dejar fuera a un vendedor indefinidamente con
     * solo seguir probando. El freno tiene un final fijo desde que empieza.
     *
     * <p>Aun así, frenar por cuenta deja abierta la puerta a molestar a alguien
     * concreto durante quince minutos. Por eso el producto no usa este
     * mecanismo sino dos topes en Redis, uno por cliente y otro por cuenta, que
     * retrasan sin cerrar. Aquí se implementa el freno porque es lo que se
     * puede sostener sin añadir Redis al servicio, y se deja escrito el
     * compromiso en lugar de callarlo.
     */
    private void registerFailedAttempt(Account account, Instant now) {
        if (account.isLocked(now)) {
            return;
        }
        int attempts = account.getFailedAttempts() + 1;
        account.setFailedAttempts(attempts);
        if (attempts >= MAX_FAILED_ATTEMPTS) {
            account.setLockedUntil(now.plus(LOCK_DURATION));
        }
        accounts.save(account);
    }

    // ------------------------------------------------------------------
    // Sesiones
    // ------------------------------------------------------------------

    private LoginResult openSession(Account account, Instant now) {
        String token = generateToken();
        AuthSession session = new AuthSession(sha256(token), account, now.plus(SESSION_DURATION));
        sessions.save(session);
        return new LoginResult(account, token, session.getExpiresAt());
    }

    /**
     * Devuelve la cuenta dueña de un token vivo.
     *
     * <p>La caducidad se comprueba aquí y no se confía en que algo haya
     * borrado la fila: la limpieza puede no haberse ejecutado, y una sesión
     * vencida que todavía existe en la tabla no debe dejar pasar a nadie.
     */
    @Transactional(readOnly = true)
    public Account requireAccount(String token, Instant now) {
        AuthSession session = sessions.findByTokenHash(sha256(token))
                .orElseThrow(InvalidSessionException::new);
        if (session.isExpired(now)) {
            throw new InvalidSessionException();
        }
        return session.getAccount();
    }

    /**
     * Cierra una sesión.
     *
     * <p>No falla si el token no existe. Cerrar sesión dos veces, o con un
     * token ya caducado, debe terminar igual de bien: el usuario quería quedar
     * fuera y queda fuera. Además, un error distinto según si el token existía
     * serviría para adivinar tokens.
     */
    @Transactional
    public void logout(String token) {
        sessions.deleteByTokenHash(sha256(token));
    }

    // ------------------------------------------------------------------
    // Utilidades
    // ------------------------------------------------------------------

    /**
     * Minúsculas y sin espacios alrededor.
     *
     * <p>{@code Locale.ROOT} y no el del sistema: con la configuración turca,
     * {@code "I".toLowerCase()} produce «ı», una letra distinta, y el correo de
     * alguien dejaría de encontrarse según dónde esté instalado el servidor.
     */
    private String normalizeEmail(String email) {
        return email.trim().toLowerCase(Locale.ROOT);
    }

    /**
     * Token de sesión con 256 bits de azar.
     *
     * <p>{@code SecureRandom} y no {@code Random}: el segundo es predecible a
     * partir de unas pocas salidas, así que quien viera un token podría
     * calcular los siguientes. Se codifica en Base64 para URL y sin relleno,
     * para que viaje entero en una cabecera sin necesidad de escaparlo.
     */
    private String generateToken() {
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    /** Resumen hexadecimal del token, que es lo que se guarda. */
    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                hex.append(Character.forDigit((b >> 4) & 0xF, 16));
                hex.append(Character.forDigit(b & 0xF, 16));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException unavailable) {
            // SHA-256 es obligatorio en toda máquina virtual Java. Si falta, la
            // instalación está rota y no hay nada sensato que hacer aquí.
            throw new IllegalStateException("SHA-256 no está disponible en esta JVM.", unavailable);
        }
    }

    /**
     * Lo que devuelve un ingreso correcto.
     *
     * <p>Lleva la cuenta además del token para que el controlador no tenga que
     * volver a la base a buscar lo que el servicio ya tenía en la mano.
     *
     * <p>El token en claro solo existe aquí: en la tabla queda su resumen, así
     * que este es el único momento en que se puede entregar.
     */
    public record LoginResult(Account account, String token, Instant expiresAt) {
    }
}
