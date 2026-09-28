"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, Megaphone, ShoppingCart, X } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/input";
import {
  DEMAND_STATUS_META,
  demandsApi,
  OFFER_STATUS_META,
  type DemandDetail,
  type OfferSummary,
} from "@/features/trading/api";
import { ApiError } from "@/lib/api";
import {
  formatCurrency,
  formatDateShort,
  formatKilos,
  formatKilosWithCargas,
  formatPercent,
  formatPricePerKilo,
  formatYieldFactor,
} from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";
import { PROCESS_LABELS, yieldFactorQuality } from "@/types/catalog";

/**
 * Una solicitud con las posturas que recibió.
 *
 * Aceptar no cierra la compra: deja los kilos acordados en el carrito al precio
 * acordado. Así el comprador puede armar su carga con varios vendedores y pagar
 * una sola vez, en vez de un envío por cada trato.
 */

export default function DemandDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const demandId = params.id;

  const [demand, setDemand] = useState<DemandDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busyOfferId, setBusyOfferId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      setDemand(await demandsApi.get(token, demandId));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        router.push("/ingresar");
        return;
      }
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router, demandId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function respond(offer: OfferSummary, accept: boolean): Promise<void> {
    const token = session.getAccessToken();
    if (!token) return;

    setBusyOfferId(offer.id);
    setActionError(null);
    try {
      const updated = await demandsApi.respond(
        token,
        offer.id,
        accept,
        accept ? undefined : rejectNote.trim() || undefined,
      );
      setDemand(updated);
      setRejectingId(null);
      setRejectNote("");
      setNotice(
        accept
          ? `Aceptaste ${formatKilos(offer.offered_kg)} de ${offer.producer_name}. Ya están en tu carrito.`
          : `Rechazaste la postura de ${offer.producer_name}.`,
      );
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos registrar tu respuesta.",
      );
    } finally {
      setBusyOfferId(null);
    }
  }

  async function close(): Promise<void> {
    const token = session.getAccessToken();
    if (!token || !demand) return;
    if (
      !window.confirm(
        "¿Cerrar esta solicitud? Las posturas que estén esperando respuesta quedarán rechazadas.",
      )
    ) {
      return;
    }

    setActionError(null);
    try {
      setDemand(await demandsApi.close(token, demand.id));
      setNotice("Solicitud cerrada.");
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cerrar la solicitud.",
      );
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !demand) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <ErrorState
          title="No encontramos esta solicitud"
          description="Puede que se haya eliminado o que no sea tuya."
          onRetry={() => void load()}
        />
      </div>
    );
  }

  const meta = DEMAND_STATUS_META[demand.status];
  const accepted = demand.offers.filter((offer) => offer.status === "accepted");

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/mi-cuenta/solicitudes"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mis solicitudes
      </Link>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold">{demand.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {formatKilosWithCargas(demand.wanted_kg)} buscados
            {demand.covered_kg > 0 &&
              ` · ${formatKilosWithCargas(demand.covered_kg)} cubiertos · faltan ${formatKilos(demand.remaining_kg)}`}
          </p>
        </div>
        <Badge variant={meta.variant} size="md">
          {meta.label}
        </Badge>
      </div>

      {/* ---------------- Condiciones ---------------- */}
      <Card className="mt-6">
        <CardContent className="pt-6">
          <h2 className="mb-3 font-display text-lg font-semibold">Lo que pediste</h2>
          <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
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
              value={demand.process ? PROCESS_LABELS[demand.process] : "Cualquiera"}
            />
            <Row
              label="Origen"
              value={
                demand.municipality
                  ? `${demand.municipality}, ${demand.department}`
                  : "Cualquiera"
              }
            />
            <Row
              label="Precio que ofreces"
              value={
                demand.offered_price_per_kg
                  ? formatPricePerKilo(demand.offered_price_per_kg)
                  : "No declarado"
              }
            />
            <Row
              label="Vigente hasta"
              value={`${formatDateShort(demand.expires_on)}${demand.is_receiving ? "" : " (vencida)"}`}
            />
          </dl>

          {demand.description && (
            <p className="mt-4 border-t border-border pt-4 text-sm leading-relaxed text-muted-foreground">
              {demand.description}
            </p>
          )}

          {demand.is_receiving && (
            <Button
              variant="ghost"
              size="sm"
              className="mt-4 text-destructive"
              onClick={close}
            >
              Cerrar esta solicitud
            </Button>
          )}
        </CardContent>
      </Card>

      {accepted.length > 0 && (
        <div className="mt-6 rounded-md border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
          <p>
            Aceptaste {accepted.length} {accepted.length === 1 ? "postura" : "posturas"}:
            los kilos acordados están en tu carrito al precio acordado.
          </p>
          <Link
            href="/carrito"
            className={cn(buttonVariants({ size: "sm", variant: "primary" }), "mt-3")}
          >
            <ShoppingCart className="size-4" aria-hidden="true" />
            Ir al carrito
          </Link>
        </div>
      )}

      {actionError && (
        <p
          className="mt-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {actionError}
        </p>
      )}

      {/* ---------------- Posturas ---------------- */}
      <h2 className="mb-4 mt-8 font-display text-xl font-bold">
        Posturas recibidas
        {demand.offer_count > 0 && (
          <span className="ml-2 text-base font-normal text-muted-foreground">
            ({demand.offer_count})
          </span>
        )}
      </h2>

      {demand.offers.length === 0 ? (
        <EmptyState
          icon={<Megaphone className="size-10" aria-hidden="true" />}
          title="Todavía nadie ha respondido"
          description={
            demand.is_receiving
              ? "Los vendedores con lotes que encajen verán tu solicitud en su panel."
              : "Esta solicitud ya no recibe posturas."
          }
        />
      ) : (
        <ul className="space-y-4">
          {demand.offers.map((offer) => {
            const offerMeta = OFFER_STATUS_META[offer.status];
            const quality = yieldFactorQuality(offer.yield_factor);
            const canRespond = offer.status === "pending" && demand.is_receiving;

            return (
              <li key={offer.id}>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-display font-semibold">
                          {offer.producer_name}
                        </p>
                        <Link
                          href={`/catalogo/${offer.product_slug}`}
                          className="text-sm text-primary hover:underline"
                        >
                          {offer.product_name}
                        </Link>
                        <p className="text-sm text-muted-foreground">
                          {offer.presentation}
                          {offer.municipality && ` · ${offer.municipality}`}
                        </p>
                      </div>
                      <Badge variant={offerMeta.variant}>{offerMeta.label}</Badge>
                    </div>

                    <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
                      <Row
                        label="Ofrece"
                        value={formatKilosWithCargas(offer.offered_kg)}
                      />
                      <Row
                        label="Precio"
                        value={formatPricePerKilo(offer.price_per_kg)}
                      />
                      <Row
                        label="Factor"
                        value={
                          offer.yield_factor
                            ? `${formatYieldFactor(offer.yield_factor)}${quality ? ` · ${quality.label}` : ""}`
                            : "No declarado"
                        }
                      />
                      <Row
                        label="Humedad"
                        value={
                          offer.moisture_pct
                            ? formatPercent(offer.moisture_pct)
                            : "No declarada"
                        }
                      />
                      <Row
                        label="Total de la postura"
                        value={formatCurrency(offer.line_total)}
                      />
                      <Row label="Recibida" value={formatDateShort(offer.created_at)} />
                    </dl>

                    {offer.message && (
                      <p className="mt-3 rounded-md bg-muted px-3 py-2 text-sm italic">
                        «{offer.message}»
                      </p>
                    )}

                    {offer.response_note && (
                      <p className="mt-3 text-sm text-muted-foreground">
                        Tu respuesta: {offer.response_note}
                      </p>
                    )}

                    {canRespond && rejectingId !== offer.id && (
                      <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
                        <Button
                          size="sm"
                          disabled={busyOfferId === offer.id}
                          onClick={() => void respond(offer, true)}
                        >
                          <Check className="size-4" aria-hidden="true" />
                          Aceptar y pasar al carrito
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:bg-destructive/10"
                          disabled={busyOfferId === offer.id}
                          onClick={() => {
                            setRejectingId(offer.id);
                            setRejectNote("");
                            setActionError(null);
                          }}
                        >
                          <X className="size-4" aria-hidden="true" />
                          Rechazar
                        </Button>
                      </div>
                    )}

                    {rejectingId === offer.id && (
                      <div className="mt-4 space-y-3 border-t border-border pt-4">
                        <div>
                          <Label htmlFor={`note-${offer.id}`}>
                            ¿Por qué la rechazas? (opcional)
                          </Label>
                          <textarea
                            id={`note-${offer.id}`}
                            value={rejectNote}
                            onChange={(event) => setRejectNote(event.target.value)}
                            rows={2}
                            maxLength={1000}
                            placeholder="Ej. El factor está por encima de lo que necesito."
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          />
                          <p className="mt-1.5 text-xs text-muted-foreground">
                            El vendedor lo recibe y sabrá qué ajustar en su siguiente
                            postura.
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={busyOfferId === offer.id}
                            onClick={() => void respond(offer, false)}
                          >
                            Confirmar el rechazo
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setRejectingId(null)}
                          >
                            Volver
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
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
