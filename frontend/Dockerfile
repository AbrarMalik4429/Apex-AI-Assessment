FROM node:22-alpine AS build
WORKDIR /frontend
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY scripts/ ./scripts/
COPY src/ ./src/
ARG FRONTEND_API_BASE_URL
ARG FRONTEND_FONT_URL=""
RUN FRONTEND_API_BASE_URL="$FRONTEND_API_BASE_URL" FRONTEND_FONT_URL="$FRONTEND_FONT_URL" npm run build

FROM nginxinc/nginx-unprivileged:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
