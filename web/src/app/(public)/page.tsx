import Link from "next/link";
import { Award, Leaf, MapPin, ShieldCheck, Sprout, Truck } from "lucide-react";

import { LogoMark } from "@/components/shared/Logo";
import { EmptyState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProductCard } from "@/features/catalog/components/ProductCard";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Page, ProductListItem } from "@/types/catalog";

/**
 * Página de inicio.
 *
 * Se renderiza en el servidor y revalida cada 5 minutos: el catálogo cambia con
 * poca frecuencia y así la primera carga no espera a la API (RNF-01).
 */
export const revalidate = 300;

const REGIONS = [
  { code: "huila", name: "Huila", description: "Dulzor y acidez cítrica" },
  { code: "narino", name: "Nariño", description: "Altura extrema, notas florales" },
  { code: "cauca", name: "Cauca", description: "Acidez brillante, dulzor de panela" },
  { code: "eje_cafetero", name: "Eje Cafetero", description: "El perfil clásico" },
  { code: "tolima", name: "Tolima", description: "Frutos rojos y chocolate" },
  { code: "sierra_nevada", name: "Sierra Nevada", description: "Origen indígena" },
];

const BENEFITS = [
  {
    icon: MapPin,
    title: "Origen verificable",
    description:
      "Cada café indica su finca, municipio y altitud. Sabes exactamente de dónde viene.",
  },
  {
    icon: Sprout,
    title: "Trato directo",
    description:
      "Compras al caficultor sin cadenas de intermediarios. Un precio más justo para quien lo cultiva.",
  },
  {
    icon: Award,
    title: "Calidad documentada",
    description:
      "Factor de rendimiento, humedad, almendra sana, pasilla y broca en cada lote.",
  },
  {
    icon: ShieldCheck,
    title: "Productores verificados",
    description:
      "Validamos identidad y documentos antes de permitir publicar en la plataforma.",
  },
  {
    icon: Leaf,
    title: "Prácticas sostenibles",
    description:
      "Certificaciones y prácticas ambientales visibles en el perfil de cada finca.",
  },
  {
    icon: Truck,
    title: "Envíos a todo el país",
    description: "Seguimiento del pedido desde el despacho hasta la entrega.",
  },
];

const TRACEABILITY_STEPS = [
  { step: "01", title: "Finca", description: "Municipio, vereda y altitud del cultivo." },
  { step: "02", title: "Cosecha", description: "Fecha de recolección y variedad." },
  {
    step: "03",
    title: "Beneficio y secado",
    description: "Lavado, natural u honey, y cómo se secó el pergamino.",
  },
  { step: "04", title: "Entrega", description: "Despacho con guía y seguimiento." },
];

async function getFeaturedProducts(): Promise<ProductListItem[]> {
  try {
    const response = await api.get<Page<ProductListItem>>("/products", {
      query: { sort: "popular", page_size: 8 },
      next: { revalidate: 300 },
    } as Parameters<typeof api.get>[1]);
    return response.items;
  } catch (error) {
    // El catálogo aún no existe (fase 8) o la API no responde: la página debe
    // seguir siendo útil en vez de romperse por completo.
    if (error instanceof ApiError) return [];
    return [];
  }
}

