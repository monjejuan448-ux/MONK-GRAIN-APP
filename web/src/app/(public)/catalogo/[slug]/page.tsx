import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Award, Leaf, MapPin, Mountain, Package, Sprout } from "lucide-react";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { AddToCart } from "@/features/catalog/components/AddToCart";
import { ProductCard } from "@/features/catalog/components/ProductCard";
import { catalogApi } from "@/features/catalog/api";
import { ProductReviews } from "@/features/reviews/components/ProductReviews";
import { Stars } from "@/features/reviews/components/Stars";
import { ApiError } from "@/lib/api";
import { formatAltitude, formatCuppingScore, formatDate } from "@/lib/format";
import {
  COFFEE_STATE_LABELS,
  PROCESS_LABELS,
  PRODUCER_TYPE_LABELS,
  ROAST_LABELS,
  type ProductDetail,
} from "@/types/catalog";

interface PageProps {
  params: Promise<{ slug: string }>;
}

async function getProduct(slug: string): Promise<ProductDetail | null> {
  try {
    return await catalogApi.getProduct(slug);
  } catch (error) {
    if (error instanceof ApiError && error.isNotFound) return null;
    throw error;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) return { title: "Café no encontrado" };

  const producer = product.producer.brand_name ?? product.producer.legal_name;
  return {
    title: product.name,
    description: `${product.name} de ${producer}${
      product.region ? `, ${product.region}` : ""
    }. ${product.sensory_profile ?? ""}`.slice(0, 160),
  };
}

