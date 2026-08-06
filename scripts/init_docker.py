#!/usr/bin/env python3
"""
Docker 环境初始化脚本

在 Docker 容器启动时自动执行：
1. 等待数据库连接就绪
2. 执行数据库迁移
3. 生成 rosetta.json 配置文件
4. 生成 .env 文件
5. 创建默认管理员账号
6. 标记 OOBE 完成

环境变量配置：
- ADMIN_USERNAME: 管理员用户名（默认 admin）
- ADMIN_EMAIL: 管理员邮箱（默认 admin@example.com）
- ADMIN_PASSWORD: 管理员密码（默认 Admin123456）
- ADMIN_NICKNAME: 管理员昵称（可选）
- SITE_NAME: 站点名称（默认 Rosetta Blog）
- SITE_URL: 站点 URL（默认 http://localhost:4321）
- SKIP_INIT: 跳过初始化（已初始化后）
"""

import asyncio
import json
import os
import secrets
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "rosetta.json"
ENV_FILE = BASE_DIR / ".env"
OOBE_LOCK_FILE = BASE_DIR / ".oobe_complete"

sys.path.insert(0, str(BASE_DIR))


def generate_secret_key() -> str:
    return secrets.token_urlsafe(32)


def get_env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").lower()
    return val in ("true", "1", "yes", "on") or default


