"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Flag, MessageSquare, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { reviewsApi, type Review, type ReviewSummary } from "@/features/reviews/api";
import { Stars } from "@/features/reviews/components/Stars";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Bloque de reseñas de la ficha del café.
 *
 * Se carga en el cliente y no en el servidor porque cambia según quién mire: la
 * propia reseña se marca como tuya y trae el botón de eliminarla, y las ajenas
 * el de reportarlas. Renderizarlo en el servidor obligaría a variar la caché de
 * la ficha por usuario para un bloque que está por debajo del pliegue.
 */
export function ProductReviews({ productId }: { productId: string }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    const accessToken = session.getAccessToken();
    setToken(accessToken);
    try {
      const [page, stats] = await Promise.all([
        reviewsApi.forProduct(productId, accessToken),
        reviewsApi.summary(productId),
      ]);
      setReviews(page.items);
      setSummary(stats);
    } catch {
      // Un fallo al cargar las reseñas no debe tumbar la ficha del café: el
      // bloque queda vacío y el resto de la página sigue siendo utilizable.
      setSummary(null);
    } finally {
      setIsLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function remove(reviewId: string) {
    if (!token) return;
    try {
      await reviewsApi.remove(token, reviewId);
      toast.success("Reseña eliminada.");
      await load();
    } catch {
      toast.error("No pudimos eliminar la reseña.");
    }
  }

  async function report(reviewId: string) {
    if (!token) {
      toast.error("Entra a tu cuenta para reportar una reseña.");
      return;
    }
    const reason = window.prompt("¿Por qué crees que esta reseña incumple las normas?");
    if (reason === null) return;
    if (reason.trim().length < 10) {
      toast.error("Cuéntanos con un poco más de detalle.");
      return;
    }

    try {
      const result = await reviewsApi.report(token, reviewId, reason.trim());
      toast.success(result.message);
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "No pudimos enviar el reporte.",
      );
    }
  }

  if (isLoading) {
    return (
      <section className="mt-16" aria-busy="true">
        <Skeleton className="mb-6 h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </section>
    );
  }

  return (
    <section className="mt-16" aria-labelledby="resenas">
      <h2 id="resenas" className="mb-6 font-display text-2xl font-bold">
        Lo que dicen quienes lo compraron
      </h2>

      {summary && summary.rating_count > 0 && (
        <div className="mb-8 flex flex-wrap items-center gap-8 rounded-lg border border-border p-6">
          <div className="text-center">
            <p className="font-display text-4xl font-bold">
              {summary.rating_avg.toFixed(1).replace(".", ",")}
            </p>
            <Stars rating={summary.rating_avg} size="md" />
            <p className="mt-1 text-sm text-muted-foreground">
              {summary.rating_count} {summary.rating_count === 1 ? "reseña" : "reseñas"}
            </p>
          </div>

          <ul className="min-w-52 flex-1 space-y-1.5">
            {[5, 4, 3, 2, 1].map((stars) => {
              const count = summary.distribution[String(stars)] ?? 0;
              const percent = summary.rating_count
                ? Math.round((count / summary.rating_count) * 100)
                : 0;
              return (
                <li key={stars} className="flex items-center gap-3 text-sm">
                  <span className="w-14 shrink-0 text-muted-foreground">
                    {stars} {stars === 1 ? "estrella" : "estrellas"}
                  </span>
                  <span
                    className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                    role="img"
                    aria-label={`${count} de ${summary.rating_count} reseñas dieron ${stars} ${
                      stars === 1 ? "estrella" : "estrellas"
                    }`}
                  >
                    <span
                      className="block h-full rounded-full bg-gold"
                      style={{ width: `${percent}%` }}
                    />
                  </span>
                  <span className="w-6 shrink-0 text-right tabular-nums text-muted-foreground">
                    {count}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {reviews.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="size-10" aria-hidden="true" />}
          title="Todavía nadie ha reseñado este café"
          description="Sé la primera persona en contar cómo te supo. Solo puede reseñar quien lo compró y lo recibió."
          action={
            <Link href="/mi-cuenta" className="text-sm underline">
              Ver mis pedidos entregados
            </Link>
          }
        />
      ) : (
        <ul className="space-y-5">
          {reviews.map((review) => (
            <li key={review.id} className="rounded-lg border border-border p-5">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <Stars rating={review.rating} />
                  <span className="font-medium">{review.author_name}</span>
                  {review.is_verified_purchase && (
                    <Badge variant="success">Compra verificada</Badge>
                  )}
                  {review.is_mine && <Badge variant="primary">Tu reseña</Badge>}
                </div>
                <time
                  dateTime={review.created_at}
                  className="text-sm text-muted-foreground"
                >
                  {formatDate(review.created_at)}
                </time>
              </div>

              {review.comment && (
                <p className="whitespace-pre-line text-sm">{review.comment}</p>
              )}

              <div className="mt-3 flex gap-2">
                {review.is_mine ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void remove(review.id)}
                  >
                    <Trash2 className="mr-1.5 size-4" aria-hidden="true" />
                    Eliminar
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => void report(review.id)}
                  >
                    <Flag className="mr-1.5 size-4" aria-hidden="true" />
                    Reportar
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
