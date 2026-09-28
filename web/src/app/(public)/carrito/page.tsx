"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Minus, Plus, ShoppingBag, Trash2 } from "lucide-react";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { EmptyState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cartApi, type Cart, type CartItem } from "@/features/cart/api";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatKilos, formatPricePerKilo } from "@/lib/format";
import { anonymousCart, session } from "@/lib/session";
import { cn } from "@/lib/utils";

/**
 * Salto de los botones de más y menos, en kilos.
 *
 * Un lote que se vende de carga en carga no se ajusta de kilo en kilo: harían
 * falta 125 clics para llegar a la siguiente cantidad que el vendedor acepta. El
 * paso se toma del mínimo del lote, que es la unidad en la que ese vendedor
 * comercia.
 */
function stepOf(item: CartItem): number {
  return Math.max(1, item.min_qty_kg);
}

export default function CartPage() {
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyItemId, setBusyItemId] = useState<string | null>(null);

  const loadCart = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      setNeedsLogin(true);
      setIsLoading(false);
      return;
    }

    try {
      // Si quedaron ítems del carrito anónimo, se fusionan antes de mostrar el
      // carrito para que la selección previa al login no se pierda.
      const pending = anonymousCart.read();
      const data =
        pending.length > 0
          ? await cartApi.merge(token, pending)
          : await cartApi.get(token);

      if (pending.length > 0) anonymousCart.clear();
      setCart(data);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        setNeedsLogin(true);
      } else {
        setError("No pudimos cargar tu carrito. Inténtalo de nuevo.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCart();
  }, [loadCart]);

  async function changeQuantity(itemId: string, quantity: number) {
    const token = session.getAccessToken();
    if (!token) return;

    setBusyItemId(itemId);
    setError(null);
    try {
      setCart(await cartApi.updateItem(token, itemId, quantity));
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos actualizar la cantidad.",
      );
    } finally {
      setBusyItemId(null);
    }
  }

  async function removeItem(itemId: string) {
    const token = session.getAccessToken();
    if (!token) return;

    setBusyItemId(itemId);
    try {
      setCart(await cartApi.removeItem(token, itemId));
      router.refresh();
    } finally {
      setBusyItemId(null);
    }
  }

  if (isLoading) {
    return (
      <div className="container-page py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-56" />
        <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
        <p className="sr-only">Cargando tu carrito…</p>
      </div>
    );
  }

  if (needsLogin) {
    return (
      <div className="container-page py-16">
        <EmptyState
          icon={<ShoppingBag className="size-10" aria-hidden="true" />}
          title="Inicia sesión para ver tu carrito"
          description="Guardamos lo que agregaste. Al entrar a tu cuenta lo encontrarás allí."
          action={
            <Link
              href="/ingresar"
              className={cn(buttonVariants({ variant: "primary", size: "lg" }))}
            >
              Iniciar sesión
            </Link>
          }
        />
      </div>
    );
  }

  if (!cart || cart.groups.length === 0) {
    return (
      <div className="container-page py-16">
        <EmptyState
          icon={<ShoppingBag className="size-10" aria-hidden="true" />}
          title="Tu carrito está vacío"
          description="Explora el catálogo y encuentra cafés de origen colombiano."
          action={
            <Link
              href="/catalogo"
              className={cn(buttonVariants({ variant: "primary", size: "lg" }))}
            >
              Ver catálogo
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="container-page py-10">
      <h1 className="mb-2 font-display text-3xl font-bold">Tu carrito</h1>
      <p className="mb-8 text-muted-foreground">
        {cart.item_count} {cart.item_count === 1 ? "producto" : "productos"} de{" "}
        {cart.groups.length} {cart.groups.length === 1 ? "vendedor" : "vendedores"}
      </p>

      {error && (
        <p
          className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      )}

      {cart.has_warnings && (
        <div
          className="mb-6 flex gap-3 rounded-md border border-gold/40 bg-gold/10 px-4 py-3"
          role="alert"
        >
          <AlertTriangle
            className="mt-0.5 size-5 shrink-0 text-gold"
            aria-hidden="true"
          />
          <p className="text-sm">
            Algunos productos cambiaron de precio o disponibilidad desde que los
            agregaste. Revísalos antes de continuar.
          </p>
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          {/* El carrito se agrupa por vendedor porque el pedido se dividirá
              así: cada productor despacha y cobra su envío por separado. */}
          {cart.groups.map((group) => (
            <Card key={group.producer_id}>
              <CardContent className="pt-6">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-3">
                  <h2 className="font-display font-semibold">{group.producer_name}</h2>
                  <Badge variant="outline">
                    {Number(group.estimated_shipping) === 0
                      ? "Envío gratis"
                      : `Envío ${formatCurrency(group.estimated_shipping)}`}
                  </Badge>
                </div>

                <ul className="space-y-5">
                  {group.items.map((item) => (
                    <li key={item.id} className="flex gap-4">
                      <div className="relative size-20 shrink-0 overflow-hidden rounded-md bg-muted">
                        <CoffeeImage
                          src={item.image_url}
                          alt={item.product_name}
                          sizes="80px"
                          className="object-cover"
                        />
                      </div>

                      <div className="min-w-0 flex-1">
                        <Link
                          href={`/catalogo/${item.product_slug}`}
                          className="font-medium hover:text-primary"
                        >
                          {item.product_name}
                        </Link>
                        <p className="text-sm text-muted-foreground">
                          {item.presentation} · {formatPricePerKilo(item.unit_price)}
                        </p>

                        {!item.is_available && (
                          <p className="mt-1 text-sm text-destructive">
                            No alcanzan los kilos (quedan{" "}
                            {formatKilos(item.available_qty)})
                          </p>
                        )}

                        {item.price_changed && item.previous_price && (
                          <p className="mt-1 text-sm text-gold">
                            El precio cambió de {formatCurrency(item.previous_price)} a{" "}
                            {formatCurrency(item.unit_price)}
                          </p>
                        )}

                        <div className="mt-2.5 flex items-center gap-3">
                          <div className="flex items-center rounded-md border border-border">
                            <button
                              type="button"
                              onClick={() =>
                                changeQuantity(item.id, item.quantity - stepOf(item))
                              }
                              disabled={
                                item.quantity - stepOf(item) < item.min_qty_kg ||
                                busyItemId === item.id
                              }
                              className="p-2 hover:bg-muted disabled:opacity-40"
                              aria-label={`Quitar ${formatKilos(stepOf(item))} de ${item.product_name}`}
                            >
                              <Minus className="size-3.5" aria-hidden="true" />
                            </button>
                            <span
                              className="min-w-20 text-center text-sm"
                              aria-live="polite"
                            >
                              {formatKilos(item.quantity)}
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                changeQuantity(item.id, item.quantity + stepOf(item))
                              }
                              disabled={
                                item.quantity + stepOf(item) > item.available_qty ||
                                busyItemId === item.id
                              }
                              className="p-2 hover:bg-muted disabled:opacity-40"
                              aria-label={`Agregar ${formatKilos(stepOf(item))} de ${item.product_name}`}
                            >
                              <Plus className="size-3.5" aria-hidden="true" />
                            </button>
                          </div>

                          <button
                            type="button"
                            onClick={() => removeItem(item.id)}
                            disabled={busyItemId === item.id}
                            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="size-3.5" aria-hidden="true" />
                            Quitar
                          </button>
                        </div>
                      </div>

                      <p className="whitespace-nowrap font-display font-semibold">
                        {formatCurrency(item.line_total)}
                      </p>
                    </li>
                  ))}
                </ul>

                <p className="mt-4 border-t border-border pt-3 text-right text-sm">
                  Subtotal del vendedor:{" "}
                  <span className="font-semibold">{formatCurrency(group.subtotal)}</span>
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* ---------------- Resumen ---------------- */}
        <aside>
          <Card className="lg:sticky lg:top-24">
            <CardContent className="pt-6">
              <h2 className="mb-4 font-display text-lg font-semibold">Resumen</h2>

              <dl className="space-y-2.5 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Subtotal</dt>
                  <dd>{formatCurrency(cart.subtotal)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Envío</dt>
                  <dd>
                    {Number(cart.shipping_total) === 0
                      ? "Gratis"
                      : formatCurrency(cart.shipping_total)}
                  </dd>
                </div>
                {Number(cart.discount_total) > 0 && (
                  <div className="flex justify-between text-forest">
                    <dt>Descuento</dt>
                    <dd>−{formatCurrency(cart.discount_total)}</dd>
                  </div>
                )}
                <div className="flex justify-between border-t border-border pt-3 text-base">
                  <dt className="font-semibold">Total</dt>
                  <dd className="font-display text-xl font-bold">
                    {formatCurrency(cart.grand_total)}
                  </dd>
                </div>
              </dl>

              <Link
                href="/checkout"
                className={cn(
                  buttonVariants({ variant: "primary", size: "lg" }),
                  "mt-6 w-full",
                )}
              >
                Continuar la compra
              </Link>

              <Link
                href="/catalogo"
                className={cn(
                  buttonVariants({ variant: "ghost", size: "md" }),
                  "mt-2 w-full",
                )}
              >
                Seguir comprando
              </Link>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
