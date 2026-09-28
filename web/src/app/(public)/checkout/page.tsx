"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, MapPin, ShieldCheck } from "lucide-react";

import { EmptyState, Skeleton } from "@/components/shared/states";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cartApi, orderApi, type Address, type Cart } from "@/features/cart/api";
import { api, ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

export default function CheckoutPage() {
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<{ id: string; number: string } | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    try {
      const [cartData, addressData] = await Promise.all([
        cartApi.get(token),
        api.get<Address[]>("/users/me/addresses", { token }).catch(() => [] as Address[]),
      ]);
      setCart(cartData);
      setAddresses(addressData);
      setSelectedAddress(
        addressData.find((address) => address.is_default)?.id ?? addressData[0]?.id ?? "",
      );
    } catch {
      setError("No pudimos cargar los datos del pedido.");
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSubmit() {
    const token = session.getAccessToken();
    if (!token || !selectedAddress) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await orderApi.checkout(token, {
        shipping_address_id: selectedAddress,
        accept_terms: acceptTerms,
        customer_notes: notes || null,
      });
      setConfirmed({ id: result.order.id, number: result.order.order_number });
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos completar tu compra. Inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="container-page py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-64" />
        <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  // ---------------- Pedido confirmado ----------------
  if (confirmed) {
    return (
      <div className="container-page py-16">
        <div className="mx-auto max-w-lg text-center">
          <CheckCircle2 className="mx-auto mb-5 size-14 text-forest" aria-hidden="true" />
          <h1 className="font-display text-3xl font-bold">¡Pedido confirmado!</h1>
          <p className="mt-3 text-muted-foreground">
            Tu pedido <strong className="text-foreground">{confirmed.number}</strong> fue
            creado. Te avisaremos por correo cuando cada productor lo despache.
          </p>

          <div className="mt-6 rounded-md border border-gold/40 bg-gold/10 px-4 py-3 text-sm">
            El pago se procesó con un proveedor <strong>simulado</strong>: no se realizó
            ningún cobro real.
          </div>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href={`/mi-cuenta/pedidos/${confirmed.id}`}
              className={cn(buttonVariants({ variant: "primary", size: "lg" }))}
            >
              Ver mi pedido
            </Link>
            <Link
              href="/catalogo"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              Seguir comprando
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!cart || cart.groups.length === 0) {
    return (
      <div className="container-page py-16">
        <EmptyState
          title="No hay nada que comprar"
          description="Tu carrito está vacío."
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

  const canSubmit = Boolean(selectedAddress) && acceptTerms && !isSubmitting;

  return (
    <div className="container-page py-10">
      <h1 className="mb-8 font-display text-3xl font-bold">Finalizar compra</h1>

      <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          {/* ---------------- Dirección ---------------- */}
          <Card>
            <CardContent className="pt-6">
              <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-semibold">
                <MapPin className="size-5 text-primary" aria-hidden="true" />
                Dirección de entrega
              </h2>

              {addresses.length > 0 ? (
                <fieldset>
                  <legend className="sr-only">Elige una dirección de entrega</legend>
                  <ul className="space-y-3">
                    {addresses.map((address) => (
                      <li key={address.id}>
                        <label
                          className={cn(
                            "flex cursor-pointer gap-3 rounded-md border p-4 transition-colors",
                            selectedAddress === address.id
                              ? "border-primary bg-primary/5"
                              : "border-border hover:bg-muted",
                          )}
                        >
                          <input
                            type="radio"
                            name="address"
                            value={address.id}
                            checked={selectedAddress === address.id}
                            onChange={() => setSelectedAddress(address.id)}
                            className="mt-1 size-4 accent-primary"
                          />
                          <span className="text-sm">
                            <span className="block font-medium">
                              {address.recipient_name}
                              {address.label && (
                                <span className="ml-2 text-xs text-muted-foreground">
                                  ({address.label})
                                </span>
                              )}
                            </span>
                            <span className="block text-muted-foreground">
                              {address.street_address}
                              {address.neighborhood && `, ${address.neighborhood}`}
                            </span>
                            <span className="block text-muted-foreground">
                              Tel. {address.phone}
                            </span>
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                </fieldset>
              ) : (
                <div className="rounded-md bg-muted px-4 py-3 text-sm">
                  <p className="text-muted-foreground">
                    Aún no tienes direcciones registradas. Necesitas una para recibir el
                    pedido.
                  </p>
                  {/* El enlace lleva el parámetro de regreso para volver aquí en
                      cuanto la dirección quede guardada: es el único paso que
                      impide terminar la compra. */}
                  <Link
                    href="/mi-cuenta/direcciones?volver=checkout"
                    className={cn(buttonVariants({ size: "sm" }), "mt-3")}
                  >
                    <MapPin className="size-4" aria-hidden="true" />
                    Agregar dirección de entrega
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ---------------- Notas ---------------- */}
          <Card>
            <CardContent className="pt-6">
              <label htmlFor="notes" className="mb-2 block font-display font-semibold">
                Indicaciones para la entrega
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                rows={3}
                maxLength={1000}
                placeholder="Ej. Dejar en portería, timbre 302."
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </CardContent>
          </Card>

          {/* ---------------- Pago ---------------- */}
          <Card>
            <CardContent className="pt-6">
              <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold">
                <ShieldCheck className="size-5 text-secondary" aria-hidden="true" />
                Método de pago
              </h2>
              <div className="rounded-md border border-gold/40 bg-gold/10 px-4 py-3 text-sm">
                <strong>Pago simulado.</strong> Esta versión no realiza cobros reales. Las
                pasarelas (Wompi, Mercado Pago, PayU y PSE) están preparadas y se
                activarán en una fase posterior.
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ---------------- Resumen y confirmación ---------------- */}
        <aside>
          <Card className="lg:sticky lg:top-24">
            <CardContent className="pt-6">
              <h2 className="mb-4 font-display text-lg font-semibold">Tu pedido</h2>

              <ul className="mb-4 space-y-3 border-b border-border pb-4">
                {cart.groups.map((group) => (
                  <li key={group.producer_id} className="text-sm">
                    <p className="font-medium">{group.producer_name}</p>
                    {group.items.map((item) => (
                      <p
                        key={item.id}
                        className="flex justify-between text-muted-foreground"
                      >
                        <span>
                          {item.quantity} × {item.product_name}
                        </span>
                        <span>{formatCurrency(item.line_total)}</span>
                      </p>
                    ))}
                  </li>
                ))}
              </ul>

              <dl className="space-y-2 text-sm">
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
                <div className="flex justify-between border-t border-border pt-2 text-base">
                  <dt className="font-semibold">Total</dt>
                  <dd className="font-display text-xl font-bold">
                    {formatCurrency(cart.grand_total)}
                  </dd>
                </div>
              </dl>

              {cart.groups.length > 1 && (
                <p className="mt-4 text-xs text-muted-foreground">
                  Tu pedido se dividirá en {cart.groups.length} envíos, uno por cada
                  productor.
                </p>
              )}

              {/* La aceptación es explícita y no viene marcada por defecto. */}
              <div className="mt-5 flex items-start gap-3">
                <input
                  id="terms"
                  type="checkbox"
                  checked={acceptTerms}
                  onChange={(event) => setAcceptTerms(event.target.checked)}
                  className="mt-1 size-4 shrink-0 accent-primary"
                />
                <label htmlFor="terms" className="text-sm leading-relaxed">
                  Acepto los{" "}
                  <Link
                    href="/legal/terminos"
                    className="text-primary underline"
                    target="_blank"
                  >
                    términos y condiciones
                  </Link>{" "}
                  y la{" "}
                  <Link
                    href="/legal/devoluciones"
                    className="text-primary underline"
                    target="_blank"
                  >
                    política de devoluciones
                  </Link>
                  .
                </label>
              </div>

              {error && (
                <p
                  className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive"
                  role="alert"
                >
                  {error}
                </p>
              )}

              <Button
                onClick={handleSubmit}
                disabled={!canSubmit}
                isLoading={isSubmitting}
                size="lg"
                className="mt-5 w-full"
              >
                Confirmar compra
              </Button>

              {!selectedAddress && addresses.length === 0 && (
                <p className="mt-2 text-center text-xs text-muted-foreground">
                  Necesitas una dirección de entrega para continuar.
                </p>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
