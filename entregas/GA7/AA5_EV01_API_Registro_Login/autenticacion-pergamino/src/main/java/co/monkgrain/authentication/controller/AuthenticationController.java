package co.monkgrain.authentication.controller;

import co.monkgrain.authentication.dto.AccountResponse;
import co.monkgrain.authentication.dto.AuthResponse;
import co.monkgrain.authentication.dto.LoginRequest;
import co.monkgrain.authentication.dto.MessageResponse;
import co.monkgrain.authentication.dto.RegistrationRequest;
import co.monkgrain.authentication.service.AuthenticationService;
import co.monkgrain.authentication.service.AuthenticationService.LoginResult;
import co.monkgrain.authentication.service.InvalidSessionException;
import jakarta.validation.Valid;
import java.time.Instant;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * Los cuatro endpoints del servicio de autenticación.
 *
 * <p>El controlador no decide nada: traduce HTTP a llamadas del servicio y
 * respuestas del servicio a códigos de estado. Las reglas están en
 * {@code AuthenticationService}, y los fallos los convierte en respuesta
 * {@code ApiExceptionHandler}.
 *
 * <p><b>Sin {@code @Validated} sobre la clase.</b> Desde Spring Framework 6.1,
 * {@code @Valid} sobre el cuerpo ya valida por sí solo; añadir {@code @Validated}
 * hace que se valide dos veces y que el segundo fallo salga como error 500 en
 * lugar de 400. Fue justo el error de AA3-EV01.
 */
@RestController
@RequestMapping("/api/auth")
public class AuthenticationController {

    /** Mismo acuse exista o no el correo. Ver {@code AuthenticationService#register}. */
    private static final String NEUTRAL_REGISTER_MESSAGE =
            "Si el correo no estaba registrado, tu cuenta quedó creada. "
                    + "Ya puedes iniciar sesión.";

    private static final String AUTHENTICATION_OK = "Autenticación satisfactoria.";

    private final AuthenticationService authentication;

    public AuthenticationController(AuthenticationService authentication) {
        this.authentication = authentication;
    }

    /**
     * Registra una cuenta.
     *
     * <p>Responde 202 y no 201. Un 201 anuncia «se creó un recurso», y la
     * gracia de esta respuesta es precisamente no decir si se creó o no: con
     * 201 para un correo nuevo y otra cosa para uno repetido, el código de
     * estado delataría lo que el mensaje calla.
     */
    @PostMapping("/register")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public MessageResponse register(@Valid @RequestBody RegistrationRequest request) {
        authentication.register(request.email(), request.password(), request.fullName());
        return new MessageResponse(NEUTRAL_REGISTER_MESSAGE);
    }

    /**
     * Inicia sesión.
     *
     * <p>Es lo que pide la evidencia: recibe usuario y contraseña, y devuelve
     * el mensaje de autenticación satisfactoria o el de error. El error no sale
     * de aquí sino del manejador, que es quien le pone el 401.
     */
    @PostMapping("/login")
    public AuthResponse login(@Valid @RequestBody LoginRequest request) {
        LoginResult result = authentication.login(request.email(), request.password(), Instant.now());
        return new AuthResponse(
                AUTHENTICATION_OK,
                result.token(),
                result.expiresAt(),
                AccountResponse.from(result.account()));
    }

    /**
     * Devuelve la cuenta de quien presenta el token.
     *
     * <p>Existe para que el token sirva de algo y para que se pueda comprobar
     * desde Postman que la sesión quedó abierta de verdad, no solo que el
     * mensaje decía que sí.
     */
    @GetMapping("/me")
    public AccountResponse currentAccount(
            @RequestHeader(value = "Authorization", required = false) String authorization) {
        return AccountResponse.from(
                authentication.requireAccount(extractToken(authorization), Instant.now()));
    }

    /** Cierra la sesión. Borra la fila, así que el token deja de valer al instante. */
    @PostMapping("/logout")
    public ResponseEntity<MessageResponse> logout(
            @RequestHeader(value = "Authorization", required = false) String authorization) {
        authentication.logout(extractToken(authorization));
        return ResponseEntity.ok(new MessageResponse("Tu sesión quedó cerrada."));
    }

    /**
     * Saca el token de la cabecera {@code Authorization: Bearer <token>}.
     *
     * <p>El prefijo se compara sin distinguir mayúsculas porque la norma
     * (RFC 7235) dice que el esquema no las distingue, y hay clientes que
     * envían «bearer».
     */
    private String extractToken(String authorization) {
        if (authorization == null || authorization.isBlank()) {
            throw new InvalidSessionException();
        }
        String value = authorization.trim();
        if (value.length() < 8 || !value.regionMatches(true, 0, "Bearer ", 0, 7)) {
            throw new InvalidSessionException();
        }
        return value.substring(7).trim();
    }
}