export default async function HomePage() {
  const featuredProducts = await getFeaturedProducts();

  return (
    <>
      {/* ---------------- Portada ---------------- */}
      <section className="relative overflow-hidden bg-coffee-dark text-cream">
        <div
          className="absolute inset-0 opacity-25"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, #6F4E37 0%, transparent 45%), " +
              "radial-gradient(circle at 80% 60%, #1F4D3A 0%, transparent 50%)",
          }}
          aria-hidden="true"
        />

        <div className="container-page relative py-20 lg:py-28">
          <div className="max-w-2xl animate-fade-in">
            <Badge
              variant="spotlight"
              size="md"
              className="mb-5 font-semibold uppercase tracking-wider"
            >
              Café colombiano de origen
            </Badge>

            <h1 className="font-display text-4xl font-bold leading-tight sm:text-5xl lg:text-6xl">
              Pergamino de la finca, sin intermediarios
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-relaxed text-cream/85">
              MONK GRAIN conecta a los caficultores, fincas y cooperativas de Colombia con
              quienes compran pergamino seco por volumen. Cada lote publica su factor de
              rendimiento y su análisis, y el precio es por kilo.
            </p>

            {/* La segunda acción no repite "Vender café": esa entrada ya vive
                de forma permanente en la barra de navegación. Duplicar el mismo
                botón en pantalla resta claridad en vez de sumar alcance. */}
            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                href="/catalogo"
                className={cn(buttonVariants({ variant: "accent", size: "lg" }))}
              >
                Comprar café
              </Link>
              <Link
                href="/productores"
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "border-cream/40 text-cream hover:bg-cream/10",
                )}
              >
                Conocer a los productores
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- Regiones ---------------- */}
      <section className="container-page py-16">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-bold sm:text-3xl">
              Cafés por región
            </h2>
            <p className="mt-2 text-muted-foreground">
              Cada región cafetera de Colombia imprime su carácter en la taza.
            </p>
          </div>
          {/* El catálogo ya filtra por región; apuntar aquí evita un 404
              mientras la página de regiones no exista. */}
          <Link
            href="/catalogo"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Ver el catálogo
          </Link>
        </header>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          {REGIONS.map((region) => (
            <Link
              key={region.code}
              href={`/catalogo?region=${region.code}`}
              className="group rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-muted/50"
            >
              <LogoMark className="mb-3 size-8 opacity-70" monochrome />
              <p className="font-display font-semibold group-hover:text-primary">
                {region.name}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {region.description}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* ---------------- Productos destacados ---------------- */}
      <section className="container-page py-4 pb-16">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-bold sm:text-3xl">
              Cafés destacados
            </h2>
            <p className="mt-2 text-muted-foreground">
              Selección de los cafés mejor valorados por nuestra comunidad.
            </p>
          </div>
          <Link
            href="/catalogo"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Ver catálogo completo
          </Link>
        </header>

        {featuredProducts.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {featuredProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="Aún no hay cafés publicados"
            description="Los productores están completando su registro. Vuelve pronto para conocer los primeros cafés de la plataforma."
            action={
              <Link
                href="/vender"
                className={cn(buttonVariants({ variant: "primary", size: "md" }))}
              >
                Publicar mi café
              </Link>
            }
          />
        )}
      </section>

      {/* ---------------- Trazabilidad ---------------- */}
      <section className="bg-forest text-cream">
        <div className="container-page py-16">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-2xl font-bold sm:text-3xl">
              Sabes de dónde viene tu café
            </h2>
            <p className="mt-3 text-cream/85">
              Cada publicación registra el recorrido completo del lote. Sin promesas
              vagas: datos concretos que puedes verificar.
            </p>
          </div>

          <ol className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {TRACEABILITY_STEPS.map((item) => (
              <li key={item.step} className="rounded-lg bg-cream/10 p-6">
                <span className="font-display text-3xl font-bold text-gold">
                  {item.step}
                </span>
                <h3 className="mt-3 font-display text-lg font-semibold">{item.title}</h3>
                <p className="mt-1.5 text-sm text-cream/80">{item.description}</p>
              </li>
            ))}
          </ol>

          <p className="mt-8 text-center text-sm text-cream/70">
            La ubicación de las fincas se muestra a nivel de municipio para proteger la
            privacidad y la seguridad de los productores.
          </p>
        </div>
      </section>

      {/* ---------------- Beneficios ---------------- */}
      <section className="container-page py-16">
        <div className="mx-auto mb-10 max-w-2xl text-center">
          <h2 className="font-display text-2xl font-bold sm:text-3xl">
            Por qué comprar en MONK GRAIN
          </h2>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {BENEFITS.map((benefit) => (
            <Card key={benefit.title}>
              <CardContent className="pt-6">
                <benefit.icon className="mb-4 size-7 text-primary" aria-hidden="true" />
                <h3 className="font-display text-lg font-semibold">{benefit.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {benefit.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* ---------------- Llamado final ---------------- */}
      <section className="container-page pb-20">
        <div className="rounded-lg border border-border bg-muted/50 px-6 py-12 text-center sm:px-12">
          <h2 className="font-display text-2xl font-bold sm:text-3xl">
            ¿Cultivas café? Véndelo directamente
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Publica tu cosecha, cuenta la historia de tu finca y llega a compradores de
            todo el país sin intermediarios.
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link
              href="/vender"
              className={cn(buttonVariants({ variant: "primary", size: "lg" }))}
            >
              Registrarme como productor
            </Link>
            <Link
              href="/vender#pasos"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              Cómo funciona
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
