import { api, apiBlob } from "@/lib/api";

export interface CartItem {
  id: string;
  variant_id: string;
  product_id: string;
  product_name: string;
  product_slug: string;
  producer_name: string;
  image_url: string | null;
  weight_grams: string;
  grind: string | null;
  quantity: number;
  unit_price: string;
  line_total: string;
  available_qty: number;
  price_changed: boolean;
  previous_price: string | null;
  is_available: boolean;
}

export interface CartSellerGroup {
  producer_id: string;
  producer_name: string;
  items: CartItem[];
  subtotal: string;
  estimated_shipping: string;
}

export interface Cart {
  id: string | null;
  groups: CartSellerGroup[];
  item_count: number;
  subtotal: string;
  shipping_total: string;
  discount_total: string;
  grand_total: string;
  currency: string;
  coupon: { code: string; description: string | null; discount_amount: string } | null;
  has_warnings: boolean;
}

export interface OrderSummary {
  id: string;
  order_number: string;
  status: string;
  grand_total: string;
  currency: string;
  item_count: number;
  seller_count: number;
  placed_at: string;
}

export const cartApi = {
  get: (token: string, coupon?: string) =>
    api.get<Cart>("/cart", { token, query: coupon ? { coupon } : undefined }),

  addItem: (token: string, variantId: string, quantity: number) =>
    api.post<Cart>("/cart/items", { variant_id: variantId, quantity }, { token }),

  updateItem: (token: string, itemId: string, quantity: number) =>
    api.patch<Cart>(`/cart/items/${itemId}`, { quantity }, { token }),

  removeItem: (token: string, itemId: string) =>
    api.delete<Cart>(`/cart/items/${itemId}`, { token }),

  merge: (token: string, items: Array<{ variant_id: string; quantity: number }>) =>
    api.post<Cart>("/cart/merge", items, { token }),
};

export interface Address {
  id: string;
  label: string | null;
  recipient_name: string;
  phone: string;
  street_address: string;
  neighborhood: string | null;
  is_default: boolean;
}

export interface OrderItem {
  id: string;
  product_id: string | null;
  variant_id: string | null;
  product_name_snapshot: string;
  variant_label_snapshot: string;
  quantity: number;
  unit_price: string;
  line_total: string;
  can_review: boolean;
  has_review: boolean;
}

export interface Shipment {
  carrier: string;
  tracking_number: string | null;
  tracking_url: string | null;
  status: string;
  estimated_delivery_date: string | null;
  dispatched_at: string | null;
  delivered_at: string | null;
}

export interface SubOrder {
  id: string;
  sub_order_number: string;
  producer_id: string;
  producer_name: string;
  status: string;
  subtotal: string;
  shipping_cost: string;
  items: OrderItem[];
  shipment: Shipment | null;
  cancellation_reason: string | null;
  is_cancellable: boolean;
  created_at: string;
}

export interface OrderDetail {
  id: string;
  order_number: string;
  status: string;
  subtotal: string;
  shipping_total: string;
  discount_total: string;
  grand_total: string;
  currency: string;
  shipping_address: Record<string, unknown>;
  customer_notes: string | null;
  sub_orders: SubOrder[];
  payment: {
    provider: string;
    method: string;
    status: string;
    amount: string;
    paid_at: string | null;
    failure_reason: string | null;
  } | null;
  placed_at: string;
}

export interface WishlistItem {
  product_id: string;
  product_name: string;
  product_slug: string;
  image_url: string | null;
  base_price: string;
  is_available: boolean;
}

export const wishlistApi = {
  list: (token: string) => api.get<WishlistItem[]>("/wishlist", { token }),

  add: (token: string, productId: string) =>
    api.post<{ message: string }>("/wishlist", { product_id: productId }, { token }),

  remove: (token: string, productId: string) =>
    api.delete<{ message: string }>(`/wishlist/${productId}`, { token }),
};

export const orderApi = {
  checkout: (
    token: string,
    data: {
      shipping_address_id: string;
      accept_terms: boolean;
      coupon_code?: string | null;
      customer_notes?: string | null;
    },
  ) =>
    api.post<{ order: { id: string; order_number: string }; message: string }>(
      "/orders",
      data,
      { token },
    ),

  list: (token: string) =>
    api.get<{ items: OrderSummary[]; total: number }>("/orders", { token }),

  detail: (token: string, orderId: string) =>
    api.get<OrderDetail>(`/orders/${orderId}`, { token }),

  cancelSubOrder: (token: string, subOrderId: string, reason: string) =>
    api.post<SubOrder>(`/orders/sub-orders/${subOrderId}/cancel`, { reason }, { token }),

  /**
   * Descarga el comprobante en PDF.
   *
   * No se abre la URL directamente en una pestaña: el endpoint exige la
   * cabecera de autorización, y una navegación del navegador no la lleva. Se
   * pide con `fetch`, se convierte en un `blob` y se dispara la descarga desde
   * un enlace temporal.
   */
  downloadReceipt: async (token: string, orderId: string, orderNumber: string) => {
    const blob = await apiBlob(`/orders/${orderId}/receipt`, token);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `MONK-GRAIN-${orderNumber}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Liberar el objeto tras el clic evita retener el PDF en memoria mientras
    // dure la sesión.
    URL.revokeObjectURL(url);
  },
};
