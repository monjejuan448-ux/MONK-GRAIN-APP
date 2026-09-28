"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Coffee,
  DollarSign,
  Flag,
  ScrollText,
  ShoppingCart,
  UserCheck,
  Users,
} from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { StatCard } from "@/components/shared/StatCard";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ORDER_STATUS_META,
  adminApi,
  type AdminDashboard,
  type PendingProducer,
} from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

export default function AdminDashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [pending, setPending] = useState<PendingProducer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(null);
    try {
      const [dashboard, pendingPage] = await Promise.all([
        adminApi.dashboard(token),
        adminApi.pendingProducers(token),
      ]);
      setData(dashboard);
      setPending(pendingPage.items);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 403) {
        setForbidden(true);
      } else {
        setError("No pudimos cargar el panel administrativo.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function review(producerId: string, approve: boolean, reason?: string) {
    const token = session.getAccessToken();
    if (!token) return;

    setBusyId(producerId);
    setError(null);
    try {
      await adminApi.reviewProducer(token, producerId, approve, reason);
      setRejectingId(null);
      setRejectReason("");
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos procesar la decisión.",
      );
    } finally {
      setBusyId(null);
    }
  }

  if (isLoading) {
    return (
      <div className="container-page py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-72" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="container-page py-16">
        <EmptyState
          title="Acceso restringido"
          description="Esta sección solo está disponible para administradores de la plataforma."
        />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="container-page py-16">
        <ErrorState onRetry={() => void load()} />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Panel administrativo</h1>
        <p className="mt-2 text-muted-foreground">Actividad de los últimos 30 días.</p>

        <nav
          aria-label="Secciones de administración"
          className="mt-5 flex flex-wrap gap-2"
        >
          <Link
            href="/admin/usuarios"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            <Users className="mr-1.5 size-4" aria-hidden="true" />
            Cuentas
          </Link>
          <Link
            href="/admin/resenas"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            <Flag className="mr-1.5 size-4" aria-hidden="true" />
            Reseñas denunciadas
            {data && data.reported_reviews > 0 && (
              <Badge variant="warning" className="ml-1.5">
                {data.reported_reviews}
              </Badge>
            )}
          </Link>
          <Link
            href="/admin/auditoria"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            <ScrollText className="mr-1.5 size-4" aria-hidden="true" />
            Auditoría
          </Link>
        </nav>
      </header>

      {error && (
        <p
          className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      )}

      <section aria-labelledby="metricas" className="mb-10">
        <h2 id="metricas" className="sr-only">
          Métricas de la plataforma
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Usuarios"
            value={data.total_users}
            hint={`${data.new_users_period} nuevos en el periodo`}
            icon={Users}
          />
          <StatCard
            label="Vendedores pendientes"
            value={data.pending_producers}
            hint={`${data.approved_producers} aprobados`}
            icon={UserCheck}
            emphasis={data.pending_producers > 0 ? "warning" : "default"}
          />
          <StatCard
            label="Facturación del periodo"
            value={formatCurrency(data.revenue_period)}
            hint={`Comisión: ${formatCurrency(data.commission_period)}`}
            icon={DollarSign}
            emphasis="success"
          />
          <StatCard
            label="Pedidos del periodo"
            value={data.orders_period}
            icon={ShoppingCart}
          />
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <StatCard
            label="Productos publicados"
            value={`${data.published_products} / ${data.total_products}`}
            icon={Coffee}
          />
          <StatCard
            label="Reseñas reportadas"
            value={data.reported_reviews}
            emphasis={data.reported_reviews > 0 ? "warning" : "default"}
          />
        </div>

        {Object.keys(data.orders_by_status).length > 0 && (
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-semibold">Pedidos por estado</h3>
            <ul className="flex flex-wrap gap-2">
              {Object.entries(data.orders_by_status).map(([status, count]) => {
                const meta = ORDER_STATUS_META[status] ?? {
                  label: status,
                  variant: "default" as const,
                };
                return (
                  <li key={status}>
                    <Badge variant={meta.variant} size="md">
                      {meta.label}: {count}
                    </Badge>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>

      {/* ---------------- Aprobación de vendedores ---------------- */}
      <section aria-labelledby="pendientes">
        <h2 id="pendientes" className="mb-4 font-display text-xl font-bold">
          Solicitudes de vendedor
        </h2>

        {pending.length === 0 ? (
          <EmptyState
            title="No hay solicitudes pendientes"
            description="Cuando alguien se registre como productor, aparecerá aquí para su revisión."
          />
        ) : (
          <ul className="space-y-4">
            {pending.map((producer) => (
              <li key={producer.id}>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0">
                        <h3 className="font-display text-lg font-semibold">
                          {producer.brand_name ?? producer.legal_name}
                        </h3>
                        <dl className="mt-2 space-y-1 text-sm text-muted-foreground">
                          <div className="flex gap-2">
                            <dt>Razón social:</dt>
                            <dd className="text-foreground">{producer.legal_name}</dd>
                          </div>
                          <div className="flex gap-2">
                            <dt>Documento:</dt>
                            <dd className="text-foreground">
                              {producer.document_number}
                            </dd>
                          </div>
                          <div className="flex gap-2">
                            <dt>Contacto:</dt>
                            <dd className="text-foreground">
                              {producer.contact_name} · {producer.contact_email}
                            </dd>
                          </div>
                          <div className="flex gap-2">
                            <dt>Ubicación:</dt>
                            <dd className="text-foreground">
                              {[producer.municipality, producer.department]
                                .filter(Boolean)
                                .join(", ")}
                            </dd>
                          </div>
                          <div className="flex gap-2">
                            <dt>Solicitud:</dt>
                            <dd className="text-foreground">
                              {formatDateShort(producer.created_at)}
                            </dd>
                          </div>
                        </dl>
                      </div>

                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => review(producer.id, true)}
                          isLoading={
                            busyId === producer.id && rejectingId !== producer.id
                          }
                        >
                          Aprobar
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setRejectingId(
                              rejectingId === producer.id ? null : producer.id,
                            )
                          }
                        >
                          Rechazar
                        </Button>
                      </div>
                    </div>

                    {/* El motivo del rechazo es obligatorio: sin él, el productor
                        no sabe qué corregir para volver a intentarlo. */}
                    {rejectingId === producer.id && (
                      <div className="mt-4 border-t border-border pt-4">
                        <label
                          htmlFor={`reason-${producer.id}`}
                          className="mb-1.5 block text-sm font-medium"
                        >
                          Motivo del rechazo <span className="text-destructive">*</span>
                        </label>
                        <textarea
                          id={`reason-${producer.id}`}
                          value={rejectReason}
                          onChange={(event) => setRejectReason(event.target.value)}
                          rows={2}
                          placeholder="Explica qué debe corregir para volver a postularse."
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        />
                        <Button
                          size="sm"
                          variant="destructive"
                          className="mt-2"
                          disabled={rejectReason.trim().length < 5}
                          isLoading={busyId === producer.id}
                          onClick={() => review(producer.id, false, rejectReason)}
                        >
                          Confirmar rechazo
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