export default async function ProductPage({ params }: PageProps) {
  const { slug } = await params;
  const product = await getProduct(slug);

  if (!product) notFound();

  const related = await catalogApi.getRelated(slug).catch(() => []);
  const producerName = product.producer.brand_name ?? product.producer.legal_name;
  const attributes = product.attributes;

  return (
    <div className="container-page py-8">
      <nav aria-label="Ruta de navegación" className="mb-6 text-sm text-muted-foreground">
        <ol className="flex flex-wrap items-center gap-1.5">
          <li>
            <Link href="/" className="hover:text-foreground">
              Inicio
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li>
            <Link href="/catalogo" className="hover:text-foreground">
              Catálogo
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li className="text-foreground">{product.name}</li>
        </ol>
      </nav>

      <div className="grid gap-10 lg:grid-cols-2">
        {/* ---------------- Galería ---------------- */}
        <div>
          <div className="relative aspect-square overflow-hidden rounded-lg bg-muted">
            <CoffeeImage
              src={product.images[0]?.image_key}
              alt={product.images[0]?.alt_text ?? product.name}
              sizes="(max-width: 1024px) 100vw, 50vw"
              className="object-cover"
              priority
            />
          </div>
        </div>

        {/* ---------------- Datos y compra ---------------- */}
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge variant="accent">{COFFEE_STATE_LABELS[product.state]}</Badge>
            {attributes?.cupping_score && (
              <Badge variant="success">
                Puntaje {formatCuppingScore(attributes.cupping_score)}
              </Badge>
            )}
          </div>

          <h1 className="font-display text-3xl font-bold leading-tight">
            {product.name}
          </h1>

          {product.rating_count > 0 && (
            <a href="#resenas" className="mt-2 inline-flex hover:opacity-80">
              <Stars
                rating={Number(product.rating_avg)}
                showValue
                count={product.rating_count}
              />
            </a>
          )}

          <Link
            href={`/productores/${product.producer.id}`}
            className="mt-2 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <Sprout className="size-4" aria-hidden="true" />
            {producerName}
            <span className="text-xs">
              ({PRODUCER_TYPE_LABELS[product.producer.type]})
            </span>
          </Link>

          {(product.municipality || product.region) && (
            <p className="mt-1.5 flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="size-4" aria-hidden="true" />
              {[product.municipality, product.department].filter(Boolean).join(", ")}
              {product.region && ` · ${product.region}`}
            </p>
          )}

          <p className="mt-5 leading-relaxed text-muted-foreground">
            {product.description}
          </p>

          <div className="mt-8">
            <AddToCart variants={product.variants} productName={product.name} />
          </div>

          <p className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
            <Package className="size-4" aria-hidden="true" />
            Despacho en {product.dispatch_days}{" "}
            {product.dispatch_days === 1 ? "día hábil" : "días hábiles"}
          </p>
        </div>
      </div>

      {/* ---------------- Trazabilidad ---------------- */}
      <section className="mt-14" aria-labelledby="trazabilidad">
        <h2 id="trazabilidad" className="mb-6 font-display text-2xl font-bold">
          Origen y trazabilidad
        </h2>

        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardContent className="pt-6">
              <h3 className="mb-4 flex items-center gap-2 font-display text-lg font-semibold">
                <Mountain className="size-5 text-primary" aria-hidden="true" />
                Ficha técnica
              </h3>
              <dl className="space-y-2.5 text-sm">
                <DataRow label="Variedad" value={attributes?.variety} />
                <DataRow
                  label="Proceso"
                  value={attributes?.process ? PROCESS_LABELS[attributes.process] : null}
                />
                <DataRow
                  label="Nivel de tueste"
                  value={attributes?.roast ? ROAST_LABELS[attributes.roast] : null}
                />
                <DataRow
                  label="Altitud"
                  value={
                    attributes?.altitude_masl
                      ? formatAltitude(attributes.altitude_masl)
                      : null
                  }
                />
                <DataRow
                  label="Puntaje de catación"
                  value={
                    attributes?.cupping_score
                      ? formatCuppingScore(attributes.cupping_score)
                      : null
                  }
                />
                <DataRow
                  label="Fecha de cosecha"
                  value={
                    attributes?.harvest_date ? formatDate(attributes.harvest_date) : null
                  }
                />
                <DataRow
                  label="Fecha de tueste"
                  value={
                    attributes?.roast_date ? formatDate(attributes.roast_date) : null
                  }
                />
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <h3 className="mb-4 flex items-center gap-2 font-display text-lg font-semibold">
                <Leaf className="size-5 text-secondary" aria-hidden="true" />
                La finca
              </h3>

              {product.farm ? (
                <>
                  <dl className="space-y-2.5 text-sm">
                    <DataRow label="Finca" value={product.farm.name} />
                    <DataRow label="Vereda" value={product.farm.village} />
                    <DataRow
                      label="Altitud del cultivo"
                      value={
                        product.farm.altitude_min_masl && product.farm.altitude_max_masl
                          ? `${product.farm.altitude_min_masl} – ${formatAltitude(
                              product.farm.altitude_max_masl,
                            )}`
                          : null
                      }
                    />
                  </dl>

                  {product.farm.environmental_practices && (
                    <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                      {product.farm.environmental_practices}
                    </p>
                  )}

                  {/* La ubicación se muestra a nivel de municipio: publicar la
                      coordenada exacta de una finca rural pondría en riesgo la
                      seguridad del productor. */}
                  <p className="mt-4 text-xs text-muted-foreground">
                    Por seguridad del productor, la ubicación se indica a nivel de
                    municipio y no con la coordenada exacta de la finca.
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Este café no tiene finca asociada en la plataforma.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {attributes?.tasting_notes && attributes.tasting_notes.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-3 font-display text-lg font-semibold">Notas de cata</h3>
            <ul className="flex flex-wrap gap-2">
              {attributes.tasting_notes.map((note) => (
                <li key={note}>
                  <Badge variant="primary" size="md">
                    {note}
                  </Badge>
                </li>
              ))}
            </ul>
          </div>
        )}

        {product.certifications.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold">
              <Award className="size-5 text-accent" aria-hidden="true" />
              Certificaciones
            </h3>
            <ul className="flex flex-wrap gap-2">
              {product.certifications.map((certification) => (
                <li key={certification.code}>
                  <Badge variant="success" size="md">
                    {certification.name}
                  </Badge>
                </li>
              ))}
            </ul>
          </div>
        )}

        {product.storage_conditions && (
          <div className="mt-6 rounded-lg bg-muted/60 p-5">
            <h3 className="mb-2 font-display font-semibold">Conservación</h3>
            <p className="text-sm text-muted-foreground">{product.storage_conditions}</p>
          </div>
        )}
      </section>

      {/* ---------------- Reseñas ---------------- */}
      <ProductReviews productId={product.id} />

      {/* ---------------- Relacionados ---------------- */}
      {related.length > 0 && (
        <section className="mt-16" aria-labelledby="relacionados">
          <h2 id="relacionados" className="mb-6 font-display text-2xl font-bold">
            También te puede interesar
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {related.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function DataRow({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-4 border-b border-border pb-2 last:border-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}
