/**
 * Cliente del catálogo propio del vendedor.
 *
 * Refleja los endpoints bajo `/producer/catalog` y `/producer/certifications`.
 * Todo lo que aquí se envía viaja con el token del productor: el servidor
 * comprueba en cada llamada que el café le pertenece.
 */

import { api, apiUpload } from "@/lib/api";
import type { Page } from "@/types/catalog";

export type ProductStatus =
  "draft" | "pending_review" | "published" | "unpublished" | "rejected";
export type CoffeeState = "pergamino";
export type CertStatus = "active" | "expiring" | "expired" | "revoked";

/** Ficha del lote: origen, análisis del pergamino y trazabilidad. */
export interface CoffeeAttributes {
  variety: string | null;
  process: string | null;
  altitude_masl: number | null;
  harvest_date: string | null;

  yield_factor: string | null;
  moisture_pct: string | null;
  healthy_bean_pct: string | null;
  pasilla_pct: string | null;
  borer_damage_pct: string | null;
  screen_sizes: number[] | null;

  lot_code: string | null;
  sica_code: string | null;
  drying_method: string | null;
  notes: string | null;
}

export interface ProductImage {
  id: string;
  image_url: string;
  alt_text: string | null;
  sort_order: number;
  is_primary: boolean;
}

export interface ProductVariant {
  id: string;
  sku: string;
  label: string;
  presentation: string;
  /** Mínimo de compra en kilos. */
  min_qty_kg: number;
  /** Precio de un kilogramo. */
  price: string;
  wholesale_price: string | null;
  is_active: boolean;
  stock_qty: number;
  reserved_qty: number;
}

export interface ProducerProduct {
  id: string;
  slug: string;
  name: string;
  description: string;
  state: CoffeeState;
  status: ProductStatus;
  base_price: string;
  wholesale_price: string | null;
  wholesale_min_qty: number | null;
  currency: string;
  dispatch_days: number;
  storage_conditions: string | null;
  allows_samples: boolean;
  images: ProductImage[];
  variants: ProductVariant[];
  attributes: CoffeeAttributes | null;
  /** Requisitos que faltan para publicar. Vacío significa que ya puede salir. */
  missing_to_publish: string[];
}

export interface ProductInput {
  name: string;
  description: string;
  state: CoffeeState;
  base_price: string;
  wholesale_price?: string | null;
  wholesale_min_qty?: number | null;
  dispatch_days: number;
  storage_conditions?: string | null;
  allows_samples: boolean;
  attributes: Partial<CoffeeAttributes>;
}

export interface VariantInput {
  presentation: string;
  min_qty_kg: number;
  /** Precio de un kilogramo. */
  price: string;
  wholesale_price?: string | null;
  /** Kilos disponibles. */
  stock_qty: number;
  low_stock_threshold: number;
  is_active: boolean;
}

export interface CertificationCatalogItem {
  id: number;
  code: string;
  name: string;
  issuing_body: string | null;
  description: string | null;
}

export interface ProducerCertification {
  id: string;
  certification_id: number;
  certification_code: string;
  certification_name: string;
  issuing_body: string | null;
  certificate_number: string | null;
  issued_at: string | null;
  expires_at: string | null;
  status: CertStatus;
  has_document: boolean;
  days_to_expiry: number | null;
}

/** `tone` usa las variantes reales de `Badge`; no existe una «danger». */
export type BadgeTone = "default" | "outline" | "success" | "warning" | "accent";

export const PRODUCT_STATUS_META: Record<
  ProductStatus,
  { label: string; tone: BadgeTone }
> = {
  draft: { label: "Borrador", tone: "outline" },
  pending_review: { label: "En revisión", tone: "warning" },
  published: { label: "Publicado", tone: "success" },
  unpublished: { label: "Retirado", tone: "outline" },
  rejected: { label: "Rechazado", tone: "warning" },
};

/**
 * Presentaciones frecuentes del pergamino, como sugerencia.
 *
 * No es un enum: el empaque del pergamino no está normalizado y el vendedor
 * escribe cómo entrega el suyo. Estas son las formas más comunes, para no
 * obligarle a redactarlo desde cero.
 */
export const PRESENTATION_SUGGESTIONS = [
  "A granel, en costal de fique",
  "Bultos de 70 kg",
  "Empacado en la finca",
  "En sacos de polipropileno",
];

/** Métodos de secado habituales en Colombia. */
export const DRYING_SUGGESTIONS = [
  "Marquesina",
  "Patio de cemento",
  "Camas africanas",
  "Secador mecánico Guardiola",
  "Silo con aire caliente",
];