async def wait_for_database(max_retries: int = 30, delay: int = 2) -> bool:
    from backend.core.config import settings
    from backend.core.database import create_engine

    db_url = settings.database_url
    print(f"[init] 等待数据库就绪: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    for i in range(max_retries):
        try:
            engine = create_engine(db_url)
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            print(f"[init] 数据库连接成功 (尝试 {i + 1} 次)")
            return True
        except Exception as e:
            print(f"[init] 数据库连接失败 ({i + 1}/{max_retries}): {e}")
            time.sleep(delay)

    print("[init] 数据库连接超时")
    return False


async def run_migrations() -> bool:
    print("[init] 执行数据库迁移...")
    try:
        import asyncio
        from alembic import command
        from backend.migrations.config import get_alembic_config

        config = get_alembic_config()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: command.upgrade(config, "head"))
        print("[init] 数据库迁移完成")
        return True
    except ImportError:
        print("[init] 未找到迁移工具，跳过迁移")
        return True
    except Exception as e:
        print(f"[init] 数据库迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def create_admin() -> bool:
    username = os.environ.get("ADMIN_USERNAME", "admin")
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("ADMIN_PASSWORD", "Admin123456")
    nickname = os.environ.get("ADMIN_NICKNAME", "Administrator")

    print(f"[init] 检查管理员账号: {username}")

    try:
        from sqlalchemy import select
        from backend.core.auth import get_password_hash
        from backend.core.database import async_session_maker, init_db
        from backend.models.user import User, UserPreference

        await init_db()

        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            if result.scalar_one_or_none():
                print(f"[init] 管理员账号已存在，跳过创建")
                return True

            user = User(
                username=username,
                email=email,
                password_hash=get_password_hash(password),
                nickname=nickname,
                is_active=True,
                is_staff=True,
                is_superuser=True,
            )
            session.add(user)
            await session.flush()

            preference = UserPreference(user_id=user.id)
            session.add(preference)

            await session.commit()
            print(f"[init] 管理员账号创建成功: {username}")
            return True
    except Exception as e:
        print(f"[init] 管理员账号创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_config() -> dict:
    site_name = os.environ.get("SITE_NAME", "Rosetta Blog")
    site_url = os.environ.get("SITE_URL", "http://localhost:4321")
    site_description = os.environ.get("SITE_DESCRIPTION", "让文字有处安放，让思想自由流淌")
    site_keywords = os.environ.get("SITE_KEYWORDS", "blog, rosetta, fastapi, astro")
    site_author = os.environ.get("SITE_AUTHOR", "Administrator")
    site_email = os.environ.get("SITE_EMAIL", "admin@example.com")

    config = {
        "environment": "production",
        "site_name": site_name,
        "site_description": site_description,
        "site_keywords": site_keywords,
        "site_author": site_author,
        "site_email": site_email,
        "site_url": site_url,
        "github_url": os.environ.get("GITHUB_URL", ""),
        "x_url": os.environ.get("X_URL", ""),
        "bilibili_url": os.environ.get("BILIBILI_URL", ""),
        "enable_comments": get_env_bool("ENABLE_COMMENTS", True),
        "enable_registration": get_env_bool("ENABLE_REGISTRATION", True),
        "enable_rss": get_env_bool("ENABLE_RSS", True),
        "default_cover_image": "",
        "admin_username": os.environ.get("ADMIN_USERNAME", "admin"),
        "admin_email": os.environ.get("ADMIN_EMAIL", "admin@example.com"),
        "admin_nickname": os.environ.get("ADMIN_NICKNAME", "Administrator"),
        "secret_key": generate_secret_key(),
        "created_at": datetime.now().isoformat(),
    }
    return config


def save_config(config: dict) -> bool:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[init] 配置文件已生成: {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"[init] 配置文件生成失败: {e}")
        return False


def generate_env_file(config: dict) -> bool:
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://rosetta:rosetta_secret@postgres:5432/rosetta")
    redis_url = os.environ.get("REDIS_URL", "redis://:redis_secret@redis:6379/0")
    redis_enabled = get_env_bool("REDIS_ENABLED", True)

    env_content = f"""# Rosetta Docker 环境配置
# 自动生成于 {config["created_at"]}

# 应用配置
APP_NAME={config["site_name"]}
APP_ENV=production
DEBUG=false

# 数据库配置
DATABASE_URL={db_url}
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis 配置
REDIS_URL={redis_url}
REDIS_ENABLED={'true' if redis_enabled else 'false'}

# JWT 配置
SECRET_KEY={config["secret_key"]}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS 配置
CORS_ORIGINS=["{config["site_url"]}"]

# 站点配置
SITE_NAME={config["site_name"]}
SITE_DESCRIPTION={config["site_description"]}
SITE_KEYWORDS={config["site_keywords"]}
SITE_AUTHOR={config["site_author"]}
SITE_EMAIL={config["site_email"]}
SITE_URL={config["site_url"]}

# 功能开关
ENABLE_COMMENTS={str(config["enable_comments"]).lower()}
ENABLE_REGISTRATION={str(config["enable_registration"]).lower()}
ENABLE_RSS_FEED={str(config["enable_rss"]).lower()}

# 日志配置
LOG_LEVEL=INFO

# 文件上传
MAX_UPLOAD_SIZE=10485760
"""

    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(f"[init] 环境变量文件已生成: {ENV_FILE}")
        return True
    except Exception as e:
        print(f"[init] 环境变量文件生成失败: {e}")
        return False


def mark_oobe_complete() -> bool:
    try:
        with open(OOBE_LOCK_FILE, "w") as f:
            f.write(datetime.now().isoformat())
        print(f"[init] OOBE 标记为已完成")
        return True
    except Exception as e:
        print(f"[init] OOBE 标记失败: {e}")
        return False


async def main():
    print("=" * 60)
    print("  Rosetta Docker 环境初始化")
    print("=" * 60)

    if OOBE_LOCK_FILE.exists() and get_env_bool("SKIP_INIT", False):
        print("[init] 检测到已初始化，跳过...")
        return 0

    if not await wait_for_database():
        print("[init] 数据库连接失败，退出")
        return 1

    if not await run_migrations():
        print("[init] 数据库迁移失败")
        return 1

    config = generate_config()

    if not save_config(config):
        return 1

    if not generate_env_file(config):
        return 1

    if not await create_admin():
        return 1

    if not mark_oobe_complete():
        return 1

    print("=" * 60)
    print("  初始化完成！")
    print(f"  管理员账号: {os.environ.get('ADMIN_USERNAME', 'admin')}")
    print(f"  管理员密码: {os.environ.get('ADMIN_PASSWORD', 'Admin123456')}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
