"""
从环境变量自动完成 OOBE 安装（Docker entrypoint 用）。

当以下环境变量存在且 `.oobe_complete` 锁文件不存在时执行：

  AUTO_OOBE=1 (或显式提供 ADMIN_USERNAME + ADMIN_PASSWORD)
  DATABASE_URL / REDIS_URL / REDIS_ENABLED
  SITE_NAME / SITE_DESCRIPTION / SITE_URL / SITE_KEYWORDS / SITE_AUTHOR / SITE_EMAIL
  ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_EMAIL / ADMIN_NICKNAME

示例：
  AUTO_OOBE=1 \
  DATABASE_URL=postgresql+asyncpg://rosetta:xx@postgres:5432/rosetta \
  REDIS_ENABLED=true REDIS_URL=redis://:xx@redis:6379/0 \
  SITE_URL=https://example.com ADMIN_USERNAME=admin ADMIN_PASSWORD=Strong1234 \
  python -m backend.scripts.auto_oobe
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger("rosetta.auto_oobe")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

ROOT = Path(__file__).resolve().parent.parent.parent
OOBE_LOCK = ROOT / "backend" / ".oobe_complete"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_bool(name: str, default: bool) -> bool:
    v = _env(name, "").lower()
    if not v:
        return default
    return v in {"1", "true", "yes", "on"}


def _parse_database_url(url: str) -> dict:
    """从 DATABASE_URL 反推出 db_type/host/port/user/password/db_name/db_path。"""
    import urllib.parse as urlparse

    if url.startswith("sqlite"):
        # sqlite+aiosqlite:///./rosetta.db → db_path=./rosetta.db
        _, rest = url.split("://", 1)
        # 去掉开头的 /，直到路径部分
        path = rest
        if path.startswith("/"):
            # sqlite+aiosqlite:////abs/path → abs；sqlite+aiosqlite:///./a → ./a
            if path.startswith("///"):
                path = path[3:]
            else:
                path = path[1:]
        return {
            "db_type": "sqlite",
            "db_host": "",
            "db_port": 0,
            "db_user": "",
            "db_password": "",
            "db_name": "",
            "db_path": path or "./rosetta.db",
        }

    parsed = urlparse.urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or 5432
    user = parsed.username or ""
    password = parsed.password or ""
    db_name = parsed.path.lstrip("/") or "rosetta"
    return {
        "db_type": "postgresql",
        "db_host": host,
        "db_port": int(port),
        "db_user": user,
        "db_password": password,
        "db_name": db_name,
        "db_path": "",
    }


def _parse_redis_url(url: str) -> tuple[str, int, str]:
    import urllib.parse as urlparse

    if not url:
        return "localhost", 6379, ""
    parsed = urlparse.urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    password = parsed.password or ""
    return host, int(port), password


async def _main() -> int:
    if OOBE_LOCK.exists():
        logger.info(f"检测到 OOBE 锁文件 {OOBE_LOCK}，跳过自动安装")
        return 0

    admin_username = _env("ADMIN_USERNAME", "admin")
    admin_password = _env("ADMIN_PASSWORD")
    if not admin_password:
        logger.error("缺少 ADMIN_PASSWORD 环境变量，无法自动完成 OOBE。跳过")
        return 1

    database_url = _env("DATABASE_URL", "sqlite+aiosqlite:///./rosetta.db")
    redis_enabled = _env_bool("REDIS_ENABLED", False)
    redis_url = _env("REDIS_URL", "redis://localhost:6379/0")
    redis_host, redis_port, redis_password = _parse_redis_url(redis_url)
    db = _parse_database_url(database_url)

    # 构造 CombinedInstallRequest
    from backend.api.oobe import CombinedInstallRequest  # noqa: PLC0415

    payload = {
        # Environment
        "environment": "production",
        # Database
        "database_type": db["db_type"],
        "db_host": db["db_host"],
        "db_port": db["db_port"],
        "db_name": db["db_name"],
        "db_user": db["db_user"],
        "db_password": db["db_password"],
        "db_path": db["db_path"],
        "redis_host": redis_host,
        "redis_port": redis_port,
        "redis_password": redis_password,
        "redis_enabled": bool(redis_enabled),
        # Site
        "site_name": _env("SITE_NAME", "Rosetta Blog"),
        "site_title": _env("SITE_TITLE", _env("SITE_NAME", "Rosetta Blog")),
        "site_description": _env("SITE_DESCRIPTION", "让文字有处安放,让思想自由流淌"),
        "site_keywords": _env("SITE_KEYWORDS", "blog, rosetta, fastapi, astro"),
        "site_author": _env("SITE_AUTHOR", "Administrator"),
        "site_email": _env("SITE_EMAIL", "admin@example.com"),
        "site_url": _env("SITE_URL", "http://localhost"),
        # Admin
        "admin_username": admin_username,
        "admin_email": _env("ADMIN_EMAIL", "admin@example.com"),
        "admin_password": admin_password,
        "admin_nickname": _env("ADMIN_NICKNAME", admin_username),
        # Features (默认较保守)
        "enable_comments": _env_bool("ENABLE_COMMENTS", True),
        "enable_registration": _env_bool("ENABLE_REGISTRATION", True),
        "enable_rss": _env_bool("ENABLE_RSS_FEED", True),
        "enable_bing_wallpaper": False,
        "enable_pagefind_search": False,
        "enable_encrypted_posts": False,
        "enable_music_player": False,
    }
    req = CombinedInstallRequest(**payload)

    from backend.api.oobe import _run_combined_install  # noqa: PLC0415

    logger.info("开始执行 OOBE 一键安装（环境变量驱动）...")
    try:
        ok = await _run_combined_install(req)
        if ok:
            logger.info("✅ OOBE 自动完成")
            return 0
        logger.error("OOBE 安装返回 False")
        return 2
    except Exception as exc:  # pragma: no cover
        logger.exception(f"OOBE 自动安装失败: {exc}")
        return 3


if __name__ == "__main__":
    code = asyncio.run(_main())
    raise SystemExit(code)
