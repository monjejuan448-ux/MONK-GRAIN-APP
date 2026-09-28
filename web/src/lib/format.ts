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

/**
 * Formatea kilogramos de pergamino: "125 kg", "12.500 kg".
 *
 * No convierte a toneladas a propósito: el comercio de pergamino habla en kilos
 * y en cargas, y ver "12,5 t" obligaría al comprador a hacer la cuenta de vuelta
 * para compararlo con un precio por kilo.
 */
export function formatKilos(kilos: number | string): string {
  const value = typeof kilos === "string" ? Number.parseFloat(kilos) : kilos;
  if (!Number.isFinite(value)) return "—";

  const formatted = new Intl.NumberFormat(DEFAULT_LOCALE, {
    maximumFractionDigits: 2,
  }).format(value);
  return `${formatted} kg`;
}

/**
 * Expresa unos kilos en cargas cuando la cifra lo merece.
 *
 * La carga de 125 kg es la unidad en la que se habla del precio del café en
 * Colombia: "1.250 kg (10 cargas)" le dice a un caficultor algo que "1.250 kg"
 * por sí solo no le dice. Por debajo de una carga se omite, porque "0,4 cargas"
 * no es como nadie cuenta.
 */
const KILOS_PER_CARGA = 125;

export function formatKilosWithCargas(kilos: number | string): string {
  const value = typeof kilos === "string" ? Number.parseFloat(kilos) : kilos;
  if (!Number.isFinite(value)) return "—";

  const base = formatKilos(value);
  if (value < KILOS_PER_CARGA) return base;

  const cargas = value / KILOS_PER_CARGA;
  const formatted = new Intl.NumberFormat(DEFAULT_LOCALE, {
    maximumFractionDigits: cargas % 1 === 0 ? 0 : 1,
  }).format(cargas);
  return `${base} (${formatted} ${cargas === 1 ? "carga" : "cargas"})`;
}

/** Precio por kilogramo: "$22.000/kg". */
export function formatPricePerKilo(amount: number | string): string {
  return `${formatCurrency(amount)}/kg`;
}

/**
 * Factor de rendimiento con dos decimales: "91,50".
 *
 * Se muestran los decimales porque medio punto de factor mueve el precio de una
 * carga, y redondear a entero borraría esa diferencia.
 */
export function formatYieldFactor(factor: string | number | null | undefined): string {
  if (factor == null) return "—";
  const value = typeof factor === "string" ? Number.parseFloat(factor) : factor;
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/** Porcentaje del análisis físico: "11,00 %". */
export function formatPercent(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const parsed = typeof value === "string" ? Number.parseFloat(value) : value;
  if (!Number.isFinite(parsed)) return "—";
  return `${new Intl.NumberFormat(DEFAULT_LOCALE, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(parsed)} %`;
}

/** Granulometría: "Mallas 15, 16 y 17". */
export function formatScreenSizes(sizes: number[] | null | undefined): string {
  if (!sizes || sizes.length === 0) return "—";
  if (sizes.length === 1) return `Malla ${sizes[0]}`;
  const head = sizes.slice(0, -1).join(", ");
  return `Mallas ${head} y ${sizes[sizes.length - 1]}`;
}

/** Formatea la altitud sobre el nivel del mar: "1.750 m s. n. m.". */
export function formatAltitude(masl: number | null | undefined): string {
  if (masl == null) return "—";
  return `${new Intl.NumberFormat(DEFAULT_LOCALE).format(masl)} m s. n. m.`;
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
