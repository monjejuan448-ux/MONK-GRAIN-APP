package co.monkgrain.authentication;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Servicio web de registro e inicio de sesión de MONK GRAIN.
 *
 * <p>GA7-220501096-AA5-EV01. Espeja el módulo {@code auth} del producto, que
 * está escrito en Python, con las mismas decisiones de seguridad: mensajes que
 * no delatan qué correos existen, contraseñas guardadas como resumen BCrypt y
 * sesiones revocables.
 */
@SpringBootApplication
public class AuthenticationApplication {

    public static void main(String[] args) {
        SpringApplication.run(AuthenticationApplication.class, args);
    }

    /**
     * BCrypt y no SHA-256 ni MD5.
     *
     * <p>Un resumen rápido es un defecto aquí, no una virtud: una tarjeta
     * gráfica calcula miles de millones de SHA-256 por segundo, así que un
     * atacante con la tabla robada prueba el diccionario entero en minutos.
     * BCrypt está hecho para ser lento a propósito y lleva la sal incorporada
     * en el propio resultado, de modo que dos personas con la misma contraseña
     * no comparten resumen.
     *
     * <p>El factor 10 significa 2^10 vueltas: unos 100 ms por verificación en
     * el equipo de desarrollo. Es el punto donde todavía no se nota al iniciar
     * sesión y ya duele mucho al que prueba contraseñas por fuerza bruta.
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(10);
    }
}
