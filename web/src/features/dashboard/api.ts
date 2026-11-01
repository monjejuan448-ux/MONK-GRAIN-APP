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

/** Lote del vendedor cuyas existencias bajaron del umbral que él mismo fijó. */
export interface InventoryAlert {
  variant_id: string;
  product_name: string;
  variant_label: string;
  /** Kilos libres: descontado lo ya reservado por pedidos en curso. */
  available_qty: number;
  low_stock_threshold: number;
}

/**
 * Lo acumulado que la plataforma le debe al vendedor.
 *
 * No es el estado de un pago: en el MVP no se cierran periodos ni se dispersan
 * fondos, así que la cifra solo crece. La interfaz lo dice con esas palabras
 * para no dar a entender un desembolso que todavía no existe.
 */
export interface SettlementSummary {
  gross_amount: string;
  commission_total: string;
  net_amount: string;
  sub_orders_count: number;
}

/** Estado de una liquidación. */
export type SettlementStatus = "draft" | "pending_payment" | "paid" | "cancelled";

export const SETTLEMENT_STATUS_META: Record<
  SettlementStatus,
  { label: string; variant: "default" | "outline" | "success" | "warning"; hint: string }
> = {
  draft: {
    label: "Borrador",
    variant: "outline",
    hint: "Calculada pero todavía sin confirmar.",
  },
  pending_payment: {
    label: "Por pagar",
    variant: "warning",
    hint: "Lista para desembolsar.",
  },
  paid: {
    label: "Pagada",
    variant: "success",
    hint: "El dinero salió, con su referencia.",
  },
  cancelled: {
    label: "Anulada",
    variant: "outline",
    hint: "No se pagará.",
  },
};

/** Cuenta donde cobra el vendedor. El número nunca llega completo. */
export interface BankAccount {
  bank_name: string;
  account_type: string;
  holder_name: string;
  masked_number: string;
  updated_at: string | null;
}

export interface BankAccountInput {
  bank_name: string;
  account_type: string;
  account_number: string;
  holder_name: string;
  holder_document: string;
}

export interface ProducerSettlement {
  id: string;
  period_start: string;
  period_end: string;
  gross_amount: string;
  commission_total: string;
  net_amount: string;
  status: SettlementStatus;
  paid_at: string | null;
  payment_reference: string | null;
  created_at: string;
  sub_orders_count: number;
}

export interface AdminSettlement extends Omit<ProducerSettlement, "sub_orders_count"> {
  producer_id: string;
  producer_name: string;
  sub_orders_count: number;
  has_bank_account: boolean;
}

export interface ClosePeriodResult {
  settlements_created: number;
  producers_settled: number;
  sub_orders_settled: number;
  net_total: string;
  skipped_without_bank_account: number;
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
  /** Qué lotes hay que reponer, no solo cuántos. */
  inventoryAlerts: (token: string) =>
    api.get<InventoryAlert[]>("/producer/inventory/alerts", { token }),
  settlementSummary: (token: string) =>
    api.get<SettlementSummary>("/producer/settlements/summary", { token }),
  settlements: (token: string) =>
    api.get<ProducerSettlement[]>("/producer/settlements", { token }),
  bankAccount: (token: string) =>
    api.get<BankAccount | null>("/producer/bank-account", { token }),
  saveBankAccount: (token: string, data: BankAccountInput) =>
    api.put<BankAccount>("/producer/bank-account", data, { token }),
  deleteBankAccount: (token: string) =>
    api.delete<{ message: string }>("/producer/bank-account", { token }),
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

  settlements: (token: string, status?: SettlementStatus) =>
    api.get<AdminSettlement[]>("/admin/settlements", {
      token,
      query: status ? { status } : undefined,
    }),

  closeSettlementPeriod: (token: string, periodStart: string, periodEnd: string) =>
    api.post<ClosePeriodResult>(
      "/admin/settlements/close",
      { period_start: periodStart, period_end: periodEnd },
      { token },
    ),

  paySettlement: (
    token: string,
    settlementId: string,
    reference: string,
    notes?: string,
  ) =>
    api.post<AdminSettlement>(
      `/admin/settlements/${settlementId}/pay`,
      { payment_reference: reference, notes: notes || null },
      { token },
    ),

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
