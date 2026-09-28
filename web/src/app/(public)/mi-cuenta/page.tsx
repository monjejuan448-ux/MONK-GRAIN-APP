"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Heart, MapPin, MessageSquare, Package, ShoppingBag, Undo2 } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { StatCard } from "@/components/shared/StatCard";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authApi, type CurrentUser } from "@/features/auth/api";
import { orderApi, type OrderSummary } from "@/features/cart/api";
import { ORDER_STATUS_META } from "@/features/dashboard/api";
import { formatCurrency, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

/** Estados agregados del pedido, distintos de los de sub-orden. */
const ORDER_LABELS: Record<string, string> = {
  pending: "Pendiente de pago",
  processing: "En proceso",
  partially_shipped: "Envío parcial",
  completed: "Completado",
  cancelled: "Cancelado",
  refunded: "Reembolsado",
};

export default function BuyerAccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      const [profile, orderPage] = await Promise.all([
        authApi.me(token),
        orderApi.list(token),
      ]);
      setUser(profile);
      setOrders(orderPage.items);
    } catch {
      setError(true);
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
        <Skeleton className="mb-8 h-9 w-56" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="container-page py-16">
        <ErrorState onRetry={() => void load()} />
      </div>
    );
  }

  const inProgress = orders.filter(
    (order) => order.status === "pending" || order.status === "processing",
  ).length;
  const completed = orders.filter((order) => order.status === "completed").length;

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">
          Hola, {user.full_name.split(" ")[0]}
        </h1>
        <p className="mt-2 text-muted-foreground">{user.email}</p>
      </header>

      <div className="mb-10 grid gap-4 sm:grid-cols-3">
        <StatCard label="Pedidos totales" value={orders.length} icon={ShoppingBag} />
        <StatCard label="En proceso" value={inProgress} icon={Package} />
        <StatCard label="Completados" value={completed} emphasis="success" />
      </div>

      <div className="grid gap-8 lg:grid-cols-[1.5fr_1fr]">
        <section aria-labelledby="pedidos">
          <h2 id="pedidos" className="mb-4 font-display text-xl font-bold">
            Mis pedidos
          </h2>

          {orders.length === 0 ? (
            <EmptyState
              title="Aún no has hecho ningún pedido"
              description="Explora el catálogo y encuentra tu próximo café."
              action={
                <Link
                  href="/catalogo"
                  className={cn(buttonVariants({ variant: "primary", size: "md" }))}
                >
                  Ver catálogo
                </Link>
              }
            />
          ) : (
            <Card>
              <CardContent className="pt-6">
                <ul className="divide-y divide-border">
                  {orders.map((order) => (
                    <li key={order.id} className="py-3 first:pt-0 last:pb-0">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="min-w-0">
                          <Link
                            href={`/mi-cuenta/pedidos/${order.id}`}
                            className="font-medium hover:text-primary"
                          >
                            {order.order_number}
                          </Link>
                          <p className="text-sm text-muted-foreground">
                            {formatDateShort(order.placed_at)} · {order.item_count}{" "}
                            {order.item_count === 1 ? "producto" : "productos"}
                            {order.seller_count > 1 &&
                              ` · ${order.seller_count} vendedores`}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge
                            variant={
                              ORDER_STATUS_META[order.status]?.variant ?? "default"
                            }
                          >
                            {ORDER_LABELS[order.status] ?? order.status}
                          </Badge>
                          <span className="whitespace-nowrap font-display font-semibold">
                            {formatCurrency(order.grand_total)}
                          </span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </section>

        <section aria-labelledby="accesos">
          <h2 id="accesos" className="mb-4 font-display text-xl font-bold">
            Mi cuenta
          </h2>
          <Card>
            <CardContent className="pt-6">
              <ul className="space-y-1">
                <AccountLink
                  href="/mi-cuenta/resenas"
                  icon={MessageSquare}
                  label="Cafés por reseñar"
                />
                <AccountLink
                  href="/mi-cuenta/devoluciones"
                  icon={Undo2}
                  label="Mis devoluciones"
                />
                <AccountLink href="/favoritos" icon={Heart} label="Mis favoritos" />
                <AccountLink
                  href="/mi-cuenta/direcciones"
                  icon={MapPin}
                  label="Direcciones"
                />
                <AccountLink
                  href="/mi-cuenta/perfil"
                  icon={ShoppingBag}
                  label="Datos personales"
                />
              </ul>

              {user.roles.some((role) => role.code === "producer") && (
                <Link
                  href="/productor"
                  className={cn(
                    buttonVariants({ variant: "secondary", size: "md" }),
                    "mt-4 w-full",
                  )}
                >
                  Ir a mi panel de productor
                </Link>
              )}

              {user.roles.some((role) => role.code === "admin") && (
                <Link
                  href="/admin"
                  className={cn(
                    buttonVariants({ variant: "outline", size: "md" }),
                    "mt-2 w-full",
                  )}
                >
                  Panel administrativo
                </Link>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}

function AccountLink({
  href,
  icon: Icon,
  label,
}: {
  href: string;
  icon: typeof Heart;
  label: string;
}) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm hover:bg-muted"
      >
        <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
        {label}
      </Link>
    </li>
  );
}
