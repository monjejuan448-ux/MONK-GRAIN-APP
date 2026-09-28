import { api, apiUpload } from "@/lib/api";

/**
 * Devoluciones, retracto y garantía.
 *
 * Los plazos, el importe y quién paga el transporte los calcula el servidor: la
 * interfaz solo los muestra. Enviar aquí un importe o una fecha propia no
 * tendría efecto, y por eso ninguna función lo ofrece.
 */

export type ReturnReason = "withdrawal" | "damaged" | "wrong_item" | "quality" | "other";

export type ReturnStatus =
  "requested" | "approved" | "rejected" | "in_transit" | "received" | "refunded";

export interface ReturnableItem {
  order_item_id: string;
  product_name: string;
  variant_label: string;
  purchased_qty: number;
  returnable_qty: number;
  unit_price: string;
}

export interface ReturnEligibility {
  sub_order_id: string;
  sub_order_number: string;
  can_request: boolean;
  allowed_reasons: ReturnReason[];
  withdrawal_deadline: string | null;
  warranty_deadline: string | null;
  delivered_at: string | null;
  items: ReturnableItem[];
  blocked_reason: string | null;
}

export interface ReturnItem {
  id: string;
  order_item_id: string;
  product_name: string;
  variant_label: string;
  quantity: number;
  line_refund: string;
}

export interface ReturnEvidence {
  id: string;
  content_type: string;
  url: string;
  created_at: string;
}

export interface ReturnDetail {
  id: string;
  return_number: string;
  sub_order_id: string;
  sub_order_number: string;
  order_number: string;
  producer_name: string;
  reason: ReturnReason;
  reason_label: string;
  description: string | null;
  status: ReturnStatus;
  declared_unopened: boolean;
  refund_amount: string | null;
  return_shipping_paid_by_seller: boolean;
  response_due_at: string;
  refund_due_at: string;
  resolution_notes: string | null;
  reviewed_at: string | null;
  refunded_at: string | null;
  items: ReturnItem[];
  evidences: ReturnEvidence[];
  filed_at: string;
  available_actions: ReturnStatus[];
}

export interface ReturnSummary {
  id: string;
  return_number: string;
  order_number: string;
  sub_order_number: string;
  producer_name: string;
  reason: ReturnReason;
  reason_label: string;
  status: ReturnStatus;
  refund_amount: string | null;
  item_count: number;
  response_due_at: string;
  filed_at: string;
}

interface PageResult<T> {
  items: T[];
  total: number;
}

export const returnsApi = {
  eligibility: (token: string, subOrderId: string) =>
    api.get<ReturnEligibility>(`/orders/sub-orders/${subOrderId}/return-eligibility`, {
      token,
    }),

  request: (
    token: string,
    data: {
      sub_order_id: string;
      reason: ReturnReason;
      description?: string | null;
      declared_unopened: boolean;
      items: Array<{ order_item_id: string; quantity: number }>;
    },
  ) => api.post<ReturnDetail>("/returns", data, { token }),

  mine: (token: string) => api.get<PageResult<ReturnSummary>>("/returns", { token }),

  detail: (token: string, returnId: string) =>
    api.get<ReturnDetail>(`/returns/${returnId}`, { token }),

  addEvidence: (token: string, returnId: string, files: File[]) => {
    const form = new FormData();
    for (const file of files) form.append("files", file);
    return apiUpload<ReturnDetail>(`/returns/${returnId}/evidence`, form, { token });
  },

  markShipped: (token: string, returnId: string) =>
    api.post<ReturnDetail>(`/returns/${returnId}/shipped`, undefined, { token }),

  // Lado del vendedor.
  forProducer: (token: string) =>
    api.get<PageResult<ReturnSummary>>("/producer/returns", { token }),

  resolve: (
    token: string,
    returnId: string,
    data: { approve: boolean; resolution_notes: string },
  ) =>
    api.post<ReturnDetail>(`/producer/returns/${returnId}/resolution`, data, { token }),

  markReceived: (token: string, returnId: string) =>
    api.post<ReturnDetail>(`/producer/returns/${returnId}/received`, undefined, {
      token,
    }),

  refund: (token: string, returnId: string) =>
    api.post<ReturnDetail>(`/producer/returns/${returnId}/refund`, undefined, { token }),
};

export const RETURN_STATUS_META: Record<
  ReturnStatus,
  { label: string; variant: "default" | "primary" | "success" | "warning" }
> = {
  requested: { label: "Radicada", variant: "warning" },
  approved: { label: "Aprobada", variant: "primary" },
  rejected: { label: "Rechazada", variant: "default" },
  in_transit: { label: "En camino de vuelta", variant: "primary" },
  received: { label: "Recibida", variant: "primary" },
  refunded: { label: "Reembolsada", variant: "success" },
};

/**
 * Cómo se presenta cada motivo al comprador.
 *
 * El retracto se describe aparte porque sus condiciones son distintas: no hay
 * que justificarlo, pero el café debe volver sellado y el transporte lo paga
 * quien devuelve.
 */
export const RETURN_REASON_META: Record<ReturnReason, { label: string; help: string }> = {
  withdrawal: {
    label: "Me arrepentí de la compra (retracto)",
    help: "Dentro de los cinco días hábiles siguientes a la entrega, sin dar explicaciones. El café debe volver sellado y el transporte corre por tu cuenta.",
  },
  damaged: {
    label: "Llegó dañado, vencido o en mal estado",
    help: "El transporte de la devolución lo paga quien vende.",
  },
  wrong_item: {
    label: "No es el café que pedí",
    help: "El transporte de la devolución lo paga quien vende.",
  },
  quality: {
    label: "No corresponde a lo publicado",
    help: "Otra variedad, otro proceso, otro peso o una calidad distinta de la anunciada.",
  },
  other: {
    label: "Otro motivo",
    help: "Cuéntanos qué pasó y lo revisamos.",
  },
};
