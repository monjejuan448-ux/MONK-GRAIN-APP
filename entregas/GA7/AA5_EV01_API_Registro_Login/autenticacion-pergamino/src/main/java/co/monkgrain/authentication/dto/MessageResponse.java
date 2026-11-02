package co.monkgrain.authentication.dto;

/**
 * Una respuesta que solo lleva un mensaje para la persona.
 *
 * <p>Un objeto y no una cadena suelta: {@code "Listo"} obliga al cliente a
 * tratar el cuerpo como texto plano, mientras que {@code {"message": "Listo"}}
 * se lee igual que todas las demás respuestas y admite campos nuevos más
 * adelante sin romper a quien ya lo consume.
 */
public record MessageResponse(String message) {
}
