"""数据库工具：PostgreSQL 连通性探测 + 数据库连接 URL 生成。

OOBE 向导安装前用 `DatabaseService.test_postgresql_connection` 自检，
用 `generate_database_url` 把表单里的 db_* 字段拼成 SQLAlchemy async URL。
建库/建表/建管理员只有 `backend/api/oobe.py::oobe_install` 一条路径：
这里曾并存一套 `initialize_full`（会凭空造出密码为 `admin123` 的超管），已删除。
"""

from dataclasses import dataclass


@dataclass
class ConnectionResult:
    """连接结果"""

    success: bool
    message: str
    details: dict | None = None


class DatabaseService:
    """数据库服务"""

    async def test_postgresql_connection(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "",
        password: str = "",
        database: str = "postgres",
        timeout: int = 5,
    ) -> ConnectionResult:
        """测试 PostgreSQL 连接"""
        try:
            import asyncpg

            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                timeout=timeout,
            )

            try:
                version = await conn.fetchval("SELECT version()")
                await conn.close()
                return ConnectionResult(
                    success=True,
                    message="PostgreSQL 连接成功",
                    details={"version": version},
                )
            except Exception as e:
                await conn.close()
                return ConnectionResult(
                    success=True,
                    message="PostgreSQL 连接成功",
                    details={"warning": str(e)},
                )

        except ImportError:
            return ConnectionResult(
                success=False,
                message="请安装 asyncpg: uv pip install asyncpg",
            )
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="连接被拒绝，请检查 PostgreSQL 服务是否启动",
                    details={"error": error_msg},
                )
            elif "authentication failed" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="认证失败，请检查用户名和密码",
                    details={"error": error_msg},
                )
            elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                return ConnectionResult(
                    success=True,
                    message="连接成功，数据库将在安装时自动创建",
                    details={"error": error_msg},
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"连接失败: {error_msg}",
                    details={"error": error_msg},
                )


def generate_database_url(config: dict) -> str:
    """生成数据库连接 URL

    SQLite 路径解析规则（db_path 优先，确保 OOBE 请求体中的 db_path 字段能真正生效）：
      1. 若 db_path 为绝对路径，直接使用
      2. 若 db_path 是相对路径或 db_path 缺失 → 以项目根 BASE_DIR 为基准解析
      3. 若最终路径不携带 .db 后缀则自动补 .db
    """
    from pathlib import Path
    from urllib.parse import quote

    from backend.core.paths import BASE_DIR

    db_type = config.get("db_type", "postgresql")
    if db_type == "sqlite":
        db_path = (config.get("db_path") or "").strip()
        db_name_cfg = (config.get("db_name") or "rosetta").strip()
        if db_path:
            candidate = Path(db_path)
            if not candidate.is_absolute():
                candidate = BASE_DIR / candidate
            # 路径后缀处理（无论 db_path 相对/绝对，最终都强制落地为 .db 文件）
            if candidate.suffix.lower() != ".db":
                candidate = candidate.with_suffix(".db")
        else:
            # ⚠️ 兼容 OOBE 历史误写 db_name=".db" / "" / "." 的情况：
            # ".db" 在 pathlib 中 suffix=''、stem='.db'（是隐藏文件的整体名字），
            # 需要通过"文件名去掉 .db 后是否为空串"这个更准确的判据。
            name = (db_name_cfg or "").strip()
            if name.endswith((".db", ".DB")):
                stem_no_ext = name[:-3]
            else:
                stem_no_ext = name
            if not stem_no_ext or stem_no_ext == ".":
                candidate = BASE_DIR / "rosetta.db"
            else:
                candidate = BASE_DIR / name
                if not (name.endswith((".db", ".DB"))):
                    candidate = candidate.with_suffix(".db")
        # aiosqlite 的 URL 里必须使用 POSIX 风格路径，否则 Windows 盘符会被当作 hostname
        return f"sqlite+aiosqlite:///{candidate.as_posix()}"

    if db_type == "postgresql":
        db_user = config.get("db_user", "")
        db_password = config.get("db_password", "")
        db_host = config.get("db_host", "localhost")
        db_port = config.get("db_port", 5432)
        db_name = config.get("db_name", "rosetta")

        # userinfo 段必须百分号编码，且**不能**用 quote_plus：
        # `+` 只在表单编码里代表空格，URL authority 里它是字面量加号，
        # 含空格的密码会被 SQLAlchemy 解出来成 `+`，连接时认证失败。
        password_part = f":{quote(db_password, safe='')}" if db_password else ""
        return f"postgresql+asyncpg://{db_user}{password_part}@{db_host}:{db_port}/{db_name}"
    return ""
