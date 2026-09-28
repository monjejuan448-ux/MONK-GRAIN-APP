"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Truck, Upload } from "lucide-react";
import { toast } from "sonner";

import { ErrorState, Skeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { returnsApi, type ReturnDetail } from "@/features/returns/api";
import { ReturnReceipt } from "@/features/returns/components/ReturnReceipt";
import { ApiError } from "@/lib/api";
import { session } from "@/lib/session";

/** Constancia de la devolución, con lo único que el comprador puede hacer: declarar que ya la envió. */
export default function BuyerReturnPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [token, setToken] = useState<string | null>(null);
  const [request, setRequest] = useState<ReturnDetail | null>(null);
  const [files, setFiles] = useState<File[]>([]);
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

  async function declareShipped() {
    if (!token) return;
    setIsBusy(true);
    try {
      setRequest(await returnsApi.markShipped(token, params.id));
      toast.success("Anotado. Quien vende ya sabe que el café va en camino.");
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos registrarlo.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function attach() {
    if (!token || files.length === 0) return;
    setIsBusy(true);
    try {
      setRequest(await returnsApi.addEvidence(token, params.id, files));
      setFiles([]);
      toast.success("Fotografías adjuntadas.");
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos subir las fotografías.",
      );
    } finally {
      setIsBusy(false);
    }
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

  const canAttach = request.status !== "rejected" && request.status !== "refunded";

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/mi-cuenta/devoluciones"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Mis devoluciones
      </Link>

      <h1 className="mb-6 font-display text-3xl font-bold">Constancia de tu solicitud</h1>

      <ReturnReceipt request={request} />

      {(request.available_actions.includes("in_transit") || canAttach) && (
        <Card className="mt-6">
          <CardContent className="space-y-5 pt-6">
            {request.available_actions.includes("in_transit") && (
              <div>
                <h3 className="font-display font-semibold">¿Ya lo enviaste?</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Cuando entregues el paquete al transportador, avísanos para que quien
                  vende esté pendiente de recibirlo.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  className="mt-3"
                  disabled={isBusy}
                  onClick={() => void declareShipped()}
                >
                  <Truck className="mr-1.5 size-4" aria-hidden="true" />
                  Ya envié el café de vuelta
                </Button>
              </div>
            )}

            {canAttach && (
              <div>
                <label htmlFor="mas-fotos" className="block font-display font-semibold">
                  Adjuntar más fotografías
                </label>
                <input
                  id="mas-fotos"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
                  className="mt-2 block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2 file:text-sm"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  disabled={isBusy || files.length === 0}
                  onClick={() => void attach()}
                >
                  <Upload className="mr-1.5 size-4" aria-hidden="true" />
                  Subir {files.length > 0 && `(${files.length})`}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
