import Link from "next/link";

import { Logo } from "@/components/shared/Logo";

/** Layout de las páginas de acceso: sin navegación que distraiga del formulario. */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-muted/30">
      <header className="container-page py-6">
        <Link href="/" aria-label="MONK GRAIN, ir al inicio">
          <Logo />
        </Link>
      </header>

      <main className="container-page flex flex-1 items-start justify-center pb-16 pt-4">
        <div className="w-full max-w-md">{children}</div>
      </main>

      <footer className="container-page pb-8 text-center">
        <p className="text-xs text-muted-foreground">
          Al continuar aceptas los{" "}
          <Link href="/legal/terminos" className="underline hover:text-foreground">
            términos y condiciones
          </Link>{" "}
          y la{" "}
          <Link href="/legal/privacidad" className="underline hover:text-foreground">
            política de privacidad
          </Link>
          .
        </p>
      </footer>
    </div>
  );
}
