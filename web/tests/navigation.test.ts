import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Que la navegación global no prometa páginas que no existen.
 *
 * La barra y el pie salen en las 41 páginas del sitio, así que un `href` a una
 * ruta sin escribir no es un enlace roto: son 41. Llegaron a haber ocho, dos de
 * ellos en la navegación principal, y una auditoría por inspección los había
 * calificado de «ninguna crítica».
 *
 * La comprobación es estructural a propósito —se contrastan los `href` contra
 * los archivos `page.tsx` del árbol de rutas— porque es lo que falla: nadie
 * escribe un enlace roto, se queda roto cuando la página que iba a escribirse no
 * se escribe.
 */

// Relativo a la raíz del proyecto, que es desde donde Vitest se ejecuta.
const APP_DIR = resolve(process.cwd(), "src/app");
const NAV_FILES = [
  resolve(process.cwd(), "src/components/shared/Navbar.tsx"),
  resolve(process.cwd(), "src/components/shared/Footer.tsx"),
];

/** Rutas que Next sirve, leídas del árbol de archivos. */
function collectRoutes(dir: string, prefix = ""): string[] {
  const routes: string[] = [];

  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);

    if (statSync(full).isDirectory()) {
      // Los grupos de rutas —(public), (auth)— organizan archivos pero no
      // aparecen en la URL.
      const segment =
        entry.startsWith("(") && entry.endsWith(")") ? prefix : `${prefix}/${entry}`;
      routes.push(...collectRoutes(full, segment));
    } else if (entry === "page.tsx") {
      routes.push(prefix === "" ? "/" : prefix);
    }
  }

  return routes;
}

/** Los enlaces internos que escriben la barra y el pie. */
function collectInternalLinks(): string[] {
  const links = new Set<string>();

  for (const file of NAV_FILES) {
    const source = readFileSync(file, "utf8");
    // Cubre las dos formas que usan estos componentes: `href="/x"` en el JSX y
    // `href: "/x"` en las tablas de enlaces.
    for (const match of source.matchAll(/href[=:]\s*"(\/[^"]*)"/g)) {
      const href = match[1];
      if (href) links.add(href);
    }
  }

  return [...links];
}

/** Quita lo que no participa en la resolución de la ruta. */
function routeOf(href: string): string {
  const path = href.split("?")[0]?.split("#")[0] ?? href;
  return path.length > 1 && path.endsWith("/") ? path.slice(0, -1) : path;
}

describe("la navegación global", () => {
  const routes = new Set(collectRoutes(APP_DIR));
  const links = collectInternalLinks();

  it("encuentra las rutas y los enlaces que va a comparar", () => {
    // Si alguna de las dos lecturas se rompe —se mueve un archivo, cambia el
    // nombre de un componente— la prueba pasaría en vacío sin comprobar nada.
    expect(routes.size).toBeGreaterThan(20);
    expect(links.length).toBeGreaterThan(8);
    expect(routes.has("/catalogo")).toBe(true);
  });

  it("no enlaza ninguna página que no exista", () => {
    const roto = links.filter((href) => !routes.has(routeOf(href)));

    expect(roto).toEqual([]);
  });

  it("sigue sin enlazar las páginas de contenido que nunca se escribieron", () => {
    // Los ocho que estaban: si alguien devuelve el enlace antes que la página,
    // esta prueba lo dice por su nombre en lugar de dejarlo salir a producción.
    const sinEscribir = [
      "/regiones",
      "/blog",
      "/nosotros",
      "/trazabilidad",
      "/sostenibilidad",
      "/ayuda",
      "/contacto",
      "/envios",
    ];

    const prometidas = sinEscribir.filter(
      (href) => links.includes(href) && !routes.has(href),
    );

    expect(prometidas).toEqual([]);
  });
});
