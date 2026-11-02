package co.monkgrain.authentication.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Lo que el cliente envía para iniciar sesión.
 *
 * <p>Sin {@code @Email} sobre el correo, a diferencia del registro. Si un
 * correo mal formado devolviera «formato inválido» y uno bien formado pero
 * inexistente devolviera «credenciales incorrectas», las dos respuestas
 * distintas ya servirían para ir descartando. Aquí todo lo que no sea un
 * ingreso correcto responde igual.
 */
public record LoginRequest(

        @NotBlank(message = "El correo es obligatorio.")
        @Size(max = 254)
        String email,

        @NotBlank(message = "La contraseña es obligatoria.")
        @Size(max = 128)
        String password) {
}
