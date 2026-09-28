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
RUN npm ci || npm install

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
ENV NEXT_TELEMETRY_DISABLED=1
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
