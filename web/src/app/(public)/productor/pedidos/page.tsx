"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Package, Truck } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import {
  ORDER_STATUS_META,
  producerApi,
  SELLER_NEXT_STATUSES,
  STATUS_ACTION_LABELS,
  type ProducerOrder,
} from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

/**
 * Bandeja de pedidos recibidos (HU-PRO-07).
 *
 * Es donde el vendedor cumple: confirma, prepara, despacha con su guía y, si no
 * puede cumplir, cancela. El panel del productor solo mostraba los pedidos en
 * modo lectura, así que el ciclo quedaba cortado justo después del pago.
 *
 * El grafo de transiciones lo impone el servidor; aquí solo se ofrecen los
 * avances válidos para no proponer un botón que va a ser rechazado.
 */

const FILTERS: Array<{ value: string; label: string }> = [
  { value: "", label: "Todos" },
  { value: "pending", label: "Por confirmar" },
  { value: "confirmed", label: "Por preparar" },
  { value: "prepared", label: "Por despachar" },
  { value: "shipped", label: "En tránsito" },
  { value: "delivered", label: "Entregados" },
  { value: "cancelled", label: "Cancelados" },
];

/** Avance en curso: el formulario que hace falta según a dónde se va. */
type Pending = { order: ProducerOrder; target: string } | null;

