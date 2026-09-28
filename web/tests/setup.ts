/**
 * Preparación común de las pruebas del frontend.
 *
 * Los matchers de `jest-dom` permiten afirmar sobre lo que el usuario percibe
 * —«está en el documento», «está deshabilitado», «tiene este texto accesible»—
 * en lugar de sobre la estructura interna que React produjo.
 */
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Sin esto, el árbol de una prueba sobrevive a la siguiente y las consultas por
// texto encuentran dos coincidencias donde debería haber una.
afterEach(() => {
  cleanup();
});
