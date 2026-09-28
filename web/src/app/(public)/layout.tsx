import { Footer } from "@/components/shared/Footer";
import { Navbar } from "@/components/shared/Navbar";

/**
 * Layout de las páginas públicas.
 *
 * El enlace de salto permite a quien navega con teclado ir directo al
 * contenido sin recorrer toda la navegación (HU-TRX-01, CA2).
 */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#contenido" className="skip-link">
        Saltar al contenido principal
      </a>
      <Navbar />
      <main id="contenido" className="flex-1">
        {children}
      </main>
      <Footer />
    </div>
  );
}
