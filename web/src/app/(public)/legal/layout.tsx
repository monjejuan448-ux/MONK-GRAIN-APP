import Link from "next/link";
import { AlertTriangle } from "lucide-react";

const SECTIONS = [
  { href: "/legal/terminos", label: "Términos y condiciones" },
  { href: "/legal/privacidad", label: "Política de privacidad" },
  { href: "/legal/datos", label: "Tratamiento de datos" },
  { href: "/legal/devoluciones", label: "Devoluciones y reembolsos" },
];

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container-page py-10">
      <div className="grid gap-10 lg:grid-cols-[220px_1fr]">
        <nav
          aria-label="Documentos legales"
          className="lg:sticky lg:top-24 lg:self-start"
        >
          <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Documentos legales
          </h2>
          <ul className="space-y-1">
            {SECTIONS.map((section) => (
              <li key={section.href}>
                <Link
                  href={section.href}
                  className="block rounded-md px-3 py-2 text-sm hover:bg-muted"
                >
                  {section.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div>
          {/*
            Estos textos los redactó el equipo de desarrollo siguiendo lo que
            exige la Ley 1581 de 2012, pero no los ha revisado un abogado. Antes
            de operar con usuarios reales deben pasar por revisión jurídica: son
            documentos con efectos vinculantes, y el aviso se muestra en la
            página —no solo en un comentario del código— para que nadie los dé
            por definitivos.
          */}
          <div className="mb-8 flex gap-3 rounded-md border border-gold/40 bg-gold/10 p-4">
            <AlertTriangle
              className="mt-0.5 size-5 shrink-0 text-coffee-dark"
              aria-hidden="true"
            />
            <div className="text-sm text-coffee-dark">
              <p className="font-semibold">Borrador pendiente de revisión jurídica</p>
              <p className="mt-1">
                Este documento fue preparado por el equipo de desarrollo y aún no lo ha
                revisado un abogado. No debe publicarse como definitivo ni considerarse
                asesoría legal. Los campos entre corchetes deben completarse con los datos
                reales de la empresa.
              </p>
            </div>
          </div>

          <article className="prose-legal max-w-3xl">{children}</article>
        </div>
      </div>
    </div>
  );
}
