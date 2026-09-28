import Link from "next/link";

import { Logo } from "@/components/shared/Logo";

const FOOTER_SECTIONS = [
  {
    title: "Comprar",
    links: [
      { href: "/catalogo", label: "Catálogo" },
      { href: "/regiones", label: "Cafés por región" },
      { href: "/productores", label: "Productores" },
      { href: "/catalogo?sort=newest", label: "Novedades" },
    ],
  },
  {
    title: "Vender",
    links: [
      { href: "/vender", label: "Registrarme como productor" },
      { href: "/vender/como-funciona", label: "Cómo funciona" },
      { href: "/vender/comisiones", label: "Comisiones" },
    ],
  },
  {
    title: "Conocer",
    links: [
      { href: "/blog", label: "Blog" },
      { href: "/trazabilidad", label: "Trazabilidad" },
      { href: "/sostenibilidad", label: "Sostenibilidad" },
      { href: "/nosotros", label: "Sobre MONK GRAIN" },
    ],
  },
  {
    title: "Ayuda",
    links: [
      { href: "/ayuda", label: "Centro de ayuda" },
      { href: "/contacto", label: "Contacto" },
      { href: "/envios", label: "Envíos y entregas" },
      { href: "/devoluciones", label: "Cambios y devoluciones" },
    ],
  },
];

const LEGAL_LINKS = [
  { href: "/legal/terminos", label: "Términos y condiciones" },
  { href: "/legal/privacidad", label: "Política de privacidad" },
  { href: "/legal/datos", label: "Tratamiento de datos" },
  { href: "/legal/devoluciones", label: "Política de devoluciones" },
];

export function Footer() {
  return (
    <footer className="mt-20 border-t border-border bg-muted/40">
      <div className="container-page py-12">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_repeat(4,1fr)]">
          <div className="max-w-xs">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Conectamos a los caficultores colombianos directamente con quienes valoran
              su trabajo. Café con origen verificable, desde la finca hasta tu taza.
            </p>
          </div>

          {FOOTER_SECTIONS.map((section) => (
            <div key={section.title}>
              <h2 className="mb-2 text-sm font-semibold">{section.title}</h2>
              <ul>
                {section.links.map((link) => (
                  <li key={link.href}>
                    {/* `py-1.5` lleva el área táctil a 27 px de alto. Un enlace
                        de solo texto mide 15 px, por debajo del mínimo de 24 px
                        que exige WCAG 2.5.8 para objetivos de puntero. */}
                    <Link
                      href={link.href}
                      className="inline-block py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-4 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} MONK GRAIN. Hecho en Colombia.
          </p>
          <ul className="flex flex-wrap gap-x-5">
            {LEGAL_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="inline-block py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}
