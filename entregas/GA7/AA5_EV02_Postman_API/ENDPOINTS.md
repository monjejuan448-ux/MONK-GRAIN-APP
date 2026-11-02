# ENDPOINTS — Servicio de autenticación de MONK GRAIN

**GA7-220501096-AA5-EV02** · API probada: `autenticacion-pergamino` (AA5-EV01)

**Base:** `http://localhost:8082/api/auth`
**Formato:** JSON en entrada y salida. UTF-8 (RFC 8259), sin juego de
caracteres declarado en la cabecera.
**Autenticación:** `Authorization: Bearer <token>` en los endpoints que la
necesitan. El token lo entrega `POST /login`.

---

## Resumen

| # | Método | Ruta | Token | Éxito |
|---|---|---|---|---|
| 1 | `POST` | `/api/auth/register` | no | `202` |
| 2 | `POST` | `/api/auth/login` | no | `200` |
| 3 | `GET` | `/api/auth/me` | **sí** | `200` |
| 4 | `POST` | `/api/auth/logout` | **sí** | `200` |

---

## 1. `POST /api/auth/register`

Crea una cuenta. El rol es siempre `BUYER`: no se puede pedir en la petición.

**Entrada**

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `email` | texto | sí | Formato de correo, máx. 254 |
| `password` | texto | sí | Mín. 12, una letra y un número, máx. 128 |
| `fullName` | texto | sí | Entre 3 y 120 caracteres |

```json
{
  "email": "ana@finca.co",
  "password": "pergamino2026",
  "fullName": "Ana Restrepo"
}
```

**Respuestas**

| Código | Cuándo | Cuerpo |
|---|---|---|
| `202` | Siempre que los datos sean válidos | `{"message":"Si el correo no estaba registrado, tu cuenta quedó creada. Ya puedes iniciar sesión."}` |
| `400` | Falta un campo, o el correo no tiene formato | `{"error":"validation_error","message":"Revisa los datos enviados.","details":["email: ..."]}` |
| `400` | El cuerpo no es JSON válido | `{"error":"malformed_body", ...}` |
| `422` | La contraseña no cumple la política | `{"error":"weak_password","details":["Debe tener al menos 12 caracteres.","Debe incluir al menos un número."]}` |

> **No hay `409`.** Un correo ya registrado responde `202` con el mismo cuerpo
> que un correo nuevo. Es deliberado: un «ese correo ya está en uso»
> convertiría el registro en un buscador de cuentas. Por el mismo motivo
> responde `202` y no `201`, que anunciaría que se creó algo.

---

## 2. `POST /api/auth/login`

Autentica y abre una sesión de 8 horas.

**Entrada**

| Campo | Tipo | Obligatorio |
|---|---|---|
| `email` | texto | sí |
| `password` | texto | sí |

```json
{ "email": "ana@finca.co", "password": "pergamino2026" }
```

**Respuesta `200`**

```json
{
  "message": "Autenticación satisfactoria.",
  "token": "QnqQHzHkblc1hdCmxVZ87FLbd-MQh_CZehXmmVgDKNU",
  "expiresAt": "2026-11-02T11:17:46Z",
  "account": {
    "id": 2,
    "email": "ana@finca.co",
    "fullName": "Ana Restrepo",
    "role": "BUYER",
    "createdAt": "2026-11-02T03:17:32Z",
    "lastLoginAt": "2026-11-02T03:17:46Z"
  }
}
```

El objeto `account` **no** incluye `passwordHash`, `failedAttempts` ni
`lockedUntil`: el primero publicaría el resumen de la contraseña en cada
respuesta, y los otros dos dirían a un atacante cuántos intentos le quedan
antes del freno.

**Otras respuestas**

| Código | Cuándo | Cuerpo |
|---|---|---|
| `400` | Falta un campo | `{"error":"validation_error", ...}` |
| `401` | Contraseña equivocada **o** correo inexistente | `{"error":"authentication_failed","message":"Correo o contraseña incorrectos."}` |
| `429` | Contraseña **correcta** con la cuenta frenada | `{"error":"account_locked","message":"Demasiados intentos fallidos. Vuelve a intentarlo en 15 minutos."}` + cabecera `Retry-After` en segundos |

