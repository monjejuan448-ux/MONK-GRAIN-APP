import { api } from "@/lib/api";

/** Tipos y llamadas de los paneles de usuario. */

export interface ProducerDashboard {
  total_sales: string;
  commission_paid: string;
  net_earnings: string;
  pending_orders: number;
  orders_to_prepare: number;
  active_products: number;
  draft_products: number;
  low_stock_variants: number;
  rating_avg: string;
  rating_count: number;
  pending_requests: number;
  top_products: Array<{
    product_id: string;
    name: string;
    slug: string;
    units_sold: number;
    revenue: string;
  }>;
  sales_by_month: Array<{ period: string; orders: number; revenue: string }>;
}

export interface ProducerOrder {
  sub_order_id: string;
  sub_order_number: string;
  order_number: string;
  buyer_name: string;
  status: string;
  subtotal: string;
  net_amount: string;
  item_count: number;
  shipping_city: string | null;
  created_at: string;
}

export interface AdminDashboard {
  total_users: number;
  new_users_period: number;
  pending_producers: number;
  approved_producers: number;
  total_products: number;
  published_products: number;
  orders_period: number;
  revenue_period: string;
  commission_period: string;
  orders_by_status: Record<string, number>;
  reported_reviews: number;
}

export interface PendingProducer {
  id: string;
  legal_name: string;
  brand_name: string | null;
  type: string;
  document_number: string;
  contact_email: string;
  contact_name: string;
  municipality: string | null;
  department: string | null;
  status: string;
  created_at: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export const producerApi = {
  dashboard: (token: string) =>
    api.get<ProducerDashboard>("/producer/dashboard", { token }),
  orders: (token: string, status?: string) =>
    api.get<PageResult<ProducerOrder>>("/producer/orders", {
      token,
      query: status ? { status } : undefined,
    }),
  updateOrderStatus: (
    token: string,
    subOrderId: string,
    data: { status: string; note?: string; carrier?: string; tracking_number?: string },
  ) => api.patch(`/orders/sub-orders/${subOrderId}/status`, data, { token }),
};

export interface AdminUserItem {
  id: string;
  email: string;
  full_name: string;
  status: "pending_verification" | "active" | "suspended";
  roles: string[];
  is_producer: boolean;
  producer_status: string | null;
  order_count: number;
  created_at: string;
  last_login_at: string | null;
}

export interface ReportedReview {
  id: string;
  product_id: string;
  product_name: string;
  product_slug: string;
  rating: number;
  comment: string | null;
  author_name: string;
  status: "published" | "hidden" | "reported";
  created_at: string;
  report_count: number;
  /** Motivos que adujeron quienes la denunciaron, del más reciente al primero. */
  report_reasons: string[];
}

export interface AuditLogEntry {
  id: number;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  created_at: string;
}

export const USER_STATUS_META: Record<
  AdminUserItem["status"],
  { label: string; variant: "success" | "warning" | "default" }
> = {
  active: { label: "Activa", variant: "success" },
  pending_verification: { label: "Sin verificar", variant: "warning" },
  suspended: { label: "Suspendida", variant: "default" },
};

export const ROLE_LABELS: Record<string, string> = {
  consumer: "Comprador",
  business: "Empresa",
  producer: "Vendedor",
  admin: "Administración",
  visitor: "Visitante",
};

export const adminApi = {
  dashboard: (token: string, days = 30) =>
    api.get<AdminDashboard>("/admin/dashboard", { token, query: { days } }),
  pendingProducers: (token: string) =>
    api.get<PageResult<PendingProducer>>("/admin/producers/pending", { token }),
  users: (token: string, filters: { q?: string; status?: string; role?: string } = {}) =>
    api.get<PageResult<AdminUserItem>>("/admin/users", {
      token,
      query: { q: filters.q, status: filters.status, role: filters.role },
    }),

  suspendUser: (token: string, userId: string, suspend: boolean, reason?: string) =>
    api.post<{ message: string }>(
      `/admin/users/${userId}/suspend`,
      { suspend, reason: reason || null },
      { token },
    ),

  reportedReviews: (token: string) =>
    api.get<PageResult<ReportedReview>>("/admin/reviews/reported", { token }),

  moderateReview: (token: string, reviewId: string, hide: boolean, reason?: string) =>
    api.post<{ message: string }>(
      `/admin/reviews/${reviewId}/moderate`,
      { hide, reason: reason || null },
      { token },
    ),

  auditLogs: (token: string) =>
    api.get<PageResult<AuditLogEntry>>("/admin/audit-logs", { token }),

  reviewProducer: (
    token: string,
    producerId: string,
    approve: boolean,
    reason?: string,
  ) =>
    api.post<PendingProducer>(
      `/admin/producers/${producerId}/review`,
      { approve, reason },
      { token },
    ),
};

/**
 * Avances que la interfaz ofrece al vendedor en cada estado.
 *
 * Es un espejo parcial de `ALLOWED_SUB_ORDER_TRANSITIONS` del backend, que es
 * quien decide de verdad: aquí solo se decide qué botón pintar. Se omite a
 * propósito el paso a `refunded`, que el grafo permite pero que no se hace a
 * mano: un reembolso pasa por el módulo de devoluciones, con su plazo, su
 * motivo y su constancia.
 */
export const SELLER_NEXT_STATUSES: Record<string, string[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["prepared", "cancelled"],
  prepared: ["shipped", "cancelled"],
  shipped: ["delivered"],
  delivered: [],
  cancelled: [],
  refunded: [],
};

/** Verbo con el que se le ofrece al vendedor cada avance. */
export const STATUS_ACTION_LABELS: Record<string, string> = {
  confirmed: "Confirmar",
  prepared: "Marcar como preparado",
  shipped: "Despachar",
  delivered: "Marcar como entregado",
  cancelled: "Cancelar",
};

/** Estados de sub-orden con su etiqueta en español y su color. */
export const ORDER_STATUS_META: Record<
  string,
  { label: string; variant: "default" | "primary" | "success" | "warning" }
> = {
  pending: { label: "Pendiente de pago", variant: "warning" },
  confirmed: { label: "Confirmado", variant: "primary" },
  prepared: { label: "Preparado", variant: "primary" },
  shipped: { label: "Enviado", variant: "primary" },
  delivered: { label: "Entregado", variant: "success" },
  cancelled: { label: "Cancelado", variant: "default" },
  refunded: { label: "Reembolsado", variant: "default" },
};
