#!/usr/bin/env bash
# ============================================================
# Rosetta · Linux 原生一键部署脚本
# ============================================================
# 功能：
#   1. 安装系统依赖（PostgreSQL 16, Redis 7, Python 3.12, Node 22, nginx, uv, pnpm）
#      * Debian/Ubuntu LTS 专用 (apt)，其他发行版请手动前置
#   2. 创建专用用户 /opt/rosetta（可选，默认当前用户就地部署）
#   3. uv sync + pnpm build
#   4. 执行 alembic upgrade head + 自动 OOBE（若 ADMIN_PASSWORD 提供）
#   5. 写入 systemd 单元 rosetta-backend.service（需 sudo）并启用
#
# 使用：
#   sudo bash deploy/linux-install.sh
#   或最小权限：
#     bash deploy/linux-install.sh --no-system-pkgs --no-systemd
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COLOR_OK=$'\033[32m'
COLOR_WARN=$'\033[33m'
COLOR_FAIL=$'\033[31m'
COLOR_INFO=$'\033[36m'
RESET=$'\033[0m'
ok()   { echo -e "${COLOR_OK}  ✅ ${1}${RESET}"; }
warn() { echo -e "${COLOR_WARN}  ⚠️  ${1}${RESET}"; }
fail() { echo -e "${COLOR_FAIL}  ❌ ${1}${RESET}" >&2; }
info() { echo -e "${COLOR_INFO}==> ${1}${RESET}"; }

SKIP_SYSTEM_PKGS=0
SKIP_SYSTEMD=0
INSTALL_DIR="$ROOT"
USER_NAME="$(whoami)"
# shellcheck disable=SC2016
ENV_FILE_MISSING=0

for arg in "$@"; do
    case "$arg" in
        --no-system-pkgs) SKIP_SYSTEM_PKGS=1 ;;
        --no-systemd)     SKIP_SYSTEMD=1 ;;
        --install-dir=*)  INSTALL_DIR="${arg#--install-dir=}" ;;
        --user=*)         USER_NAME="${arg#--user=}" ;;
        -h|--help)
            cat <<'EOF'
Usage: sudo bash deploy/linux-install.sh [OPTIONS]

  --no-system-pkgs      跳过 apt install（你自行保证依赖）
  --no-systemd          跳过写入 systemd 单元
  --install-dir=/PATH   项目安装目录 (默认：repo 根)
  --user=USER           systemd 服务运行用户 (默认：当前用户)
EOF
            exit 0 ;;
    esac
done

need_cmd() { command -v "$1" >/dev/null 2>&1; }

info "Rosetta 原生部署 (Linux) · 环境检测"
for c in python3 node; do
    if need_cmd "$c"; then ok "$c ($($c --version 2>&1 | head -1))"
    else warn "$c 未找到"
    fi
done

# ---------- 系统依赖（仅 Debian/Ubuntu） ----------
if [[ $SKIP_SYSTEM_PKGS -eq 0 ]]; then
    info "安装系统依赖 (Debian/Ubuntu LTS) via apt"
    if [[ $EUID -ne 0 ]]; then
        warn "非 root 用户, 跳过 apt 安装, 请手动安装: postgresql redis-server python3 nodejs nginx curl"
    else
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq >/dev/null
        apt-get install -y -qq --no-install-recommends \
            ca-certificates curl gnupg lsb-release openssl \
            python3 python3-venv python3-pip \
            postgresql-16 postgresql-client-16 \
            redis-server \
            nginx >/dev/null
        ok "apt 安装完成"
        # Node 22 via NodeSource（若系统自带 <22）
        if ! need_cmd node || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 22 ]]; then
            info "安装 Node 22 (nodesource)"
            (
                curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource-setup.sh
                bash /tmp/nodesource-setup.sh
                apt-get install -y -qq --no-install-recommends nodejs >/dev/null
            ) || warn "NodeSource 安装失败, 请手动装 Node 22"
        fi
        # enable redis / postgres
        systemctl enable --now postgresql redis-server 2>/dev/null || true
    fi
fi

# corepack 启用 pnpm
if ! need_cmd pnpm; then
    info "启用 corepack pnpm"
    if [[ $EUID -eq 0 ]]; then corepack enable && corepack prepare pnpm@latest --activate
    else
        (command -v sudo >/dev/null && sudo corepack enable && sudo corepack prepare pnpm@latest --activate) \
            || warn "无法启用 corepack，请手动 pnpm 全局安装"
    fi
