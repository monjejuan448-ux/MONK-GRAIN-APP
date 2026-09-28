"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Heart, Menu, Search, ShoppingCart, User, X } from "lucide-react";

import { Logo } from "@/components/shared/Logo";
import { Button, buttonVariants } from "@/components/ui/button";
import { session } from "@/lib/session";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/catalogo", label: "Catálogo" },
  { href: "/productores", label: "Productores" },
  { href: "/regiones", label: "Regiones" },
  { href: "/blog", label: "Blog" },
];

export function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  // Empieza en `false` y se resuelve tras montar. La sesión vive en
  // `sessionStorage`, que el servidor no puede leer: decidir el destino
  // durante el renderizado del servidor produciría una discrepancia de
  // hidratación. Hasta entonces el icono apunta a iniciar sesión, que es el
  // destino correcto para quien no la tiene.
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setIsAuthenticated(session.isAuthenticated());
  }, []);

  const accountHref = isAuthenticated ? "/mi-cuenta" : "/ingresar";
  const accountLabel = isAuthenticated ? "Mi cuenta" : "Iniciar sesión";

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
      <nav className="container-page" aria-label="Navegación principal">
        <div className="flex h-16 items-center justify-between gap-4">
          <Link href="/" className="shrink-0" aria-label="MONK GRAIN, ir al inicio">
            <Logo />
          </Link>

          <div className="hidden items-center gap-1 lg:flex">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-md px-3 py-2 text-sm font-medium text-foreground/80 transition-colors hover:bg-muted hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </div>

          <form
            action="/catalogo"
            className="hidden max-w-sm flex-1 md:block"
            role="search"
          >
            <label htmlFor="site-search" className="sr-only">
              Buscar café
            </label>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <input
                id="site-search"
                name="q"
                type="search"
                placeholder="Buscar por origen, variedad o finca"
                className="h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm placeholder:text-muted-foreground"
              />
            </div>
          </form>

          <div className="flex items-center gap-1">
            {/* Son enlaces, no botones: se renderizan como <a> con la apariencia
                de botón. Anidar un enlace dentro de un botón sería HTML inválido
                y confundiría a los lectores de pantalla. */}
            <Link
              href="/favoritos"
              className={cn(buttonVariants({ variant: "ghost", size: "icon" }))}
              aria-label="Favoritos"
            >
              <Heart aria-hidden="true" />
            </Link>
            <Link
              href="/carrito"
              className={cn(buttonVariants({ variant: "ghost", size: "icon" }))}
              aria-label="Carrito de compras"
            >
              <ShoppingCart aria-hidden="true" />
            </Link>
            <Link
              href={accountHref}
              className={cn(buttonVariants({ variant: "ghost", size: "icon" }))}
              aria-label={accountLabel}
            >
              <User aria-hidden="true" />
            </Link>

            <Link
              href="/vender"
              className={cn(
                buttonVariants({ variant: "secondary", size: "sm" }),
                "ml-2 hidden sm:inline-flex",
              )}
            >
              Vender café
            </Link>

            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setIsMenuOpen((open) => !open)}
              aria-expanded={isMenuOpen}
              aria-controls="mobile-menu"
              aria-label={isMenuOpen ? "Cerrar menú" : "Abrir menú"}
            >
              {isMenuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
            </Button>
          </div>
        </div>

        <div
          id="mobile-menu"
          className={cn("border-t border-border py-3 lg:hidden", !isMenuOpen && "hidden")}
        >
          <form action="/catalogo" className="mb-3 md:hidden" role="search">
            <label htmlFor="mobile-search" className="sr-only">
              Buscar café
            </label>
            <input
              id="mobile-search"
              name="q"
              type="search"
              placeholder="Buscar café"
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            />
          </form>
          <ul className="flex flex-col">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="block rounded-md px-3 py-2.5 text-sm font-medium hover:bg-muted"
                  onClick={() => setIsMenuOpen(false)}
                >
                  {link.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                href="/vender"
                className="block rounded-md px-3 py-2.5 text-sm font-medium text-secondary"
                onClick={() => setIsMenuOpen(false)}
              >
                Vender café
              </Link>
            </li>
          </ul>
        </div>
      </nav>
    </header>
  );
}
