import { api } from "@/lib/api";

/**
 * Reseñas y calificaciones.
 *
 * Quién firma la reseña y sobre qué café recae los deduce el servidor de la
 * línea de pedido: aquí solo viajan la calificación y el texto.
 */

export interface Review {
  id: string;
  product_id: string;
  rating: number;
  comment: string | null;
  author_name: string;
  created_at: string;
  updated_at: string;
  is_verified_purchase: boolean;
  can_edit: boolean;
  is_mine: boolean;
}

export interface ReviewSummary {
  rating_avg: number;
  rating_count: number;
  /** Cuántas reseñas hay de cada calificación, de 1 a 5. */
  distribution: Record<string, number>;
}

export interface PendingReview {
  order_item_id: string;
  product_id: string;
  product_slug: string;
  product_name: string;
  variant_label: string;
  order_number: string;
  delivered_at: string | null;
}

interface PageResult<T> {
  items: T[];
  total: number;
}

export const reviewsApi = {
  forProduct: (productId: string, token?: string | null, page = 1) =>
    api.get<PageResult<Review>>(`/products/${productId}/reviews`, {
      token,
      query: { page },
    }),

  summary: (productId: string) =>
    api.get<ReviewSummary>(`/products/${productId}/reviews/summary`),

  create: (
    token: string,
    data: { order_item_id: string; rating: number; comment?: string | null },
  ) => api.post<Review>("/reviews", data, { token }),

  update: (
    token: string,
    reviewId: string,
    data: { rating: number; comment?: string | null },
  ) => api.put<Review>(`/reviews/${reviewId}`, data, { token }),

  remove: (token: string, reviewId: string) =>
    api.delete<void>(`/reviews/${reviewId}`, { token }),

  report: (token: string, reviewId: string, reason: string) =>
    api.post<{ message: string }>(`/reviews/${reviewId}/report`, { reason }, { token }),

  pending: (token: string) => api.get<PendingReview[]>("/reviews/pending", { token }),
};
