"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, HandCoins } from "lucide-react";

import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { sellerTradingApi, type MyOfferSummary } from "@/features/trading/api";
import { OfferResponse } from "@/features/trading/components/OfferResponse";
import { useProtectedResource } from "@/hooks/useProtectedResource";
import { ApiError } from "@/lib/api";
import {
  formatCurrency,
  formatDateShort,
  formatKilosWithCargas,
  formatPricePerKilo,
} from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Posturas que el vendedor envió, con lo que el comprador respondió.
 *
 * El motivo de un rechazo se muestra completo: es lo que le dice al caficultor
 * qué ajustar en la siguiente, y esconderlo convertiría el rechazo en un «no»
 * sin salida. De eso se encarga `OfferResponse`, que además dice con palabras
 * cuando no hubo motivo en lugar de dejar un hueco vacío.
 *
 * La carga va por `useProtectedResource`: antes esta página repetía a mano las
 * veinticinco líneas de token, 401, 403 y `finally`, igual que otras
 * veintisiete.
 */
export default function ProducerOffersPage() {
  const {
    data: page,
    isLoading,
    hasError,
    isForbidden,
    reload,
  } = useProtectedResource((token) => sellerTradingApi.myOffers(token));

  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const offers = page?.items ?? [];

  async function withdraw(offer: MyOfferSummary): Promise<void> {
    const token = session.getAccessToken();
    if (!token) return;
    if (!window.confirm(`¿Retirar tu postura sobre «${offer.demand_title}»?`)) return;

    setBusyId(offer.id);
    setActionError(null);
    try {
      await sellerTradingApi.withdraw(token, offer.id);
      setNotice("Postura retirada.");
      await reload();
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos retirar la postura.",
      );
    } finally {
      setBusyId(null);
    }
  }

  if (isForbidden) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <EmptyState
          icon={<HandCoins className="size-10" aria-hidden="true" />}
          title="Esta sección es para vendedores"
          description="Un administrador debe aprobar tu solicitud antes de que puedas ofrecer tu café."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/productor"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver al panel
      </Link>

      <h1 className="font-display text-3xl font-bold">Mis posturas</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Lo que ofreciste a compradores que publicaron su solicitud. Una postura aceptada
        pasa al carrito del comprador y te llegará como pedido cuando la pague.
      </p>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {actionError && (
        <p
          className="mb-6 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {actionError}
        </p>
      )}

      {isLoading && <Skeleton className="h-48 w-full" />}
      {!isLoading && hasError && <ErrorState onRetry={() => void reload()} />}

      {!isLoading && !hasError && offers.length === 0 && (
        <EmptyState
          icon={<HandCoins className="size-10" aria-hidden="true" />}
          title="No has enviado ninguna postura"
          description="Mira quién está comprando y responde con uno de tus lotes."
          action={
            <Link href="/productor/solicitudes">
              <Button>Ver solicitudes de compra</Button>
            </Link>
          }
        />
      )}

      {!isLoading && !hasError && offers.length > 0 && (
        <ul className="space-y-4">
          {offers.map((offer) => (
            <li key={offer.id}>
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-display font-semibold">{offer.demand_title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {offer.buyer_name} · busca{" "}
                        {formatKilosWithCargas(offer.wanted_kg)}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Ofreciste {formatKilosWithCargas(offer.offered_kg)} de{" "}
                        {offer.product_name}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1.5">
                      <span className="font-display font-semibold">
                        {formatCurrency(offer.line_total)}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatPricePerKilo(offer.price_per_kg)}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3">
                    <OfferResponse
                      status={offer.status}
                      responseNote={offer.response_note}
                    />
                  </div>

                  <p className="mt-3 text-xs text-muted-foreground">
                    Enviada el {formatDateShort(offer.created_at)}
                    {offer.responded_at &&
                      ` · respondida el ${formatDateShort(offer.responded_at)}`}
                    {!offer.responded_at &&
                      ` · la solicitud vence el ${formatDateShort(offer.demand_expires_on)}`}
                  </p>

                  {offer.status === "pending" && (
                    <div className="mt-4 border-t border-border pt-4">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:bg-destructive/10"
                        disabled={busyId === offer.id}
                        onClick={() => void withdraw(offer)}
                      >
                        Retirar la postura
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
