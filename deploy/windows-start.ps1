# Windows PowerShell 一键部署脚本
# --------------------------------------------------------------
# 功能：
#   1. 检查 Python / Node / pnpm / uv / PostgreSQL / Redis 等依赖
#   2. 自动创建虚拟环境、安装 Python & Node 依赖
#   3. 生成 .env（若不存在） 、执行 DB 迁移
#   4. 若 ADMIN_PASSWORD 已提供则自动完成 OOBE
#   5. 构建前端 (Astro)，启动后端 (uvicorn) + 前端 (astro dev / preview)
#
# 使用：
#   powershell -ExecutionPolicy Bypass -File .\deploy\windows-start.ps1
#   或右键 - "Run with PowerShell"
# --------------------------------------------------------------
[CmdletBinding()]
param(
    [switch]$SkipEnvCopy,
    [switch]$NoFrontendBuild,
    [switch]$OnlyCheck
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

function Write-Banner([string]$t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Write-Ok([string]$t) { Write-Host "  ✅ $t" -ForegroundColor Green }
function Write-Warn([string]$t) { Write-Host "  ⚠️  $t" -ForegroundColor Yellow }
function Write-Fail([string]$t) { Write-Host "  ❌ $t" -ForegroundColor Red }
function Test-Cmd([string]$cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

Write-Banner "Rosetta 原生部署 · Windows 环境自检"

$hasPy = Test-Cmd py
$hasPython = Test-Cmd python
$hasUv = Test-Cmd uv
$hasNode = Test-Cmd node
$hasPnpm = Test-Cmd pnpm
$hasPsql = Test-Cmd psql
$hasRedisCli = Test-Cmd redis-cli

@(
    @("Python (py 启动器)", $hasPy),
    @("Python", $hasPython),
    @("uv", $hasUv),
    @("Node.js 22+", $hasNode),
    @("pnpm 10+", $hasPnpm),
    @("PostgreSQL psql", $hasPsql),
    @("Redis redis-cli", $hasRedisCli)
) | ForEach-Object {
    if ($_[1]) { Write-Ok $_[0] } else { Write-Warn ("$_[0] 未找到") }
}

if ($OnlyCheck) { Write-Host "仅自检完毕"; exit 0 }

# 关键依赖直接退出
if (-not ($hasPy -or $hasPython)) { Write-Fail "Python 不可用"; exit 2 }
if (-not $hasNode) { Write-Fail "Node.js 不可用"; exit 2 }
if (-not $hasPnpm) { Write-Warn "未找到 pnpm, 将通过 corepack enable 启用"; corepack enable ; corepack prepare pnpm@latest --activate }

Write-Banner "准备 .env 文件"
if (-not (Test-Path .env)) {
    if ($SkipEnvCopy) { Write-Warn "跳过 .env 复制" }
    else {
        if (Test-Path .env.example) {
            Copy-Item .env.example .env
            Write-Ok "已从 .env.example 复制 .env, 请按需修改 SECRET_KEY / ADMIN_PASSWORD / 数据库连接串等"
        } else {
            Write-Warn ".env.example 不存在, 请手工创建 .env"
        }
    }
} else {
    Write-Ok ".env 已存在"
}

Write-Banner "后端虚拟环境与依赖"
if (-not (Test-Path ".venv")) {
    if ($hasUv) {
        uv sync --no-dev
        Write-Ok "uv sync 完成"
    } else {
        if ($hasPy) { py -3 -m venv .venv } else { python -m venv .venv }
        .\.venv\Scripts\python.exe -m pip install -U pip
        .\.venv\Scripts\python.exe -m pip install -e .
    }
} else {
    Write-Ok ".venv 已存在, 跳过创建"
}

# Activate (for the next commands)
$venvPy = Join-Path $ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { $venvPy = "python" }

Write-Banner "执行 Alembic 迁移"
& $venvPy -m backend.migrations upgrade 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Warn "迁移未成功 (首次使用 SQLite + 未指定 DB 时属正常)" }

# 自动 OOBE
$adminPwd = if ($env:ADMIN_PASSWORD) { $env:ADMIN_PASSWORD } else { (Select-String -Path .env -Pattern '^ADMIN_PASSWORD=(.*)' -ErrorAction SilentlyContinue).Matches.Groups[1].Value }
if ($adminPwd -and -not (Test-Path "backend\.oobe_complete")) {
    Write-Banner "自动完成 OOBE 安装 (存在 ADMIN_PASSWORD 且 OOBE 未完成)"
    & $venvPy -m backend.scripts.auto_oobe 2>&1 | Out-Host
}

Write-Banner "前端构建 (Nuxt 4, frontend-nuxt)"
if (-not $NoFrontendBuild) {
    $frontDir = Join-Path $ROOT "frontend-nuxt"
    if (-not (Test-Path $frontDir)) {
        # legacy fallback: 原 Astro frontend 目录
        $frontDir = Join-Path $ROOT "frontend"
    }
    Push-Location $frontDir
    try {
        if (-not (Test-Path "node_modules")) {
            if (Test-Path "pnpm-lock.yaml") { pnpm install --frozen-lockfile }
            else { pnpm install }
        }
        # Nuxt 预生成类型（postinstall 已在 install 阶段做 nuxt prepare；如缺失补跑一次）
        if (Test-Path "nuxt.config.ts" -and -not (Test-Path ".nuxt")) { pnpm run postinstall 2>&1 | Out-Host }
        pnpm run build 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "前端 pnpm build 失败" }
        Write-Ok "前端构建完成 (目录: $(Split-Path $frontDir -Leaf))"
    } finally { Pop-Location }
}

Write-Banner "提示"
Write-Host @"
部署准备已完成！运行时服务请选择以下方式之一：

  * 开发模式：
    - 后端(新 terminal):   $venvPy -m uvicorn backend.main:app --reload --port 8000
    - 前端(新 terminal):   cd frontend-nuxt ; pnpm dev
    - 浏览器:              http://localhost:3000

  * 生产模式（IIS / 自托管）：
    - 后端:               $venvPy -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
    - 前端:               cd frontend-nuxt ; pnpm preview --host --port 3000
    - 推荐:               使用 Nginx 反代 8000/api + 3000 静态/页面

  * 旧版 Astro 已保留为 legacy：目录 frontend/ (legacy-astro)

数据库迁移 (SQLite → PostgreSQL):
    $venvPy -m backend.scripts.migrate_database --from sqlite+aiosqlite:///./rosetta.db --to postgresql+asyncpg://user:pass@localhost:5432/rosetta
"@ -ForegroundColor Cyan
