package co.monkgrain.authentication.dto;

import java.time.Instant;

/**
 * Respuesta de un ingreso correcto.
 *
 * <p>El {@code message} es lo que pide la evidencia —«autenticación
 * satisfactoria»— y el {@code token} es lo que hace útil al servicio: sin él,
 * el cliente sabría que la contraseña era buena pero no podría hacer nada con
 * ese dato.
 *
 * <p>{@code expiresAt} viaja explícito para que el cliente pueda avisar antes
 * de que la sesión caiga, en lugar de descubrirlo con un 401 en medio de un
 * formulario a medio llenar.
 */
public record AuthResponse(
        String message,
        String token,
        Instant expiresAt,
        AccountResponse account) {
}
