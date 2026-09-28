"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ScrollText } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { adminApi, type AuditLogEntry } from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Registro de auditoría.
 *
 * Solo se lee: no hay endpoint para editarlo ni borrarlo, y el rol de aplicación
 * en PostgreSQL únicamente tiene permiso de inserción y lectura sobre esa tabla.
 * Esta pantalla es la única forma de consultarlo desde la aplicación.
 */

/** Traducción de las acciones que registra el sistema. Una acción sin traducir
 *  se muestra con su código: es preferible a esconderla. */
const ACTION_LABELS: Record<string, string> = {
  "producer.approve": "Vendedor aprobado",
  "producer.reject": "Vendedor rechazado",
  "user.suspend": "Cuenta suspendida",
  "user.reactivate": "Cuenta reactivada",
  "review.hide": "Reseña ocultada",
  "review.restore": "Reseña restablecida",
};

const ENTITY_LABELS: Record<string, string> = {
  user: "Cuenta",
  producer_profile: "Vendedor",
  review: "Reseña",
  product: "Lote",
};

export default function AdminAuditPage() {
  const router = useRouter();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      const page = await adminApi.auditLogs(token);
      setEntries(page.items);
      setTotal(page.total);
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
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <EmptyState
          icon={<ScrollText className="size-10" aria-hidden="true" />}
          title="Esta sección es de administración"
          description="Tu cuenta no tiene ese rol."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/admin"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver al panel
      </Link>

      <h1 className="font-display text-3xl font-bold">Registro de auditoría</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Cada decisión administrativa con quién la tomó y cuándo. El registro es inmutable:
        no existe forma de editarlo ni de borrarlo, tampoco desde aquí.
      </p>

      {isLoading && <Skeleton className="h-64 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && entries.length === 0 && (
        <EmptyState
          icon={<ScrollText className="size-10" aria-hidden="true" />}
          title="El registro está vacío"
          description="Aún no se ha tomado ninguna decisión administrativa."
        />
      )}

      {!isLoading && !error && entries.length > 0 && (
        <>
          <p className="mb-3 text-sm text-muted-foreground">
            {total} {total === 1 ? "anotación" : "anotaciones"}
          </p>
          <Card>
            <CardContent className="pt-6">
              <ol className="divide-y divide-border">
                {entries.map((entry) => (
                  <li key={entry.id} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="font-medium">
                        {ACTION_LABELS[entry.action] ?? entry.action}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(entry.created_at)}
                      </span>
                    </div>
                    <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <Badge variant="outline">
                        {ENTITY_LABELS[entry.entity_type] ?? entry.entity_type}
                      </Badge>
                      {entry.actor_email ?? "sistema"}
                      {entry.entity_id && (
                        <span className="font-mono text-xs">{entry.entity_id}</span>
                      )}
                    </p>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
