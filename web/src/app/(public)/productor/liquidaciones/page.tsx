"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Banknote, Landmark, Trash2 } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  producerApi,
  SETTLEMENT_STATUS_META,
  type BankAccount,
  type BankAccountInput,
  type ProducerSettlement,
  type SettlementSummary,
} from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";

const CUENTA_VACIA: BankAccountInput = {
  bank_name: "",
  account_type: "ahorros",
  account_number: "",
  holder_name: "",
  holder_document: "",
};

/**
 * Dónde cobra el vendedor y qué se le ha liquidado.
 *
 * Hasta el 1 de noviembre de 2026 esta pantalla no existía, y tampoco el camino
 * detrás: la plataforma cobraba al comprador y calculaba la comisión, pero no
 * había dónde registrar una cuenta ni se generaba ninguna liquidación.
 */
export default function ProducerSettlementsPage() {
  const router = useRouter();

  const [account, setAccount] = useState<BankAccount | null>(null);
  const [summary, setSummary] = useState<SettlementSummary | null>(null);
  const [settlements, setSettlements] = useState<ProducerSettlement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const [form, setForm] = useState<BankAccountInput>(CUENTA_VACIA);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(null);
    try {
      const [cuenta, resumen, historial] = await Promise.all([
        producerApi.bankAccount(token),
        producerApi.settlementSummary(token),
        producerApi.settlements(token),
      ]);
      setAccount(cuenta);
      setSummary(resumen);
      setSettlements(historial);
      // Sin cuenta registrada el formulario se abre solo: llegar a una
      // pantalla vacía y tener que buscar el botón alargaría justo el camino
      // que hay que recorrer para poder cobrar.
      setIsEditing(cuenta === null);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 403) {
        setForbidden(true);
      } else {
        setError("No pudimos cargar tus liquidaciones.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    const token = session.getAccessToken();
    if (!token) return;

    setIsSaving(true);
    setFormError(null);
    try {
      const guardada = await producerApi.saveBankAccount(token, form);
      setAccount(guardada);
      setIsEditing(false);
      setForm(CUENTA_VACIA);
      setNotice("Guardamos tu cuenta. Ya podemos liquidarte.");
    } catch (requestError) {
      setFormError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos guardar la cuenta.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    const token = session.getAccessToken();
    if (!token) return;

    setIsSaving(true);
    try {
      await producerApi.deleteBankAccount(token);
      setAccount(null);
      setIsEditing(true);
      setNotice("Retiramos tu cuenta. Sin una cuenta registrada no podemos liquidarte.");
    } catch {
      setFormError("No pudimos retirar la cuenta.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="container-page py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-72" />
        <Skeleton className="mb-4 h-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="container-page py-10">
        <ErrorState
          title="Esta sección es para vendedores"
          description="Regístrate como vendedor para publicar tus lotes y cobrar por ellos."
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-page py-10">
        <ErrorState title="Algo salió mal" description={error} onRetry={() => void load()} />
      </div>
    );
  }

  return (
    <div className="container-page py-10">
      <h1 className="font-display text-3xl font-bold">Liquidaciones</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Lo que la plataforma te debe, y la cuenta donde te lo consignamos.
      </p>

      {notice && (
        <p
          role="status"
          className="mt-4 border border-forest/30 bg-forest/5 px-4 py-3 text-sm text-forest"
        >
          {notice}
        </p>
      )}

      {/* ---------------- Pendiente de liquidar ---------------- */}
      {summary && (
        <section aria-labelledby="pendiente" className="mt-8">
          <h2 id="pendiente" className="mb-4 font-display text-xl font-bold">
            Pendiente de liquidar
          </h2>
          <Card>
            <CardContent className="pt-6">
              <dl className="grid gap-6 sm:grid-cols-3">
                <div>
                  <dt className="text-sm text-muted-foreground">Ventas entregadas</dt>
                  <dd className="font-display text-2xl font-bold tabular-nums">
                    {formatCurrency(summary.gross_amount)}
                  </dd>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {summary.sub_orders_count}{" "}
                    {summary.sub_orders_count === 1 ? "pedido" : "pedidos"}
                  </p>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Comisión</dt>
                  <dd className="font-display text-2xl font-bold tabular-nums text-muted-foreground">
                    −{formatCurrency(summary.commission_total)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Te corresponde</dt>
                  <dd className="font-display text-2xl font-bold tabular-nums text-primary">
                    {formatCurrency(summary.net_amount)}
                  </dd>
                </div>
              </dl>
              <p className="mt-6 border-t border-border pt-4 text-sm text-muted-foreground">
                Liquidamos por periodos y solo lo ya entregado, pasados los cinco días hábiles
                del derecho de retracto. Un pedido con una reclamación abierta espera a que se
                resuelva.
              </p>
            </CardContent>
          </Card>
        </section>
      )}

      {/* ---------------- Cuenta bancaria ---------------- */}
      <section aria-labelledby="cuenta" className="mt-10">
        <h2 id="cuenta" className="mb-4 font-display text-xl font-bold">
          Dónde te consignamos
        </h2>

        {account && !isEditing ? (
          <Card>
            <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
              <div className="flex items-start gap-3">
                <Landmark className="mt-1 size-5 shrink-0 text-primary" aria-hidden="true" />
                <div>
                  <p className="font-medium">
                    {account.bank_name} · {account.account_type}
                  </p>
                  <p className="tabular-nums text-muted-foreground">{account.masked_number}</p>
                  <p className="text-sm text-muted-foreground">{account.holder_name}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                  Cambiar
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleDelete()}
                  disabled={isSaving}
                >
                  <Trash2 className="mr-1.5 size-4" aria-hidden="true" />
                  Retirar
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-6">
              {!account && (
                <p className="mb-5 border border-gold/40 bg-gold/10 px-4 py-3 text-sm">
                  <strong>Sin una cuenta registrada no podemos liquidarte.</strong> Tus ventas se
                  siguen acumulando, pero el dinero no tiene a dónde ir.
                </p>
              )}

              <form onSubmit={handleSave} className="grid gap-4 sm:grid-cols-2">
                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium">Banco</span>
                  <input
                    required
                    minLength={2}
                    maxLength={80}
                    value={form.bank_name}
                    onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
                    className="border border-input bg-background px-3 py-2"
                  />
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium">Tipo de cuenta</span>
                  <select
                    value={form.account_type}
                    onChange={(e) => setForm({ ...form, account_type: e.target.value })}
                    className="border border-input bg-background px-3 py-2"
                  >
                    <option value="ahorros">Ahorros</option>
                    <option value="corriente">Corriente</option>
                  </select>
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium">Número de cuenta</span>
                  <input
                    required
                    inputMode="numeric"
                    value={form.account_number}
                    onChange={(e) => setForm({ ...form, account_number: e.target.value })}
                    className="border border-input bg-background px-3 py-2 tabular-nums"
                  />
                  <span className="text-xs text-muted-foreground">
                    Puedes escribirlo con guiones, como viene en el extracto.
                  </span>
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium">Titular</span>
                  <input
                    required
                    minLength={3}
                    maxLength={150}
                    value={form.holder_name}
                    onChange={(e) => setForm({ ...form, holder_name: e.target.value })}
                    className="border border-input bg-background px-3 py-2"
                  />
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium">Documento del titular</span>
                  <input
                    required
                    minLength={5}
                    maxLength={30}
                    value={form.holder_document}
                    onChange={(e) => setForm({ ...form, holder_document: e.target.value })}
                    className="border border-input bg-background px-3 py-2 tabular-nums"
                  />
                </label>

                {formError && (
                  <p role="alert" className="sm:col-span-2 text-sm text-destructive">
                    {formError}
                  </p>
                )}

                <div className="flex gap-2 sm:col-span-2">
                  <Button type="submit" disabled={isSaving}>
                    {isSaving ? "Guardando…" : "Guardar cuenta"}
                  </Button>
                  {account && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setIsEditing(false);
                        setFormError(null);
                      }}
                    >
                      Cancelar
                    </Button>
                  )}
                </div>
              </form>

              <p className="mt-5 border-t border-border pt-4 text-xs text-muted-foreground">
                La cuenta se guarda cifrada. Ni el equipo de MONK GRAIN la ve en la plataforma: de
                vuelta solo viajan los cuatro últimos dígitos, para que puedas reconocerla.
              </p>
            </CardContent>
          </Card>
        )}
      </section>

      {/* ---------------- Historial ---------------- */}
      <section aria-labelledby="historial" className="mt-10">
        <h2 id="historial" className="mb-4 font-display text-xl font-bold">
          Historial
        </h2>

        {settlements.length === 0 ? (
          <EmptyState
            title="Todavía no hay liquidaciones"
            description="Aquí aparecerá cada periodo liquidado, con su importe y su referencia de pago."
          />
        ) : (
          <Card>
            <CardContent className="pt-6">
              <ul className="divide-y divide-border">
                {settlements.map((liquidacion) => {
                  const meta = SETTLEMENT_STATUS_META[liquidacion.status];
                  return (
                    <li key={liquidacion.id} className="py-4 first:pt-0 last:pb-0">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-medium">
                            {formatDateShort(liquidacion.period_start)} —{" "}
                            {formatDateShort(liquidacion.period_end)}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {liquidacion.sub_orders_count}{" "}
                            {liquidacion.sub_orders_count === 1 ? "pedido" : "pedidos"} ·{" "}
                            {formatCurrency(liquidacion.gross_amount)} menos{" "}
                            {formatCurrency(liquidacion.commission_total)} de comisión
                          </p>
                          {liquidacion.payment_reference && (
                            <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
                              <Banknote className="size-4" aria-hidden="true" />
                              Referencia {liquidacion.payment_reference}
                              {liquidacion.paid_at &&
                                ` · ${formatDateShort(liquidacion.paid_at)}`}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                          <span className="whitespace-nowrap font-display font-semibold tabular-nums">
                            {formatCurrency(liquidacion.net_amount)}
                          </span>
                        </div>
                      </div>
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
