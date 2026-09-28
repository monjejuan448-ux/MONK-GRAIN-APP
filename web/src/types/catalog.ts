/**
 * Tipos del catálogo, en espejo con los schemas del backend.
 *
 * Los importes viajan como cadena para no perder precisión al pasar por JSON,
 * donde `number` es de punto flotante (ADR-04).
 *
 * MONK GRAIN comercia un solo producto: **pergamino seco**. Todos los precios
 * son por kilogramo y todas las cantidades, kilos.
 */

export type CoffeeState = "pergamino";
export type CoffeeProcess = "washed" | "natural" | "honey" | "anaerobic" | "other";

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

/** Oferta comprable de un lote. `price` es el precio de un kilo. */
export interface ProductVariant {
  id: string;
  sku: string;
  presentation: string;
  min_qty_kg: number;
  price: string;
  wholesale_price: string | null;
  /** Kilos disponibles. */
  available_qty: number;
  is_active: boolean;
}

/** Ficha técnica del lote: origen, análisis del pergamino y trazabilidad. */
export interface CoffeeAttributes {
  variety: string | null;
  process: CoffeeProcess | null;
  altitude_masl: number | null;
  harvest_date: string | null;

  /**
   * Factor de rendimiento: kilos de pergamino que hay que trillar para obtener
   * un saco de 70 kg de café excelso. **Más bajo es mejor** y el estándar de la
   * Federación es 94.
   */
  yield_factor: string | null;
  moisture_pct: string | null;
  healthy_bean_pct: string | null;
  pasilla_pct: string | null;
  borer_damage_pct: string | null;
  /** Mallas en las que se retiene el grano, de la 14 a la 20. */
  screen_sizes: number[] | null;

  lot_code: string | null;
  sica_code: string | null;
  drying_method: string | null;
  notes: string | null;
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

/** Lote tal como aparece en el listado del catálogo. */
export interface ProductListItem {
  id: string;
  slug: string;
  name: string;
  state: CoffeeState;
  /** Precio por kilogramo, «desde». */
  base_price: string;
  currency: string;
  primary_image_url: string | null;
  producer: ProducerSummary;
  region: string | null;
  municipality: string | null;
  department: string | null;
  yield_factor: string | null;
  moisture_pct: string | null;
  available_kg: number;
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

/** Lote completo, con toda la trazabilidad de la ficha. */
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
  certification?: string;
  /** Precios por kilogramo. */
  min_price?: number;
  max_price?: number;
  /** Techo de factor que el comprador acepta: menos es mejor café. */
  max_yield_factor?: number;
  max_moisture_pct?: number;
  min_available_kg?: number;
  sort?: "price_asc" | "price_desc" | "rating" | "yield_factor" | "popular" | "newest";
  page?: number;
  page_size?: number;
}

/** Etiquetas en español para los valores del dominio. */
export const COFFEE_STATE_LABELS: Record<CoffeeState, string> = {
  pergamino: "Pergamino seco",
};

export const PROCESS_LABELS: Record<CoffeeProcess, string> = {
  washed: "Lavado",
  natural: "Natural",
  honey: "Honey",
  anaerobic: "Anaeróbico",
  other: "Otro",
};

export const PRODUCER_TYPE_LABELS: Record<ProducerSummary["type"], string> = {
  farmer: "Caficultor",
  farm: "Finca",
  cooperative: "Cooperativa",
  roaster: "Tostador",
};

/**
 * Lectura del factor de rendimiento para quien no viene del sector.
 *
 * Los cortes siguen la práctica comercial colombiana: 94 es el estándar de la
 * Federación, y por debajo de 90 se paga sobreprecio.
 */
export function yieldFactorQuality(factor: string | null): {
  label: string;
  hint: string;
  variant: "success" | "primary" | "default" | "warning";
} | null {
  if (factor === null) return null;
  const value = Number(factor);
  if (Number.isNaN(value)) return null;

  if (value <= 89) {
    return {
      label: "Excepcional",
      hint: "Rinde mucho más que el estándar: se paga sobreprecio.",
      variant: "success",
    };
  }
  if (value <= 92) {
    return {
      label: "De exportación",
      hint: "Por debajo del estándar de 94: apto para trilla de excelso.",
      variant: "primary",
    };
  }
  if (value <= 96) {
    return {
      label: "Estándar",
      hint: "En el rango de la compra corriente.",
      variant: "default",
    };
  }
  return {
    label: "Bajo rendimiento",
    hint: "Hay que trillar más pergamino para el mismo excelso.",
    variant: "warning",
  };
}

/** Lectura de la humedad, que decide si el lote se puede almacenar. */
export function moistureQuality(moisture: string | null): {
  label: string;
  hint: string;
  variant: "success" | "default" | "warning";
} | null {
  if (moisture === null) return null;
  const value = Number(moisture);
  if (Number.isNaN(value)) return null;

  if (value < 10) {
    return {
      label: "Muy seco",
      hint: "Por debajo del 10 % el grano se quiebra en la trilla.",
      variant: "warning",
    };
  }
  if (value <= 12) {
    return {
      label: "En rango",
      hint: "Entre 10 % y 12 %, el rango seguro.",
      variant: "success",
    };
  }
  return {
    label: "Húmedo",
    hint: "Por encima del 12 % hay riesgo de hongos: causal de rechazo.",
    variant: "warning",
  };
}
