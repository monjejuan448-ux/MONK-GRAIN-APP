import Link from "next/link";
import { MapPin, Star } from "lucide-react";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatRating } from "@/lib/format";
import { cn } from "@/lib/utils";
import { COFFEE_STATE_LABELS, type ProductListItem } from "@/types/catalog";

interface ProductCardProps {
  product: ProductListItem;
  className?: string;
}

export function ProductCard({ product, className }: ProductCardProps) {
  const producerName = product.producer.brand_name ?? product.producer.legal_name;

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
          alt={`${product.name}, café de ${producerName}`}
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

        <Badge variant="accent" className="absolute left-3 top-3">
          {COFFEE_STATE_LABELS[product.state]}
        </Badge>
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

        {product.sensory_profile && (
          <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
            {product.sensory_profile}
          </p>
        )}

        <div className="mt-auto flex items-end justify-between pt-4">
          <div>
            <p className="text-xs text-muted-foreground">Desde</p>
            <p className="font-display text-lg font-semibold">
              {formatCurrency(product.base_price, { currency: product.currency })}
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
