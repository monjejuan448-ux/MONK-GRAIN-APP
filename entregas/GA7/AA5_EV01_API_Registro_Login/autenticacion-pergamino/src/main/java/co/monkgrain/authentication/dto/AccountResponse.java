package co.monkgrain.authentication.dto;

import co.monkgrain.authentication.model.Account;
import co.monkgrain.authentication.model.AccountRole;
import java.time.Instant;

/**
 * La cuenta tal como sale hacia el cliente.
 *
 * <p>No lleva {@code passwordHash} ni {@code failedAttempts} ni
 * {@code lockedUntil}, y es deliberado: devolver la entidad entera publicaría
 * el resumen de la contraseña en cada respuesta, y los intentos fallidos le
 * dirían a un atacante cuánto le queda antes de que la cuenta se frene.
 */
public record AccountResponse(
        Long id,
        String email,
        String fullName,
        AccountRole role,
        Instant createdAt,
        Instant lastLoginAt) {

    public static AccountResponse from(Account account) {
        return new AccountResponse(
                account.getId(),
                account.getEmail(),
                account.getFullName(),
                account.getRole(),
                account.getCreatedAt(),
                account.getLastLoginAt());
    }
}
