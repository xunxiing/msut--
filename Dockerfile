# MSUT全栈认证系统 - 多阶段构建（Python 后端 + Nginx 前端）

# 构建参数
ARG NODE_VERSION=20.18.0
ARG ALPINE_VERSION=3.20
ARG NGINX_VERSION=1.27.2

# 前端构建阶段
FROM node:${NODE_VERSION}-alpine${ALPINE_VERSION} AS frontend-builder

WORKDIR /app/web

# 复制前端依赖文件
COPY melon-tech-web/package*.json ./
COPY melon-tech-web/tsconfig*.json ./

# 安装依赖
RUN npm ci && npm cache clean --force

# 复制前端源码并构建
COPY melon-tech-web/ ./
RUN npm run build

# 最终运行阶段（Nginx + Python 后端）
FROM nginx:${NGINX_VERSION}-alpine${ALPINE_VERSION}

# 安装运行时依赖
RUN apk add --no-cache \
    nodejs \
    npm \
    sqlite \
    curl \
    python3 \
    py3-pip \
    && rm -rf /var/cache/apk/*

# 创建非root用户
RUN addgroup -g 10001 -S appgroup && \
    adduser -u 10001 -S appuser -G appgroup

# 复制nginx配置
COPY melon-tech-web/nginx.conf /etc/nginx/nginx.conf

# 复制前端构建产物
COPY --from=frontend-builder /app/web/dist /usr/share/nginx/html

# 复制后端代码并安装 Python 依赖
WORKDIR /app/server
COPY server /app/server
# Install build deps for Alpine to compile any wheels if needed (e.g. bcrypt/cffi), then remove them
RUN apk update && apk add --no-cache --virtual .build-deps build-base python3-dev libffi-dev musl-dev \
    && python3 -m pip install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir -r /app/server/requirements.txt \
    && apk del .build-deps && rm -rf /var/cache/apk/*

# 创建启动脚本（在 root 用户下创建）
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# 启动后端服务 (FastAPI)' >> /app/start.sh && \
    echo 'PORT="${PORT:-3400}"' >> /app/start.sh && \
    echo 'cd /app' >> /app/start.sh && \
    echo 'python3 -m uvicorn server.app:app --host 0.0.0.0 --port "$PORT" &' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# 启动 nginx' >> /app/start.sh && \
    echo 'nginx -g "daemon off;" &' >> /app/start.sh && \
    echo 'wait' >> /app/start.sh && \
    chmod +x /app/start.sh

# 创建必要的目录和设置权限
RUN mkdir -p /app/server/uploads /tmp /var/cache/nginx /var/log/nginx && \
    chown -R appuser:appgroup /app/server /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    chmod -R 755 /app/server/uploads && \
    touch /run/nginx.pid && \
    chown appuser:appgroup /run/nginx.pid

# 切换到非 root 用户
USER appuser

# 环境变量（移除敏感的 JWT_SECRET）
ENV NODE_ENV=production \
    PORT=3400 \
    PUBLIC_BASE_URL=http://localhost

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3400/api/auth/me || exit 1

# 暴露端口
EXPOSE 80 3400

# OCI labels
LABEL org.opencontainers.image.title="MSUT全栈认证系统" \
      org.opencontainers.image.description="基于Python + Vue.js的全栈认证与资源管理系统" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/your-org/msut-auth-system" \
      org.opencontainers.image.vendor="MSUT" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/app/start.sh"]
