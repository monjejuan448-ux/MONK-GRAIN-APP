"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Download, PackageX, Truck, Undo2 } from "lucide-react";
import { toast } from "sonner";

import { ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { orderApi, type OrderDetail, type SubOrder } from "@/features/cart/api";
import { ORDER_STATUS_META } from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDate, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

/**
 * Detalle del pedido del comprador.
 *
 * Es la página a la que apuntan las notificaciones y desde la que arrancan las
 * dos salidas que la ley reconoce: cancelar antes del despacho, y solicitar la
 * devolución después. Qué opción se ofrece no lo decide esta pantalla: viene
 * del servidor en `is_cancellable` y en la consulta de elegibilidad.
 */
export default function OrderDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [token, setToken] = useState<string | null>(null);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const accessToken = session.getAccessToken();
    if (!accessToken) {
      router.push("/ingresar");
      return;
    }

    setToken(accessToken);
    setError(null);
    try {
      setOrder(await orderApi.detail(accessToken, params.id));
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.isNotFound
          ? "No encontramos este pedido."
          : "No pudimos cargar el pedido.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [params.id, router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function downloadReceipt() {
    if (!token || !order) return;
    setIsDownloading(true);
    try {
      await orderApi.downloadReceipt(token, order.id, order.order_number);
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos generar el comprobante.",
      );
    } finally {
      setIsDownloading(false);
    }
  }

  async function cancel(subOrder: SubOrder) {
    if (!token) return;
    const reason = window.prompt(
      `¿Por qué quieres cancelar el envío de ${subOrder.producer_name}?`,
    );
    if (!reason || reason.trim().length < 5) {
      if (reason !== null) toast.error("Cuéntanos brevemente el motivo.");
      return;
    }

    try {
      await orderApi.cancelSubOrder(token, subOrder.id, reason.trim());
      toast.success("Pedido cancelado. El inventario vuelve al catálogo.");
      await load();
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cancelar el pedido.",
      );
    }
  }

  if (isLoading) {
    return (
      <div className="container-page py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="container-page py-16">
        <ErrorState title={error ?? undefined} onRetry={() => void load()} />
      </div>
    );
  }

  const address = order.shipping_address as Record<string, string | null>;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link
        href="/mi-cuenta"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi cuenta
      </Link>

      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">{order.order_number}</h1>
          <p className="mt-1 text-muted-foreground">
            Realizado el {formatDate(order.placed_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isDownloading}
            onClick={() => void downloadReceipt()}
          >
            <Download className="mr-1.5 size-4" aria-hidden="true" />
            {isDownloading ? "Generando…" : "Comprobante en PDF"}
          </Button>
          <span className="font-display text-2xl font-bold">
            {formatCurrency(order.grand_total)}
          </span>
        </div>
      </header>

      <div className="space-y-6">
        {order.sub_orders.map((subOrder) => (
          <SubOrderCard
            key={subOrder.id}
            subOrder={subOrder}
            onCancel={() => void cancel(subOrder)}
          />
        ))}
      </div>

      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        <Card>
          <CardContent className="pt-6">
            <h2 className="mb-3 font-display font-semibold">Entrega</h2>
            <address className="text-sm not-italic text-muted-foreground">
              <span className="block text-foreground">{address.recipient_name}</span>
              {address.street_address}
              {address.neighborhood && <>, {address.neighborhood}</>}
              <br />
              {address.phone}
            </address>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h2 className="mb-3 font-display font-semibold">Resumen</h2>
            <dl className="space-y-1.5 text-sm">
              <Row label="Productos" value={formatCurrency(order.subtotal)} />
              <Row label="Envío" value={formatCurrency(order.shipping_total)} />
              {Number(order.discount_total) > 0 && (
                <Row
                  label="Descuento"
                  value={`− ${formatCurrency(order.discount_total)}`}
                />
              )}
              <div className="border-t border-border pt-1.5">
                <Row label="Total" value={formatCurrency(order.grand_total)} emphasis />
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>

      <p className="mt-8 text-sm text-muted-foreground">
        Conoce tus derechos de{" "}
        <Link href="/legal/devoluciones" className="underline hover:text-foreground">
          devolución, retracto y garantía
        </Link>
        .
      </p>
    </div>
  );
}

function SubOrderCard({
  subOrder,
  onCancel,
}: {
  subOrder: SubOrder;
  onCancel: () => void;
}) {
  const meta = ORDER_STATUS_META[subOrder.status] ?? {
    label: subOrder.status,
    variant: "default" as const,
  };

  // El botón de devolución aparece desde el despacho. Si el plazo ya venció o
  // no queda nada por devolver, lo dice la propia pantalla de solicitud, que es
  // quien consulta la elegibilidad al servidor.
  const canOpenReturn = subOrder.status === "shipped" || subOrder.status === "delivered";

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display font-semibold">{subOrder.producer_name}</h2>
            <p className="text-sm text-muted-foreground">{subOrder.sub_order_number}</p>
          </div>
          <Badge variant={meta.variant}>{meta.label}</Badge>
        </div>

        <ul className="divide-y divide-border">
          {subOrder.items.map((item) => (
            <li key={item.id} className="flex items-baseline justify-between gap-4 py-2">
              <span className="min-w-0">
                <span className="block truncate">{item.product_name_snapshot}</span>
                <span className="text-sm text-muted-foreground">
                  {item.variant_label_snapshot} · {item.quantity}{" "}
                  {item.quantity === 1 ? "unidad" : "unidades"}
                </span>
              </span>
              <span className="whitespace-nowrap font-medium">
                {formatCurrency(item.line_total)}
              </span>
            </li>
          ))}
        </ul>

        {subOrder.shipment && (
          <p className="mt-4 flex items-center gap-2 rounded-md bg-muted/50 px-3 py-2 text-sm">
            <Truck className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <span>
              Guía {subOrder.shipment.tracking_number ?? "pendiente"} ·{" "}
              {subOrder.shipment.carrier}
              {subOrder.shipment.estimated_delivery_date && (
                <>
                  {" "}
                  · entrega estimada el{" "}
                  {formatDateShort(subOrder.shipment.estimated_delivery_date)}
                </>
              )}
            </span>
          </p>
        )}

        {subOrder.cancellation_reason && (
          <p className="mt-4 text-sm text-muted-foreground">
            Motivo de la cancelación: {subOrder.cancellation_reason}
          </p>
        )}

        <div className="mt-5 flex flex-wrap gap-2">
          {subOrder.is_cancellable && (
            <Button type="button" variant="outline" size="sm" onClick={onCancel}>
              <PackageX className="mr-1.5 size-4" aria-hidden="true" />
              Cancelar este envío
            </Button>
          )}

          {canOpenReturn && (
            <Link
              href={`/mi-cuenta/devoluciones/nueva?envio=${subOrder.id}`}
              className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
            >
              <Undo2 className="mr-1.5 size-4" aria-hidden="true" />
              Solicitar devolución
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function Row({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div className="flex justify-between">
      <dt className={emphasis ? "font-medium" : "text-muted-foreground"}>{label}</dt>
      <dd className={emphasis ? "font-display font-semibold" : ""}>{value}</dd>
    </div>
  );
}
