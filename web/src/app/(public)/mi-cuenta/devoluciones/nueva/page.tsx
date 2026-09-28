"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ArrowLeft, Info } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  RETURN_REASON_META,
  returnsApi,
  type ReturnEligibility,
  type ReturnReason,
} from "@/features/returns/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Formulario de solicitud de devolución.
 *
 * Los plazos y los motivos admisibles no se calculan aquí: el servidor devuelve
 * la elegibilidad y esta pantalla se limita a pintar lo que sigue vivo. Si el
 * retracto ya venció, el motivo simplemente no aparece, y aunque alguien lo
 * enviara a mano el servidor lo rechazaría igual.
 */
export default function NewReturnPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-3xl px-4 py-10" aria-busy="true">
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <NewReturnForm />
    </Suspense>
  );
}

function NewReturnForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const subOrderId = searchParams.get("envio");

  const [token, setToken] = useState<string | null>(null);
  const [eligibility, setEligibility] = useState<ReturnEligibility | null>(null);
  const [reason, setReason] = useState<ReturnReason | "">("");
  const [description, setDescription] = useState("");
  const [unopened, setUnopened] = useState(false);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [files, setFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const accessToken = session.getAccessToken();
    if (!accessToken) {
      router.push("/ingresar");
      return;
    }
    if (!subOrderId) {
      setError("Falta indicar de qué envío quieres devolver.");
      setIsLoading(false);
      return;
    }

    setToken(accessToken);
    setError(null);
    try {
      const result = await returnsApi.eligibility(accessToken, subOrderId);
      setEligibility(result);
      setQuantities(
        Object.fromEntries(result.items.map((item) => [item.order_item_id, 0])),
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cargar este pedido.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [router, subOrderId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = Object.entries(quantities).filter(([, qty]) => qty > 0);

  async function submit() {
    if (!token || !eligibility || !reason) {
      toast.error("Elige el motivo de la devolución.");
      return;
    }
    if (selected.length === 0) {
      toast.error("Indica cuántas unidades devuelves.");
      return;
    }

    setIsSaving(true);
    try {
      const created = await returnsApi.request(token, {
        sub_order_id: eligibility.sub_order_id,
        reason,
        description: description.trim() || null,
        declared_unopened: unopened,
        items: selected.map(([order_item_id, quantity]) => ({
          order_item_id,
          quantity,
        })),
      });

      if (files.length > 0) {
        try {
          await returnsApi.addEvidence(token, created.id, files);
        } catch {
          // La solicitud ya quedó radicada: perder las fotos no puede
          // invalidarla, y se pueden adjuntar después desde la constancia.
          toast.warning("Radicamos tu solicitud, pero no pudimos subir las fotos.");
        }
      }

      toast.success(`Solicitud radicada con el número ${created.return_number}.`);
      router.push(`/mi-cuenta/devoluciones/${created.id}`);
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos radicar la solicitud.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-72" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !eligibility) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <ErrorState title={error ?? undefined} onRetry={() => void load()} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/mi-cuenta"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi cuenta
      </Link>

      <h1 className="font-display text-3xl font-bold">Solicitar una devolución</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Envío {eligibility.sub_order_number}
        {eligibility.delivered_at && (
          <> · entregado el {formatDate(eligibility.delivered_at)}</>
        )}
      </p>

      {!eligibility.can_request ? (
        <EmptyState
          title="Este envío no admite una devolución ahora mismo"
          description={eligibility.blocked_reason ?? undefined}
          action={
            <Link href="/legal/devoluciones" className="text-sm underline">
              Consultar tus derechos
            </Link>
          }
        />
      ) : (
        <div className="space-y-8">
          <section aria-labelledby="motivo">
            <h2 id="motivo" className="mb-3 font-display text-lg font-semibold">
              ¿Qué pasó?
            </h2>

            <div className="space-y-2">
              {eligibility.allowed_reasons.map((option) => {
                const meta = RETURN_REASON_META[option];
                return (
                  <label
                    key={option}
                    className="flex cursor-pointer gap-3 rounded-lg border border-border p-4 hover:bg-muted/40 has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                  >
                    <input
                      type="radio"
                      name="reason"
                      value={option}
                      checked={reason === option}
                      onChange={() => {
                        setReason(option);
                        if (option !== "withdrawal") setUnopened(false);
                      }}
                      className="mt-1 size-4 shrink-0 accent-primary"
                    />
                    <span>
                      <span className="block font-medium">{meta.label}</span>
                      <span className="mt-0.5 block text-sm text-muted-foreground">
                        {meta.help}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>

            {!eligibility.allowed_reasons.includes("withdrawal") &&
              eligibility.withdrawal_deadline && (
                <p className="mt-3 flex gap-2 text-sm text-muted-foreground">
                  <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                  El plazo para retractarte venció el{" "}
                  {formatDate(eligibility.withdrawal_deadline)}, pero la garantía sigue
                  vigente si el café tuvo algún problema.
                </p>
              )}
          </section>

          {reason === "withdrawal" && (
            <label className="flex cursor-pointer gap-3 rounded-lg border border-border bg-muted/30 p-4">
              <input
                type="checkbox"
                checked={unopened}
                onChange={(event) => setUnopened(event.target.checked)}
                className="mt-1 size-4 shrink-0 accent-primary"
              />
              <span className="text-sm">
                Declaro que el café está <strong>sellado y sin abrir</strong>, en su
                empaque original. El café es un alimento y una bolsa abierta no puede
                volver a venderse. Si el problema es con el producto, elige otro motivo:
                la garantía procede aunque lo hayas abierto.
              </span>
            </label>
          )}

          <section aria-labelledby="productos">
            <h2 id="productos" className="mb-3 font-display text-lg font-semibold">
              ¿Qué devuelves?
            </h2>

            <ul className="space-y-3">
              {eligibility.items.map((item) => (
                <li
                  key={item.order_item_id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border p-4"
                >
                  <div className="min-w-0">
                    <p className="font-medium">{item.product_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {item.variant_label} · {formatCurrency(item.unit_price)} c/u ·{" "}
                      {item.returnable_qty === 0
                        ? "ya solicitada"
                        : `hasta ${item.returnable_qty} de ${item.purchased_qty}`}
                    </p>
                  </div>

                  <label className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground">Unidades</span>
                    <input
                      type="number"
                      min={0}
                      max={item.returnable_qty}
                      disabled={item.returnable_qty === 0}
                      value={quantities[item.order_item_id] ?? 0}
                      onChange={(event) =>
                        setQuantities((current) => ({
                          ...current,
                          [item.order_item_id]: Math.max(
                            0,
                            Math.min(item.returnable_qty, Number(event.target.value)),
                          ),
                        }))
                      }
                      className="h-11 w-20 rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
                      aria-label={`Unidades de ${item.product_name} a devolver`}
                    />
                  </label>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="detalle">
            <h2 id="detalle" className="mb-3 font-display text-lg font-semibold">
              Cuéntanos más
            </h2>

            <label htmlFor="descripcion" className="mb-1.5 block text-sm font-medium">
              Descripción
              {reason !== "withdrawal" && reason !== "" && (
                <span aria-hidden="true"> *</span>
              )}
            </label>
            <textarea
              id="descripcion"
              rows={4}
              maxLength={2000}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe qué pasó con el café y con el empaque."
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />

            <label htmlFor="fotos" className="mb-1.5 mt-4 block text-sm font-medium">
              Fotografías
            </label>
            <input
              id="fotos"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
              className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2 file:text-sm"
            />
            <p className="mt-1.5 text-sm text-muted-foreground">
              No son obligatorias, pero ayudan a resolver más rápido. Solo las ven quien
              vende y nuestro equipo.
            </p>
          </section>

          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                Al radicar recibirás una{" "}
                <strong>constancia con número, fecha y hora</strong>. Consérvala: la
                necesitas si más adelante acudes a la Superintendencia de Industria y
                Comercio. Consulta el detalle de los plazos en{" "}
                <Link href="/legal/devoluciones" className="underline">
                  devoluciones y reembolsos
                </Link>
                .
              </p>

              <Button
                type="button"
                className="mt-5 w-full sm:w-auto"
                disabled={isSaving || !reason || selected.length === 0}
                onClick={() => void submit()}
              >
                {isSaving ? "Radicando…" : "Radicar solicitud"}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
