#!/bin/bash
set -e

echo "=========================================="
echo "  Rosetta Backend - Docker Entrypoint"
echo "=========================================="

APP_DIR="/app"
cd "$APP_DIR"

# 数据库迁移(每次启动都执行,确保 schema 一致)
echo "[entrypoint] 执行数据库迁移..."
python -m backend.migrations upgrade || {
    echo "[entrypoint] 数据库迁移失败,但继续启动服务"
}

echo "[entrypoint] 启动后端服务..."
echo "[entrypoint] 监听地址: 0.0.0.0:8000"
echo "[entrypoint] 工作进程数: ${WORKERS:-4}"

exec python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WORKERS:-4}" \
    --log-level "${LOG_LEVEL:-info}"
