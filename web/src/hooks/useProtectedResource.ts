"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import { session } from "@/lib/session";

/**
 * Carga un recurso que exige sesión, con sus cuatro estados.
 *
 * Nace de una duplicación medida: **28 páginas** repetían el mismo bloque de
 * unas veinticinco líneas —leer el token, redirigir si no hay, pedir el dato,
 * distinguir el 401 del 403, y apagar el indicador de carga en un `finally`—.
 * Copiado veintiocho veces, basta con que una copia olvide el `finally` para
 * que esa pantalla se quede cargando para siempre, y nadie lo nota hasta que
 * un usuario lo reporta.
 *
 * Los cuatro estados no son intercambiables y por eso se devuelven aparte:
 *
 * - **cargando** — todavía no se sabe nada.
 * - **prohibido** — hay sesión, pero no para esto. Se muestra una explicación,
 *   no un error: el usuario no hizo nada mal.
 * - **error** — algo falló y se puede reintentar.
 * - **datos** — llegó el recurso.
 *
 * El 401 no es ninguno de los cuatro: significa que la sesión caducó, y lo que
 * corresponde es volver a la pantalla de ingreso, no mostrar un mensaje.
 */
export interface ProtectedResource<T> {
  /** El recurso, o `null` mientras no haya llegado. */
  data: T | null;
  isLoading: boolean;
  /** La petición falló por algo que se puede reintentar. */
  hasError: boolean;
  /** Hay sesión, pero no da acceso a este recurso. */
  isForbidden: boolean;
  /** Vuelve a pedirlo. Es la misma función que usa el botón de reintentar. */
  reload: () => Promise<void>;
  /** Reemplaza el dato en memoria sin volver a pedirlo al servidor. */
  setData: (value: T | null) => void;
}

/**
 * @param fetcher  Cómo pedir el recurso, dado el token de la sesión.
 * @param deps     Qué hace que haya que volver a pedirlo. Igual que en
 *                 `useEffect`: si el `fetcher` depende de algo que cambia —un
 *                 identificador de la ruta, un filtro—, va aquí.
 */
export function useProtectedResource<T>(
  fetcher: (token: string) => Promise<T>,
  deps: readonly unknown[] = [],
): ProtectedResource<T> {
  const router = useRouter();

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isForbidden, setIsForbidden] = useState(false);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setHasError(false);
    setIsForbidden(false);

    try {
      setData(await fetcher(token));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        // La sesión caducó. No es un error que mostrar: es volver a entrar.
        router.push("/ingresar");
        return;
      }
      if (requestError instanceof ApiError && requestError.status === 403) {
        setIsForbidden(true);
        return;
      }
      setHasError(true);
    } finally {
      // En el `finally` y no al final del `try`: sin esto, un error deja la
      // pantalla cargando para siempre. Es el olvido que más se repetía.
      setIsLoading(false);
    }
    // `fetcher` se recrea en cada render, así que depender de él provocaría una
    // petición infinita. Lo que de verdad decide cuándo recargar es `deps`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router, ...deps]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isLoading, hasError, isForbidden, reload: load, setData };
}
