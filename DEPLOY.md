# Rosetta 部署指南

## 目录
- [环境要求](#环境要求)
- [Docker 部署(推荐)](#docker-部署推荐)
- [Vercel 部署](#vercel-部署)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

## 环境要求

### 开发环境
- Python 3.12+
- uv(Python 包管理器)
- Node.js 22+
- pnpm 10+
- SQLite(默认)或 PostgreSQL 16+

### 生产环境
- Python 3.12+
- uv(仅构建后端时需要)
- Node.js 22+(仅构建前端时需要)
- PostgreSQL 16+
- Redis 7+(推荐)
- Nginx(推荐,用于反向代理)

---

## Docker 部署(推荐)

Docker 部署是最简单的方式,一键启动 PostgreSQL、Redis、后端、前端四个服务。

### 1. 准备配置

```bash
# 克隆仓库
git clone https://github.com/Choyeon/Rosetta.git
cd Rosetta

# 复制环境配置
cp .env.example .env

# 编辑 .env,修改以下关键配置
# - SECRET_KEY: 使用 openssl rand -hex 32 生成
# - DB_PASSWORD: 设置强密码
# - REDIS_PASSWORD: 设置强密码
# - CORS_ORIGINS: 设置为你的域名,如 ["https://yourdomain.com"]
# - SITE_URL: 设置为你的域名
# - ADMIN_PASSWORD: 设置管理员密码
```

### 2. 构建并启动

```bash
# 构建并启动所有服务(后台运行)
docker compose up -d --build

# 查看启动状态
docker compose ps

# 查看日志
docker compose logs -f

# 单独查看某个服务日志
docker compose logs -f backend
docker compose logs -f frontend
```

### 3. 访问服务

启动完成后,默认端口映射:

| 服务 | 端口 | 地址 |
|---|---|---|
| 前端 | 80 | http://localhost |
| 后端 API | 8000 | http://localhost:8000 |
| API 文档 | 8000 | http://localhost:8000/docs (DEBUG=true 时) |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |

### 4. 常用运维命令

```bash
# 停止所有服务
docker compose down

# 重启某个服务
docker compose restart backend

# 重新构建并启动
docker compose up -d --build

# 查看数据库迁移状态
docker compose exec backend python -m backend.migrations status

# 执行数据库迁移
docker compose exec backend python -m backend.migrations upgrade

# 进入后端容器
docker compose exec backend bash

# 清理所有数据(谨慎!)
docker compose down -v
```

### 架构说明

- **frontend 容器**: 基于 `nginx:alpine`,服务 Astro 静态构建产物,通过 nginx 反向代理将 `/api/*` 和 `/media/*` 请求转发到 backend 容器,生产环境无需处理 CORS
- **backend 容器**: 基于 `python:3.12-slim`,运行 FastAPI + uvicorn,自动执行数据库迁移
- **postgres 容器**: PostgreSQL 16,数据持久化到 `rosetta-postgres-data` 卷
- **redis 容器**: Redis 7,数据持久化到 `rosetta-redis-data` 卷

---

## Vercel 部署

Vercel 适合部署前端(Astro 静态站点),后端需要单独部署到其他平台(如 Railway、Fly.io、Render 或自建 VPS)。

### 1. 部署后端

选择以下任一平台部署 FastAPI 后端:

- **Railway**: https://railway.app
- **Fly.io**: https://fly.io
- **Render**: https://render.com
- **自建 VPS**: 见下方[手动部署](#手动部署)

确保后端可访问,如 `https://api.yourdomain.com`。

### 2. 部署前端到 Vercel

#### 方式 A: 一键部署(推荐)

点击下方按钮一键部署:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FChoyeon%2FRosetta&project-name=rosetta-blog&repository-name=rosetta-blog)

#### 方式 B: 命令行部署

```bash
# 安装 Vercel CLI
npm install -g vercel

# 登录
vercel login

# 进入前端目录
cd frontend

# 部署到预览环境
vercel

# 部署到生产环境
vercel --prod
```

### 3. 配置环境变量

在 Vercel 项目设置中添加以下环境变量:

| 变量 | 说明 | 示例 |
|---|---|---|
| `ROSETTA_API_BASE` | 后端 API 基址 | `https://api.yourdomain.com/api` |
| `API_BASE_URL` | 构建时代理地址(可选) | `https://api.yourdomain.com` |

### 4. 配置自定义域名

在 Vercel 项目设置 → Domains 中添加你的域名,按提示配置 DNS。

---

## 手动部署

适用于自建 VPS 或物理服务器。

### 1. 准备环境

```bash
# Ubuntu/Debian 示例
sudo apt update
sudo apt install -y python3.12 python3.12-venv nodejs npm postgresql redis-server nginx git curl

# 安装 pnpm
npm install -g pnpm@10

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
git clone https://github.com/Choyeon/Rosetta.git
cd Rosetta
```

### 2. 配置 PostgreSQL

```bash
sudo -u postgres psql <<EOF
CREATE DATABASE rosetta;
CREATE USER rosetta WITH PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE rosetta TO rosetta;
\q
EOF
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

关键配置:

```env
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://rosetta:your_strong_password@localhost:5432/rosetta
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$(openssl rand -hex 32)
CORS_ORIGINS=["https://yourdomain.com"]
SITE_URL=https://yourdomain.com
```

### 4. 启动后端

```bash
# 使用 uv 同步依赖(读取 pyproject.toml + uv.lock,创建 .venv)
uv sync --frozen --no-dev

# 执行数据库迁移
uv run python -m backend.migrations upgrade

# 创建 systemd 服务
sudo tee /etc/systemd/system/rosetta-backend.service << EOF
[Unit]
Description=Rosetta Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/rosetta
Environment="PATH=/var/www/rosetta/.venv/bin:/usr/local/bin"
EnvironmentFile=/var/www/rosetta/.env
ExecStart=/var/www/rosetta/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable rosetta-backend
sudo systemctl start rosetta-backend
```

### 5. 构建并启动前端

```bash
cd frontend
pnpm install
pnpm build

# 构建产物在 dist/ 目录,可由 nginx 直接服务
sudo mkdir -p /var/www/rosetta/frontend/dist
sudo cp -r dist/* /var/www/rosetta/frontend/dist/
```

### 6. 配置 Nginx

```bash
sudo tee /etc/nginx/sites-available/rosetta << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL 证书(使用 Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # 安全头
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 前端静态文件
    root /var/www/rosetta/frontend/dist;
    index index.html;

    # Astro 静态资源长期缓存
    location /_astro/ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        client_max_body_size 20m;
    }

    # 媒体文件反向代理
    location /media/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        expires 7d;
    }

    # Astro SPA 回退
    location / {
        try_files $uri $uri/index.html $uri.html /404.html;
    }

    # gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/javascript application/json
               image/svg+xml font/woff font/woff2;
}
EOF

sudo ln -sf /etc/nginx/sites-available/rosetta /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 配置 SSL(使用 Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 配置说明

### 关键环境变量

| 变量 | 说明 | 必填 |
|---|---|---|
| `SECRET_KEY` | JWT 签名密钥,生产必须改 | ✅ |
| `DATABASE_URL` | 数据库连接字符串 | ✅ |
| `CORS_ORIGINS` | 允许的前端来源(JSON 数组) | ✅ |
| `SITE_URL` | 站点 URL | ✅ |
| `REDIS_URL` | Redis 连接(可选,内存缓存回退) | ❌ |
| `API_BASE_URL` | Vite dev 代理目标 | ❌ |
| `ROSETTA_API_BASE` | 前端 API 客户端基址 | ❌ |

### 端口约定

| 服务 | 开发环境 | 生产环境 |
|---|---|---|
| 前端 | 4321(Astro dev) | 80(nginx) |
| 后端 | 8000(uvicorn) | 8000(uvicorn) |
| PostgreSQL | 5432 | 5432 |
| Redis | 6379 | 6379 |

---

## 常见问题

### 1. 数据库迁移失败

```bash
# 查看当前迁移状态
python -m backend.migrations status

# 查看迁移历史
python -m backend.migrations history

# 强制重置(危险!会删除数据)
python -m backend.migrations reset --force
```

### 2. 前端无法访问后端 API

- 开发环境:检查 `API_BASE_URL` 是否指向正确的后端地址
- 生产环境(Docker):nginx 自动代理,无需额外配置
- 生产环境(分离部署):检查 `ROSETTA_API_BASE` 环境变量和 CORS 配置

### 3. OOBE 引导失败

首次启动时,系统会在站点根目录运行 OOBE 向导。如果失败:

```bash
# 删除 OOBE 标记文件,重新触发
rm .oobe_complete rosetta.json

# 重启后端
docker compose restart backend
# 或
sudo systemctl restart rosetta-backend
```

### 4. 媒体文件无法访问

- 检查 `media/` 目录权限(后端进程需要读写权限)
- Docker 部署:媒体文件存储在 `rosetta-backend-media` 卷中
- 手动部署:确保 nginx 反向代理 `/media/` 到后端

### 5. 更新版本

```bash
# Docker
git pull
docker compose up -d --build
docker compose exec backend python -m backend.migrations upgrade

# 手动
git pull
uv sync --frozen --no-dev
uv run python -m backend.migrations upgrade
sudo systemctl restart rosetta-backend

cd frontend
pnpm install
pnpm build
sudo cp -r dist/* /var/www/rosetta/frontend/dist/
```
