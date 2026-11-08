#!/bin/bash
set -e

echo "=========================================="
echo "  Rosetta Backend - Docker Entrypoint"
echo "=========================================="

APP_DIR="/app"
cd "$APP_DIR"

# 数据库迁移(每次启动都执行,确保 schema 一致)
echo "[entrypoint] 执行数据库迁移..."
if ! python -m backend.migrations upgrade; then
    echo "[entrypoint] 数据库迁移失败，拒绝启动服务（schema 未升级会导致运行时 500）" >&2
    exit 1
fi

# 首次启动(未完成 OOBE 且提供了管理员账号环境变量) → 自动完成安装向导
if [ ! -f "$APP_DIR/backend/.oobe_complete" ]; then
    # AUTO_OOBE 必须是显式开关：仅凭 ADMIN_PASSWORD 存在就自动建号，
    # 会让「关掉自动 OOBE」的配置形同虚设。首次部署需显式设 AUTO_OOBE=1。
    if [ "${AUTO_OOBE:-0}" = "1" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
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
