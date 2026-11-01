"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CalendarRange } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  adminApi,
  SETTLEMENT_STATUS_META,
  type AdminSettlement,
  type ClosePeriodResult,
} from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";

/** Primer y último día del mes anterior, que es el periodo que se cierra casi siempre. */
function lastMonth(): { start: string; end: string } {
  const hoy = new Date();
  const inicio = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
  const fin = new Date(hoy.getFullYear(), hoy.getMonth(), 0);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(inicio), end: iso(fin) };
}

/**
 * Cierre de periodos y constancia de los pagos a vendedores.
 *
 * El dinero que mueve esta pantalla queda en la auditoría inmutable: cada
 * liquidación creada y cada pago registrado dejan su entrada con quién lo hizo.
 */
export default function AdminSettlementsPage() {
  const router = useRouter();
  const inicial = lastMonth();

  const [settlements, setSettlements] = useState<AdminSettlement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const [periodStart, setPeriodStart] = useState(inicial.start);
  const [periodEnd, setPeriodEnd] = useState(inicial.end);
  const [isClosing, setIsClosing] = useState(false);
  const [result, setResult] = useState<ClosePeriodResult | null>(null);

  const [payingId, setPayingId] = useState<string | null>(null);
  const [reference, setReference] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(null);
    try {
      setSettlements(await adminApi.settlements(token));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 403) {
        setForbidden(true);
      } else {
        setError("No pudimos cargar las liquidaciones.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleClose(event: React.FormEvent) {
    event.preventDefault();
    const token = session.getAccessToken();
    if (!token) return;

    setIsClosing(true);
    setActionError(null);
    try {
      setResult(await adminApi.closeSettlementPeriod(token, periodStart, periodEnd));
      await load();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cerrar el periodo.",
      );
    } finally {
      setIsClosing(false);
    }
  }

  async function handlePay(settlementId: string) {
    const token = session.getAccessToken();
    if (!token) return;

    setActionError(null);
    try {
      await adminApi.paySettlement(token, settlementId, reference);
      setPayingId(null);
      setReference("");
      await load();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos registrar el pago.",
      );
    }
  }

  if (isLoading) {
    return (
      <div className="container-page py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-72" />
        <Skeleton className="mb-4 h-40" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="container-page py-10">
        <ErrorState
          title="Sin permiso"
          description="Gestionar liquidaciones requiere el permiso correspondiente."
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-page py-10">
        <ErrorState
          title="Algo salió mal"
          description={error}
          onRetry={() => void load()}
        />
      </div>
    );
  }

  const porPagar = settlements.filter((s) => s.status === "pending_payment");

  return (
    <div className="container-page py-10">
      <h1 className="font-display text-3xl font-bold">Liquidaciones</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Cierra un periodo para generar lo que hay que pagar a cada vendedor, y deja
        constancia del desembolso cuando salga el dinero.
      </p>

      {/* ---------------- Cerrar periodo ---------------- */}
      <section aria-labelledby="cerrar" className="mt-8">
        <h2 id="cerrar" className="mb-4 font-display text-xl font-bold">
          Cerrar un periodo
        </h2>
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleClose} className="flex flex-wrap items-end gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium">Desde</span>
                <input
                  type="date"
                  required
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                  className="border border-input bg-background px-3 py-2"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium">Hasta</span>
                <input
                  type="date"
                  required
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                  className="border border-input bg-background px-3 py-2"
                />
              </label>
              <Button type="submit" disabled={isClosing}>
                <CalendarRange className="mr-1.5 size-4" aria-hidden="true" />
                {isClosing ? "Cerrando…" : "Cerrar periodo"}
              </Button>
            </form>

            <p className="mt-4 text-sm text-muted-foreground">
              Entra solo lo <strong>entregado</strong>, pasados los cinco días hábiles del
              derecho de retracto y sin reclamaciones abiertas. Cerrar dos veces el mismo
              periodo no duplica nada.
            </p>

            {result && (
              <div
                role="status"
                className="mt-4 border border-border bg-muted/40 px-4 py-3 text-sm"
              >
                {result.settlements_created === 0 ? (
                  <p>No había nada que liquidar en ese periodo.</p>
                ) : (
                  <p>
                    <strong>
                      {result.settlements_created}{" "}
                      {result.settlements_created === 1 ? "liquidación" : "liquidaciones"}
                    </strong>{" "}
                    por {formatCurrency(result.net_total)}, de {result.sub_orders_settled}{" "}
                    {result.sub_orders_settled === 1 ? "pedido" : "pedidos"}.
                  </p>
                )}
                {result.skipped_without_bank_account > 0 && (
                  <p className="mt-2 flex items-start gap-1.5 text-coffee-dark">
                    <AlertTriangle
                      className="mt-0.5 size-4 shrink-0"
                      aria-hidden="true"
                    />
                    <span>
                      {result.skipped_without_bank_account}{" "}
                      {result.skipped_without_bank_account === 1
                        ? "vendedor quedó fuera"
                        : "vendedores quedaron fuera"}{" "}
                      por no tener cuenta bancaria registrada. Su dinero sigue acumulado y
                      entrará en el próximo cierre.
                    </span>
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {actionError && (
        <p role="alert" className="mt-6 text-sm text-destructive">
          {actionError}
        </p>
      )}

      {/* ---------------- Listado ---------------- */}
      <section aria-labelledby="listado" className="mt-10">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 id="listado" className="font-display text-xl font-bold">
            Todas las liquidaciones
          </h2>
          {porPagar.length > 0 && (
            <span className="text-sm text-muted-foreground">
              {porPagar.length} por pagar ·{" "}
              {formatCurrency(
                porPagar.reduce((total, s) => total + Number(s.net_amount), 0).toFixed(2),
              )}
            </span>
          )}
        </div>

        {settlements.length === 0 ? (
          <EmptyState
            title="Todavía no hay liquidaciones"
            description="Cierra un periodo para generar lo que hay que pagar a cada vendedor."
          />
        ) : (
          <Card>
            <CardContent className="pt-6">
              <ul className="divide-y divide-border">
                {settlements.map((liquidacion) => {
                  const meta = SETTLEMENT_STATUS_META[liquidacion.status];
                  const estaPagando = payingId === liquidacion.id;
                  return (
                    <li key={liquidacion.id} className="py-4 first:pt-0 last:pb-0">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-medium">{liquidacion.producer_name}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatDateShort(liquidacion.period_start)} —{" "}
                            {formatDateShort(liquidacion.period_end)} ·{" "}
                            {liquidacion.sub_orders_count}{" "}
                            {liquidacion.sub_orders_count === 1 ? "pedido" : "pedidos"}
                          </p>
                          {liquidacion.payment_reference && (
                            <p className="mt-1 text-sm text-muted-foreground">
                              Referencia {liquidacion.payment_reference}
                              {liquidacion.paid_at &&
                                ` · ${formatDateShort(liquidacion.paid_at)}`}
                            </p>
                          )}
                          {!liquidacion.has_bank_account && (
                            <p className="mt-1 text-sm text-coffee-dark">
                              Este vendedor retiró su cuenta bancaria.
                            </p>
                          )}
                        </div>

                        <div className="flex items-center gap-3">
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                          <span className="whitespace-nowrap font-display font-semibold tabular-nums">
                            {formatCurrency(liquidacion.net_amount)}
                          </span>
                          {liquidacion.status === "pending_payment" && !estaPagando && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setPayingId(liquidacion.id);
                                setReference("");
                              }}
                            >
                              Registrar pago
                            </Button>
                          )}
                        </div>
                      </div>

                      {estaPagando && (
                        <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-border pt-4">
                          <label className="flex flex-1 flex-col gap-1.5 sm:max-w-xs">
                            <span className="text-sm font-medium">
                              Referencia del pago
                            </span>
                            <input
                              autoFocus
                              required
                              minLength={3}
                              value={reference}
                              onChange={(e) => setReference(e.target.value)}
                              placeholder="TRF-2026-00412"
                              className="border border-input bg-background px-3 py-2"
                            />
                            <span className="text-xs text-muted-foreground">
                              Obligatoria: sin constancia de por dónde salió el dinero, no
                              es un pago registrado.
                            </span>
                          </label>
                          <Button
                            size="sm"
                            disabled={reference.trim().length < 3}
                            onClick={() => void handlePay(liquidacion.id)}
                          >
                            Confirmar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setPayingId(null)}
                          >
                            Cancelar
                          </Button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
