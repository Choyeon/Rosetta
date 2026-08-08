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

# 首次启动(未完成 OOBE 且提供了管理员账号环境变量) → 自动完成安装向导
if [ ! -f "$APP_DIR/backend/.oobe_complete" ]; then
    if [ -n "${ADMIN_PASSWORD:-}" ] || [ "${AUTO_OOBE:-0}" = "1" ]; then
        echo "[entrypoint] 检测到未完成 OOBE 且存在环境变量配置,尝试自动完成 OOBE 安装..."
        python -m backend.scripts.auto_oobe || {
            echo "[entrypoint] OOBE 自动安装失败, 仍继续启动服务 (请手动通过 /oobe 向导继续)"
        }
    else
        echo "[entrypoint] OOBE 未完成, 启动后请打开浏览器访问 /oobe 完成向导"
    fi
fi

echo "[entrypoint] 启动后端服务..."
echo "[entrypoint] 监听地址: 0.0.0.0:8000"
echo "[entrypoint] 工作进程数: ${WORKERS:-4}"

exec python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WORKERS:-4}" \
    --log-level "${LOG_LEVEL:-info}"
