# Frontend Multi-Stage Build: Node build stage -> Nginx static serving
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Serving stage with Nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
