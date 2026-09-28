import Link from "next/link";
import { MapPin, Star } from "lucide-react";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { Badge } from "@/components/ui/badge";
import {
  formatKilosWithCargas,
  formatPercent,
  formatPricePerKilo,
  formatRating,
  formatYieldFactor,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { yieldFactorQuality, type ProductListItem } from "@/types/catalog";

interface ProductCardProps {
  product: ProductListItem;
  className?: string;
}

export function ProductCard({ product, className }: ProductCardProps) {
  const producerName = product.producer.brand_name ?? product.producer.legal_name;
  // La calidad del factor se muestra como etiqueta y no como número suelto: un
  // «91,50» no le dice nada a quien no compra café a diario.
  const quality = yieldFactorQuality(product.yield_factor);

  return (
    <article
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-lg border border-border",
        "bg-card transition-shadow hover:shadow-md",
        className,
      )}
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-muted">
        <CoffeeImage
          src={product.primary_image_url}
          alt={`${product.name}, pergamino de ${producerName}`}
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
          className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
        />

        {!product.is_available && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/70">
            <Badge variant="outline" className="bg-background">
              Agotado
            </Badge>
          </div>
        )}

        {/* El estado no se muestra: todo el catálogo es pergamino y repetirlo
            en cada tarjeta gasta el espacio sin informar. Lo que distingue un
            lote de otro es su factor. */}
        {quality && (
          <Badge variant={quality.variant} className="absolute left-3 top-3">
            Factor {formatYieldFactor(product.yield_factor)}
          </Badge>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {producerName}
        </p>

        <h3 className="mt-1 font-display text-base font-semibold leading-snug">
          {/* El enlace cubre toda la tarjeta, pero el texto accesible es el
              nombre del producto, no un "ver más" sin contexto. */}
          <Link
            href={`/catalogo/${product.slug}`}
            className="after:absolute after:inset-0"
          >
            {product.name}
          </Link>
        </h3>

        {product.region && (
          <p className="mt-1.5 flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="size-3.5" aria-hidden="true" />
            {product.region}
          </p>
        )}

        <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
          {quality && (
            <>
              <dt className="text-muted-foreground">Calidad</dt>
              <dd className="text-right font-medium">{quality.label}</dd>
            </>
          )}
          {product.moisture_pct && (
            <>
              <dt className="text-muted-foreground">Humedad</dt>
              <dd className="text-right font-medium">
                {formatPercent(product.moisture_pct)}
              </dd>
            </>
          )}
          <dt className="text-muted-foreground">Disponible</dt>
          <dd className="text-right font-medium">
            {product.available_kg > 0 ? formatKilosWithCargas(product.available_kg) : "—"}
          </dd>
        </dl>

        <div className="mt-auto flex items-end justify-between pt-4">
          <div>
            <p className="text-xs text-muted-foreground">Desde</p>
            <p className="font-display text-lg font-semibold">
              {formatPricePerKilo(product.base_price)}
            </p>
          </div>

          {product.rating_count > 0 && (
            <p className="flex items-center gap-1 text-sm">
              <Star className="size-4 fill-gold text-gold" aria-hidden="true" />
              <span className="font-medium">{formatRating(product.rating_avg)}</span>
              <span className="text-muted-foreground">({product.rating_count})</span>
            </p>
          )}
        </div>
      </div>
    </article>
  );
}
