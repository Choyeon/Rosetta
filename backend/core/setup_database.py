"""
数据库服务

提供数据库初始化和管理功能：
- PostgreSQL 连接测试
- 数据库自动创建
- Redis 连接测试
- 数据库迁移支持
"""

from dataclasses import dataclass
from enum import Enum


class DatabaseType(Enum):
    """数据库类型"""

    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


@dataclass
class ConnectionResult:
    """连接结果"""

    success: bool
    message: str
    details: dict | None = None


@dataclass
class DatabaseConfig:
    """数据库配置"""

    db_type: str = "postgresql"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rosetta"
    db_user: str = ""
    db_password: str = ""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""


class DatabaseService:
    """数据库服务"""

    def __init__(self, config: DatabaseConfig | None = None):
        self.config = config or DatabaseConfig()

    def update_config(self, config: DatabaseConfig):
        """更新数据库配置"""
        self.config = config

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

    async def test_redis_connection(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: str = "",
        db: int = 0,
        timeout: int = 5,
    ) -> ConnectionResult:
        """测试 Redis 连接"""
        try:
            import redis.asyncio as redis

            client = redis.Redis(
                host=host,
                port=port,
                password=password if password else None,
                db=db,
                decode_responses=True,
            )
            await client.ping()
            await client.close()
            return ConnectionResult(
                success=True,
                message="Redis 连接成功",
            )
        except ImportError:
            return ConnectionResult(
                success=False,
                message="请安装 redis: uv pip install redis",
            )
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="连接被拒绝，请检查 Redis 服务是否启动",
                    details={"error": error_msg},
                )
            elif "Authentication" in error_msg or "auth" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="认证失败，请检查密码",
                    details={"error": error_msg},
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"连接失败: {error_msg}",
                    details={"error": error_msg},
                )

    async def create_postgresql_database(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "",
        password: str = "",
        db_name: str = "rosetta",
    ) -> ConnectionResult:
        """创建 PostgreSQL 数据库"""
        try:
            import asyncpg

            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database="postgres",
                timeout=10,
            )

            try:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                await conn.close()
                return ConnectionResult(
                    success=True,
                    message=f"数据库 {db_name} 创建成功",
                )
            except asyncpg.DuplicateDatabaseError:
                await conn.close()
                return ConnectionResult(
                    success=True,
                    message=f"数据库 {db_name} 已存在",
                )
            except Exception as e:
                await conn.close()
                return ConnectionResult(
                    success=False,
                    message=f"创建数据库时出错: {str(e)}",
                    details={"error": str(e)},
                )

        except ImportError:
            return ConnectionResult(
                success=False,
                message="请安装 asyncpg: uv pip install asyncpg",
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"数据库创建失败: {str(e)}",
                details={"error": str(e)},
            )

    async def init_database_schema(
        self,
        config: dict,
    ) -> ConnectionResult:
        """初始化数据库表结构"""
        try:
            from backend.core.database import init_db

            await init_db()

            return ConnectionResult(
                success=True,
                message="数据库表结构初始化成功",
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"数据库初始化失败: {str(e)}",
                details={"error": str(e)},
            )

    async def create_admin_user(
        self,
        config: dict,
    ) -> ConnectionResult:
        """创建管理员用户"""
        try:
            from sqlalchemy import select

            from backend.core.auth import get_password_hash
            from backend.core.database import async_session_maker
            from backend.models.user import User

            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(User.username == config["admin_username"])
                )
                if result.scalar_one_or_none():
                    return ConnectionResult(
                        success=True,
                        message=f"管理员账户 {config['admin_username']} 已存在",
                    )

                admin = User(
                    username=config["admin_username"],
                    email=config["admin_email"],
                    password_hash=get_password_hash(config.get("admin_password", "admin123")),
                    nickname=config.get("admin_nickname", config["admin_username"]),
                    is_active=True,
                    is_staff=True,
                    is_superuser=True,
                )
                session.add(admin)
                await session.commit()

                return ConnectionResult(
                    success=True,
                    message=f"管理员账户 {config['admin_username']} 创建成功",
                )

        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"创建管理员失败: {str(e)}",
                details={"error": str(e)},
            )

    async def create_default_data(
        self,
        config: dict,
    ) -> ConnectionResult:
        """创建默认数据"""
        try:
            from backend.core.database import async_session_maker
            from backend.models.blog import Category, Tag
            from backend.models.core import Navigation, Page

            async with async_session_maker() as session:
                default_category = Category(
                    name={"zh": "未分类", "en": "Uncategorized", "ja": "未分類", "zh_TW": "未分類"},
                    slug="uncategorized",
                    description={
                        "zh": "默认分类",
                        "en": "Default category",
                        "ja": "デフォルト分類",
                        "zh_TW": "預設分類",
                    },
                    color="primary",
                )
                session.add(default_category)

                default_tags = [
                    Tag(
                        name={"zh": "技术", "en": "Technology", "ja": "技術", "zh_TW": "技術"},
                        slug="technology",
                        color="#3B82F6",
                    ),
                    Tag(
                        name={"zh": "生活", "en": "Life", "ja": "生活", "zh_TW": "生活"},
                        slug="life",
                        color="#10B981",
                    ),
                    Tag(
                        name={"zh": "随笔", "en": "Essay", "ja": "随筆", "zh_TW": "隨筆"},
                        slug="essay",
                        color="#8B5CF6",
                    ),
                ]
                for tag in default_tags:
                    session.add(tag)

                about_page = Page(
                    title={"zh": "关于", "en": "About", "ja": "概要", "zh_TW": "關於"},
                    slug="about",
                    content={
                        "zh": "# 关于\n\n欢迎来到我们的博客！",
                        "en": "# About\n\nWelcome to our blog!",
                        "ja": "# 概要\n\n私たちのブログへようこそ！",
                        "zh_TW": "# 關於\n\n歡迎來到我們的部落格！",
                    },
                    status="published",
                )
                session.add(about_page)

                guestbook_page = Page(
                    title={
                        "zh": "留言板",
                        "en": "Guestbook",
                        "ja": "ゲストブック",
                        "zh_TW": "留言板",
                    },
                    slug="guestbook",
                    content={
                        "zh": "# 留言板\n\n欢迎留下你的想法！",
                        "en": "# Guestbook\n\nFeel free to leave your thoughts!",
                    },
                    status="published",
                )
                session.add(guestbook_page)

                archive_page = Page(
                    title={"zh": "归档", "en": "Archive", "ja": "アーカイブ", "zh_TW": "歸檔"},
                    slug="archive",
                    content={"zh": "# 文章归档", "en": "# Archive"},
                    status="published",
                )
                session.add(archive_page)

                default_navs = [
                    Navigation(
                        title={"zh": "首页", "en": "Home", "ja": "ホーム", "zh_TW": "首頁"},
                        url="/",
                        location="header",
                        order=1,
                        is_active=True,
                    ),
                    Navigation(
                        title={"zh": "文章", "en": "Posts", "ja": "記事", "zh_TW": "文章"},
                        url="/posts",
                        location="header",
                        order=2,
                        is_active=True,
                    ),
                    Navigation(
                        title={
                            "zh": "分类",
                            "en": "Categories",
                            "ja": "カテゴリー",
                            "zh_TW": "分類",
                        },
                        url="/categories",
                        location="header",
                        order=3,
                        is_active=True,
                    ),
                    Navigation(
                        title={"zh": "标签", "en": "Tags", "ja": "タグ", "zh_TW": "標籤"},
                        url="/tags",
                        location="header",
                        order=4,
                        is_active=True,
                    ),
                    Navigation(
                        title={"zh": "关于", "en": "About", "ja": "概要", "zh_TW": "關於"},
                        url="/page/about",
                        location="header",
                        order=5,
                        is_active=True,
                    ),
                    Navigation(
                        title={
                            "zh": "留言板",
                            "en": "Guestbook",
                            "ja": "ゲストブック",
                            "zh_TW": "留言板",
                        },
                        url="/page/guestbook",
                        location="header",
                        order=6,
                        is_active=True,
                    ),
                ]

                for nav in default_navs:
                    session.add(nav)

                await session.commit()

                return ConnectionResult(
                    success=True,
                    message="默认数据创建成功",
                )

        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"创建默认数据失败: {str(e)}",
                details={"error": str(e)},
            )

    async def initialize_full(
        self,
        config: dict,
        progress_callback=None,
    ) -> dict[str, ConnectionResult]:
        """完整初始化数据库"""
        results = {}

        if progress_callback:
            await progress_callback("正在测试数据库连接...")

        db_result = await self.test_postgresql_connection(
            host=config.get("db_host", "localhost"),
            port=config.get("db_port", 5432),
            user=config.get("db_user", ""),
            password=config.get("db_password", ""),
        )
        results["connection"] = db_result

        if not db_result.success:
            return results

        if progress_callback:
            await progress_callback("正在创建数据库...")

        create_result = await self.create_postgresql_database(
            host=config.get("db_host", "localhost"),
            port=config.get("db_port", 5432),
            user=config.get("db_user", ""),
            password=config.get("db_password", ""),
            db_name=config.get("db_name", "rosetta"),
        )
        results["database"] = create_result

        if progress_callback:
            await progress_callback("正在初始化表结构...")

        schema_result = await self.init_database_schema(config)
        results["schema"] = schema_result

        if progress_callback:
            await progress_callback("正在创建管理员账户...")

        admin_result = await self.create_admin_user(config)
        results["admin"] = admin_result

        if progress_callback:
            await progress_callback("正在创建默认数据...")

        data_result = await self.create_default_data(config)
        results["default_data"] = data_result

        return results


def generate_database_url(config: dict) -> str:
    """生成数据库连接 URL

    SQLite 路径解析规则（db_path 优先，确保 OOBE 请求体中的 db_path 字段能真正生效）：
      1. 若 db_path 为绝对路径，直接使用
      2. 若 db_path 是相对路径或 db_path 缺失 → 以项目根 BASE_DIR 为基准解析
      3. 若最终路径不携带 .db 后缀则自动补 .db
    """
    from urllib.parse import quote_plus
    from pathlib import Path

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

        password_part = f":{quote_plus(db_password)}" if db_password else ""
        return f"postgresql+asyncpg://{db_user}{password_part}@{db_host}:{db_port}/{db_name}"
    return ""


def generate_redis_url(config: dict) -> str:
    """生成 Redis 连接 URL"""
    from urllib.parse import quote_plus

    redis_host = config.get("redis_host", "localhost")
    redis_port = config.get("redis_port", 6379)
    redis_password = config.get("redis_password", "")

    if redis_password:
        return f"redis://:{quote_plus(redis_password)}@{redis_host}:{redis_port}/0"
    return f"redis://{redis_host}:{redis_port}/0"
