"use client";

/**
 * Gestión de la sesión en el cliente.
 *
 * Los tokens viven hoy en `sessionStorage`, lo que es aceptable para el MVP
 * pero no para producción: quedan expuestos a cualquier script que se cuele en
 * la página. La fase 9 los mueve a cookies `httpOnly`, que el JavaScript de la
 * página no puede leer. Aislar el acceso en este módulo hace que ese cambio
 * afecte a un solo archivo.
 */

const ACCESS_KEY = "mg_access_token";
const REFRESH_KEY = "mg_refresh_token";
const ANON_CART_KEY = "mg_anon_cart";

export interface AnonymousCartItem {
  variant_id: string;
  quantity: number;
}

export const session = {
  getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return sessionStorage.getItem(ACCESS_KEY);
  },

  getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return sessionStorage.getItem(REFRESH_KEY);
  },

  save(accessToken: string, refreshToken: string): void {
    sessionStorage.setItem(ACCESS_KEY, accessToken);
    sessionStorage.setItem(REFRESH_KEY, refreshToken);
  },

  clear(): void {
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  },

  isAuthenticated(): boolean {
    return Boolean(session.getAccessToken());
  },
};

/**
 * Carrito de quien aún no ha iniciado sesión.
 *
 * Se conserva en `localStorage` y se fusiona con el carrito de la cuenta al
 * autenticarse, para que nadie pierda su selección por iniciar sesión
 * (HU-CC-05, CA3).
 */
export const anonymousCart = {
  read(): AnonymousCartItem[] {
    if (typeof window === "undefined") return [];
    try {
      const raw = localStorage.getItem(ANON_CART_KEY);
      return raw ? (JSON.parse(raw) as AnonymousCartItem[]) : [];
    } catch {
      return [];
    }
  },

  add(variantId: string, quantity: number): void {
    const items = anonymousCart.read();
    const existing = items.find((item) => item.variant_id === variantId);
    if (existing) {
      existing.quantity += quantity;
    } else {
      items.push({ variant_id: variantId, quantity });
    }
    localStorage.setItem(ANON_CART_KEY, JSON.stringify(items));
  },

  clear(): void {
    localStorage.removeItem(ANON_CART_KEY);
  },

  count(): number {
    return anonymousCart.read().reduce((total, item) => total + item.quantity, 0);
  },
};
