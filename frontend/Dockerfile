# Multi-stage: build the SPA, serve via nginx
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
# Live mode by default for Cloud Run; VITE_API_BASE injected at build time
ARG VITE_API_BASE=""
ENV VITE_USE_MOCKS=false VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
