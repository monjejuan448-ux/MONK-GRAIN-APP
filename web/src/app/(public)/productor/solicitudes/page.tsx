"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Megaphone, Send } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { producerCatalogApi, type ProducerProduct } from "@/features/producer/api";
import { sellerTradingApi, type DemandSummary } from "@/features/trading/api";
import { ApiError } from "@/lib/api";
import {
  formatDateShort,
  formatKilos,
  formatKilosWithCargas,
  formatPercent,
  formatPricePerKilo,
  formatYieldFactor,
} from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";
import { PROCESS_LABELS } from "@/types/catalog";

/**
 * Solicitudes de compra que el vendedor puede atender.
 *
 * Responder es enviar una postura respaldada por una de las ofertas de sus lotes
 * publicados: de ahí sale el análisis que verá el comprador. Por eso el
 * formulario no pide factor ni humedad —ya están en la ficha del lote—, solo
 * cuántos kilos y a qué precio.
 */

/** Oferta comprable de un lote publicado, aplanada para el desplegable. */
interface SellableOption {
  variantId: string;
  label: string;
  minKg: number;
  availableKg: number;
  listPrice: string;
}

function sellableOptions(products: ProducerProduct[]): SellableOption[] {
  const options: SellableOption[] = [];
  for (const product of products) {
    if (product.status !== "published") continue;
    for (const variant of product.variants) {
      const available = variant.stock_qty - variant.reserved_qty;
      if (!variant.is_active || available <= 0) continue;
      options.push({
        variantId: variant.id,
        label: `${product.name} — ${variant.presentation}`,
        minKg: variant.min_qty_kg,
        availableKg: available,
        listPrice: variant.price,
      });
    }
  }
  return options;
}

