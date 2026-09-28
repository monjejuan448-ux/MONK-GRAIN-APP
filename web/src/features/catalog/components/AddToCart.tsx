"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Check, ShoppingCart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cartApi } from "@/features/cart/api";
import { ApiError } from "@/lib/api";
import {
  formatCurrency,
  formatKilos,
  formatKilosWithCargas,
  formatPricePerKilo,
} from "@/lib/format";
import { anonymousCart, session } from "@/lib/session";
import { cn } from "@/lib/utils";
import type { ProductVariant } from "@/types/catalog";

/**
 * Compra de kilos de un lote de pergamino.
 *
 * La cantidad son kilogramos y el precio es por kilo, de modo que el total es
 * una multiplicación que el comprador puede rehacer de cabeza. Cada oferta trae
 * su mínimo de compra: el servidor lo hace cumplir, y aquí se arranca en él para
 * que nadie llegue al carrito a que lo rechacen.
 */

interface AddToCartProps {
  variants: ProductVariant[];
  productName: string;
}

/** Salto del control de cantidad, en kilos. Subir de kilo en kilo hasta 125
 *  sería inutilizable, así que el paso se ajusta al tamaño del mínimo. */
function stepFor(minKg: number): number {
  if (minKg >= 125) return 125; // de carga en carga
  if (minKg >= 70) return 70; // de bulto en bulto
  if (minKg >= 12) return minKg;
  return 1;
}

export function AddToCart({ variants, productName }: AddToCartProps) {
  const router = useRouter();
  const available = variants.filter((variant) => variant.is_active);

  const firstWithStock = available.find((variant) => variant.available_qty > 0);
  const [selectedId, setSelectedId] = useState(
    firstWithStock?.id ?? available[0]?.id ?? "",
  );
  const [quantity, setQuantity] = useState(
    firstWithStock?.min_qty_kg ?? available[0]?.min_qty_kg ?? 1,
  );
  const [status, setStatus] = useState<"idle" | "loading" | "added">("idle");
  const [error, setError] = useState<string | null>(null);

  const selected = available.find((variant) => variant.id === selectedId);
  const maxKg = selected?.available_qty ?? 0;
  const minKg = selected?.min_qty_kg ?? 1;
  const isOutOfStock = maxKg === 0;
  // Un lote cuyas existencias no alcanzan para el mínimo no es comprable. El
  // servidor lo impide al publicar, pero un lote puede quedar así al venderse
  // parte de sus kilos.
  const belowMinimum = !isOutOfStock && maxKg < minKg;

  async function handleAdd() {
    if (!selected) return;
    setStatus("loading");
    setError(null);

    const token = session.getAccessToken();

    try {
      if (token) {
        await cartApi.addItem(token, selected.id, quantity);
      } else {
        // Sin sesión el carrito vive en el navegador y se fusiona con el de la
        // cuenta al iniciar sesión, para no perder la selección (HU-CC-05, CA3).
        anonymousCart.add(selected.id, quantity);
      }
      setStatus("added");
      router.refresh();
      setTimeout(() => setStatus("idle"), 2500);
    } catch (requestError) {
      setStatus("idle");
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos agregar el lote. Inténtalo de nuevo.",
      );
    }
  }

  if (available.length === 0) {
    return (
      <p className="rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
        Este lote no tiene ofertas disponibles por ahora.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <fieldset>
        <legend className="mb-2 text-sm font-semibold">
          Cómo lo entrega el vendedor
        </legend>
        <div className="flex flex-wrap gap-2">
          {available.map((variant) => {
            const isSelected = variant.id === selectedId;
            const soldOut = variant.available_qty === 0;

            return (
              <button
                key={variant.id}
                type="button"
                onClick={() => {
                  setSelectedId(variant.id);
                  setQuantity(variant.min_qty_kg);
                }}
                aria-pressed={isSelected}
                className={cn(
                  "rounded-md border px-4 py-2.5 text-left text-sm transition-colors",
                  isSelected
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted",
                  soldOut && "opacity-60",
                )}
              >
                <span className="block font-medium">{variant.presentation}</span>
                <span className="block text-xs text-muted-foreground">
                  {formatPricePerKilo(variant.price)}
                  {variant.min_qty_kg > 1 &&
                    ` · desde ${formatKilos(variant.min_qty_kg)}`}
                  {soldOut && " · agotado"}
                </span>
              </button>
            );
          })}
        </div>
      </fieldset>

      {selected && !isOutOfStock && !belowMinimum && (
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="quantity" className="mb-1.5 block text-sm font-semibold">
              Cantidad en kilos
            </label>
            <input
              id="quantity"
              type="number"
              min={minKg}
              max={maxKg}
              step={stepFor(minKg)}
              value={quantity}
              onChange={(event) => {
                const value = Number(event.target.value);
                // Se acota al mínimo del lote y a los kilos disponibles: el
                // servidor rechazaría cualquier cosa fuera de ahí.
                setQuantity(Math.min(Math.max(minKg, value), maxKg));
              }}
              aria-describedby="quantity-hint"
              className="h-11 w-32 rounded-md border border-input bg-background px-3 text-sm"
            />
          </div>

          <p id="quantity-hint" className="pb-3 text-sm text-muted-foreground">
            {minKg > 1 && <>Desde {formatKilos(minKg)}. </>}
            Quedan {formatKilosWithCargas(maxKg)}.
          </p>
        </div>
      )}

      {belowMinimum && (
        <p className="rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
          Quedan {formatKilos(maxKg)}, por debajo del mínimo de {formatKilos(minKg)} que
          pide el vendedor. Escríbele si te interesa el remanente.
        </p>
      )}

      {selected && !isOutOfStock && !belowMinimum && (
        <div className="rounded-lg bg-muted/60 p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-muted-foreground">
              {formatKilos(quantity)} × {formatPricePerKilo(selected.price)}
            </span>
            <span className="font-display text-2xl font-bold">
              {formatCurrency(Number(selected.price) * quantity)}
            </span>
          </div>
        </div>
      )}

      {error && (
        <p
          className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      )}

      <Button
        onClick={handleAdd}
        disabled={isOutOfStock || belowMinimum || status === "loading"}
        isLoading={status === "loading"}
        size="lg"
        className="w-full"
      >
        {status === "added" ? (
          <>
            <Check aria-hidden="true" />
            Agregado al carrito
          </>
        ) : isOutOfStock ? (
          "Agotado"
        ) : belowMinimum ? (
          "No alcanza el mínimo"
        ) : (
          <>
            <ShoppingCart aria-hidden="true" />
            Agregar al carrito
          </>
        )}
      </Button>

      <p className="sr-only" role="status">
        {status === "added"
          ? `${formatKilos(quantity)} de ${productName} agregados al carrito`
          : ""}
      </p>
    </div>
  );
}
