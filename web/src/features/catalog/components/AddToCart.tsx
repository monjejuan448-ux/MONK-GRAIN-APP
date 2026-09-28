"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Check, ShoppingCart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cartApi } from "@/features/cart/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatWeight } from "@/lib/format";
import { anonymousCart, session } from "@/lib/session";
import { cn } from "@/lib/utils";
import { GRIND_LABELS, type ProductVariant } from "@/types/catalog";

interface AddToCartProps {
  variants: ProductVariant[];
  productName: string;
}

export function AddToCart({ variants, productName }: AddToCartProps) {
  const router = useRouter();
  const available = variants.filter((variant) => variant.is_active);

  const [selectedId, setSelectedId] = useState(
    available.find((variant) => variant.available_qty > 0)?.id ?? available[0]?.id ?? "",
  );
  const [quantity, setQuantity] = useState(1);
  const [status, setStatus] = useState<"idle" | "loading" | "added">("idle");
  const [error, setError] = useState<string | null>(null);

  const selected = available.find((variant) => variant.id === selectedId);
  const maxQuantity = selected?.available_qty ?? 0;
  const isOutOfStock = maxQuantity === 0;

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
          : "No pudimos agregar el producto. Inténtalo de nuevo.",
      );
    }
  }

  if (available.length === 0) {
    return (
      <p className="rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
        Este café no tiene presentaciones disponibles por ahora.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <fieldset>
        <legend className="mb-2 text-sm font-semibold">Presentación</legend>
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
                  setQuantity(1);
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
                <span className="block font-medium">
                  {formatWeight(variant.weight_grams)}
                  {variant.grind && (
                    <span className="font-normal text-muted-foreground">
                      {" · "}
                      {GRIND_LABELS[variant.grind]}
                    </span>
                  )}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {formatCurrency(variant.price)}
                  {soldOut && " · agotado"}
                </span>
              </button>
            );
          })}
        </div>
      </fieldset>

      {selected && !isOutOfStock && (
        <div className="flex items-end gap-4">
          <div>
            <label htmlFor="quantity" className="mb-1.5 block text-sm font-semibold">
              Cantidad
            </label>
            <input
              id="quantity"
              type="number"
              min={1}
              max={maxQuantity}
              value={quantity}
              onChange={(event) => {
                const value = Number(event.target.value);
                setQuantity(Math.min(Math.max(1, value), maxQuantity));
              }}
              className="h-11 w-24 rounded-md border border-input bg-background px-3 text-sm"
            />
          </div>

          <p className="pb-3 text-sm text-muted-foreground">
            {maxQuantity <= 5
              ? `¡Solo quedan ${maxQuantity}!`
              : `${maxQuantity} disponibles`}
          </p>
        </div>
      )}

      {selected && (
        <div className="rounded-lg bg-muted/60 p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-muted-foreground">Total</span>
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
        disabled={isOutOfStock || status === "loading"}
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
        ) : (
          <>
            <ShoppingCart aria-hidden="true" />
            Agregar al carrito
          </>
        )}
      </Button>

      <p className="sr-only" role="status">
        {status === "added" ? `${productName} agregado al carrito` : ""}
      </p>
    </div>
  );
}
