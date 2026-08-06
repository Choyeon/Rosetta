"""
博客相关数据模型

包含文章、分类、标签、评论等核心内容模型。

PostgreSQL 优化：
- 使用 JSONB 替代 JSON，支持 GIN 索引
- 添加复合索引优化查询性能
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    false,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.config import settings
from backend.core.database import Base

JSON_TYPE = JSONB if settings.is_postgresql else JSON

if TYPE_CHECKING:
    from backend.models.user import User


post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

post_likes = Table(
    "post_likes",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    """
    文章分类

    用于对文章进行归类，每个分类有唯一的 slug 用于 URL。
    支持多语言名称和描述。

    PostgreSQL 优化：使用 JSONB 存储多语言数据
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str] = mapped_column(String(20), default="primary", nullable=False)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="父分类 ID（层级分类）",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False,
        comment="是否启用（False 前台不展示）",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="category")

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side=[id], backref="children"
    )

    def __repr__(self) -> str:
        name = self.name.get("zh", "Unnamed") if self.name else "Unnamed"
        return f"<Category(id={self.id}, name='{name}')>"


class Tag(Base):
    """
    文章标签

    标签可以关联多篇文章，文章也可以有多个标签。
    支持多语言名称。

    PostgreSQL 优化：使用 JSONB 存储多语言数据
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(20), default="#64748B", nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    posts: Mapped[list["Post"]] = relationship("Post", secondary=post_tags, back_populates="tags")

    def __repr__(self) -> str:
        name = self.name.get("zh", "Unnamed") if self.name else "Unnamed"
        return f"<Tag(id={self.id}, name='{name}')>"


class Post(Base):
    """
    文章模型

    博客的核心内容，支持 Markdown 格式、分类、标签、评论等功能。
    支持多语言标题、内容、摘要等字段。

    PostgreSQL 优化：
    - 使用 JSONB 替代 JSON，支持 GIN 索引
    - 添加复合索引优化常见查询
    """

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    subtitle: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), default="原创", nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    audio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    content: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    excerpt: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)

    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author: Mapped["User"] = relationship("User", back_populates="posts")

    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[Category | None] = relationship("Category", back_populates="posts")

    tags: Mapped[list[Tag]] = relationship("Tag", secondary=post_tags, back_populates="posts")
    likes: Mapped[list["User"]] = relationship("User", secondary=post_likes, backref="liked_posts")

    status: Mapped[str] = mapped_column(String(10), default="draft", nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(String(10), default="public", nullable=False)
    password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    meta_title: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    meta_description: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    meta_keywords: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)

    # 文章系列
    series_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("post_series.id", ondelete="SET NULL"), nullable=True, index=True
    )
    series_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 内容加密：存储需要密码访问的加密内容（AES加密后base64）
    encrypted_content: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    encryption_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    encryption_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    encryption_salt: Mapped[str | None] = mapped_column(String(128), nullable=True)
    encryption_verifier: Mapped[str | None] = mapped_column(String(256), nullable=True)
    encryption_algorithm: Mapped[str] = mapped_column(
        String(50), default="AES-256-GCM", nullable=False
    )

    # 定时发布
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_posts_status_created", "status", "created_at"),
        Index("ix_posts_status_published", "status", "published_at"),
        Index("ix_posts_status_pinned_published", "status", "is_pinned", "published_at"),
        Index("ix_posts_title_gin", "title", postgresql_using="gin"),
        Index("ix_posts_content_gin", "content", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        title = self.title.get("zh", "Untitled") if self.title else "Untitled"
        return f"<Post(id={self.id}, title='{title}')>"


class Comment(Base):
    """
    评论模型

    支持游客与登录用户评论、1 层嵌套回复、审核工作流、点赞、置顶。
    记录脱敏 IP 与 User-Agent，配合敏感词过滤与频控。

    PostgreSQL 优化：复合索引加速"某文章按时间取审核后评论"等常见查询
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post: Mapped["Post"] = relationship("Post", back_populates="comments")

    user_id: Mapped[int | None] = mapped_column(
        # 用户删除 → 保留评论作为「匿名」内容继续展示；禁止 CASCADE 误删
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user: Mapped["User | None"] = relationship("User", back_populates="comments")

    parent_id: Mapped[int | None] = mapped_column(
        # 父评论删除 → 子评论提升为根评论（parent_id=NULL），不丢回复内容
        Integer, ForeignKey("comments.id", ondelete="SET NULL"), nullable=True
    )
    parent: Mapped["Comment | None"] = relationship("Comment", remote_side=[id], backref="replies")

    author_name: Mapped[str] = mapped_column(String(30), nullable=False)
    author_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    author_website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    author_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    author_user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    qq: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True, comment="评论者 QQ（可选，游客填）"
    )
    github: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="评论者 GitHub 用户名（可选，游客填）"
    )
    avatar_source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="auto", server_default="auto",
        comment="头像来源：auto/custom/github/qq/gravatar",
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending", index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_comments_post_status_created", "post_id", "status", "created_at"),
        Index("ix_comments_parent", "parent_id"),
        Index("ix_comments_author_ip_created", "author_ip", "created_at"),
        Index("ix_comments_post_active", "post_id", "active"),
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, post_id={self.post_id}, status={self.status})>"


class PostViewHistory(Base):
    """
    文章阅读历史

    记录用户的阅读历史，用于"最近阅读"功能。
    """

    __tablename__ = "post_view_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User")

    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    post: Mapped["Post"] = relationship("Post")

    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_post_view_histories_user_post", "user_id", "post_id", unique=True),)

    def __repr__(self) -> str:
        return f"<PostViewHistory(user_id={self.user_id}, post_id={self.post_id})>"
