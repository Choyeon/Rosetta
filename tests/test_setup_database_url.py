"""安装期连接串（`rosetta.json` 与 `.env` 两份）的纯函数回归测试。

这两处历史上各踩过坑：Windows 盘符在 aiosqlite URL 里被当成 hostname、
OOBE 表单把 `db_name` 填成 ".db"/"" 时生成出无文件名路径、
以及 userinfo 用 `quote_plus` 编码密码（空格变成字面量 `+`，SQLAlchemy 解出来
的密码就是错的，PG 连接必然认证失败；`.env` 里的 Redis 密码更是完全没编码）。
分支很多却一条测试都没有——这里补齐。
"""

from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy.engine.url import make_url

import backend.core.paths as _paths
from backend.core.setup_config import ConfigService
from backend.core.setup_database import generate_database_url


def test_sqlite_absolute_path_keeps_directory(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    target = tmp_path / "elsewhere" / "site.db"
    url = generate_database_url({"db_type": "sqlite", "db_path": str(target)})
    assert url.startswith("sqlite+aiosqlite:///")
    # POSIX 风格：盘符后的冒号不能被解析成 hostname
    assert ":" not in url.removeprefix("sqlite+aiosqlite:///").split("/")[-1]
    assert url.endswith("site.db")
    assert "\\" not in url


def test_sqlite_relative_path_resolves_under_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    url = generate_database_url({"db_type": "sqlite", "db_path": "sub/rosetta"})
    assert url == f"sqlite+aiosqlite:///{(tmp_path / 'sub' / 'rosetta.db').as_posix()}"


def test_sqlite_missing_path_falls_back_to_rosetta_db(tmp_path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    for db_name in ("", ".", ".db", "   "):
        url = generate_database_url({"db_type": "sqlite", "db_path": "", "db_name": db_name})
        assert url.endswith("/rosetta.db"), f"db_name={db_name!r} 时应当回退到 rosetta.db"


def test_sqlite_db_name_without_suffix_gets_one(tmp_path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    url = generate_database_url({"db_type": "sqlite", "db_path": "", "db_name": "myblog"})
    assert url.endswith("/myblog.db")


def test_sqlite_db_name_with_uppercase_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    url = generate_database_url({"db_type": "sqlite", "db_path": "", "db_name": "myblog.DB"})
    assert url.endswith("/myblog.DB")


def test_postgresql_url_quotes_password(tmp_path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    url = generate_database_url(
        {
            "db_type": "postgresql",
            "db_user": "rosetta",
            "db_password": "p@ss w/ord#",
            "db_host": "db.internal",
            "db_port": 6543,
            "db_name": "rosetta",
        }
    )
    assert url == "postgresql+asyncpg://rosetta:p%40ss%20w%2Ford%23@db.internal:6543/rosetta"
    # 真正的判据：连接串要能被 SQLAlchemy 原样解回密码。
    # 用 quote_plus 时空格会被编码成 `+`，到这里就变成字面量加号（认证失败）。
    assert make_url(url).password == "p@ss w/ord#"


def test_postgresql_url_without_password():
    url = generate_database_url(
        {"db_type": "postgresql", "db_user": "ro", "db_password": "", "db_name": "blog"}
    )
    assert url == "postgresql+asyncpg://ro@localhost:5432/blog"


def test_unknown_db_type_returns_empty():
    assert generate_database_url({"db_type": "mysql"}) == ""


def test_missing_db_type_defaults_to_postgresql():
    assert generate_database_url({}) == "postgresql+asyncpg://@localhost:5432/rosetta"


# ---------------------------------------------------------------------------
# .env 侧（进程真正读取的那一份）：与上面同源但实现独立，所以单独钉
# ---------------------------------------------------------------------------

BASE_ENV_CONFIG = {
    "created_at": "2026-09-26T00:00:00",
    "environment": "development",
    "site_name": "Rosetta",
    "site_description": "d",
    "site_author": "a",
    "site_email": "e@example.com",
    "site_url": "http://localhost:3000",
    "secret_key": "x" * 48,
    "enable_comments": True,
    "enable_registration": False,
    "enable_rss": True,
}


def _env_value(env_content: str, key: str) -> str:
    for line in env_content.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    raise AssertionError(f"{key} 未出现在 .env 内容里:\n{env_content}")


def test_env_postgres_url_password_survives_parsing(tmp_path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    cfg = {
        **BASE_ENV_CONFIG,
        "db_type": "postgresql",
        "db_user": "rosetta",
        "db_password": "p@ss w/ord#",
        "db_host": "db.internal",
        "db_port": 6543,
        "db_name": "rosetta",
    }
    url = _env_value(ConfigService().generate_env_content(cfg), "DATABASE_URL")
    assert make_url(url).password == "p@ss w/ord#"
    assert make_url(url).host == "db.internal"


def test_env_redis_url_password_survives_parsing(tmp_path, monkeypatch):
    monkeypatch.setattr(_paths, "BASE_DIR", tmp_path)
    cfg = {
        **BASE_ENV_CONFIG,
        "db_type": "sqlite",
        "db_name": "rosetta",
        "redis_host": "cache.internal",
        "redis_port": 6380,
        "redis_password": "r@dis:p/ass",
    }
    url = _env_value(ConfigService().generate_env_content(cfg), "REDIS_URL")
    parsed = urlparse(url)
    assert unquote(parsed.password) == "r@dis:p/ass"
    assert parsed.hostname == "cache.internal"
    assert parsed.port == 6380


def test_env_sqlite_url_is_absolute(tmp_path, monkeypatch):
    """必须是绝对路径：否则不同 cwd 的进程（dev.ps1 / Nitro / 迁移脚本）各开各的库文件。"""
    base = tmp_path / "proj"
    base.mkdir()
    monkeypatch.setattr(_paths, "BASE_DIR", base)
    cfg = {**BASE_ENV_CONFIG, "db_type": "sqlite", "db_name": "blog", "db_path": ""}
    url = _env_value(ConfigService().generate_env_content(cfg), "DATABASE_URL")
    assert url.startswith("sqlite+aiosqlite:///")
    file_part = url.removeprefix("sqlite+aiosqlite:///")
    assert "\\" not in file_part
    assert Path(file_part).is_absolute(), f".env 里的 sqlite 路径不能是相对的：{file_part}"
    assert file_part.endswith("blog.db")
