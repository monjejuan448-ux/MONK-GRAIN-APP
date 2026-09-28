"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Heart, Trash2 } from "lucide-react";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, ProductGridSkeleton } from "@/components/shared/states";
import { wishlistApi, type WishlistItem } from "@/features/cart/api";
import { ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { session } from "@/lib/session";

/**
 * Lista de deseos del comprador (HU-CC-04).
 *
 * El enlace estaba en el panel de la cuenta y en el pie de página desde el
 * principio, apuntando a una ruta que no existía: los tres endpoints de
 * favoritos no tenían ningún llamador en la interfaz.
 *
 * Un café que dejó de estar disponible se marca en lugar de desaparecer: quien
 * lo guardó tiene derecho a saber que sigue ahí y que ahora está agotado
 * (HU-CC-04, CA3).
 */

export default function WishlistPage() {
  const router = useRouter();
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = session.getAccessToken();
    if (!token) {
      router.push("/ingresar");
      return;
    }

    setError(false);
    try {
      setItems(await wishlistApi.list(token));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.isUnauthorized) {
        router.push("/ingresar");
        return;
      }
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRemove(item: WishlistItem): Promise<void> {
    const token = session.getAccessToken();
    if (!token) return;

    setRemovingId(item.product_id);
    setActionError(null);
    try {
      await wishlistApi.remove(token, item.product_id);
      // Se quita de la lista en memoria en lugar de recargarla entera: el
      // resultado visible es el mismo y evita un parpadeo de toda la rejilla.
      setItems((current) => current.filter((row) => row.product_id !== item.product_id));
      setNotice(`${item.product_name} se quitó de tus favoritos.`);
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "No pudimos quitarlo de tus favoritos.",
      );
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <Link
        href="/mi-cuenta"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Volver a mi cuenta
      </Link>

      <h1 className="font-display text-3xl font-bold">Mis favoritos</h1>
      <p className="mb-8 mt-1 text-muted-foreground">
        Los cafés que guardaste. Si alguno se agota lo verás marcado, no desaparecido.
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

      {isLoading && <ProductGridSkeleton count={4} />}
      {!isLoading && error && <ErrorState onRetry={() => void load()} />}

      {!isLoading && !error && items.length === 0 && (
        <EmptyState
          icon={<Heart className="size-10" aria-hidden="true" />}
          title="Todavía no has guardado ningún café"
          description="Usa el corazón de cualquier ficha para tenerlo a mano."
          action={
            <Link href="/catalogo">
              <Button>Explorar el catálogo</Button>
            </Link>
          }
        />
      )}

      {!isLoading && !error && items.length > 0 && (
        <ul className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <li
              key={item.product_id}
              className="flex flex-col overflow-hidden rounded-lg border border-border"
            >
              <Link href={`/catalogo/${item.product_slug}`} className="block">
                <CoffeeImage
                  src={item.image_url}
                  alt={item.product_name}
                  sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                  className="aspect-[4/3] w-full"
                />
              </Link>

              <div className="flex flex-1 flex-col gap-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    href={`/catalogo/${item.product_slug}`}
                    className="font-display font-semibold hover:text-primary"
                  >
                    {item.product_name}
                  </Link>
                  {!item.is_available && <Badge variant="warning">Agotado</Badge>}
                </div>

                <p className="font-display text-lg font-semibold">
                  {formatCurrency(item.base_price)}
                </p>

                <div className="mt-auto flex gap-2 pt-2">
                  <Link href={`/catalogo/${item.product_slug}`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">
                      Ver el café
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:bg-destructive/10"
                    disabled={removingId === item.product_id}
                    onClick={() => void handleRemove(item)}
                    aria-label={`Quitar ${item.product_name} de favoritos`}
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
