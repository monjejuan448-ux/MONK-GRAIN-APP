package co.monkgrain.authentication.repository;

import co.monkgrain.authentication.model.Account;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Acceso a las cuentas.
 *
 * <p>Spring Data deriva la consulta del nombre del método, así que no hay SQL
 * que escribir ni, lo más importante, que concatenar: el valor viaja siempre
 * como parámetro y la inyección de SQL no tiene por dónde entrar.
 */
public interface AccountRepository extends JpaRepository<Account, Long> {

    /**
     * Busca por correo.
     *
     * <p>Devuelve {@code Optional} y no {@code null}: el que llama está
     * obligado a decidir qué hace cuando no existe, en vez de descubrirlo con
     * un {@code NullPointerException} tres líneas más abajo.
     *
     * <p>Quien llama normaliza a minúsculas antes; la columna guarda siempre la
     * forma normalizada.
     */
    Optional<Account> findByEmail(String email);

    boolean existsByEmail(String email);
}
