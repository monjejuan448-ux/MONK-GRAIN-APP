"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, PackageCheck, Wallet, X } from "lucide-react";
import { toast } from "sonner";

import { ErrorState, Skeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { returnsApi, type ReturnDetail } from "@/features/returns/api";
import { ReturnReceipt } from "@/features/returns/components/ReturnReceipt";
import { ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Resolución de una devolución por parte de quien vende.
 *
 * Las acciones que se pintan vienen de `available_actions`, que calcula el
 * servidor. No se deducen aquí del estado: la interfaz mostraría opciones que
 * el servidor va a rechazar, y ocultarlas tampoco sería control de acceso.
 */
export default function ProducerReturnPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [token, setToken] = useState<string | null>(null);
  const [request, setRequest] = useState<ReturnDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const accessToken = session.getAccessToken();
    if (!accessToken) {
      router.push("/ingresar");
      return;
    }

    setToken(accessToken);
    setError(null);
    try {
      setRequest(await returnsApi.detail(accessToken, params.id));
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos cargar la solicitud.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [params.id, router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<ReturnDetail>, success: string) {
    setIsBusy(true);
    try {
      setRequest(await action());
      toast.success(success);
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos completar la operación.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function resolve(approve: boolean) {
    if (!token) return;
    if (notes.trim().length < 10) {
      toast.error("Explica tu decisión: es la respuesta escrita que exige la ley.");
      return;
    }
    await run(
      () =>
        returnsApi.resolve(token, params.id, { approve, resolution_notes: notes.trim() }),
      approve ? "Devolución aprobada." : "Respuesta registrada.",
    );
    setNotes("");
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10" aria-busy="true">
        <Skeleton className="mb-8 h-9 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <ErrorState title={error ?? undefined} onRetry={() => void load()} />
      </div>
    );
  }

  const actions = request.available_actions;
  const mustAnswer = actions.includes("approved") || actions.includes("rejected");

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/productor/devoluciones"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Todas las devoluciones
      </Link>

      <h1 className="mb-6 font-display text-3xl font-bold">Reclamación recibida</h1>

      <ReturnReceipt request={request} />

      {mustAnswer && (
        <Card className="mt-6">
          <CardContent className="pt-6">
            <h2 className="font-display font-semibold">Tu respuesta</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              El Decreto 735 de 2013 exige una respuesta escrita que diga si la
              reclamación procede y por qué. Es el documento que el comprador puede llevar
              a la Superintendencia, así que sé concreto.
            </p>

            <label htmlFor="respuesta" className="mt-4 block text-sm font-medium">
              Motivos de la decisión <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="respuesta"
              rows={4}
              minLength={10}
              maxLength={2000}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Revisamos las fotografías y el empaque llegó efectivamente roto…"
              className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />

            <div className="mt-4 flex flex-wrap gap-2">
              <Button type="button" disabled={isBusy} onClick={() => void resolve(true)}>
                <Check className="mr-1.5 size-4" aria-hidden="true" />
                Aprobar la devolución
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={isBusy}
                onClick={() => void resolve(false)}
              >
                <X className="mr-1.5 size-4" aria-hidden="true" />
                Rechazar con motivos
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {(actions.includes("received") || actions.includes("refunded")) && (
        <Card className="mt-6">
          <CardContent className="pt-6">
            <h2 className="font-display font-semibold">Siguientes pasos</h2>

            <div className="mt-3 flex flex-wrap gap-2">
              {actions.includes("received") && (
                <Button
                  type="button"
                  variant="outline"
                  disabled={isBusy || !token}
                  onClick={() => {
                    if (!token) return;
                    void run(
                      () => returnsApi.markReceived(token, params.id),
                      "Recepción confirmada.",
                    );
                  }}
                >
                  <PackageCheck className="mr-1.5 size-4" aria-hidden="true" />
                  Confirmar que recibí el café
                </Button>
              )}

              {actions.includes("refunded") && (
                <Button
                  type="button"
                  disabled={isBusy || !token}
                  onClick={() => {
                    if (!token) return;
                    void run(
                      () => returnsApi.refund(token, params.id),
                      "Reembolso registrado.",
                    );
                  }}
                >
                  <Wallet className="mr-1.5 size-4" aria-hidden="true" />
                  Registrar el reembolso de{" "}
                  {request.refund_amount ? formatCurrency(request.refund_amount) : "—"}
                </Button>
              )}
            </div>

            <p className="mt-3 text-sm text-muted-foreground">
              El importe no es negociable: el artículo 47 de la Ley 1480 de 2011 prohíbe
              descuentos y retenciones sobre el dinero que se devuelve. La comisión de la
              plataforma se reduce en la misma proporción.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
