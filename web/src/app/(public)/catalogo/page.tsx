import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { EmptyState, ProductGridSkeleton } from "@/components/shared/states";
import { buttonVariants } from "@/components/ui/button";
import {
  CatalogFilters,
  ResultCount,
  SortSelect,
} from "@/features/catalog/components/CatalogFilters";
import { ProductCard } from "@/features/catalog/components/ProductCard";
import { catalogApi } from "@/features/catalog/api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CatalogFilters as Filters, Page, ProductListItem } from "@/types/catalog";

export const metadata: Metadata = {
  title: "Catálogo de pergamino",
  description:
    "Lotes de café pergamino seco de origen colombiano, con su factor de rendimiento, humedad y análisis físico. Filtra por región, variedad, proceso, factor y volumen disponible.",
};

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

const EMPTY_PAGE: Page<ProductListItem> = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 0,
  has_next: false,
  has_previous: false,
};

async function loadProducts(filters: Filters): Promise<Page<ProductListItem>> {
  try {
    return await catalogApi.listProducts(filters);
  } catch (error) {
    // La página debe seguir siendo navegable aunque la API falle: se muestra un
    // estado vacío en lugar de un error que rompe toda la pantalla.
    if (!(error instanceof ApiError)) return EMPTY_PAGE;
    return EMPTY_PAGE;
  }
}

function parseFilters(params: Record<string, string | string[] | undefined>): Filters {
  const single = (key: string): string | undefined => {
    const value = params[key];
    return Array.isArray(value) ? value[0] : value;
  };

  return {
    q: single("q"),
    region: single("region"),
    department: single("department"),
    process: single("process") as Filters["process"],
    variety: single("variety"),
    certification: single("certification"),
    // Precios por kilogramo.
    min_price: single("min_price") ? Number(single("min_price")) : undefined,
    max_price: single("max_price") ? Number(single("max_price")) : undefined,
    max_yield_factor: single("max_yield_factor")
      ? Number(single("max_yield_factor"))
      : undefined,
    max_moisture_pct: single("max_moisture_pct")
      ? Number(single("max_moisture_pct"))
      : undefined,
    min_available_kg: single("min_available_kg")
      ? Number(single("min_available_kg"))
      : undefined,
    sort: (single("sort") ?? "newest") as Filters["sort"],
    page: single("page") ? Number(single("page")) : 1,
    page_size: 12,
  };
}

export default async function CatalogPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const filters = parseFilters(params);
  const results = await loadProducts(filters);

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Catálogo de pergamino</h1>
        <p className="mt-2 text-muted-foreground">
          Lotes de pergamino seco, directamente de quienes los cultivan. Los precios son
          por kilogramo.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[260px_1fr]">
        <aside aria-label="Filtros de búsqueda">
          <Suspense fallback={<div className="h-96 animate-pulse rounded-lg bg-muted" />}>
            <CatalogFilters />
          </Suspense>
        </aside>

        <div>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <ResultCount total={results.total} />
            <Suspense fallback={null}>
              <SortSelect />
            </Suspense>
          </div>

          <Suspense fallback={<ProductGridSkeleton count={6} />}>
            {results.items.length > 0 ? (
              <>
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
                  {results.items.map((product) => (
                    <ProductCard key={product.id} product={product} />
                  ))}
                </div>

                {results.total_pages > 1 && (
                  <Pagination
                    page={results.page}
                    totalPages={results.total_pages}
                    hasNext={results.has_next}
                    hasPrevious={results.has_previous}
                    params={params}
                  />
                )}
              </>
            ) : (
              <EmptyState
                title="Ningún lote coincide con tu búsqueda"
                description="Prueba ampliando los criterios: quita algún filtro o busca por otra región."
                action={
                  <Link
                    href="/catalogo"
                    className={cn(buttonVariants({ variant: "outline", size: "md" }))}
                  >
                    Limpiar filtros
                  </Link>
                }
              />
            )}
          </Suspense>
        </div>
      </div>
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  hasNext,
  hasPrevious,
  params,
}: {
  page: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  params: Record<string, string | string[] | undefined>;
}) {
  const buildHref = (targetPage: number) => {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === "string" && key !== "page") search.set(key, value);
    }
    search.set("page", String(targetPage));
    return `/catalogo?${search.toString()}`;
  };

  return (
    <nav className="mt-10 flex items-center justify-center gap-3" aria-label="Paginación">
      <Link
        href={hasPrevious ? buildHref(page - 1) : "#"}
        aria-disabled={!hasPrevious}
        tabIndex={hasPrevious ? undefined : -1}
        className={cn(
          buttonVariants({ variant: "outline", size: "sm" }),
          !hasPrevious && "pointer-events-none opacity-50",
        )}
      >
        Anterior
      </Link>

      <span className="text-sm text-muted-foreground" aria-current="page">
        Página {page} de {totalPages}
      </span>

      <Link
        href={hasNext ? buildHref(page + 1) : "#"}
        aria-disabled={!hasNext}
        tabIndex={hasNext ? undefined : -1}
        className={cn(
          buttonVariants({ variant: "outline", size: "sm" }),
          !hasNext && "pointer-events-none opacity-50",
        )}
      >
        Siguiente
      </Link>
    </nav>
  );
}
