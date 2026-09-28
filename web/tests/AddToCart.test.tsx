import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AddToCart } from "@/features/catalog/components/AddToCart";
import type { ProductVariant } from "@/types/catalog";

/**
 * La compra de kilos de un lote.
 *
 * Es el componente donde el mínimo de compra se traduce en lo que el comprador
 * puede hacer, y donde un error se paga en pesos: el total que se muestra es el
 * que va a pagar.
 */

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const addItem = vi.fn();
vi.mock("@/features/cart/api", () => ({
  cartApi: {
    addItem: (...args: unknown[]) => addItem(...args),
  },
}));

vi.mock("@/lib/session", () => ({
  session: { getAccessToken: () => "token-de-prueba" },
  anonymousCart: { add: vi.fn() },
}));

function variant(overrides: Partial<ProductVariant> = {}): ProductVariant {
  return {
    id: "var-1",
    sku: "PERGAMINO-125KG",
    presentation: "A granel, en costal de fique",
    min_qty_kg: 125,
    price: "22000",
    wholesale_price: null,
    available_qty: 1250,
    is_active: true,
    ...overrides,
  };
}

describe("AddToCart", () => {
  beforeEach(() => {
    addItem.mockReset();
    addItem.mockResolvedValue(undefined);
  });

  it("arranca en el mínimo del lote, no en un kilo", async () => {
    // Arrancar en 1 kg obligaría a corregirlo siempre y dejaría que el servidor
    // rechace lo que la interfaz propuso.
    render(<AddToCart variants={[variant()]} productName="Pergamino de Prueba" />);

    const cantidad = screen.getByLabelText(/cantidad en kilos/i);
    expect(cantidad).toHaveValue(125);
  });

  it("muestra el precio por kilo y el mínimo en la oferta", () => {
    render(<AddToCart variants={[variant()]} productName="Pergamino de Prueba" />);

    // El precio sale dos veces —en el botón de la oferta y en el resumen del
    // total—, así que se consulta el botón, que es lo que elige el comprador.
    const oferta = screen.getByRole("button", { name: /a granel, en costal de fique/i });
    expect(oferta).toHaveTextContent("22.000");
    expect(oferta).toHaveTextContent(/desde 125 kg/i);
  });

  it("calcula el total como kilos por precio del kilo", () => {
    render(<AddToCart variants={[variant()]} productName="Pergamino de Prueba" />);

    // 125 × 22.000 = 2.750.000, el precio de una carga.
    expect(screen.getByText(/2\.750\.000/)).toBeInTheDocument();
  });

  it("no deja bajar del mínimo", () => {
    render(<AddToCart variants={[variant()]} productName="Pergamino de Prueba" />);
    const cantidad = screen.getByLabelText(/cantidad en kilos/i);

    // Se cambia el valor de una vez y no letra por letra: el campo está
    // controlado y acota en cada pulsación, así que escribir «10» produciría
    // estados intermedios que no representan lo que el comprador hizo.
    fireEvent.change(cantidad, { target: { value: "10" } });

    // La interfaz acota al mínimo en lugar de dejar que el servidor lo rechace.
    expect(cantidad).toHaveValue(125);
  });

  it("no deja pasar de los kilos disponibles", () => {
    render(
      <AddToCart
        variants={[variant({ available_qty: 300 })]}
        productName="Pergamino de Prueba"
      />,
    );
    const cantidad = screen.getByLabelText(/cantidad en kilos/i);

    fireEvent.change(cantidad, { target: { value: "5000" } });

    expect(cantidad).toHaveValue(300);
  });

  it("avanza de carga en carga cuando el mínimo es una carga", () => {
    // De kilo en kilo harían falta 125 clics para llegar a la siguiente cantidad
    // que el vendedor acepta.
    render(<AddToCart variants={[variant()]} productName="Pergamino de Prueba" />);

    expect(screen.getByLabelText(/cantidad en kilos/i)).toHaveAttribute("step", "125");
  });

  it("agrega los kilos elegidos al carrito", async () => {
    const user = userEvent.setup();
    render(<AddToCart variants={[variant()]} productName="Pergamino de Prueba" />);

    await user.click(screen.getByRole("button", { name: /agregar al carrito/i }));

    expect(addItem).toHaveBeenCalledWith("token-de-prueba", "var-1", 125);
  });

  it("marca el lote agotado y no deja comprarlo", () => {
    render(
      <AddToCart
        variants={[variant({ available_qty: 0 })]}
        productName="Pergamino de Prueba"
      />,
    );

    // «agotado» aparece en el botón de la oferta y en el de compra; el que
    // importa es el segundo, que debe quedar deshabilitado.
    const comprar = screen.getByRole("button", { name: "Agotado" });
    expect(comprar).toBeDisabled();
  });

  it("explica el remanente que no alcanza el mínimo, en vez de fallar", () => {
    // Un lote puede quedar así al venderse parte de sus kilos: quedan 80 de un
    // lote que se vende desde 125.
    render(
      <AddToCart
        variants={[variant({ available_qty: 80 })]}
        productName="Pergamino de Prueba"
      />,
    );

    expect(screen.getByText(/por debajo del mínimo/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /no alcanza el mínimo/i })).toBeDisabled();
  });

  it("al cambiar de oferta ajusta la cantidad al mínimo de la nueva", async () => {
    const user = userEvent.setup();
    render(
      <AddToCart
        variants={[
          variant(),
          variant({
            id: "var-2",
            presentation: "Bultos de 70 kg",
            min_qty_kg: 700,
            price: "21000",
            available_qty: 1400,
          }),
        ]}
        productName="Pergamino de Prueba"
      />,
    );

    await user.click(screen.getByRole("button", { name: /bultos de 70 kg/i }));

    expect(screen.getByLabelText(/cantidad en kilos/i)).toHaveValue(700);
  });

  it("avisa cuando el lote no tiene ninguna oferta activa", () => {
    render(<AddToCart variants={[]} productName="Pergamino de Prueba" />);

    expect(screen.getByText(/no tiene ofertas disponibles/i)).toBeInTheDocument();
  });
});