export const PROCESS_OPTIONS = [
  { value: "washed", label: "Lavado" },
  { value: "natural", label: "Natural" },
  { value: "honey", label: "Honey" },
  { value: "anaerobic", label: "Anaeróbico" },
  { value: "other", label: "Otro" },
];

export const CERT_STATUS_META: Record<CertStatus, { label: string; tone: BadgeTone }> = {
  active: { label: "Vigente", tone: "success" },
  expiring: { label: "Por vencer", tone: "warning" },
  expired: { label: "Vencida", tone: "warning" },
  revoked: { label: "Revocada", tone: "outline" },
};

export const producerCatalogApi = {
  list: (token: string) => api.get<Page<ProducerProduct>>("/producer/catalog", { token }),

  get: (token: string, productId: string) =>
    api.get<ProducerProduct>(`/producer/catalog/${productId}`, { token }),

  create: (token: string, input: ProductInput) =>
    api.post<ProducerProduct>("/producer/catalog", input, { token }),

  update: (token: string, productId: string, input: ProductInput) =>
    api.put<ProducerProduct>(`/producer/catalog/${productId}`, input, { token }),

  publish: (token: string, productId: string) =>
    api.post<ProducerProduct>(`/producer/catalog/${productId}/publish`, undefined, {
      token,
    }),

  unpublish: (token: string, productId: string) =>
    api.post<ProducerProduct>(`/producer/catalog/${productId}/unpublish`, undefined, {
      token,
    }),

  uploadImage: (token: string, productId: string, file: File, altText: string) => {
    const form = new FormData();
    form.append("file", file);
    if (altText.trim()) form.append("alt_text", altText.trim());
    return apiUpload<ProducerProduct>(`/producer/catalog/${productId}/images`, form, {
      token,
    });
  },

  deleteImage: (token: string, productId: string, imageId: string) =>
    api.delete<ProducerProduct>(`/producer/catalog/${productId}/images/${imageId}`, {
      token,
    }),

  addVariant: (token: string, productId: string, input: VariantInput) =>
    api.post<ProducerProduct>(`/producer/catalog/${productId}/variants`, input, {
      token,
    }),

  updateVariant: (
    token: string,
    productId: string,
    variantId: string,
    input: VariantInput,
  ) =>
    api.put<ProducerProduct>(
      `/producer/catalog/${productId}/variants/${variantId}`,
      input,
      { token },
    ),

  deleteVariant: (token: string, productId: string, variantId: string) =>
    api.delete<ProducerProduct>(`/producer/catalog/${productId}/variants/${variantId}`, {
      token,
    }),

  productCertifications: (token: string, productId: string) =>
    api.get<CertificationCatalogItem[]>(`/producer/catalog/${productId}/certifications`, {
      token,
    }),

  attachCertification: (token: string, productId: string, certificationId: number) =>
    api.post<CertificationCatalogItem[]>(
      `/producer/catalog/${productId}/certifications/${certificationId}`,
      undefined,
      { token },
    ),

  detachCertification: (token: string, productId: string, certificationId: number) =>
    api.delete<CertificationCatalogItem[]>(
      `/producer/catalog/${productId}/certifications/${certificationId}`,
      { token },
    ),
};

export const certificationApi = {
  catalog: (token: string) =>
    api.get<CertificationCatalogItem[]>("/producer/certifications/catalog", { token }),

  mine: (token: string) =>
    api.get<ProducerCertification[]>("/producer/certifications", { token }),

  add: (
    token: string,
    input: {
      certification_id: number;
      certificate_number?: string;
      issued_at?: string;
      expires_at?: string;
      file?: File | null;
    },
  ) => {
    const form = new FormData();
    form.append("certification_id", String(input.certification_id));
    if (input.certificate_number)
      form.append("certificate_number", input.certificate_number);
    if (input.issued_at) form.append("issued_at", input.issued_at);
    if (input.expires_at) form.append("expires_at", input.expires_at);
    if (input.file) form.append("file", input.file);
    return apiUpload<ProducerCertification>("/producer/certifications", form, { token });
  },

  remove: (token: string, certificationId: string) =>
    api.delete<void>(`/producer/certifications/${certificationId}`, { token }),

  documentLink: (token: string, certificationId: string) =>
    api.get<{ url: string; expires_in_seconds: number }>(
      `/producer/certifications/${certificationId}/document`,
      { token },
    ),
};