> **El `401` es el mismo en los dos casos**, byte por byte salvo la marca de
> tiempo. Distinguirlos convertiría el endpoint en una forma de averiguar qué
> correos están registrados.
>
> **El `429` solo aparece con la contraseña correcta.** Con la contraseña
> equivocada y la cuenta frenada se responde el `401` neutral: anunciar el
> freno a cualquiera confirmaría que el correo existe.
>
> **No hay `404`.** Diría «ese usuario no está aquí», que es el dato que se
> calla.

---

## 3. `GET /api/auth/me`

Devuelve la cuenta dueña del token.

**Cabecera:** `Authorization: Bearer <token>`
El esquema no distingue mayúsculas: `bearer` también vale (RFC 7235).

**Respuesta `200`**

```json
{
  "id": 2,
  "email": "ana@finca.co",
  "fullName": "Ana Restrepo",
  "role": "BUYER",
  "createdAt": "2026-11-02T03:17:32Z",
  "lastLoginAt": "2026-11-02T03:17:46Z"
}
```

| Código | Cuándo |
|---|---|
| `401` | Sin cabecera, con otro esquema, con un token inventado, con una sesión caducada o con una sesión ya cerrada |

---

## 4. `POST /api/auth/logout`

Cierra la sesión borrando su fila. El token deja de valer al instante, sin
esperar la caducidad.

**Cabecera:** `Authorization: Bearer <token>`

**Respuesta `200`:** `{"message":"Tu sesión quedó cerrada."}`

> **Es idempotente y no falla nunca con 404.** Cerrar sesión dos veces, o con
> un token que nunca existió, responde `200`: el usuario quería quedar fuera y
> queda fuera. Además, un error distinto según si el token existía serviría
> para adivinar tokens.
>
> Cierra **solo esa** sesión. La del otro dispositivo sigue abierta.

---

## Forma de los errores

Todos los errores tienen la misma estructura, para que el cliente pueda
mostrar `message` sin mirar nada más:

```json
{
  "error": "authentication_failed",
  "message": "Correo o contraseña incorrectos.",
  "details": ["opcional, solo en errores de validación"],
  "timestamp": "2026-11-02T03:17:46.967Z"
}
```

| `error` | Código | Significado |
|---|---|---|
| `validation_error` | `400` | Falta un campo o tiene mal el formato |
| `malformed_body` | `400` | El cuerpo no es JSON válido |
| `authentication_failed` | `401` | No se pudo autenticar (sin decir por qué) |
| `invalid_session` | `401` | El token no corresponde a una sesión viva |
| `weak_password` | `422` | La contraseña no cumple la política |
| `account_locked` | `429` | Cuenta frenada por intentos fallidos |
| `internal_error` | `500` | Fallo no previsto. El detalle va a la bitácora del servidor, nunca a la respuesta |

---

## Códigos que este servicio **no** usa, y por qué

| Código | Por qué no |
|---|---|
| `201` en el registro | Anunciaría que se creó un recurso, y eso delata si el correo existía |
| `409` en el registro | Diría «ese correo ya está en uso» |
| `404` en el ingreso | Diría «ese usuario no está aquí» |
| `403` con la cuenta frenada | Dice «no puedes y no insistas»; la verdad es «ahora no, vuelve después», que es `429` |

---

## Cómo probarlo

```bash
# 1. levantar el servicio (puerto 8082)
cd entregas/GA7/AA5_EV01_API_Registro_Login/autenticacion-pergamino
$MVN package && java -jar target/autenticacion-pergamino.jar

# 2. con Postman: importar
#    entregas/GA7/AA5_EV02_Postman_API/postman/MONK_GRAIN_Autenticacion.postman_collection.json
#    y ejecutar con el Collection Runner, en orden.

# 3. desde la consola, el mismo recorrido:
newman run entregas/GA7/AA5_EV02_Postman_API/postman/MONK_GRAIN_Autenticacion.postman_collection.json
```
