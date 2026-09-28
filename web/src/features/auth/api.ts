import { api } from "@/lib/api";

/** Llamadas al módulo de autenticación del backend. */

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  avatar_key: string | null;
  status: "pending_verification" | "active" | "suspended";
  locale: string;
  email_notifications_enabled: boolean;
  roles: Array<{ code: string; name: string }>;
  permissions: string[];
  created_at: string;
}

export const authApi = {
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    phone?: string | null;
    data_consent: boolean;
  }) => api.post<{ message: string }>("/auth/register", data),

  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>("/auth/login", data),

  logout: (refreshToken: string) =>
    api.post<{ message: string }>("/auth/logout", { refresh_token: refreshToken }),

  refresh: (refreshToken: string) =>
    api.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken }),

  verifyEmail: (token: string) =>
    api.post<{ message: string }>("/auth/verify-email", { token }),

  resendVerification: (email: string) =>
    api.post<{ message: string }>("/auth/resend-verification", { email }),

  requestPasswordReset: (email: string) =>
    api.post<{ message: string }>("/auth/password-reset", { email }),

  confirmPasswordReset: (token: string, password: string) =>
    api.post<{ message: string }>("/auth/password-reset/confirm", { token, password }),

  me: (token: string) => api.get<CurrentUser>("/auth/me", { token }),

  changePassword: (token: string, currentPassword: string, password: string) =>
    api.post<{ message: string }>(
      "/auth/change-password",
      { current_password: currentPassword, password },
      { token },
    ),
};
