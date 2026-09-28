import { describe, expect, it } from "vitest";

import {
  formatKilos,
  formatKilosWithCargas,
  formatPercent,
  formatPricePerKilo,
  formatScreenSizes,
  formatYieldFactor,
} from "@/lib/format";

/**
 * El formateo del dominio de pergamino.
 *
 * Importa porque estas funciones son lo que el comprador lee para decidir una
 * compra de millones de pesos: un kilo mal escrito o un factor redondeado
 * cambian lo que entiende.
 */

describe("formatKilos", () => {
  it("escribe los kilos con separador de miles en español", () => {
    expect(formatKilos(1250)).toBe("1.250 kg");
  });

  it("acepta la cadena que llega del JSON", () => {
    // Los importes y cantidades viajan como cadena para no perder precisión.
    expect(formatKilos("625")).toBe("625 kg");
  });

  it("no convierte a toneladas", () => {
    // El comercio de pergamino habla en kilos: ver «12,5 t» obligaría a hacer la
    // cuenta de vuelta para comparar con un precio por kilo.
    expect(formatKilos(12500)).toBe("12.500 kg");
  });

  it("devuelve un guion ante un valor que no es número", () => {
    expect(formatKilos("no es un número")).toBe("—");
  });
});

describe("formatKilosWithCargas", () => {
  it("añade la lectura en cargas, que es la unidad del negocio", () => {
    expect(formatKilosWithCargas(1250)).toBe("1.250 kg (10 cargas)");
  });

  it("usa el singular con una sola carga", () => {
    expect(formatKilosWithCargas(125)).toBe("125 kg (1 carga)");
  });

  it("muestra un decimal cuando la división no es exacta", () => {
    expect(formatKilosWithCargas(375)).toBe("375 kg (3 cargas)");
    expect(formatKilosWithCargas(500)).toBe("500 kg (4 cargas)");
  });

  it("omite la conversión por debajo de una carga", () => {
    // «0,6 cargas» no es como nadie cuenta.
    expect(formatKilosWithCargas(80)).toBe("80 kg");
  });
});

describe("formatYieldFactor", () => {
  it("conserva los dos decimales", () => {
    // Medio punto de factor mueve el precio de una carga: redondear a entero
    // borraría esa diferencia.
    expect(formatYieldFactor("91.50")).toBe("91,50");
    expect(formatYieldFactor("94")).toBe("94,00");
  });

  it("devuelve un guion cuando el lote no lo declaró", () => {
    expect(formatYieldFactor(null)).toBe("—");
    expect(formatYieldFactor(undefined)).toBe("—");
  });
});

describe("formatPercent", () => {
  it("escribe el porcentaje con dos decimales y su espacio", () => {
    expect(formatPercent("11.00")).toBe("11,00 %");
    expect(formatPercent("97.5")).toBe("97,50 %");
  });

  it("devuelve un guion ante la ausencia del dato", () => {
    expect(formatPercent(null)).toBe("—");
  });
});

describe("formatPricePerKilo", () => {
  it("deja claro que el precio es por kilogramo", () => {
    expect(formatPricePerKilo("22000")).toContain("/kg");
    expect(formatPricePerKilo("22000")).toContain("22.000");
  });
});

describe("formatScreenSizes", () => {
  it("usa el singular con una sola malla", () => {
    expect(formatScreenSizes([16])).toBe("Malla 16");
  });

  it("enumera varias con «y» antes de la última", () => {
    expect(formatScreenSizes([15, 16, 17])).toBe("Mallas 15, 16 y 17");
    expect(formatScreenSizes([17, 18])).toBe("Mallas 17 y 18");
  });

  it("devuelve un guion cuando no hay granulometría declarada", () => {
    expect(formatScreenSizes(null)).toBe("—");
    expect(formatScreenSizes([])).toBe("—");
  });
});
