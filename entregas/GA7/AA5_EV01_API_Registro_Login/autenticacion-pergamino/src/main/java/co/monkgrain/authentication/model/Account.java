package co.monkgrain.authentication.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * Una cuenta de la plataforma.
 *
 * <p>La contraseña no está en esta clase, y no es un olvido: lo que se guarda
 * es {@code passwordHash}, el resumen BCrypt. La contraseña en claro existe
 * durante la petición y desaparece con ella.
 */
@Entity
@Table(name = "auth_accounts")
public class Account {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * El correo identifica la cuenta.
     *
     * <p>{@code unique} en la columna y no solo una consulta previa en el
     * servicio: entre consultar y escribir caben dos peticiones simultáneas, y
     * la única barrera que ninguna de las dos puede saltarse es la de la base
     * de datos. Se guarda siempre en minúsculas, porque quien escribe
     * «Ana@finca.co» al registrarse escribirá «ana@finca.co» al volver.
     */
    @Column(nullable = false, unique = true, length = 254)
    private String email;

    /**
     * Resumen BCrypt de la contraseña, nunca la contraseña.
     *
     * <p>60 caracteres: BCrypt produce siempre esa longitud, e incluye dentro
     * el algoritmo, el factor de coste y la sal.
     */
    @Column(name = "password_hash", nullable = false, length = 60)
    private String passwordHash;

    @Column(name = "full_name", nullable = false, length = 120)
    private String fullName;

    /**
     * {@code STRING} y no {@code ORDINAL}.
     *
     * <p>Con el ordinal, el rol se guarda como 0, 1 o 2 según el orden en que
     * están escritos en el enumerado: insertar un valor nuevo en medio
     * convertiría a todos los compradores en vendedores sin tocar la base.
     */
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AccountRole role = AccountRole.BUYER;

    /**
     * Intentos fallidos seguidos desde el último ingreso correcto.
     *
     * <p>Vive en la cuenta y no en memoria porque el freno debe sobrevivir a
     * un reinicio del servicio: si no, bastaría con esperar un despliegue para
     * volver a empezar a probar contraseñas.
     */
    @Column(name = "failed_attempts", nullable = false)
    private int failedAttempts = 0;

    /** Hasta cuándo está frenada la cuenta. {@code null} si no lo está. */
    @Column(name = "locked_until")
    private Instant lockedUntil;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    /** Constructor sin argumentos: lo exige JPA para reconstruir la entidad. */
    protected Account() {
    }

    public Account(String email, String passwordHash, String fullName) {
        this.email = email;
        this.passwordHash = passwordHash;
        this.fullName = fullName;
    }

    /** Si la cuenta está frenada en este momento. */
    public boolean isLocked(Instant now) {
        return lockedUntil != null && lockedUntil.isAfter(now);
    }

    public Long getId() {
        return id;
    }

    public String getEmail() {
        return email;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public void setPasswordHash(String passwordHash) {
        this.passwordHash = passwordHash;
    }

    public String getFullName() {
        return fullName;
    }

    public AccountRole getRole() {
        return role;
    }

    public void setRole(AccountRole role) {
        this.role = role;
    }

    public int getFailedAttempts() {
        return failedAttempts;
    }

    public void setFailedAttempts(int failedAttempts) {
        this.failedAttempts = failedAttempts;
    }

    public Instant getLockedUntil() {
        return lockedUntil;
    }

    public void setLockedUntil(Instant lockedUntil) {
        this.lockedUntil = lockedUntil;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getLastLoginAt() {
        return lastLoginAt;
    }

    public void setLastLoginAt(Instant lastLoginAt) {
        this.lastLoginAt = lastLoginAt;
    }
}