fi

# uv
if ! need_cmd uv; then
    info "安装 uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # shellcheck disable=SC1091
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

# ---------- .env ----------
info "准备 .env 文件"
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        # 替换一些生产友好的默认值：
        sed -i.bak \
            -e 's|^DATABASE_URL=sqlite.*|DATABASE_URL=postgresql+asyncpg://rosetta:rosetta_secret@127.0.0.1:5432/rosetta|' \
            -e 's|^REDIS_ENABLED=false|REDIS_ENABLED=true|' \
            -e 's|^DEBUG=true|DEBUG=false|' \
            -e 's|^APP_ENV=development|APP_ENV=production|' \
            -e "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo change-me-change-me-change-me)|" \
            .env && rm -f .env.bak
        ok ".env 已生成 (PostgreSQL/Redis 默认配置, 请按需修改)"
    else
        ENV_FILE_MISSING=1
        warn ".env.example 不存在, 请手工创建 .env"
    fi
else
    ok ".env 已存在"
fi

# ---------- 后端依赖 + 迁移 ----------
info "同步 Python 依赖"
if [[ -d ".venv" ]]; then ok ".venv 已存在"
else
    uv sync --frozen --no-dev --no-install-project
    uv sync --frozen --no-dev
    ok "uv sync 完成"
fi
VENV_PY="$ROOT/.venv/bin/python"
[[ -x "$VENV_PY" ]] || VENV_PY="python3"

info "执行 Alembic 迁移"
$VENV_PY -m backend.migrations upgrade || warn "Alembic 迁移失败, 请检查 DB 连接串"

# ---------- 自动 OOBE ----------
if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
    # shellcheck disable=SC1090
    [[ -f .env ]] && set -a && source .env && set +a || true
fi
if [[ -n "${ADMIN_PASSWORD:-}" ]] && [[ ! -f "$ROOT/backend/.oobe_complete" ]]; then
    info "检测到 ADMIN_PASSWORD，自动完成 OOBE"
    $VENV_PY -m backend.scripts.auto_oobe || warn "OOBE 自动安装失败"
fi

# ---------- 前端构建 ----------
info "构建前端 (Astro)"
cd "$ROOT/frontend"
[[ -d node_modules ]] || pnpm install --frozen-lockfile
pnpm run build || { fail "前端构建失败"; exit 4; }
ok "前端构建完成"
cd "$ROOT"

# ---------- systemd ----------
if [[ $SKIP_SYSTEMD -eq 0 ]]; then
    info "写入并启用 systemd 单元 rosetta-backend.service"
    if [[ $EUID -ne 0 ]]; then
        warn "非 root, 跳过 systemd 写入; 你可以手动复制 deploy/rosetta-backend.service 到 /etc/systemd/system/"
    else
        sed -e "s|__INSTALL_DIR__|$ROOT|g" \
            -e "s|__USER__|$USER_NAME|g" \
            -e "s|__VENV_PY__|$VENV_PY|g" \
            deploy/rosetta-backend.service > /etc/systemd/system/rosetta-backend.service
        systemctl daemon-reload
        systemctl enable --now rosetta-backend.service || warn "rosetta-backend 启用失败 (可能端口被占用)"
        ok "rosetta-backend systemd 单元已注册"
    fi
fi

# ---------- 提示 ----------
info "部署完成！"
cat <<EOF
下一步建议：

  1. 编辑 .env 确认 SECRET_KEY / ADMIN_PASSWORD / DATABASE_URL / SITE_URL。
  2. 若使用 systemd：
        systemctl status rosetta-backend
        journalctl -u rosetta-backend -f
  3. 生产建议配置 Nginx：
        将 deploy/nginx-site.conf 复制到 /etc/nginx/sites-available/rosetta.conf
        ln -s ../sites-available/rosetta.conf /etc/nginx/sites-enabled/rosetta.conf
        nginx -t && systemctl reload nginx
  4. 跨库数据迁移 (SQLite -> PG)：
        $VENV_PY -m backend.scripts.migrate_database \
            --from sqlite+aiosqlite:///./rosetta.db \
            --to   postgresql+asyncpg://user:pass@localhost:5432/rosetta
  5. 运行环境健康检查：
        bash deploy/health-check.sh

EOF
