# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS base
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# --- Development image (code mounted from the host) -----------------------------
FROM base AS dev
COPY package.json package-lock.json ./
RUN npm ci
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh \
    && sha256sum package-lock.json | cut -d' ' -f1 > node_modules/.lock-hash
ENTRYPOINT ["entrypoint.sh"]
EXPOSE 3000
CMD ["npm", "run", "dev"]

# --- Production build -----------------------------------------------------------
FROM base AS build
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Fixed at build time: relays (next.config.ts), the public address in the pages rendered in
# advance, and everything that starts with NEXT_PUBLIC_.
ARG API_INTERNAL_URL=http://backend:8000
ARG S3_INTERNAL_URL=
ARG UMAMI_INTERNAL_URL=http://umami:3000
ARG SITE_URL=http://localhost:3000
ARG NEXT_PUBLIC_WS_ORIGIN=
ARG NEXT_PUBLIC_UMAMI_WEBSITE_ID=
ARG NEXT_PUBLIC_META_PIXEL_ID=
ARG NEXT_PUBLIC_SENTRY_DSN=
ARG NEXT_PUBLIC_SENTRY_ENVIRONMENT=production
ENV API_INTERNAL_URL=$API_INTERNAL_URL \
    S3_INTERNAL_URL=$S3_INTERNAL_URL \
    UMAMI_INTERNAL_URL=$UMAMI_INTERNAL_URL \
    SITE_URL=$SITE_URL \
    NEXT_PUBLIC_WS_ORIGIN=$NEXT_PUBLIC_WS_ORIGIN \
    NEXT_PUBLIC_UMAMI_WEBSITE_ID=$NEXT_PUBLIC_UMAMI_WEBSITE_ID \
    NEXT_PUBLIC_META_PIXEL_ID=$NEXT_PUBLIC_META_PIXEL_ID \
    NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN \
    NEXT_PUBLIC_SENTRY_ENVIRONMENT=$NEXT_PUBLIC_SENTRY_ENVIRONMENT
RUN npm run build

FROM base AS prod
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD ["node", "-e", "fetch('http://localhost:3000/robots.txt').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "server.js"]
