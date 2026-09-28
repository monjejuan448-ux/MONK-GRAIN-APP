"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  PRODUCT_STATUS_META,
  producerCatalogApi,
  type ProducerProduct,
  type ProductInput,
} from "@/features/producer/api";
import { ImageManager } from "@/features/producer/components/ImageManager";
import { ProductForm } from "@/features/producer/components/ProductForm";
import { VariantManager } from "@/features/producer/components/VariantManager";
import { ApiError } from "@/lib/api";
import { session } from "@/lib/session";

export default function EditProductPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const productId = params.id;

  const [token, setToken] = useState<string | null>(null);
  const [product, setProduct] = useState<ProducerProduct | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
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
      setProduct(await producerCatalogApi.get(accessToken, productId));
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 403
          ? "Este café no pertenece a tu catálogo."
          : "No pudimos cargar este café.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [productId, router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function save(input: ProductInput) {
    if (!token) return;

    setIsSaving(true);
    try {
      setProduct(await producerCatalogApi.update(token, productId, input));
      toast.success("Cambios guardados.");
    } catch (requestError) {
      toast.error(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos guardar los cambios.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function togglePublication() {
    if (!token || !product) return;

    const isPublished = product.status === "published";
    try {
      setProduct(
        isPublished
          ? await producerCatalogApi.unpublish(token, productId)
          : await producerCatalogApi.publish(token, productId),
      );
      toast.success(
        isPublished ? "Café retirado del catálogo." : "Tu café ya está publicado.",
      );
    } catch (requestError) {
      const missing =
        requestError instanceof ApiError ? requestError.missingRequirements : [];
      toast.error(
        missing.length ? missing.join(" ") : "No pudimos completar la operación.",
      );
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-10">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !product || !token) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <ErrorState
          title={error ?? "No pudimos cargar este café."}
          onRetry={() => void load()}
        />
      </div>
    );
  }

  const meta = PRODUCT_STATUS_META[product.status];
  const isReady = product.missing_to_publish.length === 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href="/productor/catalogo"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi catálogo
      </Link>

      <header className="mb-8">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-bold">{product.name}</h1>
          <Badge variant={meta.tone}>{meta.label}</Badge>
        </div>

        {product.status === "published" ? (
          <p className="mt-2 text-sm text-muted-foreground">
            Visible en el catálogo:{" "}
            <Link href={`/catalogo/${product.slug}`} className="underline">
              ver como lo ve un comprador
            </Link>
          </p>
        ) : (
          <div className="mt-4 rounded-md border border-border bg-muted/40 p-4">
            {isReady ? (
              <p className="flex items-center gap-2 text-sm">
                <CheckCircle2 className="size-4 text-forest" aria-hidden="true" />
                Este café ya reúne todo lo necesario para publicarse.
              </p>
            ) : (
              <>
                <p className="text-sm font-medium">Para publicarlo falta:</p>
                <ul className="mt-2 list-inside list-disc text-sm text-muted-foreground">
                  {product.missing_to_publish.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        <div className="mt-4">
          <Button
            type="button"
            variant={product.status === "published" ? "outline" : "primary"}
            onClick={() => void togglePublication()}
            disabled={product.status !== "published" && !isReady}
          >
            {product.status === "published" ? "Retirar del catálogo" : "Publicar"}
          </Button>
        </div>
      </header>

      <div className="space-y-10">
        <ImageManager token={token} product={product} onChange={setProduct} />
        <VariantManager token={token} product={product} onChange={setProduct} />

        <section aria-labelledby="datos-titulo">
          <h2 id="datos-titulo" className="mb-4 font-display text-lg font-semibold">
            Información del café
          </h2>
          <ProductForm product={product} onSubmit={save} isSaving={isSaving} />
        </section>
      </div>
    </div>
  );
}
