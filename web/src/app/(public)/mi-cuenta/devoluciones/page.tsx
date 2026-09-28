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
import { formatCurrency, formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";

export default function BuyerReturnsPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<ReturnSummary[]>([]);
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
      const page = await returnsApi.mine(token);
      setRequests(page.items);
    } catch {
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/mi-cuenta"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi cuenta
      </Link>

      <h1 className="font-display text-3xl font-bold">Mis devoluciones</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Cada solicitud conserva su número de radicación. Consérvalo: es lo que acompaña
        una reclamación ante la autoridad.
      </p>

      {isLoading && <Skeleton className="h-40 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && requests.length === 0 && (
        <EmptyState
          icon={<Undo2 className="size-10" aria-hidden="true" />}
          title="No has solicitado ninguna devolución"
          description="Puedes hacerlo desde el detalle de cualquier pedido ya despachado."
        />
      )}

      {!isLoading && !error && requests.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <ul className="divide-y divide-border">
              {requests.map((request) => {
                const meta = RETURN_STATUS_META[request.status];
                return (
                  <li key={request.id} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          href={`/mi-cuenta/devoluciones/${request.id}`}
                          className="font-medium hover:text-primary"
                        >
                          {request.return_number}
                        </Link>
                        <p className="text-sm text-muted-foreground">
                          {formatDateShort(request.filed_at)} · {request.producer_name} ·{" "}
                          {request.reason_label}
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
