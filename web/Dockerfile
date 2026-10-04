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
RUN npm run build

FROM base AS prod
ENV NODE_ENV=production
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
