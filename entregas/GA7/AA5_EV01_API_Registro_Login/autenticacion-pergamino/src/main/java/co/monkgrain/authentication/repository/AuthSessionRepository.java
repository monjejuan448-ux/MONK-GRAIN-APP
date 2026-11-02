package co.monkgrain.authentication.repository;

import co.monkgrain.authentication.model.Account;
import co.monkgrain.authentication.model.AuthSession;
import java.time.Instant;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** Acceso a las sesiones abiertas. */
public interface AuthSessionRepository extends JpaRepository<AuthSession, Long> {

    /**
     * Busca la sesión y trae su cuenta en la misma consulta.
     *
     * <p><b>El {@code join fetch} no es un adorno.</b> Sin él, Spring Data
     * genera la consulta derivada del nombre y deja la cuenta como un
     * sustituto perezoso. El servicio devuelve la cuenta, su transacción
     * termina ahí, y cuando el controlador lee el correo ya no hay sesión de
     * Hibernate abierta: el resultado es {@code LazyInitializationException} y
     * un error 500 en {@code GET /api/auth/me}.
     *
     * <p>No se arregló poniendo {@code FetchType.EAGER} en la entidad: eso
     * obligaría a traer la cuenta también cuando no se necesita —al cerrar
     * sesión, por ejemplo, donde solo hace falta borrar la fila—. La consulta
     * que sí necesita la cuenta es esta, y es aquí donde se pide.
     *
     * <p>Tampoco se arregló con {@code spring.jpa.open-in-view=true}, que es
     * el atajo habitual: mantener la sesión abierta durante toda la petición
     * esconde este problema y, de paso, cualquier consulta accidental que haga
     * una plantilla.
     */
    @Query("select s from AuthSession s join fetch s.account where s.tokenHash = :tokenHash")
    Optional<AuthSession> findByTokenHash(@Param("tokenHash") String tokenHash);

    void deleteByTokenHash(String tokenHash);

    /**
     * Cierra todas las sesiones de una cuenta.
     *
     * <p>Se usa al cambiar la contraseña: si alguien la cambió porque sospecha
     * que se la robaron, dejar vivas las sesiones abiertas vaciaría el gesto de
     * sentido.
     */
    void deleteByAccount(Account account);

    /**
     * Borra lo que ya caducó.
     *
     * <p>Una sesión vencida no deja pasar a nadie —el servicio comprueba la
     * fecha— pero ocupa sitio y crece sin tope. Esta consulta existe para que
     * una tarea de mantenimiento pueda limpiarla.
     */
    @Modifying
    @Query("delete from AuthSession s where s.expiresAt <= :moment")
    int deleteExpired(@Param("moment") Instant moment);
}
