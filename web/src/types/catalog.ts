/**
 * Tipos del catálogo, en espejo con los schemas del backend.
 *
 * Los importes viajan como cadena para no perder precisión al pasar por JSON,
 * donde `number` es de punto flotante (ADR-04).
 */

export type CoffeeState = "green" | "roasted" | "ground";
export type CoffeeProcess = "washed" | "natural" | "honey" | "anaerobic" | "other";
export type RoastLevel = "light" | "medium" | "medium_dark" | "dark";
export type GrindType = "whole_bean" | "coarse" | "medium" | "fine";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ProductImage {
  id: string;
  /** URL pública ya resuelta por el backend a partir de la clave S3. */
  image_key: string;
  alt_text: string | null;
  is_primary: boolean;
}

export interface ProductVariant {
  id: string;
  sku: string;
  weight_grams: string;
  grind: GrindType | null;
  price: string;
  wholesale_price: string | null;
  available_qty: number;
  is_active: boolean;
}

export interface CoffeeAttributes {
  variety: string | null;
  process: CoffeeProcess | null;
  roast: RoastLevel | null;
  altitude_masl: number | null;
  sensory_profile: string | null;
  tasting_notes: string[] | null;
  cupping_score: string | null;
  harvest_date: string | null;
  roast_date: string | null;
}

export interface ProducerSummary {
  id: string;
  brand_name: string | null;
  legal_name: string;
  type: "farmer" | "farm" | "cooperative" | "roaster";
  logo_url: string | null;
  municipality: string;
  department: string;
  rating_avg: string;
}

/** Producto tal como aparece en el listado del catálogo. */
export interface ProductListItem {
  id: string;
  slug: string;
  name: string;
  state: CoffeeState;
  base_price: string;
  currency: string;
  primary_image_url: string | null;
  producer: ProducerSummary;
  region: string | null;
  municipality: string | null;
  department: string | null;
  sensory_profile: string | null;
  cupping_score: string | null;
  rating_avg: string;
  rating_count: number;
  is_available: boolean;
}

/**
 * Origen del café.
 *
 * Solo expone la ubicación aproximada: la coordenada exacta de la finca no
 * sale del servidor (ADR-08).
 */
export interface FarmSummary {
  name: string;
  village: string | null;
  altitude_min_masl: number | null;
  altitude_max_masl: number | null;
  approx_lat: string | null;
  approx_lng: string | null;
  environmental_practices: string | null;
}

/** Producto completo, con toda la trazabilidad de la ficha. */
export interface ProductDetail extends ProductListItem {
  description: string;
  images: ProductImage[];
  variants: ProductVariant[];
  attributes: CoffeeAttributes;
  certifications: Array<{ code: string; name: string }>;
  farm: FarmSummary | null;
  dispatch_days: number;
  storage_conditions: string | null;
  allows_samples: boolean;
}

export interface CatalogFilters {
  q?: string;
  department?: string;
  municipality?: string;
  region?: string;
  variety?: string;
  process?: CoffeeProcess;
  roast?: RoastLevel;
  state?: CoffeeState;
  certification?: string;
  min_price?: number;
  max_price?: number;
  min_score?: number;
  sort?: "price_asc" | "price_desc" | "rating" | "score" | "popular" | "newest";
  page?: number;
  page_size?: number;
}

/** Etiquetas en español para los valores del dominio. */
export const COFFEE_STATE_LABELS: Record<CoffeeState, string> = {
  green: "Verde",
  roasted: "Tostado",
  ground: "Molido",
};

export const PROCESS_LABELS: Record<CoffeeProcess, string> = {
  washed: "Lavado",
  natural: "Natural",
  honey: "Honey",
  anaerobic: "Anaeróbico",
  other: "Otro",
};

export const ROAST_LABELS: Record<RoastLevel, string> = {
  light: "Tueste claro",
  medium: "Tueste medio",
  medium_dark: "Tueste medio-oscuro",
  dark: "Tueste oscuro",
};

export const GRIND_LABELS: Record<GrindType, string> = {
  whole_bean: "Grano entero",
  coarse: "Molienda gruesa",
  medium: "Molienda media",
  fine: "Molienda fina",
};

export const PRODUCER_TYPE_LABELS: Record<ProducerSummary["type"], string> = {
  farmer: "Caficultor",
  farm: "Finca",
  cooperative: "Cooperativa",
  roaster: "Tostador",
};
