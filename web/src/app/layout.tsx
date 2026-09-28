import type { Metadata } from "next";
import { Toaster } from "sonner";

import "@/styles/globals.css";

export const metadata: Metadata = {
  title: {
    default: "MONK GRAIN — Café colombiano de origen",
    template: "%s | MONK GRAIN",
  },
  description:
    "Marketplace de café colombiano que conecta caficultores, fincas y cooperativas " +
    "con tostadores, cafeterías y consumidores. Trazabilidad desde la finca.",
  keywords: [
    "café colombiano",
    "café de origen",
    "caficultores",
    "café especial",
    "trazabilidad",
    "marketplace de café",
  ],
  openGraph: {
    title: "MONK GRAIN — Café colombiano de origen",
    description:
      "Compra café directamente a los caficultores colombianos, con trazabilidad " +
      "verificable desde la finca.",
    type: "website",
    locale: "es_CO",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-CO" suppressHydrationWarning>
      <body className="min-h-screen font-sans">
        {children}
        {/*
          Los avisos se anuncian con `role="status"`, de modo que un lector de
          pantalla los lee sin robar el foco a quien esté escribiendo.
        */}
        <Toaster position="bottom-right" richColors closeButton />
      </body>
    </html>
  );
}
