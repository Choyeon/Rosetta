"""数据库工具：PostgreSQL 连通性探测 + 数据库连接 URL 生成。

OOBE 向导安装前用 `DatabaseService.test_postgresql_connection` 自检，
用 `generate_database_url` 把表单里的 db_* 字段拼成 SQLAlchemy async URL。
建库/建表/建管理员只有 `backend/api/oobe.py::oobe_install` 一条路径：
这里曾并存一套 `initialize_full`（会凭空造出密码为 `admin123` 的超管），已删除。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---- 结构化错误码：给向导前端做「可操作报错」用 -------------------------
# 语义（前端按 code 分支渲染，而不是去匹配中文 message）：
#   DB_OK              连接成功
#   DB_DRIVER_MISSING  服务端缺 asyncpg，装不上就别谈连库
#   DB_UNREACHABLE     主机/端口不可达（服务没起、端口错、防火墙）
#   DB_AUTH_FAILED     账号或密码不对
#   DB_NOT_EXIST       账号能连上，但目标库还没建
#   DB_PERMISSION_DENIED 账号无建库/连接权限
#   DB_TIMEOUT         连接超时
#   DB_UNKNOWN         其余：只给脱敏摘要，绝不回显连接串
DB_OK = "DB_OK"
DB_DRIVER_MISSING = "DB_DRIVER_MISSING"
DB_UNREACHABLE = "DB_UNREACHABLE"
DB_AUTH_FAILED = "DB_AUTH_FAILED"
DB_NOT_EXIST = "DB_NOT_EXIST"
DB_PERMISSION_DENIED = "DB_PERMISSION_DENIED"
DB_TIMEOUT = "DB_TIMEOUT"
DB_UNKNOWN = "DB_UNKNOWN"

# 连接串里出现 `://user:password@host/db` 时，脱敏只会保留 scheme + host[:port]。
# 目的：安装失败的 HTTP 500 / SSE error 帧绝不把管理员刚填的数据库口令回显出去
# （OOBE 是匿名端点，任何人都能连 /oobe/install/stream 看 SSE 回放）。
_URL_CRED_RE = re.compile(r"(?P<scheme>[a-z][a-z0-9+.\-]*://)(?P<user>[^:/@\s]*)(?::[^@\s]*)?@")


def scrub_database_url(text: str | None) -> str:
    """把任意文本里出现的数据库 URL 凭据抹成 `***`。

    只抹 user:password@ 这一段，host/port/db 保留——排查时需要知道连的是哪台机器，
    但绝不需要知道口令。非 URL 文本原样返回。
    """
    if not text:
        return ""
    return _URL_CRED_RE.sub(lambda m: f"{m.group('scheme')}{m.group('user')}:***@", str(text))


def classify_db_error(exc: BaseException | str) -> tuple[str, str, str]:
    """把 asyncpg / OSError 的原始异常归类成 (code, message, hint)。

    message 给人类看，hint 给「下一步该做什么」。两者都必须是脱敏后的文本。
    """
    raw = str(exc) if not isinstance(exc, BaseException) else f"{type(exc).__name__}: {exc}"
    safe = scrub_database_url(raw).replace("\n", " ").strip()
    low = safe.lower()

    if "no module named 'asyncpg'" in low or "no module named asyncpg" in low:
        return (
            DB_DRIVER_MISSING,
            "服务端缺少 PostgreSQL 驱动 asyncpg",
            "在后端目录执行 uv sync（或 uv pip install asyncpg）后重启服务；也可以改用 SQLite 完成安装。",
        )
    if "connection refused" in low or "connect call failed" in low or "nodename nor servname" in low:
        return (
            DB_UNREACHABLE,
            "连不上数据库主机（连接被拒绝）",
            "确认 PostgreSQL 已启动、主机与端口填写正确、防火墙/安全组放行该端口。",
        )
    # "timed out" 与 "timeout" 都要匹配：asyncio.TimeoutError 与 socket 的常见文案是
    # "connection timed out"，只查 "timeout" 会漏判成 DB_UNKNOWN，用户就拿不到任何可操作提示。
    # 排除 "statement timeout" —— 那是 SQL 执行超时，属于库已连上的应用层问题，不是连不上。
    if ("timeout" in low or "timed out" in low) and "statement" not in low:
        return (
            DB_TIMEOUT,
            "连接数据库超时",
            "确认主机可达且端口未被拦截；跨公网连接请检查安全组与 pg_hba.conf。",
        )
    if "password authentication failed" in low or "authentication failed" in low:
        return (
            DB_AUTH_FAILED,
            "数据库账号或密码不正确",
            "检查用户名与密码；注意 PostgreSQL 的用户名区分大小写。",
        )
    if "does not exist" in low and "database" in low:
        return (
            DB_NOT_EXIST,
            "目标数据库不存在",
            "用超级用户执行 CREATE DATABASE 建库后重试，或换一个已存在的库名。",
        )
    if "role" in low and "does not exist" in low:
        return (
            DB_AUTH_FAILED,
            "数据库用户不存在",
            "先用 CREATE ROLE 建好该用户并授予登录权限。",
        )
    if "permission denied" in low or "pg_hba.conf" in low:
        return (
            DB_PERMISSION_DENIED,
            "数据库权限不足或被 pg_hba.conf 拒绝",
            "为该用户授予建库权限（CREATEDB），或在 pg_hba.conf 放行来源地址后 reload。",
        )
    return (DB_UNKNOWN, f"数据库连接失败：{safe}", "请核对主机、端口、库名、账号与密码后重试。")


@dataclass
class ConnectionResult:
    """连接结果"""

    success: bool
    message: str
    details: dict | None = None
    # 结构化错误码（见模块顶部常量）。旧调用方不读它，缺省 DB_OK 保持向后兼容。
    code: str = DB_OK
    # 「下一步该做什么」的可操作提示；成功时为 None
    hint: str | None = None


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
                code=DB_DRIVER_MISSING,
                hint="在后端目录执行 uv sync（或 uv pip install asyncpg）后重启服务。",
            )
        except Exception as e:
            # 统一走分类层：`details.error` 必须是**脱敏后**的原始信息。
            # 旧实现直接把 asyncpg 原文塞进 message/details，而 asyncpg 的部分异常
            # 文本会带出连接串（含口令）——OOBE 是匿名端点，等于公开口令。
            code, message, hint = classify_db_error(e)
            return ConnectionResult(
                success=False,
                message=message,
                details={"error": scrub_database_url(str(e))},
                code=code,
                hint=hint,
            )

    async def probe_database(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "",
        password: str = "",
        database: str = "rosetta",
        maintenance_db: str = "postgres",
        timeout: int = 5,
    ) -> ConnectionResult:
        """安装前的**目标库**体检：能连上 + 目标库是否已存在 + 有没有建库权限。

        与 `test_postgresql_connection` 的区别：后者只连维护库证明「账号密码对」，
        而安装真正要写的是 `database` 这个库。WordPress 那句
        "Can't select database" 就是这一层没查的结果——账号对了但库不存在，
        安装照样在半路炸掉。这里先问清楚，向导就能给出 `CREATE DATABASE` 提示。

        目标库不存在**不算失败**（安装时会建），但会用 `code=DB_NOT_EXIST` 明确告知，
        并顺带检查该账号是否有 CREATEDB 权限——没有的话现在就该说，别等安装时报错。
        """
        base = await self.test_postgresql_connection(
            host=host, port=port, user=user, password=password,
            database=maintenance_db, timeout=timeout,
        )
        if not base.success:
            return base

        try:
            import asyncpg
        except ImportError:
            return ConnectionResult(
                success=False,
                message="请安装 asyncpg: uv pip install asyncpg",
                code=DB_DRIVER_MISSING,
                hint="在后端目录执行 uv sync（或 uv pip install asyncpg）后重启服务。",
            )

        try:
            conn = await asyncpg.connect(
                host=host, port=port, database=maintenance_db,
                user=user, password=password, timeout=timeout,
            )
        except Exception as e:
            code, message, hint = classify_db_error(e)
            return ConnectionResult(
                success=False, message=message,
                details={"error": scrub_database_url(str(e))}, code=code, hint=hint,
            )

        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", database
            )
            version = await conn.fetchval("SELECT version()")
            if exists:
                return ConnectionResult(
                    success=True,
                    message=f"数据库 {database} 已就绪",
                    details={"version": version, "database": database, "exists": True},
                    code=DB_OK,
                )

            # 库不存在 → 关键问题是"这个账号能不能自己建库"
            can_create = await conn.fetchval(
                "SELECT 1 FROM pg_roles WHERE rolname = $1 AND rolcreatedb", user
            )
            if can_create:
                return ConnectionResult(
                    success=True,
                    message=f"账号可用，数据库 {database} 将在安装时自动创建",
                    details={"version": version, "database": database, "exists": False},
                    code=DB_NOT_EXIST,
                    hint=f"如需手动建库：CREATE DATABASE \"{database}\";",
                )
            return ConnectionResult(
                success=False,
                message=f"数据库 {database} 不存在，且当前账号没有建库权限（CREATEDB）",
                details={"version": version, "database": database, "exists": False},
                code=DB_PERMISSION_DENIED,
                hint=(
                    f"用超级用户执行：CREATE DATABASE \"{database}\" OWNER \"{user}\";"
                    f" 或 ALTER ROLE \"{user}\" CREATEDB;"
                ),
            )
        except Exception as e:
            code, message, hint = classify_db_error(e)
            return ConnectionResult(
                success=False, message=message,
                details={"error": scrub_database_url(str(e))}, code=code, hint=hint,
            )
        finally:
            try:
                await conn.close()
            except Exception:
                # 关闭失败不影响探测结论；连接本身由 asyncpg 的 GC / 服务端超时兜底
                pass


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
