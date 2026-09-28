"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Eye, EyeOff, Flag } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Stars } from "@/features/reviews/components/Stars";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/input";
import { adminApi, type ReportedReview } from "@/features/dashboard/api";
import { ApiError } from "@/lib/api";
import { formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Cola de moderación de reseñas denunciadas.
 *
 * Se muestran los motivos de cada denuncia, que es lo que permite distinguir una
 * reseña que hay que ocultar de una que simplemente no gustó al vendedor. Una
 * reseña denunciada sigue publicada y contando en el promedio hasta que alguien
 * decida: la denuncia por sí sola no la retira.
 */

export default function AdminReviewsPage() {
  const router = useRouter();
  const [reviews, setReviews] = useState<ReportedReview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [hidingId, setHidingId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
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
      const page = await adminApi.reportedReviews(token);
      setReviews(page.items);
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

  async function moderate(review: ReportedReview, hide: boolean): Promise<void> {
    const token = session.getAccessToken();
    if (!token) return;

    setBusyId(review.id);
    setActionError(null);
    try {
      await adminApi.moderateReview(
        token,
        review.id,
        hide,
        hide ? reason.trim() : undefined,
      );
      setNotice(
        hide
          ? "Reseña ocultada. Ya no cuenta en el promedio del lote."
          : "Reseña restablecida.",
      );
      setHidingId(null);
      setReason("");
      await load();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos moderar la reseña.",
      );
    } finally {
      setBusyId(null);
    }
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <EmptyState
          icon={<Flag className="size-10" aria-hidden="true" />}
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

      <h1 className="font-display text-3xl font-bold">Reseñas denunciadas</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Una denuncia no retira nada: la reseña sigue publicada y contando en el promedio
        hasta que alguien decida. Lee los motivos antes de ocultar algo que quizá solo
        incomoda al vendedor.
      </p>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {actionError && (
        <p
          className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {actionError}
        </p>
      )}

      {isLoading && <Skeleton className="h-52 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && reviews.length === 0 && (
        <EmptyState
          icon={<Flag className="size-10" aria-hidden="true" />}
          title="No hay reseñas denunciadas"
          description="Cuando alguien denuncie una reseña, aparecerá aquí con su motivo."
        />
      )}

      {!isLoading && !error && reviews.length > 0 && (
        <ul className="space-y-4">
          {reviews.map((review) => {
            const isHidden = review.status === "hidden";
            return (
              <li key={review.id}>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium">{review.product_name}</p>
                        <div className="mt-1 flex items-center gap-2">
                          <Stars rating={review.rating} />
                          <span className="text-sm text-muted-foreground">
                            {review.author_name} · {formatDateShort(review.created_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <Badge variant={isHidden ? "default" : "warning"}>
                          {isHidden ? "Oculta" : "Publicada"}
                        </Badge>
                        <Badge variant="outline">
                          {review.report_count}{" "}
                          {review.report_count === 1 ? "denuncia" : "denuncias"}
                        </Badge>
                      </div>
                    </div>

                    {review.comment && (
                      <p className="mt-3 rounded-md bg-muted px-3 py-2 text-sm italic">
                        «{review.comment}»
                      </p>
                    )}

                    {review.report_reasons.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-muted-foreground">
                          Motivos de la denuncia
                        </p>
                        <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-muted-foreground">
                          {review.report_reasons.map((motivo, index) => (
                            <li key={index}>{motivo}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {hidingId !== review.id && (
                      <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
                        {isHidden ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busyId === review.id}
                            onClick={() => void moderate(review, false)}
                          >
                            <Eye className="size-4" aria-hidden="true" />
                            Restablecer
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:bg-destructive/10"
                            disabled={busyId === review.id}
                            onClick={() => {
                              setHidingId(review.id);
                              setReason("");
                              setActionError(null);
                            }}
                          >
                            <EyeOff className="size-4" aria-hidden="true" />
                            Ocultar
                          </Button>
                        )}
                        <Link
                          href={`/catalogo/${review.product_slug}`}
                          className="text-sm text-primary hover:underline"
                        >
                          Ver el lote
                        </Link>
                      </div>
                    )}

                    {hidingId === review.id && (
                      <div className="mt-4 space-y-3 border-t border-border pt-4">
                        <div>
                          <Label htmlFor={`reason-${review.id}`}>
                            Motivo de la decisión
                          </Label>
                          <textarea
                            id={`reason-${review.id}`}
                            value={reason}
                            onChange={(event) => setReason(event.target.value)}
                            rows={2}
                            maxLength={500}
                            placeholder="Queda guardado con la reseña y en la auditoría."
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          />
                          <p className="mt-1.5 text-xs text-muted-foreground">
                            Al ocultarla deja de contar en el promedio del lote.
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={busyId === review.id}
                            onClick={() => void moderate(review, true)}
                          >
                            Confirmar y ocultar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setHidingId(null)}
                          >
                            Volver
                          </Button>
                        </div>
                      </div>
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
