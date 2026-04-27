# Build Vite SPA
FROM node:22-alpine AS build
WORKDIR /app

COPY frontend_new/package.json frontend_new/package-lock.json ./
RUN npm ci

COPY frontend_new/ .
RUN npm run build

# Static + API reverse proxy to FastAPI
FROM nginx:1.27-alpine
COPY frontend_new/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
