package co.monkgrain.authentication.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Lo que el cliente envía para registrarse.
 *
 * <p><b>Por qué un objeto propio y no la entidad {@code Account}.</b> Recibir
 * la entidad dejaría que cualquiera enviara {@code {"role": "ADMIN"}} o
 * {@code {"id": 7}} y se hiciera administrador, o sobrescribiera la cuenta
 * ajena número 7. Lo que no está en esta clase, no entra: el rol y el
 * identificador los decide el servicio. Es la misma lección de AA3-EV01.
 *
 * <p><b>Por qué aquí sí es un {@code record} y en AA3 no.</b> Allí las pantallas
 * eran formularios HTML, y un {@code record} se construye entero o no se
 * construye: un número mal escrito dejaba el objeto en {@code null} y la
 * plantilla fallaba con error 500. Este servicio solo habla JSON, donde un
 * campo con el tipo equivocado lo rechaza Jackson antes, con un 400 limpio.
 */
public record RegistrationRequest(

        @NotBlank(message = "El correo es obligatorio.")
        @Email(message = "El correo no tiene un formato válido.")
        @Size(max = 254, message = "El correo no puede pasar de 254 caracteres.")
        String email,

        /*
         * El mínimo de 12 y la exigencia de letra y número se comprueban en el
         * servicio, no aquí: son tres reglas distintas y la persona merece
         * saber cuál incumplió, no un «contraseña inválida» a secas. Aquí solo
         * se frena lo que ni siquiera llega a ser una contraseña.
         */
        @NotBlank(message = "La contraseña es obligatoria.")
        @Size(max = 128, message = "La contraseña no puede pasar de 128 caracteres.")
        String password,

        @NotBlank(message = "El nombre es obligatorio.")
        @Size(min = 3, max = 120, message = "El nombre debe tener entre 3 y 120 caracteres.")
        String fullName) {
}
