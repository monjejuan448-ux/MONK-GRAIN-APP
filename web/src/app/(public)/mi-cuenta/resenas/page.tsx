"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, MessageSquare } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { reviewsApi, type PendingReview } from "@/features/reviews/api";
import { StarPicker } from "@/features/reviews/components/Stars";
import { ApiError } from "@/lib/api";
import { formatDateShort } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Cafés entregados que este comprador todavía no ha reseñado (RF-06.4).
 *
 * La lista la calcula el servidor: cruzar pedidos entregados con reseñas
 * existentes en el cliente exigiría traerse ambas cosas enteras, y quedaría
 * desfasada en cuanto alguien reseñara desde otra pantalla.
 */
export default function PendingReviewsPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingReview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    const accessToken = session.getAccessToken();
    if (!accessToken) {
      router.push("/ingresar");
      return;
    }

    setToken(accessToken);
    setError(false);
    try {
      setPending(await reviewsApi.pending(accessToken));
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

      <h1 className="font-display text-3xl font-bold">Cafés por reseñar</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Tu opinión ayuda a quien todavía no sabe cuál elegir, y le dice al caficultor cómo
        llegó su café.
      </p>

      {isLoading && <Skeleton className="h-40 w-full" />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && pending.length === 0 && (
        <EmptyState
          icon={<MessageSquare className="size-10" aria-hidden="true" />}
          title="No tienes cafés pendientes de reseñar"
          description="Aquí aparecerán los cafés de tus pedidos entregados."
          action={
            <Link href="/catalogo" className="text-sm underline">
              Ver catálogo
            </Link>
          }
        />
      )}

      {!isLoading && !error && pending.length > 0 && token && (
        <ul className="space-y-5">
          {pending.map((item) => (
            <li key={item.order_item_id}>
              <ReviewForm
                item={item}
                token={token}
                onDone={() => {
                  setPending((current) =>
                    current.filter((other) => other.order_item_id !== item.order_item_id),
                  );
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ReviewForm({
  item,
  token,
  onDone,
}: {
  item: PendingReview;
  token: string;
  onDone: () => void;
}) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function submit() {
    if (rating < 1) {
      toast.error("Elige cuántas estrellas le das.");
      return;
    }

    setIsSaving(true);
    try {
      await reviewsApi.create(token, {
        order_item_id: item.order_item_id,
        rating,
        comment: comment.trim() || null,
      });
      toast.success("Publicamos tu reseña. Gracias.");
      onDone();
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : "No pudimos publicar tu reseña.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="mb-4">
          <Link
            href={`/catalogo/${item.product_slug}`}
            className="font-display font-semibold hover:text-primary"
          >
            {item.product_name}
          </Link>
          <p className="text-sm text-muted-foreground">
            {item.variant_label} · pedido {item.order_number}
            {item.delivered_at && (
              <> · entregado el {formatDateShort(item.delivered_at)}</>
            )}
          </p>
        </div>

        <StarPicker value={rating} onChange={setRating} disabled={isSaving} />

        <label
          htmlFor={`comentario-${item.order_item_id}`}
          className="mb-1.5 mt-4 block text-sm font-medium"
        >
          Tu comentario
        </label>
        <textarea
          id={`comentario-${item.order_item_id}`}
          rows={3}
          maxLength={2000}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder="¿Cómo te supo? ¿Con qué método lo preparaste?"
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        />

        <p className="mt-2 text-sm text-muted-foreground">
          Tu reseña se publica firmada con tu nombre de pila y la inicial de tu apellido.
          Puedes corregirla durante los treinta días siguientes, o eliminarla cuando
          quieras.
        </p>

        <Button
          type="button"
          className="mt-4"
          disabled={isSaving || rating < 1}
          onClick={() => void submit()}
        >
          {isSaving ? "Publicando…" : "Publicar reseña"}
        </Button>
      </CardContent>
    </Card>
  );
}
