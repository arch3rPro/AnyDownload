# 前端构建阶段
FROM node:20-alpine AS build
WORKDIR /app
COPY . .
RUN npm install --registry=https://registry.npmmirror.com
RUN npm run build

# 生产环境
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 