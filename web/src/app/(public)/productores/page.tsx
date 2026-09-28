import type { Metadata } from "next";
import Link from "next/link";
import { Coffee, MapPin, Star } from "lucide-react";

import { EmptyState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { catalogApi, type ProducerListItem } from "@/features/catalog/api";
import { formatRating } from "@/lib/format";
import { PRODUCER_TYPE_LABELS } from "@/types/catalog";

export const metadata: Metadata = {
  title: "Productores",
  description:
    "Conoce a las fincas, cooperativas y tostadores colombianos que venden su café en " +
    "MONK GRAIN, con su origen y su historia.",
};

/** El listado cambia poco; se revalida cada hora en vez de en cada visita. */
export const revalidate = 3600;

function ProducerCard({ producer }: { producer: ProducerListItem }) {
  const name = producer.brand_name ?? producer.legal_name;
  const location = [producer.municipality, producer.department]
    .filter(Boolean)
    .join(", ");

  return (
    <article className="flex h-full flex-col rounded-lg border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-display text-lg font-semibold leading-snug">{name}</h2>
        <Badge variant="outline">{PRODUCER_TYPE_LABELS[producer.type]}</Badge>
      </div>

      {location && (
        <p className="mt-2 flex items-center gap-1.5 text-sm text-muted-foreground">
          <MapPin className="size-4" aria-hidden="true" />
          {location}
        </p>
      )}

      {producer.story && (
        <p className="mt-3 line-clamp-3 text-sm text-muted-foreground">
          {producer.story}
        </p>
      )}

      <div className="mt-auto flex items-center justify-between pt-4">
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Coffee className="size-4" aria-hidden="true" />
          {producer.product_count} {producer.product_count === 1 ? "café" : "cafés"}
        </p>

        {producer.rating_count > 0 && (
          <p className="flex items-center gap-1 text-sm">
            <Star className="size-4 fill-gold text-gold" aria-hidden="true" />
            <span className="font-medium">{formatRating(producer.rating_avg)}</span>
            <span className="text-muted-foreground">({producer.rating_count})</span>
          </p>
        )}
      </div>
    </article>
  );
}

export default async function ProducersPage() {
  const page = await catalogApi.listProducers();

  return (
    <div className="container-page py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Quién cultiva tu café</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Cada lote del catálogo tiene detrás una finca, una cooperativa o un tostador con
          nombre propio. Estos son los que hoy venden en MONK GRAIN.
        </p>
      </header>

      {page.items.length === 0 ? (
        <EmptyState
          icon={<Coffee className="size-10" aria-hidden="true" />}
          title="Todavía no hay productores publicados"
          description="Estamos revisando las primeras solicitudes de vendedores."
          action={
            <Link href="/vender" className={buttonVariants()}>
              Quiero vender mi café
            </Link>
          }
        />
      ) : (
        <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {page.items.map((producer) => (
            <li key={producer.id}>
              <ProducerCard producer={producer} />
            </li>
          ))}
        </ul>
      )}

      <aside className="mt-12 rounded-lg border border-border bg-muted/30 p-6 text-center">
        <h2 className="font-display text-xl font-semibold">¿Cultivas o tuestas café?</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm text-muted-foreground">
          Publica tu café y véndelo directamente, sin intermediarios.
        </p>
        <Link href="/vender" className={`mt-4 inline-flex ${buttonVariants()}`}>
          Vender en MONK GRAIN
        </Link>
      </aside>
    </div>
  );
}
