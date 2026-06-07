FROM node:22-alpine AS base
WORKDIR /app

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS deps
COPY package*.json ./
RUN npm ci

# ── Development ───────────────────────────────────────────────────────────────
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# ── Build ─────────────────────────────────────────────────────────────────────
FROM deps AS build
COPY . .
ARG VITE_API_URL
ARG VITE_MQTT_URL
ARG VITE_MQTT_USER
ARG VITE_MQTT_PASS
ENV VITE_API_URL=$VITE_API_URL \
    VITE_MQTT_URL=$VITE_MQTT_URL \
    VITE_MQTT_USER=$VITE_MQTT_USER \
    VITE_MQTT_PASS=$VITE_MQTT_PASS
RUN npm run build

# ── Production (Nginx) ────────────────────────────────────────────────────────
FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
