# ============================================================
# MONK GRAIN — Imagen del frontend web
# ============================================================

FROM node:22-alpine AS base
WORKDIR /app

# ------------------------------------------------------------
# Dependencias
# ------------------------------------------------------------
FROM base AS deps
COPY package.json package-lock.json* ./
# `npm ci` a secas: el respaldo en `npm install` ocultaba que no existía
# package-lock.json y hacía que cada construcción resolviera versiones distintas.
RUN npm ci

# ------------------------------------------------------------
# Desarrollo: recarga automática
# ------------------------------------------------------------
FROM base AS development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ------------------------------------------------------------
# Build de producción
# ------------------------------------------------------------
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Las variables `NEXT_PUBLIC_*` se incrustan en el paquete del navegador **al
# compilar**, no al arrancar: declararlas solo como entorno del contenedor llega
# demasiado tarde y el navegador acaba llamando a `localhost`. La política de
# seguridad de contenido también se calcula aquí, y sin el origen real de la API
# su `connect-src` bloquearía las peticiones del propio sitio.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ARG NEXT_PUBLIC_DEFAULT_LOCALE=es-CO
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_PUBLIC_DEFAULT_LOCALE=$NEXT_PUBLIC_DEFAULT_LOCALE \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ------------------------------------------------------------
# Producción: salida standalone, usuario sin privilegios
# ------------------------------------------------------------
FROM base AS production
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
