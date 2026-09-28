/**
 * Formateo de moneda, fechas y magnitudes.
 *
 * La localización se resuelve por configuración y no está incrustada en los
 * componentes: una futura expansión a otro país no obliga a tocarlos (RNF-09).
 */

const DEFAULT_LOCALE = process.env.NEXT_PUBLIC_DEFAULT_LOCALE ?? "es-CO";
const DEFAULT_CURRENCY = "COP";

/**
 * Formatea un importe en pesos colombianos.
 *
 * El peso no usa decimales en la práctica comercial, así que se omiten. Los
 * importes llegan del backend como cadena para no perder precisión en el
 * tránsito por JSON, donde `number` es de punto flotante.
 */
export function formatCurrency(
  amount: number | string,
  options: { currency?: string; showDecimals?: boolean } = {},
): string {
  const { currency = DEFAULT_CURRENCY, showDecimals = false } = options;
  const value = typeof amount === "string" ? Number.parseFloat(amount) : amount;

  if (!Number.isFinite(value)) return "—";

  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    style: "currency",
    currency,
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  }).format(value);
}

/** Formatea una fecha en formato legible: "12 de agosto de 2026". */
export function formatDate(date: string | Date): string {
  const value = typeof date === "string" ? new Date(date) : date;
  if (Number.isNaN(value.getTime())) return "—";

  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(value);
}

/** Formatea una fecha corta: "12/08/2026". */
export function formatDateShort(date: string | Date): string {
  const value = typeof date === "string" ? new Date(date) : date;
  if (Number.isNaN(value.getTime())) return "—";

  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(value);
}

/** Convierte gramos a la unidad más legible: "250 g", "1 kg". */
export function formatWeight(grams: number | string): string {
  const value = typeof grams === "string" ? Number.parseFloat(grams) : grams;
  if (!Number.isFinite(value)) return "—";

  if (value >= 1000) {
    const kilos = value / 1000;
    const formatted = new Intl.NumberFormat(DEFAULT_LOCALE, {
      maximumFractionDigits: 2,
    }).format(kilos);
    return `${formatted} kg`;
  }

  return `${new Intl.NumberFormat(DEFAULT_LOCALE).format(value)} g`;
}

/** Formatea la altitud sobre el nivel del mar: "1.750 m s. n. m.". */
export function formatAltitude(masl: number | null | undefined): string {
  if (masl == null) return "—";
  return `${new Intl.NumberFormat(DEFAULT_LOCALE).format(masl)} m s. n. m.`;
}

/** Formatea el puntaje de catación con un decimal: "86,5". */
export function formatCuppingScore(score: number | string | null | undefined): string {
  if (score == null) return "—";
  const value = typeof score === "string" ? Number.parseFloat(score) : score;
  if (!Number.isFinite(value)) return "—";

  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(value);
}

/** Formatea una calificación promedio: "4,5". */
export function formatRating(rating: number | string | null | undefined): string {
  if (rating == null) return "—";
  const value = typeof rating === "string" ? Number.parseFloat(rating) : rating;
  if (!Number.isFinite(value)) return "—";

  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}
