import { api } from "@/lib/api";

/** Tipos y llamadas de la cuenta del comprador: direcciones y geografía. */

export interface Address {
  id: string;
  label: string | null;
  recipient_name: string;
  phone: string;
  street_address: string;
  neighborhood: string | null;
  notes: string | null;
  municipality_id: number;
  department_id: number;
  is_default: boolean;
}

/** Datos del formulario de dirección. El departamento no viaja: lo deriva el
 *  servidor del municipio, para que no pueda llegar una combinación imposible. */
export interface AddressInput {
  label?: string | null;
  recipient_name: string;
  phone: string;
  municipality_id: number;
  street_address: string;
  neighborhood?: string | null;
  notes?: string | null;
  is_default?: boolean;
}

export interface GeoItem {
  id: number;
  name: string;
  dane_code: string;
}

export const addressesApi = {
  list: (token: string) => api.get<Address[]>("/users/me/addresses", { token }),

  create: (token: string, data: AddressInput) =>
    api.post<Address>("/users/me/addresses", data, { token }),

  /** Actualización parcial: solo se envían los campos que cambiaron. */
  update: (token: string, addressId: string, data: Partial<AddressInput>) =>
    api.patch<Address>(`/users/me/addresses/${addressId}`, data, { token }),

  remove: (token: string, addressId: string) =>
    api.delete<{ message: string }>(`/users/me/addresses/${addressId}`, { token }),

  /** Marca una dirección como predeterminada; el servidor retira la anterior. */
  makeDefault: (token: string, addressId: string) =>
    api.patch<Address>(
      `/users/me/addresses/${addressId}`,
      { is_default: true },
      { token },
    ),
};

export interface Profile {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  email_notifications_enabled: boolean;
}

/** Campos del perfil que el titular puede corregir. El correo no está: para
 *  cambiarlo hay que volver a verificarlo, porque es la llave de la
 *  recuperación de contraseña. */
export interface ProfileInput {
  full_name?: string;
  phone?: string | null;
  email_notifications_enabled?: boolean;
}

export const profileApi = {
  update: (token: string, data: ProfileInput) =>
    api.patch<Profile>("/users/me", data, { token }),
};

export const geoApi = {
  departments: () => api.get<GeoItem[]>("/users/geo/departments"),
  municipalities: (departmentId: number) =>
    api.get<GeoItem[]>(`/users/geo/departments/${departmentId}/municipalities`),
};
