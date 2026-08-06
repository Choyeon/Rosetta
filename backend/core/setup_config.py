"""
配置管理服务

提供配置管理和验证功能：
- 配置模板
- 配置验证
- 多环境支持
- 配置文件生成
- 断点续传支持
"""

import hashlib
import json
import os
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from backend.core.paths import BASE_DIR
from backend.core.oobe_constants import (
    FEATURE_FLAG_DB_KEY_MAP,
    USERNAME_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_PATTERN,
    PASSWORD_MIN_LENGTH,
    EMAIL_PATTERN,
)


class Environment(Enum):
    """环境类型"""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class ConfigStep(Enum):
    """配置步骤"""

    WELCOME = 1
    ENVIRONMENT = 2
    DATABASE = 3
    SITE = 4
    ADMIN = 5
    COMPLETE = 6


@dataclass
class SiteConfig:
    """站点配置"""

    site_name: str = "Rosetta"
    site_title: str = ""
    site_description: str = "让文字有处安放，让思想自由流淌"
    site_keywords: str = "blog, rosetta"
    site_author: str = "Administrator"
    site_email: str = "admin@example.com"
    site_url: str = "http://localhost:4321"
    github_url: str = ""
    x_url: str = ""
    bilibili_url: str = ""
    footer_text: str = ""
    enable_comments: bool = True
    enable_registration: bool = True
    enable_rss: bool = True
    default_cover_image: str = ""
    # 额外功能开关（非持久化到 SiteConfig 表，仅用于生成配置文件）
    extra_features: dict = field(default_factory=dict)


@dataclass
class AdminConfig:
    """管理员配置"""

    username: str = ""
    email: str = ""
    password: str = ""
    nickname: str = ""


@dataclass
class OOBEState:
    """OOBE 状态"""

    current_step: int = 1
    total_steps: int = 5
    environment: Environment = Environment.DEVELOPMENT
    database_config: dict = field(default_factory=dict)
    site_config: SiteConfig = field(default_factory=SiteConfig)
    admin_config: AdminConfig = field(default_factory=AdminConfig)
    completed: bool = False
    errors: list[dict] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    started_at: str | None = None
    last_updated: str | None = None
    config_file: Path | None = None

    def to_dict(self) -> dict:
        """转换为字典（敏感字段以 SHA-256 摘要存储，不存明文）"""
        def _digest(val: str) -> str:
            return hashlib.sha256(val.encode()).hexdigest()[:16]

        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "environment": self.environment.value,
            "database_config": {
                k: _digest(v) if k in ("db_password", "redis_password") else v
                for k, v in self.database_config.items()
            } if self.database_config else {},
            "site_config": self.site_config.__dict__ if self.site_config else {},
            "admin_config": {
                "username": self.admin_config.username,
                "email": self.admin_config.email,
                "password": _digest(self.admin_config.password),
                "nickname": self.admin_config.nickname,
            },
            "completed": self.completed,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
        }


class ConfigTemplates:
    """配置模板"""

    @staticmethod
    def get_development_template() -> dict:
        """开发环境配置模板"""
        return {
            "environment": "development",
            "debug": True,
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "rosetta_dev",
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
            },
        }

    @staticmethod
    def get_production_template() -> dict:
        """生产环境配置模板"""
        return {
            "environment": "production",
            "debug": False,
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "rosetta",
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
            },
        }

    @staticmethod
    def get_templates() -> dict[str, dict]:
        """获取所有配置模板"""
        return {
            "development": ConfigTemplates.get_development_template(),
            "production": ConfigTemplates.get_production_template(),
        }

    @staticmethod
    def get_template_names() -> list[str]:
        """获取模板名称列表"""
        return list(ConfigTemplates.get_templates().keys())


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate_site_config(config: dict) -> tuple[bool, str]:
        """验证站点配置"""
        if not config.get("site_name"):
            return False, "站点名称不能为空"

        if not config.get("site_email"):
            return False, "联系邮箱不能为空"

        email = config.get("site_email", "")
        if "@" not in email or "." not in email:
            return False, "邮箱格式不正确"

        return True, ""

    @staticmethod
    def validate_admin_config(config: dict) -> tuple[bool, str]:
        """验证管理员配置"""
        import re

        if not config.get("username"):
            return False, "用户名不能为空"

        username = config.get("username", "")
        if len(username) < USERNAME_MIN_LENGTH:
            return False, f"用户名至少{USERNAME_MIN_LENGTH}位"

        if len(username) > USERNAME_MAX_LENGTH:
            return False, f"用户名最多{USERNAME_MAX_LENGTH}位"

        if not re.match(USERNAME_PATTERN, username):
            return False, "用户名只能包含字母、数字、下划线和连字符"

        if not config.get("email"):
            return False, "邮箱不能为空"

        email = config.get("email", "")
        if not re.match(EMAIL_PATTERN, email):
            return False, "邮箱格式不正确"

        password = config.get("password", "")
        if len(password) < PASSWORD_MIN_LENGTH:
            return False, f"密码至少{PASSWORD_MIN_LENGTH}位"

        return True, ""

    @staticmethod
    def validate_database_config(config: dict) -> tuple[bool, str]:
        """验证数据库配置"""
        if not config.get("db_user"):
            return False, "数据库用户名不能为空"

        if not config.get("db_name"):
            return False, "数据库名称不能为空"

        return True, ""

    @staticmethod
    def validate_environment(environment: str) -> tuple[bool, str]:
        """验证环境配置"""
        valid_envs = ["development", "production"]
        if environment not in valid_envs:
            return False, f"环境必须是以下之一: {', '.join(valid_envs)}"
        return True, ""


