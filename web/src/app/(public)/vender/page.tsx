import type { Metadata } from "next";
import Link from "next/link";
import { Award, Camera, Coffee, LineChart, Package, ShieldCheck } from "lucide-react";

import { COMMISSION_LABEL } from "@/lib/business";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Vender pergamino",
  description:
    "Publica tu pergamino seco en MONK GRAIN con su factor de rendimiento y su análisis, " +
    "y véndelo por kilo a quien compra por volumen, sin intermediarios.",
};

const STEPS = [
  {
    icon: ShieldCheck,
    title: "Crea tu cuenta y verifícala",
    description:
      "Registras tu finca o cooperativa con sus datos legales. Nuestro equipo revisa la " +
      "solicitud antes de habilitarte para vender.",
  },
  {
    icon: Camera,
    title: "Publica tu café",
    description:
      "Cuentas su origen, su proceso y su perfil de taza; subes las fotografías y defines " +
      "las presentaciones con su precio e inventario.",
  },
  {
    icon: Award,
    title: "Respáldalo con tus certificados",
    description:
      "Cargas los certificados con su vigencia. Solo puedes exhibir en un café lo que " +
      "tengas acreditado y al día.",
  },
  {
    icon: Package,
    title: "Recibe pedidos y despacha",
    description:
      "Cada pedido llega a tu panel con el detalle de lo vendido. Tú preparas y despachas; " +
      "el inventario se descuenta solo.",
  },
];

export default function SellPage() {
  return (
    <div>
      <section className="bg-coffee-dark px-4 py-16 text-cream">
        <div className="mx-auto max-w-3xl text-center">
          <Badge variant="spotlight" size="md">
            Para caficultores
          </Badge>

          <h1 className="mt-4 font-display text-4xl font-bold leading-tight sm:text-5xl">
            Tu pergamino, al precio que pones tú
          </h1>

          <p className="mt-4 text-lg text-cream/85">
            MONK GRAIN conecta a las fincas y cooperativas cafeteras de Colombia con
            quienes compran pergamino por volumen. Publicas tu lote con su factor y su
            análisis, fijas tu precio por kilo y tu mínimo de compra, sin intermediarios
            que diluyan lo que recibes por tu cosecha.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/registro" className={buttonVariants({ variant: "accent" })}>
              Registrarme como vendedor
            </Link>
            <Link href="/productor" className={buttonVariants({ variant: "outline" })}>
              Ya tengo cuenta
            </Link>
          </div>
        </div>
      </section>

      <section aria-labelledby="pasos" className="mx-auto max-w-5xl px-4 py-16">
        <h2 id="pasos" className="text-center font-display text-3xl font-bold">
          Cómo funciona
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-center text-muted-foreground">
          De la finca al catálogo en cuatro pasos.
        </p>

        <ol className="mt-10 grid gap-6 sm:grid-cols-2">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <Card className="h-full">
                <CardContent className="flex gap-4 p-6">
                  <div
                    className="flex size-11 shrink-0 items-center justify-center rounded-full bg-accent/15"
                    aria-hidden="true"
                  >
                    <step.icon className="size-5 text-accent-foreground" />
                  </div>

                  <div>
                    <h3 className="font-display text-lg font-semibold">
                      <span className="text-muted-foreground">{index + 1}.</span>{" "}
                      {step.title}
                    </h3>
                    <p className="mt-1.5 text-sm text-muted-foreground">
                      {step.description}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <section
        aria-labelledby="condiciones"
        className="border-t border-border bg-muted/30"
      >
        <div className="mx-auto max-w-5xl px-4 py-16">
          <h2 id="condiciones" className="text-center font-display text-3xl font-bold">
            Condiciones claras
          </h2>

          <dl className="mt-10 grid gap-8 sm:grid-cols-3">
            <div className="text-center">
              <dt className="font-display text-3xl font-bold text-coffee">
                {COMMISSION_LABEL}
              </dt>
              <dd className="mt-2 text-sm text-muted-foreground">
                Comisión por venta. Se calcula al confirmarse el pedido y queda registrada
                en tu liquidación.
              </dd>
            </div>

            <div className="text-center">
              <dt className="font-display text-3xl font-bold text-coffee">
                Tú fijas el precio
              </dt>
              <dd className="mt-2 text-sm text-muted-foreground">
                Defines el precio al detal y, si quieres, uno mayorista para compras por
                volumen.
              </dd>
            </div>

            <div className="text-center">
              <dt className="font-display text-3xl font-bold text-coffee">
                Sin exclusividad
              </dt>
              <dd className="mt-2 text-sm text-muted-foreground">
                Puedes retirar tu café del catálogo cuando quieras, sin penalidad.
              </dd>
            </div>
          </dl>

          <div className="mt-10 rounded-lg border border-border bg-background p-6">
            <h3 className="flex items-center gap-2 font-display text-lg font-semibold">
              <Coffee className="size-5 text-accent-foreground" aria-hidden="true" />
              Qué cuidamos de tu información
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              <li>
                La ubicación exacta de tu finca <strong>no se publica</strong>: el mapa
                muestra una posición aproximada del municipio.
              </li>
              <li>
                Tus datos bancarios se guardan cifrados y nunca aparecen en la ficha
                pública.
              </li>
              <li>
                Los certificados que cargues son privados: los abren únicamente tú y el
                equipo de MONK GRAIN.
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-4 py-16 text-center">
        <LineChart
          className="mx-auto size-10 text-accent-foreground"
          aria-hidden="true"
        />
        <h2 className="mt-4 font-display text-3xl font-bold">¿Listo para empezar?</h2>
        <p className="mt-2 text-muted-foreground">
          Crear la cuenta es gratis. Solo cobramos cuando vendes.
        </p>
        <Link href="/registro" className={`mt-6 inline-flex ${buttonVariants()}`}>
          Registrar mi finca
        </Link>
      </section>
    </div>
  );
}
