import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Salida standalone: la imagen de producción solo lleva lo necesario para
  // ejecutar, sin node_modules completo.
  output: "standalone",

  images: {
    remotePatterns: [
      // Almacenamiento de imágenes (MinIO en desarrollo, S3 en producción).
      { protocol: "http", hostname: "localhost", port: "9000" },
      { protocol: "http", hostname: "localhost", port: "3000" },
      { protocol: "https", hostname: "**.amazonaws.com" },
    ],
  },

  /**
   * Proxy de medios.
   *
   * El almacenamiento se publica en `localhost:9000` para el navegador, pero el
   * optimizador de imágenes corre **dentro** del contenedor de Next, donde
   * `localhost` es el propio contenedor y no MinIO: la descarga fallaba con
   * `ECONNREFUSED` y la ficha acababa mostrando el marcador aunque la imagen
   * existiera.
   *
   * Sirviendo los archivos bajo `/media` la misma URL vale para los dos lados:
   * el navegador la pide a Next y Next la resuelve por la red interna de Docker.
   * En producción, con un S3 accesible desde ambos, esta reescritura sobra y
   * `MEDIA_INTERNAL_URL` puede apuntar directamente al bucket.
   */
  async rewrites() {
    const mediaOrigin = process.env.MEDIA_INTERNAL_URL ?? "http://minio:9000";
    return [{ source: "/media/:path*", destination: `${mediaOrigin}/:path*` }];
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "geolocation=(), microphone=(), camera=()",
          },
          { key: "Content-Security-Policy", value: contentSecurityPolicy() },
        ],
      },
    ];
  },
};

/**
 * Política de seguridad de contenido.
 *
 * Alcance real: `script-src` admite `'unsafe-inline'` porque el App Router
 * incorpora el estado de hidratación en etiquetas `<script>` en línea. Eso
 * significa que la política **no** detiene un script inyectado en la propia
 * página; lo que sí impide es cargar código de otro dominio, enviar
 * formularios fuera del sitio, incrustar la página en un iframe ajeno o
 * reescribir la URL base — es decir, corta las vías habituales de exfiltración
 * aunque la inyección llegue a producirse.
 *
 * Cerrar el hueco restante exige servir un `nonce` distinto en cada petición
 * desde el middleware; queda anotado como mejora pendiente en la auditoría.
 */
function contentSecurityPolicy(): string {
  const isDev = process.env.NODE_ENV !== "production";
  const apiOrigin = process.env.NEXT_PUBLIC_API_URL
    ? new URL(process.env.NEXT_PUBLIC_API_URL).origin
    : "";

  return [
    "default-src 'self'",
    // 'unsafe-eval' solo en desarrollo: lo necesita la recarga en caliente.
    `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: http://localhost:9000 https://*.amazonaws.com",
    "font-src 'self' data:",
    `connect-src 'self' ${apiOrigin}`.trim(),
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}

export default nextConfig;
