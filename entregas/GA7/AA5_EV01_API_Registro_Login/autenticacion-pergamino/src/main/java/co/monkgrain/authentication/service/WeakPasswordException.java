package co.monkgrain.authentication.service;

import java.util.List;

/**
 * La contraseña no cumple la política.
 *
 * <p>Lleva la lista de reglas incumplidas y no un mensaje único: si alguien
 * escribió una contraseña corta y sin números, decírselo de una vez evita que
 * lo intente tres veces. Aquí no hay nada que ocultar —la política es pública
 * y está escrita en el formulario—, a diferencia de lo que ocurre al ingresar.
 */
public class WeakPasswordException extends RuntimeException {

    private final List<String> problems;

    public WeakPasswordException(List<String> problems) {
        super("La contraseña no cumple la política de seguridad.");
        this.problems = List.copyOf(problems);
    }

    public List<String> getProblems() {
        return problems;
    }
}
