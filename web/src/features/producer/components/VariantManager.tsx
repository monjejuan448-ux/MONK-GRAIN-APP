"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  PRESENTATION_SUGGESTIONS,
  producerCatalogApi,
  type ProducerProduct,
} from "@/features/producer/api";
import { ApiError } from "@/lib/api";
import { formatKilos, formatPricePerKilo } from "@/lib/format";

interface VariantManagerProps {
  token: string;
  product: ProducerProduct;
  onChange: (product: ProducerProduct) => void;
}

const EMPTY = {
  // `?? ""` porque el acceso por índice a un arreglo puede ser `undefined` con
  // `noUncheckedIndexedAccess`, aunque aquí la sugerencia exista siempre.
  presentation: PRESENTATION_SUGGESTIONS[0] ?? "",
  // Una carga, la unidad en la que se habla del café en Colombia.
  min_qty_kg: "125",
  price: "",
  stock: "0",
};

export function VariantManager({ token, product, onChange }: VariantManagerProps) {
  const [draft, setDraft] = useState(EMPTY);
  const [isSaving, setIsSaving] = useState(false);

  async function add() {
    if (!draft.price || Number(draft.price) <= 0) {
      toast.error("Indica el precio por kilo de esta oferta.");
      return;
    }
    if (!draft.presentation.trim()) {
      toast.error("Escribe cómo entregas el lote.");
      return;
    }

    const minKg = Number(draft.min_qty_kg) || 1;
    const stockKg = Number(draft.stock) || 0;
    // El servidor también lo rechaza; avisarlo aquí ahorra el viaje y explica el
    // motivo en el sitio donde se corrige.
    if (stockKg > 0 && minKg > stockKg) {
      toast.error(
        `El mínimo (${minKg} kg) no puede superar los kilos disponibles (${stockKg} kg).`,
      );
      return;
    }

    setIsSaving(true);
    try {
      onChange(
        await producerCatalogApi.addVariant(token, product.id, {
          presentation: draft.presentation.trim(),
          min_qty_kg: minKg,
          price: draft.price,
          stock_qty: stockKg,
          // Aviso de existencias bajas cuando ya no alcanza para dos compras
          // del mínimo.
          low_stock_threshold: minKg * 2,
          is_active: true,
        }),
      );
      setDraft(EMPTY);
      toast.success("Oferta agregada.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "No pudimos agregarla.");
    } finally {
      setIsSaving(false);
    }
  }

  async function remove(variantId: string) {
    try {
      onChange(await producerCatalogApi.deleteVariant(token, product.id, variantId));
      toast.success("Oferta retirada.");
    } catch (error) {
      // El servidor la rechaza si tiene kilos comprometidos en pedidos.
      toast.error(error instanceof ApiError ? error.message : "No pudimos retirarla.");
    }
  }

  return (
    <section aria-labelledby="presentaciones-titulo" className="space-y-4">
      <div>
        <h2 id="presentaciones-titulo" className="font-display text-lg font-semibold">
          Cómo vendes este lote
        </h2>
        <p className="text-sm text-muted-foreground">
          Cada oferta tiene su propio precio por kilo, su mínimo de compra y sus kilos
          disponibles. Puedes publicar varias: a granel más barato, empacado más caro.
        </p>
      </div>

      {product.variants.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <caption className="sr-only">Ofertas a la venta de {product.name}</caption>
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th scope="col" className="py-2 font-medium">
                  Entrega y mínimo
                </th>
                <th scope="col" className="py-2 font-medium">
                  Precio por kilo
                </th>
                <th scope="col" className="py-2 font-medium">
                  Kilos disponibles
                </th>
                <th scope="col" className="py-2 font-medium">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {product.variants.map((variant) => (
                <tr key={variant.id} className="border-b border-border/60">
                  <td className="py-3">
                    <span className="font-medium">{variant.label}</span>
                    <span className="block text-xs text-muted-foreground">
                      {variant.sku}
                    </span>
                  </td>
                  <td className="py-3">{formatPricePerKilo(variant.price)}</td>
                  <td className="py-3">
                    {formatKilos(variant.stock_qty - variant.reserved_qty)}
                    {variant.reserved_qty > 0 && (
                      <Badge variant="outline" className="ml-2">
                        {formatKilos(variant.reserved_qty)} reservados
                      </Badge>
                    )}
                  </td>
                  <td className="py-3 text-right">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => remove(variant.id)}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                      <span className="sr-only">Retirar {variant.label}</span>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid gap-3 rounded-md border border-dashed border-border p-4 sm:grid-cols-4">
        <div className="sm:col-span-2">
          <label htmlFor="entrega" className="mb-1.5 block text-sm font-medium">
            Cómo lo entregas
          </label>
          <Input
            id="entrega"
            list="presentation-suggestions"
            value={draft.presentation}
            onChange={(event) => setDraft({ ...draft, presentation: event.target.value })}
          />
          {/* Sugerencias, no lista cerrada: el empaque del pergamino no está
              normalizado y cada finca lo entrega a su manera. */}
          <datalist id="presentation-suggestions">
            {PRESENTATION_SUGGESTIONS.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </div>

        <div>
          <label htmlFor="minimo" className="mb-1.5 block text-sm font-medium">
            Mínimo (kg)
          </label>
          <Input
            id="minimo"
            type="number"
            min={1}
            step={1}
            value={draft.min_qty_kg}
            onChange={(event) => setDraft({ ...draft, min_qty_kg: event.target.value })}
          />
          <p className="mt-1.5 text-xs text-muted-foreground">125 kg = 1 carga</p>
        </div>

        <div>
          <label htmlFor="precio" className="mb-1.5 block text-sm font-medium">
            Precio por kilo
          </label>
          <Input
            id="precio"
            type="number"
            min={1}
            step={100}
            value={draft.price}
            onChange={(event) => setDraft({ ...draft, price: event.target.value })}
          />
        </div>

        <div>
          <label htmlFor="stock" className="mb-1.5 block text-sm font-medium">
            Kilos disponibles
          </label>
          <Input
            id="stock"
            type="number"
            min={0}
            value={draft.stock}
            onChange={(event) => setDraft({ ...draft, stock: event.target.value })}
          />
        </div>

        <div className="self-end sm:col-span-3">
          <Button
            type="button"
            variant="outline"
            onClick={add}
            disabled={isSaving}
            aria-busy={isSaving}
          >
            <Plus className="mr-1.5 size-4" aria-hidden="true" />
            {isSaving ? "Agregando…" : "Agregar oferta"}
          </Button>
        </div>
      </div>
    </section>
  );
}
