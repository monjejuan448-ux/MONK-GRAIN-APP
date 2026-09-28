/**
 * Cliente HTTP del backend.
 *
 * Traduce la respuesta de error estructurada de la API a una excepción tipada,
 * de modo que la interfaz pueda mostrar un mensaje entendible en lugar de un
 * código crudo.
 */

/**
 * Base de la API, distinta según dónde se ejecute la petición.
 *
 * En el navegador la API se alcanza por `localhost`, pero desde el servidor de
 * Next.js —que corre dentro de su propio contenedor— `localhost` es ese mismo
 * contenedor y la conexión se rechaza. Ahí hay que usar el nombre del servicio
 * en la red de Docker (`backend`).
 */
const API_URL =
  typeof window === "undefined"
    ? (process.env.API_INTERNAL_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://backend:8000/api/v1")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1");

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: {
      fields?: Array<{ field: string; message: string }>;
      [key: string]: unknown;
    };
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: Record<string, string>;
  /**
   * Detalles que acompañan al error, más allá de los errores por campo. El
   * backend los usa para explicar una regla de negocio: al publicar un café,
   * por ejemplo, devuelve en `missing` la lista de lo que falta.
   */
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody | null) {
    const message = body?.error?.message ?? "No fue posible completar la operación.";
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.error?.code ?? "unknown_error";
    this.details = (body?.error?.details ?? {}) as Record<string, unknown>;

    this.fieldErrors = Object.fromEntries(
      (body?.error?.details?.fields ?? []).map((item) => [item.field, item.message]),
    );
  }

  /** Requisitos incumplidos que el servidor enumeró, si los hay. */
  get missingRequirements(): string[] {
    const missing = this.details.missing;
    return Array.isArray(missing) ? (missing as string[]) : [];
  }

  /** Un 401 significa que la sesión caducó y hay que volver a autenticarse. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Token de acceso. Se inyecta desde el proveedor de sesión. */
  token?: string | null;
  /** Parámetros de consulta; los valores nulos se omiten. */
  query?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_URL}${path}`);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  return url.toString();
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, token, query, headers, ...rest } = options;

  const response = await fetch(buildUrl(path, query), {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    let errorBody: ApiErrorBody | null = null;
    try {
      errorBody = (await response.json()) as ApiErrorBody;
    } catch {
      // Una respuesta de error sin cuerpo JSON (502 del proxy, por ejemplo)
      // no debe enmascarar el código de estado real.
    }
    throw new ApiError(response.status, errorBody);
  }

  return (await response.json()) as T;
}

/**
 * Envía un formulario con archivos.
 *
 * No fija `Content-Type`: el navegador debe añadirlo junto con el `boundary`
 * que separa las partes, y escribirlo a mano rompería el envío.
 */
export async function apiUpload<T>(
  path: string,
  form: FormData,
  options: { token?: string; method?: string } = {},
): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: options.method ?? "POST",
    headers: options.token ? { Authorization: `Bearer ${options.token}` } : {},
    body: form,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    let errorBody: ApiErrorBody | null = null;
    try {
      errorBody = (await response.json()) as ApiErrorBody;
    } catch {
      // Un error sin cuerpo JSON no debe ocultar el código de estado.
    }
    throw new ApiError(response.status, errorBody);
  }

  return (await response.json()) as T;
}

/**
 * Descarga un recurso binario, como el comprobante en PDF.
 *
 * No sirve `apiRequest`: esa función asume una respuesta JSON y aquí lo que
 * llega es un archivo. El cuerpo del error, en cambio, sí es JSON, así que se
 * traduce a `ApiError` igual que en el resto del cliente.
 */
export async function apiBlob(path: string, token?: string | null): Promise<Blob> {
  const response = await fetch(buildUrl(path), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    let errorBody: ApiErrorBody | null = null;
    try {
      errorBody = (await response.json()) as ApiErrorBody;
    } catch {
      // Un error sin cuerpo JSON no debe ocultar el código de estado.
    }
    throw new ApiError(response.status, errorBody);
  }

  return await response.blob();
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "DELETE" }),
};
