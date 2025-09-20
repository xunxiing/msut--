# 构建阶段
FROM node:18-alpine AS builder

WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 配置 npm 镜像源
RUN npm config set registry https://registry.npmmirror.com

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .
ENV NODE_OPTIONS=--max-old-space-size=1024
# 构建应用
RUN npm run build

# 生产阶段
FROM nginx:alpine AS production

# 复制构建产物到 nginx 默认目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置文件
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
