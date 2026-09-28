"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Undo2 } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  RETURN_STATUS_META,
  returnsApi,
  type ReturnSummary,
} from "@/features/returns/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Devoluciones de las ventas del productor.
 *
 * El servidor las devuelve ordenadas por vencimiento, así que el orden de la
 * lista es el orden en que hay que responder para no incumplir los quince días
 * hábiles del Decreto 735 de 2013.
 */
export default function ProducerReturnsPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<ReturnSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(null);
    try {
      const page = await returnsApi.forProducer(token);
      setRequests(page.items);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 403
          ? "Esta sección es para vendedores aprobados."
          : "No pudimos cargar tus devoluciones.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link
        href="/productor"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi panel
      </Link>

      <h1 className="font-display text-3xl font-bold">Devoluciones</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Tienes quince días hábiles para responder por escrito cada reclamación. Las de
        arriba son las que vencen antes.
      </p>

      {isLoading && <Skeleton className="h-40 w-full" />}
      {!isLoading && error && <ErrorState title={error} onRetry={() => void load()} />}

      {!isLoading && !error && requests.length === 0 && (
        <EmptyState
          icon={<Undo2 className="size-10" aria-hidden="true" />}
          title="No tienes devoluciones"
          description="Aquí aparecerán las reclamaciones sobre tus ventas."
        />
      )}

      {!isLoading && !error && requests.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <ul className="divide-y divide-border">
              {requests.map((request) => {
                const meta = RETURN_STATUS_META[request.status];
                const isOverdue =
                  request.status === "requested" && request.response_due_at < today;
                return (
                  <li key={request.id} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          href={`/productor/devoluciones/${request.id}`}
                          className="font-medium hover:text-primary"
                        >
                          {request.return_number}
                        </Link>
                        <p className="text-sm text-muted-foreground">
                          {request.sub_order_number} · {request.reason_label} ·{" "}
                          {request.item_count}{" "}
                          {request.item_count === 1 ? "unidad" : "unidades"}
                        </p>
                        <p
                          className={
                            isOverdue
                              ? "text-sm font-medium text-destructive"
                              : "text-sm text-muted-foreground"
                          }
                        >
                          {request.status === "requested"
                            ? `Responder antes del ${formatDateShort(request.response_due_at)}`
                            : `Radicada el ${formatDateShort(request.filed_at)}`}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={meta.variant}>{meta.label}</Badge>
                        {request.refund_amount && (
                          <span className="whitespace-nowrap font-display font-semibold">
                            {formatCurrency(request.refund_amount)}
                          </span>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
