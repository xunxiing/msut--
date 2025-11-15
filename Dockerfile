# MSUT fullstack auth system - multi-stage build (Python backend only, no embedded Nginx)

# Build args
ARG NODE_VERSION=20.18.0
ARG ALPINE_VERSION=3.20

# Frontend build stage (build static assets for external Nginx or other static hosting)
FROM node:${NODE_VERSION}-alpine${ALPINE_VERSION} AS frontend-builder

WORKDIR /app/web

# Install frontend dependencies
COPY melon-tech-web/package*.json ./
COPY melon-tech-web/tsconfig*.json ./
RUN npm ci && npm cache clean --force

# Build frontend
COPY melon-tech-web/ ./
RUN npm run build

# Final runtime stage: Python backend (no Nginx inside the container)
FROM python:3.11-alpine${ALPINE_VERSION}

WORKDIR /app

# Runtime deps: curl for healthcheck, sqlite for CLI access, gosu for dropping privileges
RUN apk add --no-cache \
    curl \
    sqlite \
    gosu \
    && rm -rf /var/cache/apk/*

# Non-root user
RUN addgroup -g 10001 -S appgroup && \
    adduser -u 10001 -S appuser -G appgroup

# Copy built frontend (optional; can be served by external Nginx or another static server)
COPY --from=frontend-builder /app/web/dist /app/web/dist

# Copy backend code
COPY server /app/server

# Install Python deps (with build deps for native wheels), then clean up
RUN echo "=== apk update ===" && apk update \
    && echo "=== install build deps ===" && apk add --no-cache --virtual .build-deps build-base python3-dev libffi-dev musl-dev \
    && echo "=== upgrade pip ===" && python3 -m pip install --no-cache-dir --upgrade pip --break-system-packages \
    && echo "=== install Python deps ===" && pip3 install --no-cache-dir -r /app/server/requirements.txt --break-system-packages \
    && echo "=== cleanup build deps ===" && apk del .build-deps && rm -rf /var/cache/apk/* && echo "=== done ==="

# Ensure dirs exist and basic permissions are set
RUN mkdir -p /app/server/uploads /app/server/data && \
    chown -R appuser:appgroup /app /app/server /app/web && \
    chmod -R 755 /app/server/uploads

# Start script (runs as root, prepares DATA_DIR/DB, then gosu to appuser and starts uvicorn)
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo 'umask 000' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'DATA_DIR="${DATA_DIR:-/app/server/data}"' >> /app/start.sh && \
    echo 'DB_FILE="$DATA_DIR/data.sqlite"' >> /app/start.sh && \
    echo 'mkdir -p /app/server/uploads "$DATA_DIR"' >> /app/start.sh && \
    echo 'chown -R appuser:appgroup /app/server/uploads "$DATA_DIR"' >> /app/start.sh && \
    echo 'chmod -R u+rwX,g+rwX /app/server/uploads "$DATA_DIR"' >> /app/start.sh && \
    echo 'if [ -d "$DB_FILE" ]; then' >> /app/start.sh && \
    echo '  echo "[init] WARN: $DB_FILE is a directory; attempting to fix..."' >> /app/start.sh && \
    echo '  if rmdir "$DB_FILE" 2>/dev/null; then' >> /app/start.sh && \
    echo '    echo "[init] Removed empty directory at DB file path"' >> /app/start.sh && \
    echo '  else' >> /app/start.sh && \
    echo '    mv "$DB_FILE" "$DB_FILE.dirbak-$(date +%s)" 2>/dev/null || true' >> /app/start.sh && \
    echo '    echo "[init] Renamed directory to backup: $DB_FILE.dirbak-*"' >> /app/start.sh && \
    echo '  fi' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo 'touch "$DB_FILE" || true' >> /app/start.sh && \
    echo 'chown appuser:appgroup "$DB_FILE" || true' >> /app/start.sh && \
    echo 'chmod 0666 "$DB_FILE" || true' >> /app/start.sh && \
    echo 'echo "[init] DB_DIR=$DATA_DIR"' >> /app/start.sh && \
    echo 'echo "[init] DB_FILE=$DB_FILE"' >> /app/start.sh && \
    echo 'echo "[init] ls -ld $DATA_DIR:" && ls -ld "$DATA_DIR" || true' >> /app/start.sh && \
    echo 'echo "[init] ls -l $DATA_DIR:" && ls -l "$DATA_DIR" || true' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'PORT="${PORT:-3400}"' >> /app/start.sh && \
    echo 'cd /app' >> /app/start.sh && \
    echo 'echo "[init] Starting FastAPI on port $PORT"' >> /app/start.sh && \
    echo 'exec gosu appuser python3 -m uvicorn server.app:app --host 0.0.0.0 --port "$PORT" --log-level info' >> /app/start.sh && \
    chmod +x /app/start.sh

ENV NODE_ENV=production \
    PORT=3400 \
    PUBLIC_BASE_URL=http://localhost \
    PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD sh -c 'curl -f http://localhost:${PORT:-3400}/api/auth/me || exit 1'

VOLUME ["/app/server/uploads", "/app/server/data"]

EXPOSE 3400

LABEL org.opencontainers.image.title="MSUT fullstack auth system" \
      org.opencontainers.image.description="Python + Vue.js fullstack auth and resource management (backend-only container, no Nginx)" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/your-org/msut-auth-system" \
      org.opencontainers.image.vendor="MSUT" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/app/start.sh"]

