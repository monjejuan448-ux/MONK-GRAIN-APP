import { describe, expect, it } from "vitest";

import { moistureQuality, yieldFactorQuality } from "@/types/catalog";

/**
 * La lectura del análisis para quien no viene del sector.
 *
 * Un «91,50» no le dice nada a alguien que no sabe que 94 es el estándar de la
 * Federación. Estas dos funciones son las que traducen el número a una decisión,
 * y los cortes siguen la práctica comercial colombiana: por debajo de 90 se paga
 * sobreprecio, y por encima del 12 % de humedad hay riesgo de hongos.
 */

describe("yieldFactorQuality", () => {
  it("llama excepcional a lo que rinde muy por encima del estándar", () => {
    expect(yieldFactorQuality("86.00")?.label).toBe("Excepcional");
    expect(yieldFactorQuality("89")?.label).toBe("Excepcional");
  });

  it("llama de exportación a lo que está por debajo del estándar de 94", () => {
    expect(yieldFactorQuality("90")?.label).toBe("De exportación");
    expect(yieldFactorQuality("92.00")?.label).toBe("De exportación");
  });

  it("llama estándar al rango de la compra corriente", () => {
    expect(yieldFactorQuality("94.00")?.label).toBe("Estándar");
    expect(yieldFactorQuality("96")?.label).toBe("Estándar");
  });

  it("advierte cuando el rendimiento es bajo", () => {
    expect(yieldFactorQuality("97")?.label).toBe("Bajo rendimiento");
    expect(yieldFactorQuality("110")?.label).toBe("Bajo rendimiento");
  });

  it("respeta que menos es mejor", () => {
    // Es la inversión que más se presta a equivocarse: un factor más bajo debe
    // resultar en una etiqueta mejor, nunca al revés.
    const mejor = yieldFactorQuality("86.00");
    const peor = yieldFactorQuality("98.00");
    expect(mejor?.variant).toBe("success");
    expect(peor?.variant).toBe("warning");
  });

  it("no inventa una lectura cuando el lote no declaró su factor", () => {
    expect(yieldFactorQuality(null)).toBeNull();
    expect(yieldFactorQuality("no es un número")).toBeNull();
  });

  it("explica qué significa, no solo cómo se llama", () => {
    expect(yieldFactorQuality("94")?.hint).toBeTruthy();
    expect(yieldFactorQuality("86")?.hint).toContain("sobreprecio");
  });
});

describe("moistureQuality", () => {
  it("considera en rango el 10 % a 12 %", () => {
    expect(moistureQuality("10.00")?.label).toBe("En rango");
    expect(moistureQuality("11.50")?.label).toBe("En rango");
    expect(moistureQuality("12")?.label).toBe("En rango");
  });

  it("advierte por debajo del 10 %, donde el grano se quiebra en la trilla", () => {
    const seco = moistureQuality("9.50");
    expect(seco?.label).toBe("Muy seco");
    expect(seco?.variant).toBe("warning");
  });

  it("advierte por encima del 12 %, donde hay riesgo de hongos", () => {
    const humedo = moistureQuality("12.80");
    expect(humedo?.label).toBe("Húmedo");
    expect(humedo?.variant).toBe("warning");
    expect(humedo?.hint).toContain("rechazo");
  });

  it("no inventa una lectura sin el dato", () => {
    expect(moistureQuality(null)).toBeNull();
  });
});
