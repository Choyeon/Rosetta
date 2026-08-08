#!/usr/bin/env bash
# ============================================================
# Rosetta · 通用健康检查脚本 (Linux/macOS/WSL2/Git Bash)
# ============================================================
# 覆盖：
#   1. 进程：uvicorn/backend、Astro preview、postgres、redis
#   2. 端口：后端 8000、前端 4321、PG 5432、Redis 6379
#   3. HTTP 端点：/health 后端 / 前端
#   4. DB 连通性（使用 .env 里的 DATABASE_URL/REDIS_URL）
#   5. OOBE 状态
#
# Usage: bash deploy/health-check.sh
# ============================================================
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; CYAN=$'\033[36m'; RESET=$'\033[0m'
PASS=0; WARN=0; FAIL=0

pass() { echo -e " ${GREEN}[PASS]${RESET} $1"; PASS=$((PASS+1)); }
warn() { echo -e " ${YELLOW}[WARN]${RESET} $1"; WARN=$((WARN+1)); }
fail() { echo -e " ${RED}[FAIL]${RESET} $1"; FAIL=$((FAIL+1)); }
h1()   { echo; echo -e "${CYAN}== $1 ==${RESET}"; }
cmd()  { command -v "$1" >/dev/null 2>&1; }

# 加载 .env（若存在）
if [[ -f .env ]]; then
    set -a; # shellcheck disable=SC1091
    source .env 2>/dev/null || true
    set +a
fi
DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./rosetta.db}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:4321}"

# ---------- 工具 & 进程 ----------
h1 "1. 依赖命令 & 进程"
for c in python3 node pnpm uv psql redis-cli curl; do
    if cmd "$c"; then pass "binary $c"; else warn "binary $c 不在 PATH"; fi
done
for pat in 'uvicorn backend.main' 'pnpm (preview|astro)'; do
    if pgrep -f "$pat" >/dev/null 2>&1; then pass "进程匹配: $pat"
    else warn "无运行进程: $pat"; fi
done

# ---------- 端口 ----------
h1 "2. 端口监听"
check_port() {
    local port=$1 name=$2
    if cmd ss; then
        ss -ltn "( sport = :$port )" 2>/dev/null | awk 'NR>1 {found=1} END {exit !found}' 2>/dev/null
    else
        (echo >"/dev/tcp/127.0.0.1/$port") 2>/dev/null
    fi
    if [[ $? -eq 0 ]]; then pass "端口 $port ($name)"; else fail "端口 $port ($name) 未监听"; fi
}
check_port 8000 "backend"
check_port 4321 "frontend"
if grep -q "postgres" <<<"$DATABASE_URL"; then check_port 5432 "postgresql"; fi
if grep -q "redis" <<<"$REDIS_URL"; then check_port 6379 "redis"; fi

# ---------- HTTP ----------
h1 "3. HTTP 健康检查"
if cmd curl; then
    for name_url_pair in "backend:$BACKEND_URL/health" "frontend:$FRONTEND_URL/"; do
        NAME="${name_url_pair%%:*}"
        URL="${name_url_pair#*:}"
        CODE=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 "$URL" 2>/dev/null || echo "000")
        if [[ "$CODE" =~ ^(200|204|301|302)$ ]]; then pass "$NAME $URL -> HTTP $CODE"
        else fail "$NAME $URL -> HTTP $CODE"; fi
    done
else
    warn "curl 缺失, 跳过 HTTP 检查"
fi

# ---------- DB / Redis 连通 ----------
h1 "4. DB & Redis 连通性"
if [[ "$DATABASE_URL" == postgresql* ]]; then
    HOST="$(python3 - "$DATABASE_URL" <<'PY' 2>/dev/null || echo localhost)
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url)
print(p.hostname or "localhost")
PY
"
    PORT="$(python3 - "$DATABASE_URL" <<'PY' 2>/dev/null || echo 5432)
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url); print(p.port or 5432)
PY
"
    USER="$(python3 - "$DATABASE_URL" <<'PY' 2>/dev/null || echo "")
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url); print(p.username or "")
PY
"
    DB="$(python3 - "$DATABASE_URL" <<'PY' 2>/dev/null || echo "")
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url); print((p.path or "").lstrip("/") or "")
PY
"
    if PGPASSWORD="${PASSWORD:-$(python3 - "$DATABASE_URL" <<'PY' 2>/dev/null || echo "")
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url); print(p.password or "")
PY
}" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -c "SELECT 1;" >/dev/null 2>&1; then
        pass "PostgreSQL 连接 OK (${USER}@${HOST}:${PORT}/${DB})"
    else
        fail "PostgreSQL 连接失败 (${USER}@${HOST}:${PORT}/${DB})"
    fi
elif [[ "$DATABASE_URL" == sqlite* ]]; then
    PATH_PART="${DATABASE_URL#sqlite*:///}"
    PATH_PART="${PATH_PART#/}"
    if [[ -f "$PATH_PART" ]]; then
        pass "SQLite 文件存在: $PATH_PART ($(stat -c%s "$PATH_PART" 2>/dev/null || wc -c < "$PATH_PART") bytes)"
    else
        warn "SQLite 文件未找到: $PATH_PART (可能首次尚未生成)"
    fi
fi

# Redis
if [[ "$REDIS_URL" == redis* ]]; then
    RH="$(python3 - "$REDIS_URL" <<'PY' 2>/dev/null || echo localhost)
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url); print(p.hostname or "localhost")
PY
"
    RP="$(python3 - "$REDIS_URL" <<'PY' 2>/dev/null || echo 6379)
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url); print(p.port or 6379)
PY
"
    RPW="$(python3 - "$REDIS_URL" <<'PY' 2>/dev/null || echo "")
import sys, urllib.parse as u
url=sys.argv[1]; p=u.urlparse(url); print(p.password or "")
PY
"
    if [[ -n "$RPW" ]]; then ARGS=(-h "$RH" -p "$RP" -a "$RPW" PING)
    else ARGS=(-h "$RH" -p "$RP" PING)
    fi
    OUT="$(redis-cli "${ARGS[@]}" 2>/dev/null || echo ERR)"
    if [[ "$OUT" == PONG ]]; then pass "Redis PONG ($RH:$RP)"
    else fail "Redis 未响应: $RH:$RP ($OUT)"; fi
fi

# ---------- OOBE ----------
h1 "5. OOBE & 运行时状态"
if [[ -f "$ROOT/backend/.oobe_complete" ]]; then pass "OOBE 已完成"
else warn "OOBE 尚未完成, 请打开 /oobe 或设置 ADMIN_PASSWORD 后重新部署"; fi
if [[ -d "$ROOT/frontend/dist" ]]; then pass "前端构建产物 frontend/dist 存在"
else warn "前端尚未构建 (执行 pnpm build)"; fi

# ---------- Summary ----------
echo
TOTAL=$((PASS+WARN+FAIL))
echo -e "${CYAN}========= Health Summary =========${RESET}"
echo -e " Total : $TOTAL"
echo -e " ${GREEN}Pass  : $PASS${RESET}"
echo -e " ${YELLOW}Warn  : $WARN${RESET}"
echo -e " ${RED}Fail  : $FAIL${RESET}"
echo -e "${CYAN}==================================${RESET}"

if [[ $FAIL -eq 0 ]]; then exit 0; else exit 2; fi
