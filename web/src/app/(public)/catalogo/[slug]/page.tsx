import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Award,
  FlaskConical,
  Leaf,
  MapPin,
  Mountain,
  Package,
  Sprout,
} from "lucide-react";

import { CoffeeImage } from "@/components/shared/CoffeeImage";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { AddToCart } from "@/features/catalog/components/AddToCart";
import { ProductCard } from "@/features/catalog/components/ProductCard";
import { catalogApi } from "@/features/catalog/api";
import { ProductReviews } from "@/features/reviews/components/ProductReviews";
import { Stars } from "@/features/reviews/components/Stars";
import { ApiError } from "@/lib/api";
import {
  formatAltitude,
  formatDate,
  formatKilosWithCargas,
  formatPercent,
  formatScreenSizes,
  formatYieldFactor,
} from "@/lib/format";
import {
  moistureQuality,
  PROCESS_LABELS,
  PRODUCER_TYPE_LABELS,
  yieldFactorQuality,
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
  if (!product) return { title: "Lote no encontrado" };

  const producer = product.producer.brand_name ?? product.producer.legal_name;
  const factor = product.yield_factor
    ? `Factor ${formatYieldFactor(product.yield_factor)}. `
    : "";
  return {
    title: product.name,
    description: `Pergamino seco de ${producer}${
      product.region ? `, ${product.region}` : ""
    }. ${factor}${product.description}`.slice(0, 160),
  };
}

export default async function ProductPage({ params }: PageProps) {
  const { slug } = await params;
  const product = await getProduct(slug);

  if (!product) notFound();

  const related = await catalogApi.getRelated(slug).catch(() => []);
  const producerName = product.producer.brand_name ?? product.producer.legal_name;
  const attributes = product.attributes;
  const quality = yieldFactorQuality(attributes?.yield_factor ?? null);
  const moisture = moistureQuality(attributes?.moisture_pct ?? null);

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
            {/* El factor va primero y con su lectura al lado: es el dato que
                decide la compra, y el número solo no se interpreta sin saber que
                94 es el estándar de la Federación. */}
            {quality && (
              <Badge variant={quality.variant} size="md">
                Factor {formatYieldFactor(attributes?.yield_factor)} · {quality.label}
              </Badge>
            )}
            {moisture && (
              <Badge variant={moisture.variant === "warning" ? "warning" : "outline"}>
                Humedad {formatPercent(attributes?.moisture_pct)}
              </Badge>
            )}
            {attributes?.lot_code && (
              <Badge variant="outline">Lote {attributes.lot_code}</Badge>
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

          <div className="mt-4 space-y-1.5 text-sm text-muted-foreground">
            <p className="flex items-center gap-2">
              <Package className="size-4" aria-hidden="true" />
              Despacho en {product.dispatch_days}{" "}
              {product.dispatch_days === 1 ? "día hábil" : "días hábiles"}
            </p>
            {product.available_kg > 0 && (
              <p className="flex items-center gap-2">
                <Mountain className="size-4" aria-hidden="true" />
                Quedan {formatKilosWithCargas(product.available_kg)} de este lote
              </p>
            )}
            {product.allows_samples && (
              <p className="flex items-center gap-2">
                <FlaskConical className="size-4" aria-hidden="true" />
                El vendedor envía muestra antes de una compra por volumen
              </p>
            )}
          </div>
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
                  label="Altitud"
                  value={
                    attributes?.altitude_masl
                      ? formatAltitude(attributes.altitude_masl)
                      : null
                  }
                />
                <DataRow
                  label="Fecha de cosecha"
                  value={
                    attributes?.harvest_date ? formatDate(attributes.harvest_date) : null
                  }
                />
                <DataRow label="Método de secado" value={attributes?.drying_method} />
                <DataRow label="Código del lote" value={attributes?.lot_code} />
                <DataRow
                  label="Código SICA"
                  value={attributes?.sica_code}
                  hint="Declarado por el productor; MONK GRAIN no lo verifica ante la Federación."
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
                  Este lote no tiene finca asociada en la plataforma.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ---------------- Análisis del pergamino ---------------- */}
        <Card className="mt-6">
          <CardContent className="pt-6">
            <h3 className="mb-1 flex items-center gap-2 font-display text-lg font-semibold">
              <FlaskConical className="size-5 text-primary" aria-hidden="true" />
              Análisis del pergamino
            </h3>
            <p className="mb-4 text-sm text-muted-foreground">
              Lo declara el productor. Pide una muestra y haz tu propio análisis antes de
              cerrar una compra por volumen.
            </p>

            <dl className="grid gap-x-8 gap-y-2.5 text-sm sm:grid-cols-2">
              <DataRow
                label="Factor de rendimiento"
                value={
                  attributes?.yield_factor
                    ? `${formatYieldFactor(attributes.yield_factor)}${
                        quality ? ` · ${quality.label}` : ""
                      }`
                    : null
                }
                hint="Kilos de pergamino por saco de 70 kg de excelso. Más bajo es mejor; el estándar de la Federación es 94."
              />
              <DataRow
                label="Humedad"
                value={
                  attributes?.moisture_pct ? formatPercent(attributes.moisture_pct) : null
                }
                hint={moisture?.hint}
              />
              <DataRow
                label="Almendra sana"
                value={
                  attributes?.healthy_bean_pct
                    ? formatPercent(attributes.healthy_bean_pct)
                    : null
                }
              />
              <DataRow
                label="Pasilla"
                value={
                  attributes?.pasilla_pct ? formatPercent(attributes.pasilla_pct) : null
                }
              />
              <DataRow
                label="Daño por broca"
                value={
                  attributes?.borer_damage_pct
                    ? formatPercent(attributes.borer_damage_pct)
                    : null
                }
              />
              <DataRow
                label="Granulometría"
                value={
                  attributes?.screen_sizes && attributes.screen_sizes.length > 0
                    ? formatScreenSizes(attributes.screen_sizes)
                    : null
                }
              />
            </dl>

            {attributes?.notes && (
              <p className="mt-4 border-t border-border pt-4 text-sm leading-relaxed text-muted-foreground">
                {attributes.notes}
              </p>
            )}
          </CardContent>
        </Card>

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
  hint,
}: {
  label: string;
  value: string | number | null | undefined;
  /** Qué significa el dato. El análisis del pergamino usa vocabulario del
   *  sector, y un comprador nuevo no tiene por qué conocerlo. */
  hint?: string;
}) {
  if (!value) return null;
  return (
    <div className="border-b border-border pb-2 last:border-0">
      <div className="flex justify-between gap-4">
        <dt className="text-muted-foreground">{label}</dt>
        <dd className="text-right font-medium">{value}</dd>
      </div>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
