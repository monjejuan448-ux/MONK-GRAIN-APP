"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Coffee, Plus } from "lucide-react";
import { toast } from "sonner";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { EmptyState, ErrorState, Skeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  PRODUCT_STATUS_META,
  producerCatalogApi,
  type ProducerProduct,
} from "@/features/producer/api";
import { ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { session } from "@/lib/session";

export default function ProducerCatalogPage() {
  const router = useRouter();
  const [products, setProducts] = useState<ProducerProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(null);
    try {
      const page = await producerCatalogApi.list(token);
      setProducts(page.items);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 403
          ? "Esta sección es para vendedores aprobados."
          : "No pudimos cargar tu catálogo.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function togglePublication(product: ProducerProduct) {
    const token = session.getAccessToken();
    if (!token) return;

    const isPublished = product.status === "published";
    try {
      const updated = isPublished
        ? await producerCatalogApi.unpublish(token, product.id)
        : await producerCatalogApi.publish(token, product.id);

      setProducts((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      toast.success(
        isPublished ? "Café retirado del catálogo." : "Tu café ya está publicado.",
      );
    } catch (requestError) {
      // Al publicar, el servidor responde qué requisitos faltan.
      const missing =
        requestError instanceof ApiError ? requestError.missingRequirements : [];

      toast.error(
        missing.length ? missing.join(" ") : "No pudimos completar la operación.",
      );
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Mi catálogo</h1>
          <p className="mt-1 text-muted-foreground">
            Publica tus cafés y mantén su información al día.
          </p>
        </div>

        <Link href="/productor/catalogo/nuevo" className={buttonVariants()}>
          <Plus className="mr-1.5 size-4" aria-hidden="true" />
          Publicar un café
        </Link>
      </header>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {!isLoading && error && <ErrorState title={error} onRetry={() => void load()} />}

      {!isLoading && !error && products.length === 0 && (
        <EmptyState
          icon={<Coffee className="size-10" aria-hidden="true" />}
          title="Aún no has publicado ningún café"
          description="Crea tu primera ficha con fotos, presentaciones y certificados."
          action={
            <Link href="/productor/catalogo/nuevo" className={buttonVariants()}>
              Publicar mi primer café
            </Link>
          }
        />
      )}

      {!isLoading && !error && products.length > 0 && (
        <ul className="space-y-4">
          {products.map((product) => {
            const meta = PRODUCT_STATUS_META[product.status];
            const cover =
              product.images.find((image) => image.is_primary) ?? product.images[0];

            return (
              <li
                key={product.id}
                className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4 sm:flex-row"
              >
                <div className="relative size-24 shrink-0 overflow-hidden rounded-md bg-muted">
                  <CoffeeImage
                    src={cover?.image_url}
                    alt={cover?.alt_text ?? product.name}
                    sizes="96px"
                    className="object-cover"
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-display text-lg font-semibold">{product.name}</h2>
                    <Badge variant={meta.tone}>{meta.label}</Badge>
                  </div>

                  <p className="mt-1 text-sm text-muted-foreground">
                    {formatCurrency(product.base_price)} · {product.variants.length}{" "}
                    {product.variants.length === 1 ? "presentación" : "presentaciones"} ·{" "}
                    {product.images.length}{" "}
                    {product.images.length === 1 ? "fotografía" : "fotografías"}
                  </p>

                  {product.missing_to_publish.length > 0 && (
                    <p className="mt-2 text-sm text-amber-700">
                      Para publicarlo: {product.missing_to_publish.join(" ")}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Link
                    href={`/productor/catalogo/${product.id}`}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Editar
                  </Link>

                  <Button
                    type="button"
                    size="sm"
                    variant={product.status === "published" ? "outline" : "primary"}
                    onClick={() => void togglePublication(product)}
                    disabled={
                      product.status !== "published" &&
                      product.missing_to_publish.length > 0
                    }
                  >
                    {product.status === "published" ? "Retirar" : "Publicar"}
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
