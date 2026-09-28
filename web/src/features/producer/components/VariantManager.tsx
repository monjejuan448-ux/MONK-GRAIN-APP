"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  GRIND_OPTIONS,
  producerCatalogApi,
  type GrindType,
  type ProducerProduct,
} from "@/features/producer/api";
import { ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

interface VariantManagerProps {
  token: string;
  product: ProducerProduct;
  onChange: (product: ProducerProduct) => void;
}

const EMPTY = {
  weight_grams: "250",
  grind: "whole_bean" as GrindType,
  price: "",
  stock: "0",
};

export function VariantManager({ token, product, onChange }: VariantManagerProps) {
  const [draft, setDraft] = useState(EMPTY);
  const [isSaving, setIsSaving] = useState(false);

  async function add() {
    if (!draft.price || Number(draft.price) <= 0) {
      toast.error("Indica el precio de esta presentación.");
      return;
    }

    setIsSaving(true);
    try {
      onChange(
        await producerCatalogApi.addVariant(token, product.id, {
          weight_grams: draft.weight_grams,
          grind: draft.grind,
          price: draft.price,
          stock_qty: Number(draft.stock) || 0,
          low_stock_threshold: 5,
          is_active: true,
        }),
      );
      setDraft(EMPTY);
      toast.success("Presentación agregada.");
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "No pudimos agregar la presentación.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function remove(variantId: string) {
    try {
      onChange(await producerCatalogApi.deleteVariant(token, product.id, variantId));
      toast.success("Presentación retirada.");
    } catch (error) {
      // El servidor la rechaza si tiene unidades comprometidas en pedidos.
      toast.error(error instanceof ApiError ? error.message : "No pudimos retirarla.");
    }
  }

  return (
    <section aria-labelledby="presentaciones-titulo" className="space-y-4">
      <div>
        <h2 id="presentaciones-titulo" className="font-display text-lg font-semibold">
          Presentaciones
        </h2>
        <p className="text-sm text-muted-foreground">
          Cada peso y molienda tiene su precio y su inventario.
        </p>
      </div>

      {product.variants.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <caption className="sr-only">
              Presentaciones a la venta de {product.name}
            </caption>
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th scope="col" className="py-2 font-medium">
                  Presentación
                </th>
                <th scope="col" className="py-2 font-medium">
                  Precio
                </th>
                <th scope="col" className="py-2 font-medium">
                  Disponible
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
                  <td className="py-3">{formatCurrency(variant.price)}</td>
                  <td className="py-3">
                    {variant.stock_qty - variant.reserved_qty}
                    {variant.reserved_qty > 0 && (
                      <Badge variant="outline" className="ml-2">
                        {variant.reserved_qty} reservadas
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
        <div>
          <label htmlFor="peso" className="mb-1.5 block text-sm font-medium">
            Peso (g)
          </label>
          <Input
            id="peso"
            type="number"
            min={1}
            value={draft.weight_grams}
            onChange={(event) => setDraft({ ...draft, weight_grams: event.target.value })}
          />
        </div>

        <div>
          <label htmlFor="molienda" className="mb-1.5 block text-sm font-medium">
            Molienda
          </label>
          <select
            id="molienda"
            className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
            value={draft.grind}
            onChange={(event) =>
              setDraft({ ...draft, grind: event.target.value as GrindType })
            }
          >
            {GRIND_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="precio" className="mb-1.5 block text-sm font-medium">
            Precio (COP)
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
            Unidades
          </label>
          <Input
            id="stock"
            type="number"
            min={0}
            value={draft.stock}
            onChange={(event) => setDraft({ ...draft, stock: event.target.value })}
          />
        </div>

        <div className="sm:col-span-4">
          <Button
            type="button"
            variant="outline"
            onClick={add}
            disabled={isSaving}
            aria-busy={isSaving}
          >
            <Plus className="mr-1.5 size-4" aria-hidden="true" />
            {isSaving ? "Agregando…" : "Agregar presentación"}
          </Button>
        </div>
      </div>
    </section>
  );
}
