"""
Rosetta FastAPI 后端核心配置

配置管理模块，使用 Pydantic Settings 进行类型安全的配置管理。
支持从环境变量和 .env 文件加载配置。

环境配置说明:
- 开发环境 (development): 支持 SQLite/PostgreSQL + 内存/Redis 缓存，灵活配置
- 生产环境 (production): PostgreSQL + Redis，高性能可扩展

Example:
    >>> from backend.core.config import settings
    >>> print(settings.app_name)
    'Rosetta API'
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类

    使用 Pydantic Settings 管理所有配置项，支持：
    - 环境变量覆盖
    - .env 文件加载
    - 类型验证
    - 默认值

    Attributes:
        app_name: 应用名称
        app_version: 应用版本
        debug: 调试模式开关
        database_url: 数据库连接 URL
        redis_url: Redis 连接 URL
        secret_key: JWT 签名密钥
        algorithm: JWT 加密算法
        access_token_expire_minutes: 访问令牌过期时间（分钟）
        refresh_token_expire_days: 刷新令牌过期时间（天）
        cors_origins: 允许的 CORS 源列表
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基础配置
    app_name: str = Field(
        default="Rosetta API",
        description="应用名称",
    )
    app_version: str = Field(
        default="1.0.0",
        description="应用版本",
    )
    debug: bool = Field(
        default=True,
        description="调试模式，启用后会开启 API 文档和详细错误信息",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="运行环境: development=灵活配置(SQLite/PostgreSQL+内存/Redis), production=PostgreSQL+Redis",
    )

    # 数据库配置
    database_url: str = Field(
        default="sqlite+aiosqlite:///./rosetta.db",
        description="数据库连接 URL，开发环境默认 SQLite，生产环境应使用 PostgreSQL",
    )
    database_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="数据库连接池大小（仅 PostgreSQL 有效）",
    )
    database_max_overflow: int = Field(
        default=20,
        ge=0,
        le=50,
        description="数据库连接池最大溢出数（仅 PostgreSQL 有效）",
    )
    database_echo: bool = Field(
        default=False,
        description="是否打印 SQL 语句",
    )
    database_ssl: bool = Field(
        default=False,
        description="PostgreSQL 是否使用 SSL 连接（生产环境外部数据库建议开启）",
    )

    # Redis 配置
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 连接 URL，生产环境用于缓存和会话存储",
    )
    redis_enabled: bool = Field(
        default=False,
        description="是否启用 Redis（开发和生产环境均可启用）",
    )

    # JWT 认证配置
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT 签名密钥，生产环境必须更改",
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT 加密算法",
    )
    access_token_expire_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="访问令牌过期时间（分钟）",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="刷新令牌过期时间（天）",
    )

    # CORS 配置
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:4321",
            "http://127.0.0.1:4321",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="允许的 CORS 源列表",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="是否允许携带凭据",
    )
    cors_allow_methods: list[str] = Field(
        default=["*"],
        description="允许的 HTTP 方法",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        description="允许的 HTTP 头",
    )

    @property
    def effective_cors_origins(self) -> list[str]:
        """获取有效的 CORS 来源列表（前后端同域代理，无需通配跨域）"""
        return self.cors_origins

    # 文件上传配置
    media_dir: str = Field(
        default="media",
        description="媒体文件存储目录",
    )
    static_dir: str = Field(
        default="static",
        description="静态文件存储目录",
    )
    max_upload_size: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
        description="最大上传文件大小（字节）",
    )
    allowed_extensions: list[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "webp", "svg", "pdf", "doc", "docx"],
        description="允许上传的文件扩展名",
    )

    # 日志配置
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="日志级别",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式",
    )

    # 站点配置
    site_name: str = Field(
        default="Rosetta Blog",
        description="站点名称",
    )
    site_description: str = Field(
        default="Rosetta开源博客系统",
        description="站点描述",
    )
    site_keywords: str = Field(
        default="Rosetta, FastAPI, Astro, Svelte, Blog",
        description="站点关键词",
    )
    site_author: str = Field(
        default="Rosetta Team",
        description="站点作者",
    )
    site_email: str = Field(
        default="contact@rosetta.dev",
        description="站点联系邮箱",
    )
    site_url: str = Field(
        default="http://localhost:4321",
        description="站点 URL",
    )
    pagination_page_size: int = Field(
        default=12,
        ge=1,
        le=100,
        description="默认分页大小",
    )

    # SMTP 邮件配置
    smtp_host: str = Field(
        default="smtp.qq.com",
        description="SMTP 服务器地址",
    )
    smtp_port: int = Field(
        default=465,
        ge=1,
        le=65535,
        description="SMTP 服务器端口",
    )
    smtp_user: str = Field(
        default="",
        description="SMTP 用户名",
    )
    smtp_password: str = Field(
        default="",
        description="SMTP 密码",
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="是否使用 TLS",
    )
    smtp_from_email: str = Field(
        default="",
        description="发件人邮箱",
    )

    # 功能开关
    enable_comments: bool = Field(
        default=True,
        description="是否启用评论功能",
    )
    comment_require_approval: bool = Field(
        default=False,
        description="评论是否需要审核",
    )
    enable_registration: bool = Field(
        default=True,
        description="是否启用用户注册",
    )
    enable_rss_feed: bool = Field(
        default=True,
        description="是否启用 RSS 订阅",
    )

    # 安全策略配置
    security_password_policy: bool = Field(
        default=True,
        description="是否启用密码强度策略（≥8位+大小写+数字+禁止常见密码）",
    )
    force_hsts: bool = Field(
        default=False,
        description="是否强制启用 HSTS 响应头（即使请求 scheme=http 也写入）",
    )
    max_login_attempts: int = Field(
        default=10,
        ge=1,
        le=20,
        description="最大登录失败尝试次数，超过后锁定",
    )
    login_lockout_minutes: int = Field(
        default=10,
        ge=1,
        le=120,
        description="登录失败锁定时长（分钟）",
    )

    # 速率限制阈值
    rate_limit_sensitive_requests: int = Field(
        default=10,
        ge=1,
        description="敏感接口（登录/注册/刷新/重置密码）每窗口请求数",
    )
    rate_limit_sensitive_window: int = Field(
        default=60,
        ge=1,
        description="敏感接口限流窗口（秒）",
    )
    rate_limit_write_requests: int = Field(
        default=60,
        ge=1,
        description="普通写接口每窗口请求数",
    )
    rate_limit_write_window: int = Field(
        default=60,
        ge=1,
        description="普通写接口限流窗口（秒）",
    )

    # 国际化配置
    default_language: str = Field(
        default="zh",
        description="默认语言代码",
    )
    supported_languages: list[str] = Field(
        default=["zh", "en", "ja", "zh_Hant"],
        description="支持的语言列表",
    )

    # 监控配置
    sentry_dsn: str | None = Field(
        default=None,
        description="Sentry DSN，用于错误监控",
    )

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """
        验证密钥安全性

        开发/staging 环境仅告警；生产环境下使用默认值或长度不足 32 时拒绝启动。
        """
        default_secret = "your-secret-key-change-in-production"
        if self.environment == "production":
            if self.secret_key == default_secret:
                raise ValueError(
                    "生产环境禁止使用默认 SECRET_KEY：请设置 SECRET_KEY 环境变量为"
                    "至少 32 字符的随机字符串（例如 openssl rand -hex 32 生成）"
                )
            if len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY 长度不足 32 字符：请通过 SECRET_KEY 环境变量设置强密钥"
                )
        elif len(self.secret_key) < 32:
            import warnings

            warnings.warn(
                "Secret key is too short. Use a strong key with at least 32 characters.",
                UserWarning,
            )
        return self

    @property
    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """检查是否为开发环境"""
        return self.environment == "development"

    @property
    def is_sqlite(self) -> bool:
        """检查是否使用 SQLite 数据库"""
        return "sqlite" in self.database_url.lower()

    @property
    def is_postgresql(self) -> bool:
        """检查是否使用 PostgreSQL 数据库"""
        return "postgresql" in self.database_url.lower()

    def get_database_info(self) -> dict[str, str]:
        """获取数据库信息"""
        if self.is_sqlite:
            return {
                "type": "SQLite",
                "description": "轻量级文件数据库，适合开发环境",
            }
        elif self.is_postgresql:
            return {
                "type": "PostgreSQL",
                "description": "高性能关系数据库，适合生产环境",
            }
        return {
            "type": "Unknown",
            "description": "未知数据库类型",
        }


@lru_cache
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）

    使用 lru_cache 确保配置只加载一次。

    Returns:
        Settings: 配置实例
    """
    return Settings()


settings = get_settings()