class ConfigService:
    """配置管理服务"""

    def __init__(self, base_dir: Path | None = None):
        from backend.core.paths import CONFIG_FILE, ENV_FILE, OOBE_LOCK_FILE, STATE_FILE

        self.base_dir = base_dir or BASE_DIR
        self.config_file = CONFIG_FILE
        self.env_file = ENV_FILE
        self.lock_file = OOBE_LOCK_FILE
        self.state_file = STATE_FILE
        self.state = OOBEState()

    def load_state(self) -> OOBEState | None:
        """加载保存的状态（断点续传）"""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)

            self.state.current_step = data.get("current_step", 1)
            self.state.environment = Environment(data.get("environment", "development"))
            self.state.database_config = data.get("database_config", {})
            self.state.site_config = SiteConfig(**data.get("site_config", {}))
            self.state.admin_config = AdminConfig(**data.get("admin_config", {}))
            self.state.completed = data.get("completed", False)
            self.state.errors = data.get("errors", [])
            self.state.retry_count = data.get("retry_count", 0)
            self.state.started_at = data.get("started_at")
            self.state.last_updated = data.get("last_updated")

            return self.state
        except Exception:
            return None

    def save_state(self):
        """保存当前状态（断点续传）"""
        now = datetime.now().isoformat()
        if not self.state.started_at:
            self.state.started_at = now
        self.state.last_updated = now

        data = self.state.to_dict()

        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def clear_state(self):
        """清除保存的状态"""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception:
            pass

    def is_oobe_complete(self) -> bool:
        """检查 OOBE 是否已完成"""
        return self.lock_file.exists()

    def reset_oobe(self):
        """重置 OOBE 状态"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
            if self.env_file.exists():
                self.env_file.unlink()
            if self.config_file.exists():
                self.config_file.unlink()
            self.clear_state()
        except Exception:
            pass

    def generate_secret_key(self) -> str:
        """生成密钥"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def _create_site_config(req) -> "SiteConfig":
        """从请求对象构建 SiteConfig（兼容 CombinedInstallRequest / SiteConfigRequest）"""
        sc = SiteConfig()
        for attr in (
            "site_name", "site_title", "site_description", "site_keywords",
            "site_author", "site_email", "site_url", "github_url", "x_url",
            "bilibili_url", "footer_text", "enable_comments", "enable_registration",
            "enable_rss", "default_cover_image",
        ):
            val = getattr(req, attr, None)
            if val is not None:
                setattr(sc, attr, val)
        return sc

    @staticmethod
    def _create_admin_config(req) -> "AdminConfig":
        """从请求对象构建 AdminConfig"""
        ac = AdminConfig()
        ac.username = getattr(req, "admin_username", getattr(req, "username", ""))
        ac.email = getattr(req, "admin_email", getattr(req, "email", ""))
        ac.password = getattr(req, "admin_password", getattr(req, "password", ""))
        ac.nickname = getattr(req, "admin_nickname", getattr(req, "nickname", ac.username))
        return ac

    def generate_config(self, state: OOBEState) -> dict:
        """生成完整配置"""
        config = {
            "environment": state.environment.value,
            "site_name": state.site_config.site_name,
            "site_title": state.site_config.site_title,
            "site_description": state.site_config.site_description,
            "site_keywords": state.site_config.site_keywords,
            "site_author": state.site_config.site_author,
            "site_email": state.site_config.site_email,
            "site_url": state.site_config.site_url,
            "github_url": state.site_config.github_url,
            "x_url": state.site_config.x_url,
            "bilibili_url": state.site_config.bilibili_url,
            "footer_text": state.site_config.footer_text,
            "enable_comments": state.site_config.enable_comments,
            "enable_registration": state.site_config.enable_registration,
            "enable_rss": state.site_config.enable_rss,
            "default_cover_image": state.site_config.default_cover_image,
            "admin_username": state.admin_config.username,
            "admin_email": state.admin_config.email,
            "admin_nickname": state.admin_config.nickname,
            "admin_password": state.admin_config.password,
            "db_type": state.database_config.get("db_type", "postgresql"),
            "db_host": state.database_config.get("db_host", "localhost"),
            "db_port": state.database_config.get("db_port", 5432),
            "db_name": state.database_config.get("db_name", "rosetta"),
            "db_user": state.database_config.get("db_user", ""),
            "db_password": state.database_config.get("db_password", ""),
            "redis_host": state.database_config.get("redis_host", "localhost"),
            "redis_port": state.database_config.get("redis_port", 6379),
            "redis_password": state.database_config.get("redis_password", ""),
            "secret_key": self.generate_secret_key(),
            "created_at": datetime.now().isoformat(),
        }

        # 合并额外功能开关
        config.update(state.site_config.extra_features)

        return config

    def generate_env_content(self, config: dict) -> str:
        """生成 .env 文件内容"""
        from urllib.parse import quote_plus

        env = config["environment"]
        db_type = config.get("db_type", "postgresql")

        db_password = config.get("db_password", "")
        if db_type == "sqlite":
            db_name = config.get("db_name", "rosetta")
            if not db_name.endswith(".db"):
                db_name = f"{db_name}.db"
            database_url = f"sqlite+aiosqlite:///{db_name}"
        else:
            password_part = f":{quote_plus(db_password)}" if db_password else ""
            database_url = f"postgresql+asyncpg://{config['db_user']}{password_part}@{config['db_host']}:{config['db_port']}/{config['db_name']}"

        redis_url = ""
        redis_enabled = "true"
        if config.get("redis_host"):
            redis_host = config.get("redis_host", "localhost")
            redis_port = config.get("redis_port", 6379)
            redis_password = config.get("redis_password", "")
            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/0"

        env_content = f"""# Rosetta 环境配置
# 由 OOBE 向导自动生成于 {config["created_at"]}

# 应用配置
APP_NAME={config["site_name"]}
APP_ENV={env}
DEBUG={"true" if env == "development" else "false"}

# 数据库配置
DATABASE_URL={database_url}
"""

        if redis_url:
            env_content += f"""
# Redis 配置
REDIS_URL={redis_url}
REDIS_ENABLED={redis_enabled}
"""

        env_content += f"""
# JWT 配置
SECRET_KEY={config["secret_key"]}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# 站点配置
SITE_NAME={config["site_name"]}
SITE_TITLE={config.get("site_title", "")}
SITE_DESCRIPTION={config["site_description"]}
SITE_KEYWORDS={config.get("site_keywords", "")}
SITE_AUTHOR={config["site_author"]}
SITE_EMAIL={config["site_email"]}
SITE_URL={config["site_url"]}
FOOTER_TEXT={config.get("footer_text", "")}

# 社交链接
GITHUB_URL={config.get("github_url", "")}
X_URL={config.get("x_url", "")}
BILIBILI_URL={config.get("bilibili_url", "")}

# 功能开关
ENABLE_COMMENTS={str(config["enable_comments"]).lower()}
ENABLE_REGISTRATION={str(config["enable_registration"]).lower()}
ENABLE_RSS_FEED={str(config["enable_rss"]).lower()}

# 默认封面图
DEFAULT_COVER_IMAGE={config.get("default_cover_image", "")}
"""

        return env_content

    def save_config(self, config: dict) -> bool:
        """保存配置文件（原子写入，防止半成品残留）"""
        try:
            # 先写 .env 临时文件
            env_content = self.generate_env_content(config)
            env_tmp = self.env_file.with_suffix(".env.tmp")
            with open(env_tmp, "w", encoding="utf-8") as f:
                f.write(env_content)
            os.replace(env_tmp, self.env_file)

            # 先写 rosetta.json 临时文件
            json_tmp = self.config_file.with_suffix(".json.tmp")
            with open(json_tmp, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            os.replace(json_tmp, self.config_file)

            # 最后写锁文件（成功后才写，确保原子性）
            with open(self.lock_file, "w") as f:
                f.write(datetime.now().isoformat())

            return True
        except Exception:
            return False

    def get_templates(self) -> dict[str, dict]:
        """获取配置模板"""
        return ConfigTemplates.get_templates()

    def apply_template(self, template_name: str) -> dict | None:
        """应用配置模板"""
        templates = ConfigTemplates.get_templates()
        if template_name not in templates:
            return None

        template = templates[template_name]
        self.state.environment = Environment(template_name)

        if "database" in template:
            db = template["database"]
            self.state.database_config = {
                "db_type": "postgresql",
                "db_host": db.get("host", "localhost"),
                "db_port": db.get("port", 5432),
                "db_name": db.get("name", "rosetta"),
            }

        if "redis" in template:
            redis = template["redis"]
            self.state.database_config["redis_host"] = redis.get("host", "localhost")
            self.state.database_config["redis_port"] = redis.get("port", 6379)

        self.save_state()
        return template

    def update_step(self, step: int):
        """更新当前步骤"""
        self.state.current_step = step
        self.save_state()

    def add_error(self, step: str, message: str, details: str = None):
        """添加错误"""
        self.state.errors.append(
            {
                "step": step,
                "message": message,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.save_state()

    def clear_errors(self):
        """清除错误"""
        self.state.errors = []
        self.save_state()
