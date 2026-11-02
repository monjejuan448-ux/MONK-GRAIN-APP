import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CoverageBar } from "@/features/trading/components/CoverageBar";
import { OfferResponse } from "@/features/trading/components/OfferResponse";
import { YieldFactorReading } from "@/features/trading/components/YieldFactorReading";

/**
 * Los componentes del mercado de dos sentidos.
 *
 * Se consulta por lo que el usuario percibe —texto accesible, atributos de
 * accesibilidad— y no por la estructura interna que React produjo: un cambio
 * de maquetación no debe romper una prueba que verifica una regla del negocio.
 */

describe("CoverageBar", () => {
  it("muestra los kilos y el porcentaje juntos", () => {
    // El porcentaje solo engaña: «80 %» de una solicitud pequeña puede ser
    // menos café que el 20 % de una grande.
    render(<CoverageBar wantedKg={1250} coveredKg={1000} remainingKg={250} />);

    expect(screen.getByText(/1\.000 kg.*de.*1\.250 kg/)).toBeInTheDocument();
    expect(screen.getByText("80 %")).toBeInTheDocument();
  });

  it("dice cuántos kilos faltan mientras no esté cubierta", () => {
    render(<CoverageBar wantedKg={1250} coveredKg={250} remainingKg={1000} />);

    expect(screen.getByText(/Faltan.*1\.000 kg/)).toBeInTheDocument();
  });

  it("deja de pedir kilos cuando ya está cubierta", () => {
    render(<CoverageBar wantedKg={1250} coveredKg={1250} remainingKg={0} />);

    expect(screen.queryByText(/Faltan/)).not.toBeInTheDocument();
    expect(screen.getByText("100 %")).toBeInTheDocument();
  });

  it("es legible para quien navega por voz", () => {
    // Un lector de pantalla no ve el ancho de un div: sin estos atributos la
    // barra sencillamente no existe.
    render(<CoverageBar wantedKg={1250} coveredKg={500} remainingKg={750} />);

    const barra = screen.getByRole("progressbar");
    expect(barra).toHaveAttribute("aria-valuenow", "500");
    expect(barra).toHaveAttribute("aria-valuemax", "1250");
    expect(barra).toHaveAccessibleName(/40 por ciento/);
  });

  it("no divide por cero cuando no se pidió nada", () => {
    render(<CoverageBar wantedKg={0} coveredKg={0} remainingKg={0} />);

    expect(screen.getByText("0 %")).toBeInTheDocument();
  });
});

describe("YieldFactorReading", () => {
  it("nunca muestra el número solo", () => {
    // Un «88.50» no dice nada a quien no sabe que el estándar es 94.
    render(<YieldFactorReading factor="88.50" />);

    expect(screen.getByText("88.50")).toBeInTheDocument();
    expect(screen.getByText("Excepcional")).toBeInTheDocument();
  });

  it("dice «o mejor» cuando el número es un techo y no una medida", () => {
    render(<YieldFactorReading factor="92.00" asCeiling />);

    expect(screen.getByText(/o mejor/)).toBeInTheDocument();
  });

  it("dice que no hay requisito cuando el comprador no puso ninguno", () => {
    render(<YieldFactorReading factor={null} />);

    expect(screen.getByText("Cualquier factor")).toBeInTheDocument();
  });
});

describe("OfferResponse", () => {
  it("muestra el motivo del rechazo completo", () => {
    // Es lo que le dice al caficultor qué ajustar en la siguiente postura.
    const motivo =
      "El factor de 96 queda por encima del 92 que necesitamos para trilla de excelso.";
    render(<OfferResponse status="rejected" responseNote={motivo} />);

    expect(screen.getByText(motivo)).toBeInTheDocument();
  });

  it("dice con palabras que no hubo motivo, en lugar de dejar un hueco", () => {
    // Un recuadro vacío parece un fallo de la página.
    render(<OfferResponse status="rejected" responseNote={null} />);

    expect(screen.getByText(/no explicó el motivo/)).toBeInTheDocument();
  });

  it("no habla de motivos cuando la postura fue aceptada", () => {
    render(<OfferResponse status="accepted" responseNote={null} />);

    expect(screen.getByText("Aceptada")).toBeInTheDocument();
    expect(screen.queryByText(/motivo/)).not.toBeInTheDocument();
  });

  it("distingue esperar de haber sido rechazada", () => {
    render(<OfferResponse status="pending" responseNote={null} />);

    expect(screen.getByText("Esperando respuesta")).toBeInTheDocument();
  });
});
