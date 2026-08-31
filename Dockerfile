# ============================================================
# Rosetta 博客系统 Dockerfile
# ============================================================
# 多阶段构建:后端(uv + FastAPI) + 前端(Astro 静态站点 + nginx)
# 用法:
#   docker build -t rosetta-backend --target backend .
#   docker build -t rosetta-frontend --target frontend .
#   docker compose up -d
# ============================================================

# ============================================================
# 阶段 1: 后端依赖构建(uv 安装到虚拟环境)
# ============================================================
FROM python:3.12-slim AS backend-builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 优先复制锁文件与项目元数据以利用 Docker 层缓存
COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/

# 同步生产依赖到 .venv(冻结锁文件,不更新)
RUN uv sync --frozen --no-dev --no-install-project

# ============================================================
# 阶段 2: 后端运行时
# ============================================================
FROM python:3.12-slim AS backend

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境(已含所有依赖)
COPY --from=backend-builder /build/.venv /app/.venv

# 复制后端源码
COPY backend/ ./backend/
COPY pyproject.toml uv.lock ./
COPY docker/backend-entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/media

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

# ============================================================
# 阶段 3: 前端构建(Nuxt 4 / Nitro 通用服务器)
# ============================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /build

ENV PNPM_HOME="/pnpm" \
    PATH="$PNPM_HOME:$PATH" \
    NODE_ENV=production

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ .

# 生产代理目标（由 compose 注入 backend 服务名）
# 注意：nitro.devProxy 仅 dev 生效，生产 /api 由前端容器内的 nginx 反向代理到 backend
ARG NUXT_API_BASE_URL=http://localhost:8000
ENV NUXT_PUBLIC_API_BASE_URL=${NUXT_API_BASE_URL}

RUN pnpm run build

# ============================================================
# 阶段 4: 前端运行时(nginx 反代 Nitro 服务器 + 后端 API)
# ============================================================
FROM nginx:alpine AS frontend

# Nitro 服务器产物（含 public 静态资源与 server 运行时）
COPY --from=frontend-builder /build/.output /var/www/rosetta/.output
WORKDIR /var/www/rosetta

# 复制 nginx 配置
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# 安装健康检查工具
RUN apk add --no-cache curl wget 2>/dev/null || true

# 启动脚本：先起 Nitro 服务器（node .output/server/index.mjs，监听 3000），再起 nginx
RUN printf '#!/bin/sh\nset -e\ncd /var/www/rosetta\nnode .output/server/index.mjs &\nnginx -g "daemon off;"\n' > /start.sh \
    && chmod +x /start.sh

# /health 由 nginx 配置直接返回，避免回落到 404 导致 healthy 判定失败
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1/health >/dev/null || wget -q -O /dev/null --spider http://127.0.0.1/health || exit 1

EXPOSE 80

CMD ["/start.sh"]