export default function ProducerDemandsPage() {
  const router = useRouter();
  const [demands, setDemands] = useState<DemandSummary[]>([]);
  const [options, setOptions] = useState<SellableOption[]>([]);
  const [onlyMatching, setOnlyMatching] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [respondingTo, setRespondingTo] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      const [page, catalog] = await Promise.all([
        sellerTradingApi.openDemands(token, onlyMatching),
        // El catálogo propio ya trae las ofertas de cada lote, así que una sola
        // petición alcanza para armar el desplegable del formulario.
        producerCatalogApi.list(token).catch(() => ({ items: [] as ProducerProduct[] })),
      ]);
      setDemands(page.items);
      setOptions(sellableOptions(catalog.items));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        router.push("/ingresar");
        return;
      }
      if (requestError instanceof ApiError && requestError.status === 403) {
        setForbidden(true);
        return;
      }
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router, onlyMatching]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <EmptyState
          icon={<Megaphone className="size-10" aria-hidden="true" />}
          title="Esta sección es para vendedores"
          description="Si ya enviaste tu solicitud, un administrador debe aprobarla antes de que puedas responder a compradores."
          action={
            <Link href="/vender">
              <Button variant="outline">Cómo vender en MONK GRAIN</Button>
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/productor"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver al panel
      </Link>

      <h1 className="font-display text-3xl font-bold">Quién está comprando</h1>
      <p className="mb-6 mt-1 text-muted-foreground">
        Compradores que publicaron lo que necesitan. Responde con una postura sobre uno de
        tus lotes publicados: el comprador verá su análisis y decidirá.
      </p>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      <label className="mb-6 flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={onlyMatching}
          onChange={(event) => setOnlyMatching(event.target.checked)}
          className="size-4 rounded border-input accent-primary"
        />
        Solo las que mis lotes pueden cumplir
      </label>

      {!isLoading && options.length === 0 && (
        <p className="mb-6 rounded-md border border-border bg-muted px-4 py-3 text-sm text-muted-foreground">
          Para responder necesitas al menos un lote publicado con kilos disponibles.{" "}
          <Link href="/productor/catalogo" className="text-primary hover:underline">
            Ir a mi catálogo
          </Link>
        </p>
      )}

      {isLoading && <Skeleton className="h-48 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && demands.length === 0 && (
        <EmptyState
          icon={<Megaphone className="size-10" aria-hidden="true" />}
          title={
            onlyMatching
              ? "Ninguna solicitud encaja con tus lotes"
              : "No hay solicitudes vigentes"
          }
          description={
            onlyMatching
              ? "Desmarca el filtro para ver todas las que están abiertas."
              : "Cuando un comprador publique lo que busca, aparecerá aquí."
          }
        />
      )}

      {!isLoading && !error && demands.length > 0 && (
        <ul className="space-y-4">
          {demands.map((demand) => (
            <li key={demand.id}>
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-display font-semibold">{demand.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {demand.buyer_name}
                        {demand.municipality &&
                          ` · recibe en ${demand.municipality}, ${demand.department}`}
                      </p>
                    </div>
                    <Badge variant="primary">
                      {formatKilosWithCargas(demand.remaining_kg)}
                    </Badge>
                  </div>

                  <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
                    <Row
                      label="Factor máximo"
                      value={
                        demand.max_yield_factor
                          ? formatYieldFactor(demand.max_yield_factor)
                          : "Sin límite"
                      }
                    />
                    <Row
                      label="Humedad máxima"
                      value={
                        demand.max_moisture_pct
                          ? formatPercent(demand.max_moisture_pct)
                          : "Sin límite"
                      }
                    />
                    <Row label="Variedad" value={demand.variety ?? "Cualquiera"} />
                    <Row
                      label="Proceso"
                      value={
                        demand.process ? PROCESS_LABELS[demand.process] : "Cualquiera"
                      }
                    />
                    <Row
                      label="Ofrece"
                      value={
                        demand.offered_price_per_kg
                          ? formatPricePerKilo(demand.offered_price_per_kg)
                          : "No lo declaró"
                      }
                    />
                    <Row
                      label="Responder antes del"
                      value={formatDateShort(demand.expires_on)}
                    />
                  </dl>

                  {respondingTo === demand.id ? (
                    <OfferForm
                      demand={demand}
                      options={options}
                      onSent={async (message) => {
                        setNotice(message);
                        setRespondingTo(null);
                        await load();
                      }}
                      onCancel={() => setRespondingTo(null)}
                    />
                  ) : (
                    <div className="mt-4 border-t border-border pt-4">
                      <Button
                        size="sm"
                        disabled={options.length === 0}
                        onClick={() => setRespondingTo(demand.id)}
                      >
                        <Send className="size-4" aria-hidden="true" />
                        Responder con una postura
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OfferForm({
  demand,
  options,
  onSent,
  onCancel,
}: {
  demand: DemandSummary;
  options: SellableOption[];
  onSent: (message: string) => Promise<void>;
  onCancel: () => void;
}) {
  const router = useRouter();
  const first = options[0];
  const [variantId, setVariantId] = useState(first?.variantId ?? "");
  const selected = options.find((option) => option.variantId === variantId) ?? first;

  // Se propone lo que falta por cubrir, acotado a lo que el vendedor tiene y sin
  // bajar del mínimo de su propia oferta: así el caso corriente sale válido sin
  // que haya que corregirlo.
  const suggestedKg = selected
    ? Math.max(selected.minKg, Math.min(demand.remaining_kg, selected.availableKg))
    : 0;
  const [offeredKg, setOfferedKg] = useState(String(suggestedKg));
  const [price, setPrice] = useState(selected?.listPrice ?? "");
  const [message, setMessage] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  function changeVariant(nextId: string): void {
    setVariantId(nextId);
    const option = options.find((item) => item.variantId === nextId);
    if (!option) return;
    setOfferedKg(
      String(Math.max(option.minKg, Math.min(demand.remaining_kg, option.availableKg))),
    );
    setPrice(option.listPrice);
  }

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }
    if (!selected) return;

    setFormError(null);
    const kg = Number(offeredKg);
    if (!kg || kg < selected.minKg) {
      setFormError(`Esta oferta se vende desde ${formatKilos(selected.minKg)}.`);
      return;
    }
    if (kg > selected.availableKg) {
      setFormError(`Solo tienes ${formatKilos(selected.availableKg)} disponibles.`);
      return;
    }
    if (!price || Number(price) <= 0) {
      setFormError("Indica el precio por kilo al que ofreces.");
      return;
    }

    setIsSaving(true);
    try {
      await sellerTradingApi.offer(token, demand.id, {
        variant_id: selected.variantId,
        offered_kg: kg,
        price_per_kg: price,
        message: message.trim() || null,
      });
      await onSent(`Postura enviada: ${formatKilos(kg)} a ${formatPricePerKilo(price)}.`);
    } catch (requestError) {
      setFormError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos enviar la postura. Inténtalo de nuevo.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  const total = Number(price) * Number(offeredKg || 0);

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="mt-4 space-y-4 border-t border-border pt-4"
    >
      <h3 className="font-display font-semibold">Tu postura</h3>

      {formError && (
        <p className="text-sm text-destructive" role="alert">
          {formError}
        </p>
      )}

      <div>
        <Label htmlFor={`variant-${demand.id}`} required>
          Con qué lote respondes
        </Label>
        <select
          id={`variant-${demand.id}`}
          value={variantId}
          onChange={(event) => changeVariant(event.target.value)}
          className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
        >
          {options.map((option) => (
            <option key={option.variantId} value={option.variantId}>
              {option.label} · {formatKilos(option.availableKg)} disponibles
            </option>
          ))}
        </select>
        {selected && (
          <p className="mt-1.5 text-xs text-muted-foreground">
            Se vende desde {formatKilos(selected.minKg)} y lo listas a{" "}
            {formatPricePerKilo(selected.listPrice)}. El comprador verá el análisis de
            este lote.
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor={`kg-${demand.id}`} required>
            Kilos que ofreces
          </Label>
          <Input
            id={`kg-${demand.id}`}
            type="number"
            min={selected?.minKg ?? 1}
            max={selected?.availableKg}
            step={selected && selected.minKg >= 125 ? 125 : 1}
            value={offeredKg}
            onChange={(event) => setOfferedKg(event.target.value)}
          />
        </div>

        <div>
          <Label htmlFor={`price-${demand.id}`} required>
            Precio por kilo
          </Label>
          <Input
            id={`price-${demand.id}`}
            type="number"
            min={1}
            step={100}
            value={price}
            onChange={(event) => setPrice(event.target.value)}
          />
          {demand.offered_price_per_kg && (
            <p
              className={cn(
                "mt-1.5 text-xs",
                Number(price) > Number(demand.offered_price_per_kg)
                  ? "text-gold"
                  : "text-muted-foreground",
              )}
            >
              {Number(price) > Number(demand.offered_price_per_kg)
                ? `Pides más de lo que ofrece (${formatPricePerKilo(demand.offered_price_per_kg)}). Explícalo abajo.`
                : `El comprador ofrece ${formatPricePerKilo(demand.offered_price_per_kg)}.`}
            </p>
          )}
        </div>
      </div>

      {total > 0 && (
        <p className="rounded-md bg-muted px-3 py-2 text-sm">
          Tu postura: {formatKilos(Number(offeredKg))} × {formatPricePerKilo(price)} ={" "}
          <span className="font-display font-semibold">
            {new Intl.NumberFormat("es-CO", {
              style: "currency",
              currency: "COP",
              maximumFractionDigits: 0,
            }).format(total)}
          </span>
        </p>
      )}

      <div>
        <Label htmlFor={`message-${demand.id}`}>Mensaje para el comprador</Label>
        <textarea
          id={`message-${demand.id}`}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          rows={2}
          maxLength={1000}
          placeholder="Ej. Lote listo en bodega, puedo despachar esta semana."
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
      </div>

      <div className="flex flex-wrap gap-3">
        <Button type="submit" size="sm" isLoading={isSaving}>
          Enviar postura
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onCancel}
          disabled={isSaving}
        >
          Cancelar
        </Button>
      </div>
    </form>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border pb-1.5 last:border-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}