export default function ProducerOrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<ProducerOrder[]>([]);
  const [filter, setFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [forbidden, setForbidden] = useState(false);

  const [pending, setPending] = useState<Pending>(null);
  const [carrier, setCarrier] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [note, setNote] = useState("");
  const [isSaving, setIsSaving] = useState(false);
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
      const page = await producerApi.orders(token, filter || undefined);
      setOrders(page.items);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        router.push("/ingresar");
        return;
      }
      // Un 403 no es un fallo de carga: es una cuenta que no es de vendedor, o
      // un vendedor cuya solicitud aún no ha sido aprobada.
      if (requestError instanceof ApiError && requestError.status === 403) {
        setForbidden(true);
        return;
      }
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router, filter]);

  useEffect(() => {
    void load();
  }, [load]);

  function startAdvance(order: ProducerOrder, target: string): void {
    setActionError(null);
    setCarrier("");
    setTrackingNumber("");
    setNote("");

    // Despachar y cancelar piden datos; los demás avances no necesitan nada y
    // se aplican de una vez, sin un paso intermedio que no aporta.
    if (target === "shipped" || target === "cancelled") {
      setPending({ order, target });
      return;
    }
    void submitAdvance(order, target);
  }

  async function submitAdvance(
    order: ProducerOrder,
    target: string,
    extra: { carrier?: string; tracking_number?: string; note?: string } = {},
  ): Promise<void> {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setIsSaving(true);
    setActionError(null);
    try {
      await producerApi.updateOrderStatus(token, order.sub_order_id, {
        status: target,
        ...extra,
      });
      setNotice(
        `Pedido ${order.sub_order_number}: ${ORDER_STATUS_META[target]?.label ?? target}.`,
      );
      setPending(null);
      await load();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos actualizar el pedido. Inténtalo de nuevo.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  function handleFormSubmit(event: React.FormEvent): void {
    event.preventDefault();
    if (!pending) return;

    if (pending.target === "cancelled" && note.trim().length < 5) {
      setActionError("Explica por qué se cancela: el comprador recibe ese motivo.");
      return;
    }

    void submitAdvance(
      pending.order,
      pending.target,
      pending.target === "shipped"
        ? {
            // Vacíos se omiten: el operador simulado genera la guía de prueba.
            carrier: carrier.trim() || undefined,
            tracking_number: trackingNumber.trim() || undefined,
            note: note.trim() || undefined,
          }
        : { note: note.trim() },
    );
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <EmptyState
          icon={<Package className="size-10" aria-hidden="true" />}
          title="Esta sección es para vendedores"
          description="Si ya enviaste tu solicitud, un administrador debe aprobarla antes de que puedas recibir pedidos."
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
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link
        href="/productor"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver al panel
      </Link>

      <h1 className="font-display text-3xl font-bold">Pedidos recibidos</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Cada pedido avanza de un estado al siguiente y el comprador ve el cambio. Un
        pedido ya despachado no se cancela: se devuelve, desde la sección de devoluciones.
      </p>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {/* ---------------- Filtros ---------------- */}
      <div
        className="mb-6 flex flex-wrap gap-2"
        role="group"
        aria-label="Filtrar pedidos por estado"
      >
        {FILTERS.map((item) => (
          <button
            key={item.value}
            type="button"
            aria-pressed={filter === item.value}
            onClick={() => setFilter(item.value)}
            className={cn(
              "rounded-full border px-3.5 py-1.5 text-sm transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              filter === item.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border hover:bg-muted",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {actionError && !pending && (
        <p
          className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {actionError}
        </p>
      )}

      {isLoading && <Skeleton className="h-52 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && orders.length === 0 && (
        <EmptyState
          icon={<Package className="size-10" aria-hidden="true" />}
          title={filter ? "Ningún pedido en este estado" : "Aún no has recibido pedidos"}
          description={
            filter
              ? "Prueba con otro filtro."
              : "Cuando alguien compre tu café, el pedido aparecerá aquí para que lo despaches."
          }
        />
      )}

      {!isLoading && !error && orders.length > 0 && (
        <ul className="space-y-4">
          {orders.map((order) => {
            const meta = ORDER_STATUS_META[order.status] ?? {
              label: order.status,
              variant: "default" as const,
            };
            const nextStatuses = SELLER_NEXT_STATUSES[order.status] ?? [];
            const isPending = pending?.order.sub_order_id === order.sub_order_id;

            return (
              <li key={order.sub_order_id}>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-display font-semibold">
                            {order.sub_order_number}
                          </span>
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                        </div>
                        <p className="mt-1.5 text-sm text-muted-foreground">
                          {formatDateShort(order.created_at)} · {order.buyer_name}
                          {order.shipping_city && ` · ${order.shipping_city}`}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {order.item_count}{" "}
                          {order.item_count === 1 ? "artículo" : "artículos"} · pedido{" "}
                          {order.order_number}
                        </p>
                      </div>

                      <div className="text-right">
                        <p className="font-display text-lg font-semibold">
                          {formatCurrency(order.subtotal)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Recibes {formatCurrency(order.net_amount)}
                        </p>
                      </div>
                    </div>

                    {/* ---------------- Avances ---------------- */}
                    {nextStatuses.length > 0 && !isPending && (
                      <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
                        {nextStatuses.map((target) => (
                          <Button
                            key={target}
                            size="sm"
                            variant={target === "cancelled" ? "ghost" : "primary"}
                            className={
                              target === "cancelled"
                                ? "text-destructive hover:bg-destructive/10"
                                : undefined
                            }
                            disabled={isSaving}
                            onClick={() => startAdvance(order, target)}
                          >
                            {target === "shipped" && (
                              <Truck className="size-4" aria-hidden="true" />
                            )}
                            {STATUS_ACTION_LABELS[target] ?? target}
                          </Button>
                        ))}
                      </div>
                    )}

                    {isPending && pending && (
                      <form
                        onSubmit={handleFormSubmit}
                        noValidate
                        className="mt-4 space-y-4 border-t border-border pt-4"
                      >
                        <h3 className="font-display font-semibold">
                          {pending.target === "shipped"
                            ? "Datos del despacho"
                            : "Motivo de la cancelación"}
                        </h3>

                        {actionError && (
                          <p className="text-sm text-destructive" role="alert">
                            {actionError}
                          </p>
                        )}

                        {pending.target === "shipped" ? (
                          <>
                            <div className="grid gap-4 sm:grid-cols-2">
                              <div>
                                <Label htmlFor={`carrier-${order.sub_order_id}`}>
                                  Transportadora
                                </Label>
                                <Input
                                  id={`carrier-${order.sub_order_id}`}
                                  value={carrier}
                                  onChange={(event) => setCarrier(event.target.value)}
                                  maxLength={50}
                                  placeholder="Servientrega, Coordinadora…"
                                />
                              </div>
                              <div>
                                <Label htmlFor={`tracking-${order.sub_order_id}`}>
                                  Número de guía
                                </Label>
                                <Input
                                  id={`tracking-${order.sub_order_id}`}
                                  value={trackingNumber}
                                  onChange={(event) =>
                                    setTrackingNumber(event.target.value)
                                  }
                                  maxLength={80}
                                />
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Si aún no tienes la guía puedes despachar sin ella: se
                              genera una de prueba y podrás registrar la real después.
                            </p>
                          </>
                        ) : (
                          <div>
                            <Label htmlFor={`note-${order.sub_order_id}`} required>
                              Explica qué ocurrió
                            </Label>
                            <textarea
                              id={`note-${order.sub_order_id}`}
                              value={note}
                              onChange={(event) => setNote(event.target.value)}
                              rows={3}
                              maxLength={500}
                              placeholder="Ej. El lote no pasó el control de humedad."
                              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                            />
                            <p className="mt-1.5 text-xs text-muted-foreground">
                              El comprador recibe este motivo y las unidades vuelven a tu
                              inventario.
                            </p>
                          </div>
                        )}

                        <div className="flex flex-wrap gap-3">
                          <Button
                            type="submit"
                            size="sm"
                            isLoading={isSaving}
                            variant={
                              pending.target === "cancelled" ? "destructive" : "primary"
                            }
                          >
                            {pending.target === "shipped"
                              ? "Confirmar despacho"
                              : "Cancelar el pedido"}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            disabled={isSaving}
                            onClick={() => {
                              setPending(null);
                              setActionError(null);
                            }}
                          >
                            Volver
                          </Button>
                        </div>
                      </form>
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
