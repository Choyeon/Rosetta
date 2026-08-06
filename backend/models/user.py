"""
Rosetta FastAPI 后端 - 用户模型

定义用户相关的数据库模型，包括：
- User: 用户主表
- UserTitle: 用户头衔/徽章
- UserPreference: 用户偏好设置
- RefreshToken: 刷新令牌

Example:
    >>> from backend.models.user import User
    >>>
    >>> # 创建用户
    >>> user = User(
    >>>     username="admin",
    >>>     email="admin@example.com",
    >>>     password_hash=get_password_hash("password"),
    >>> )
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.utils.compat import UTC

if TYPE_CHECKING:
    from backend.models.blog import Comment, Post
    from backend.models.core import Notification


class UserTitle(Base):
    """
    用户头衔/徽章模型

    用于给用户添加特殊标识，如"管理员"、"VIP"等。

    Attributes:
        id: 主键
        name: 头衔名称
        color: 显示颜色（十六进制）
        icon: 图标（SVG 或图标类名）
        description: 头衔描述
        created_at: 创建时间

    Example:
        >>> title = UserTitle(
        >>>     name="管理员",
        >>>     color="#FF5722",
        >>>     icon="shield",
        >>> )
    """

    __tablename__ = "user_titles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="头衔ID",
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="头衔名称",
    )
    color: Mapped[str] = mapped_column(
        String(20),
        default="#3B82F6",
        comment="显示颜色",
    )
    icon: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="图标",
    )
    description: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="头衔描述",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    # 关系
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="title",
        doc="拥有此头衔的用户列表",
    )

    def __repr__(self) -> str:
        return f"<UserTitle(id={self.id}, name='{self.name}')>"


class User(Base):
    """
    用户模型

    存储用户的基本信息、权限设置和社交链接。

    Attributes:
        id: 用户ID
        username: 用户名（唯一）
        email: 邮箱地址（唯一）
        password_hash: 密码哈希
        avatar: 头像URL
        cover_image: 封面图片URL
        nickname: 昵称
        bio: 个人简介
        website: 个人网站
        github: GitHub 主页
        title_id: 头衔ID
        is_active: 是否激活
        is_staff: 是否为管理员
        is_superuser: 是否为超级管理员
        is_banned: 是否被封禁
        last_login: 最后登录时间
        created_at: 创建时间
        updated_at: 更新时间

    Example:
        >>> user = User(
        >>>     username="admin",
        >>>     email="admin@example.com",
        >>>     password_hash=get_password_hash("secure_password"),
        >>>     is_superuser=True,
        >>> )
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="用户ID",
    )
    username: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名",
    )
    email: Mapped[str] = mapped_column(
        String(254),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱地址",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希",
    )

    # 个人信息
    avatar: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="头像URL",
    )
    cover_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="封面图片URL",
    )
    nickname: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="昵称",
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="个人简介",
    )

    # 社交链接
    website: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="个人网站",
    )
    github: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="GitHub 主页",
    )
    qq: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="QQ 号（可选，用于头像识别）",
    )
    avatar_source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="auto",
        server_default="auto",
        comment="头像来源：auto/custom/github/qq/gravatar",
    )

    # 头衔
    title_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("user_titles.id", ondelete="SET NULL"),
        nullable=True,
        comment="头衔ID",
    )
    title: Mapped[UserTitle | None] = relationship(
        "UserTitle",
        back_populates="users",
        doc="用户头衔",
    )

    # 权限状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活",
    )
    is_staff: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为管理员",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为超级管理员",
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否被封禁",
    )

    # 认证安全字段
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        index=True,
        comment="Refresh token 版本号，密码修改/重置时自增",
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="账号锁定到期时间（失败次数过多时）",
    )
    notify_by_email: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="是否接收邮件通知",
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        comment="失败登录次数，自动到期清空",
    )

    # 时间戳
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    # 关系
    posts: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="author",
        doc="用户发布的文章",
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="user",
        doc="用户的评论",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="recipient",
        foreign_keys="Notification.recipient_id",
        doc="收到的通知",
    )
    triggered_notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="actor",
        foreign_keys="Notification.actor_id",
        doc="触发的通知",
    )
    preferences: Mapped["UserPreference | None"] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        doc="用户偏好设置",
    )

    # 索引
    __table_args__ = (
        Index("ix_users_username_lower", func.lower(username)),
        Index("ix_users_email_lower", func.lower(email)),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"

    @property
    def display_name(self) -> str:
        """获取显示名称（优先昵称，否则用户名）"""
        return self.nickname or self.username

    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login = datetime.now(UTC)


class UserPreference(Base):
    """
    用户偏好设置模型

    存储用户的个性化设置。

    Attributes:
        id: 主键
        user_id: 用户ID（外键）
        public_profile: 是否公开个人资料
        theme: 主题偏好（light/dark/system）
        created_at: 创建时间
        updated_at: 更新时间

    Example:
        >>> preference = UserPreference(
        >>>     user_id=user.id,
        >>>     theme="dark",
        >>> )
    """

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="偏好设置ID",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="用户ID",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="preferences",
        doc="关联的用户",
    )

    # 偏好设置
    public_profile: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否公开个人资料",
    )
    show_email: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否显示邮箱",
    )
    show_posts: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否显示文章列表",
    )
    show_comments: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否显示评论列表",
    )
    show_stats: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否显示统计数据",
    )
    show_social_links: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否显示社交链接",
    )
    theme: Mapped[str] = mapped_column(
        String(20),
        default="light",
        nullable=False,
        comment="主题偏好",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<UserPreference(user_id={self.user_id}, theme='{self.theme}')>"


class RefreshToken(Base):
    """
    刷新令牌模型

    存储用户的刷新令牌，用于获取新的访问令牌。

    Attributes:
        id: 主键
        token: 刷新令牌（唯一）
        user_id: 用户ID（外键）
        expires_at: 过期时间
        revoked: 是否已撤销
        created_at: 创建时间

    Example:
        >>> refresh_token = RefreshToken(
        >>>     token="eyJhbGciOiJIUzI1NiIs...",
        >>>     user_id=user.id,
        >>>     expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        >>> )
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="令牌ID",
    )
    token: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True,
        comment="刷新令牌",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    user: Mapped["User"] = relationship(
        "User",
        doc="关联的用户",
    )

    # 令牌状态
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="过期时间",
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否已撤销",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    # 索引
    __table_args__ = (Index("ix_refresh_tokens_user_expires", user_id, expires_at),)

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """检查令牌是否已过期"""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """检查令牌是否有效（未过期且未撤销）"""
        return not self.revoked and not self.is_expired
