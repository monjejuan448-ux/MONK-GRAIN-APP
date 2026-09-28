import { api } from "@/lib/api";
import type {
  CatalogFilters,
  Page,
  ProductDetail,
  ProductListItem,
} from "@/types/catalog";

export interface ProducerListItem {
  id: string;
  legal_name: string;
  brand_name: string | null;
  type: "farmer" | "farm" | "cooperative" | "roaster";
  logo_key: string | null;
  cover_key: string | null;
  story: string | null;
  municipality: string | null;
  department: string | null;
  rating_avg: string;
  rating_count: number;
  product_count: number;
}

export const catalogApi = {
  listProducts: (filters: CatalogFilters = {}) =>
    api.get<Page<ProductListItem>>("/products", {
      query: filters as Record<string, string | number | undefined>,
    }),

  getProduct: (slug: string, token?: string | null) =>
    api.get<ProductDetail>(`/products/${slug}`, { token }),

  getRelated: (slug: string) => api.get<ProductListItem[]>(`/products/${slug}/related`),

  listProducers: (params: { department?: string; region?: string; type?: string } = {}) =>
    api.get<Page<ProducerListItem>>("/producers", { query: params }),

  getProducer: (id: string) => api.get<ProducerListItem>(`/producers/${id}`),
};
