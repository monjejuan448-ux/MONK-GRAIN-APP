package co.monkgrain.negotiation;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Punto de entrada del módulo de negociación.
 *
 * <p>MONK GRAIN — el mercado de pergamino en su segundo sentido: el comprador
 * publica lo que busca y los caficultores responden con su precio.
 */
@SpringBootApplication
public class NegotiationApplication {

    public static void main(String[] args) {
        SpringApplication.run(NegotiationApplication.class, args);
    }
}
