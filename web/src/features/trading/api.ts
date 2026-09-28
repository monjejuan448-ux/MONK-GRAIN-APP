import { api } from "@/lib/api";
import type { CoffeeProcess, Page } from "@/types/catalog";

/**
 * Oferta y demanda: el comprador publica lo que busca y el vendedor responde.
 *
 * Los importes viajan como cadena para no perder precisión al pasar por JSON, y
 * son siempre precios por kilogramo.
 */

export type DemandStatus =
  "open" | "partially_covered" | "fulfilled" | "closed" | "cancelled";

export type OfferStatus = "pending" | "accepted" | "rejected" | "withdrawn";

export interface DemandSummary {
  id: string;
  title: string;
  buyer_name: string;
  wanted_kg: number;
  covered_kg: number;
  remaining_kg: number;
  max_yield_factor: string | null;
  max_moisture_pct: string | null;
  variety: string | null;
  process: CoffeeProcess | null;
  municipality: string | null;
  department: string | null;
  offered_price_per_kg: string | null;
  expires_on: string;
  status: DemandStatus;
  /** Si admite posturas hoy. Lo decide el servidor, que es quien conoce la
   *  regla del vencimiento. */
  is_receiving: boolean;
  offer_count: number;
  created_at: string;
}

export interface OfferSummary {
  id: string;
  producer_id: string;
  producer_name: string;
  product_id: string;
  product_name: string;
  product_slug: string;
  variant_id: string;
  presentation: string;
  offered_kg: number;
  price_per_kg: string;
  line_total: string;
  message: string | null;
  status: OfferStatus;
  response_note: string | null;
  yield_factor: string | null;
  moisture_pct: string | null;
  municipality: string | null;
  available_kg: number;
  created_at: string;
  responded_at: string | null;
}

export interface DemandDetail extends DemandSummary {
  description: string | null;
  offers: OfferSummary[];
}

export interface DemandInput {
  title: string;
  description?: string | null;
  wanted_kg: number;
  max_yield_factor?: string | null;
  max_moisture_pct?: string | null;
  variety?: string | null;
  process?: CoffeeProcess | null;
  municipality_id?: number | null;
  offered_price_per_kg?: string | null;
  expires_on: string;
}

export interface MyOfferSummary {
  id: string;
  demand_id: string;
  demand_title: string;
  buyer_name: string;
  wanted_kg: number;
  product_name: string;
  presentation: string;
  offered_kg: number;
  price_per_kg: string;
  line_total: string;
  status: OfferStatus;
  response_note: string | null;
  demand_expires_on: string;
  created_at: string;
  responded_at: string | null;
}

export const demandsApi = {
  create: (token: string, data: DemandInput) =>
    api.post<DemandDetail>("/demands", data, { token }),

  mine: (token: string) => api.get<Page<DemandSummary>>("/demands", { token }),

  get: (token: string, demandId: string) =>
    api.get<DemandDetail>(`/demands/${demandId}`, { token }),

  update: (
    token: string,
    demandId: string,
    data: Partial<
      Pick<DemandInput, "title" | "description" | "offered_price_per_kg" | "expires_on">
    >,
  ) => api.patch<DemandDetail>(`/demands/${demandId}`, data, { token }),

  close: (token: string, demandId: string) =>
    api.post<DemandDetail>(`/demands/${demandId}/close`, undefined, { token }),

  respond: (token: string, offerId: string, accept: boolean, note?: string) =>
    api.post<DemandDetail>(
      `/demands/offers/${offerId}/respond`,
      { accept, note: note || null },
      { token },
    ),
};

export const sellerTradingApi = {
  openDemands: (token: string, onlyMatching: boolean) =>
    api.get<Page<DemandSummary>>("/producer/demands", {
      token,
      query: { only_matching: onlyMatching },
    }),

  offer: (
    token: string,
    demandId: string,
    data: {
      variant_id: string;
      offered_kg: number;
      price_per_kg: string;
      message?: string | null;
    },
  ) => api.post<MyOfferSummary>(`/producer/demands/${demandId}/offers`, data, { token }),

  myOffers: (token: string) =>
    api.get<Page<MyOfferSummary>>("/producer/offers", { token }),

  withdraw: (token: string, offerId: string) =>
    api.post<MyOfferSummary>(`/producer/offers/${offerId}/withdraw`, undefined, {
      token,
    }),
};

export const DEMAND_STATUS_META: Record<
  DemandStatus,
  { label: string; variant: "primary" | "warning" | "success" | "default" }
> = {
  open: { label: "Buscando", variant: "primary" },
  partially_covered: { label: "Parcialmente cubierta", variant: "warning" },
  fulfilled: { label: "Completa", variant: "success" },
  closed: { label: "Cerrada", variant: "default" },
  cancelled: { label: "Cancelada", variant: "default" },
};

export const OFFER_STATUS_META: Record<
  OfferStatus,
  { label: string; variant: "primary" | "success" | "default" | "warning" }
> = {
  pending: { label: "Esperando respuesta", variant: "primary" },
  accepted: { label: "Aceptada", variant: "success" },
  rejected: { label: "Rechazada", variant: "default" },
  withdrawn: { label: "Retirada", variant: "default" },
};
