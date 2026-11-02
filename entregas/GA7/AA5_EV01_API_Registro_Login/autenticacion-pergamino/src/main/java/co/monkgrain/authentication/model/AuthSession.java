package co.monkgrain.authentication.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * Una sesión abierta.
 *
 * <p><b>Por qué una tabla y no un JWT.</b> Un JWT no se puede revocar: lleva la
 * firma dentro, así que cualquier servicio lo da por bueno hasta que caduque,
 * aunque el usuario haya cerrado sesión o le hayan robado el teléfono. Para
 * invalidarlo haría falta igualmente una lista de rechazados en la base, que es
 * exactamente lo que el JWT prometía evitar. Con un identificador opaco contra
 * esta tabla, cerrar sesión es borrar una fila.
 *
 * <p>El precio es una consulta por petición. A la escala de MONK GRAIN eso no
 * se nota; poder cerrar una sesión robada, sí.
 */
@Entity
@Table(name = "auth_sessions")
public class AuthSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Resumen SHA-256 del token, no el token.
     *
     * <p>Mismo razonamiento que con las contraseñas: quien se lleve una copia
     * de la base no debe quedarse con sesiones vivas en la mano. Aquí sí sirve
     * SHA-256 y no hace falta BCrypt, porque el token lo genera el servidor con
     * 256 bits de azar: no hay diccionario que probar contra él.
     */
    @Column(name = "token_hash", nullable = false, unique = true, length = 64)
    private String tokenHash;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "account_id", nullable = false)
    private Account account;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    protected AuthSession() {
    }

    public AuthSession(String tokenHash, Account account, Instant expiresAt) {
        this.tokenHash = tokenHash;
        this.account = account;
        this.expiresAt = expiresAt;
    }

    public boolean isExpired(Instant now) {
        return !expiresAt.isAfter(now);
    }

    public Long getId() {
        return id;
    }

    public String getTokenHash() {
        return tokenHash;
    }

    public Account getAccount() {
        return account;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }
}
