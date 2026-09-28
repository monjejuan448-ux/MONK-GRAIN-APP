"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Coffee, Package, Star, TrendingUp, Wallet } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { StatCard } from "@/components/shared/StatCard";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ORDER_STATUS_META,
  producerApi,
  type ProducerDashboard,
  type ProducerOrder,
} from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDateShort, formatRating } from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

export default function ProducerDashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<ProducerDashboard | null>(null);
  const [orders, setOrders] = useState<ProducerOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(null);
    try {
      const [dashboard, orderPage] = await Promise.all([
        producerApi.dashboard(token),
        producerApi.orders(token),
      ]);
      setData(dashboard);
      setOrders(orderPage.items.slice(0, 8));
    } catch (requestError) {
      // El backend ya rechaza a quien no es productor; aquí solo se traduce a
      // un mensaje comprensible en lugar de un error genérico.
      if (requestError instanceof ApiError && requestError.status === 403) {
        setForbidden(true);
      } else {
        setError("No pudimos cargar tu panel.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (isLoading) {
    return (
      <div className="container-page py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <p className="sr-only">Cargando tu panel de productor…</p>
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="container-page py-16">
        <EmptyState
          title="Esta sección es para productores"
          description="Tu cuenta no tiene un perfil de productor aprobado. Regístrate como vendedor para publicar tus cafés."
          action={
            <Link
              href="/vender"
              className={cn(buttonVariants({ variant: "primary", size: "lg" }))}
            >
              Registrarme como productor
            </Link>
          }
        />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState onRetry={() => void load()} />
      </div>
    );
  }

  return (
    <div className="container-page py-10">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Panel del productor</h1>
          <p className="mt-2 text-muted-foreground">
            Resumen de tus ventas, pedidos y catálogo.
          </p>
        </div>

        <nav aria-label="Gestión del catálogo" className="flex flex-wrap gap-2">
          <Link href="/productor/catalogo" className={cn(buttonVariants())}>
            <Coffee className="mr-1.5 size-4" aria-hidden="true" />
            Mis cafés
          </Link>
          <Link
            href="/productor/certificaciones"
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            Certificaciones
          </Link>
          <Link
            href="/productor/devoluciones"
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            Devoluciones
          </Link>
        </nav>
      </header>

      {/* ---------------- Métricas ---------------- */}
      <section aria-labelledby="metricas" className="mb-10">
        <h2 id="metricas" className="sr-only">
          Métricas principales
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Ventas confirmadas"
            value={formatCurrency(data.total_sales)}
            hint="No incluye pedidos sin pago confirmado"
            icon={TrendingUp}
          />
          <StatCard
            label="Ganancia neta"
            value={formatCurrency(data.net_earnings)}
            hint={`Comisión descontada: ${formatCurrency(data.commission_paid)}`}
            icon={Wallet}
            emphasis="success"
          />
          <StatCard
            label="Pedidos por atender"
            value={data.pending_orders + data.orders_to_prepare}
            hint={`${data.pending_orders} sin pago · ${data.orders_to_prepare} por preparar`}
            icon={Package}
            emphasis={data.orders_to_prepare > 0 ? "warning" : "default"}
          />
          <StatCard
            label="Calificación"
            value={data.rating_count > 0 ? formatRating(data.rating_avg) : "—"}
            hint={`${data.rating_count} ${data.rating_count === 1 ? "reseña" : "reseñas"}`}
            icon={Star}
          />
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Productos activos"
            value={data.active_products}
            icon={Coffee}
          />
          <StatCard label="Borradores" value={data.draft_products} icon={Coffee} />
          <StatCard
            label="Presentaciones con bajo inventario"
            value={data.low_stock_variants}
            icon={AlertTriangle}
            emphasis={data.low_stock_variants > 0 ? "warning" : "default"}
          />
        </div>
      </section>

      <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        {/* ---------------- Pedidos ---------------- */}
        <section aria-labelledby="pedidos">
          <div className="mb-4 flex items-center justify-between">
            <h2 id="pedidos" className="font-display text-xl font-bold">
              Pedidos recientes
            </h2>
            <Link
              href="/productor/pedidos"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
            >
              Ver todos
            </Link>
          </div>

          {orders.length === 0 ? (
            <EmptyState
              title="Aún no has recibido pedidos"
              description="Cuando un comprador adquiera uno de tus cafés, aparecerá aquí."
            />
          ) : (
            <Card>
              <CardContent className="pt-6">
                <ul className="divide-y divide-border">
                  {orders.map((order) => {
                    const meta = ORDER_STATUS_META[order.status] ?? {
                      label: order.status,
                      variant: "default" as const,
                    };
                    return (
                      <li
                        key={order.sub_order_id}
                        className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                      >
                        <div className="min-w-0">
                          <p className="font-medium">{order.sub_order_number}</p>
                          <p className="text-sm text-muted-foreground">
                            {order.buyer_name} · {order.item_count}{" "}
                            {order.item_count === 1 ? "producto" : "productos"} ·{" "}
                            {formatDateShort(order.created_at)}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                          <span className="whitespace-nowrap font-display font-semibold">
                            {formatCurrency(order.net_amount)}
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
          )}
        </section>

        {/* ---------------- Más vendidos ---------------- */}
        <section aria-labelledby="top">
          <h2 id="top" className="mb-4 font-display text-xl font-bold">
            Más vendidos
          </h2>

          {data.top_products.length === 0 ? (
            <EmptyState
              title="Sin ventas todavía"
              description="Aquí verás cuáles de tus cafés se venden más."
            />
          ) : (
            <Card>
              <CardContent className="pt-6">
                <ol className="space-y-4">
                  {data.top_products.map((product, index) => (
                    <li key={product.product_id} className="flex items-start gap-3">
                      <span
                        className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 font-display text-sm font-bold text-primary"
                        aria-hidden="true"
                      >
                        {index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/catalogo/${product.slug}`}
                          className="font-medium hover:text-primary"
                        >
                          {product.name}
                        </Link>
                        <p className="text-sm text-muted-foreground">
                          {product.units_sold}{" "}
                          {product.units_sold === 1 ? "unidad" : "unidades"} ·{" "}
                          {formatCurrency(product.revenue)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}
        </section>
      </div>
    </div>
  );
}
