import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Configuración de las pruebas del frontend.
 *
 * `jsdom` porque lo que se prueba son componentes y funciones que tocan el DOM;
 * `setupFiles` carga los matchers de Testing Library para poder afirmar sobre lo
 * que el usuario ve y no sobre la estructura interna de React.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    // Sin esto, cada archivo de prueba arranca su propio entorno jsdom y la
    // suite tarda varias veces más de lo necesario.
    pool: "threads",
  },
  resolve: {
    alias: {
      // El mismo alias que usa Next y que declara tsconfig.
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
