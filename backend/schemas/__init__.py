"""
Rosetta FastAPI 后端 - Pydantic Schemas

定义所有 API 请求和响应的数据模型，包括：
- 请求验证
- 响应序列化
- 数据转换
- 多语言支持

Example:
    >>> from backend.schemas import UserCreate, UserResponse
    >>>
    >>> user_data = UserCreate(
    >>>     username="admin",
    >>>     email="admin@example.com",
    >>>     password="SecurePassword123",
    >>> )
"""

import re
from datetime import datetime
from typing import Any, Dict, Generic, List, Literal, TypeVar

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from backend.core.i18n import LANGUAGE_CODES, get_i18n_value, normalize_language
from backend.schemas.activity import (
    ActivityBase,
    ActivityCreate,
    ActivityLocalizedResponse,
    ActivityResponse,
    ActivityType,
    ActivityUpdate,
)
from backend.schemas.announcement import (
    AnnouncementBase,
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementType,
    AnnouncementUpdate,
)
from backend.schemas.gallery import (
    AlbumCreate,
    AlbumDetailResponse,
    AlbumResponse,
    AlbumUpdate,
    PhotoCreate,
    PhotoResponse,
    PhotoUpdate,
)

T = TypeVar("T")


# ==================== 基础响应模型 ====================


class BaseResponse(BaseModel):
    """
    基础响应模型

    用于简单的操作结果返回。

    Attributes:
        success: 操作是否成功
        message: 响应消息
    """

    success: bool = True
    message: str = "操作成功"


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模型

    用于返回分页数据。

    Attributes:
        items: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        total_pages: 总页数
    """

    items: list[T]
    total: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, le=100, description="每页大小")
    total_pages: int = Field(..., ge=0, description="总页数")


class TokenResponse(BaseModel):
    """
    令牌响应模型

    用于登录成功后返回认证令牌。

    Attributes:
        access_token: 访问令牌
        refresh_token: 刷新令牌
        token_type: 令牌类型
        expires_in: 过期时间（秒）
    """

    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class LoginRequest(BaseModel):
    """
    登录请求模型

    Attributes:
        username: 用户名或邮箱
        password: 密码
    """

    username: str = Field(..., min_length=1, max_length=254, description="用户名或邮箱")
    password: str = Field(..., min_length=1, max_length=128, description="密码")


# ==================== 用户相关模型 ====================


class UserBase(BaseModel):
    """
    用户基础模型

    包含用户的基本信息字段。
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=150,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="用户名（只允许字母、数字、下划线和连字符）",
    )
    email: EmailStr = Field(..., description="邮箱地址")
    nickname: str | None = Field(None, max_length=50, description="昵称")
    bio: str | None = Field(None, max_length=500, description="个人简介")
    website: str | None = Field(None, max_length=200, description="个人网站")
    github: str | None = Field(None, max_length=200, description="GitHub 主页")
    qq: str | None = Field(None, max_length=20, description="QQ 号（可选，用于头像识别）")
    avatar_source: Literal["auto","custom","github","qq","gravatar"] = Field("auto", description="头像来源")

    @field_validator("website", "github")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """验证 URL 格式"""
        if v and not v.startswith(("http://", "https://")):
            return f"https://{v}"
        return v


class UserCreate(UserBase):
    """
    用户创建模型

    用于用户注册。
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="密码（至少8位，包含大小写字母和数字）",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度必须至少 8 个字符")
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        return v


class UserUpdate(BaseModel):
    """
    用户更新模型

    用于更新用户信息。
    """

    nickname: str | None = Field(None, max_length=50)
    bio: str | None = Field(None, max_length=500)
    website: str | None = Field(None, max_length=200)
    github: str | None = Field(None, max_length=200)
    qq: str | None = Field(None, max_length=20)
    avatar_source: Literal["auto","custom","github","qq","gravatar"] | None = None
    avatar: str | None = Field(None, max_length=500)
    cover_image: str | None = Field(None, max_length=500)


class AdminUserUpdate(BaseModel):
    """
    管理员更新用户模型

    用于管理员更新用户状态。
    """

    is_staff: bool | None = None
    is_banned: bool | None = None
    qq: str | None = Field(None, max_length=20)
    github: str | None = Field(None, max_length=200)
    website: str | None = Field(None, max_length=200)
    avatar_source: Literal["auto","custom","github","qq","gravatar"] | None = None
    avatar: str | None = Field(None, max_length=500)


class UserResponse(UserBase):
    """
    用户响应模型

    用于返回用户信息。
    """

    id: int
    avatar: str | None = None
    cover_image: str | None = None
    is_active: bool
    is_staff: bool
    is_superuser: bool
    title: "UserTitleResponse | None" = None
    qq: str | None = None
    github: str | None = None
    website: str | None = None
    avatar_source: str | None = None
    resolved_avatar_url: str | None = None
    created_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class UserTitleResponse(BaseModel):
    """
    用户头衔响应模型
    """

    id: int
    name: str
    color: str
    icon: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class UserPreferenceResponse(BaseModel):
    """
    用户偏好设置响应模型
    """

    public_profile: bool
    show_email: bool
    show_posts: bool
    show_comments: bool
    show_stats: bool
    theme: str

    model_config = {"from_attributes": True}


class UserPreferenceUpdate(BaseModel):
    """
    用户偏好设置更新模型
    """

    public_profile: bool | None = None
    show_email: bool | None = None
    show_posts: bool | None = None
    show_comments: bool | None = None
    show_stats: bool | None = None
    theme: str | None = None


class PasswordChange(BaseModel):
    """
    修改密码请求模型

    用于用户修改自己的密码。
    """

    current_password: str = Field(..., min_length=1, description="当前密码")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密码（至少8位，包含大小写字母和数字）",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度必须至少 8 个字符")
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        return v


class PasswordReset(BaseModel):
    """
    重置密码请求模型

    用于管理员重置用户密码。
    """

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密码（至少8位，包含大小写字母和数字）",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度必须至少 8 个字符")
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        return v


class AdminUserCreate(BaseModel):
    """
    管理员创建用户模型

    用于管理员创建新用户。
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=150,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="用户名（只允许字母、数字、下划线和连字符）",
    )
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="密码（至少8位，包含大小写字母和数字）",
    )
    nickname: str | None = Field(None, max_length=50, description="昵称")
    bio: str | None = Field(None, max_length=500, description="个人简介")
    website: str | None = Field(None, max_length=200, description="个人网站")
    github: str | None = Field(None, max_length=200, description="GitHub 主页")
    is_staff: bool = Field(default=False, description="是否为管理员")
    is_active: bool = Field(default=True, description="是否激活")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度必须至少 8 个字符")
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        return v

    @field_validator("website", "github")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """验证 URL 格式"""
        if v and not v.startswith(("http://", "https://")):
            return f"https://{v}"
        return v


class AdminUserUpdateFull(BaseModel):
    """
    管理员完整更新用户模型

    用于管理员更新用户的所有信息。
    """

    username: str | None = Field(None, min_length=3, max_length=150, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr | None = None
    nickname: str | None = Field(None, max_length=50)
    bio: str | None = Field(None, max_length=500)
    website: str | None = Field(None, max_length=200)
    github: str | None = Field(None, max_length=200)
    avatar: str | None = Field(None, max_length=500)
    cover_image: str | None = Field(None, max_length=500)
    is_staff: bool | None = None
    is_active: bool | None = None
    is_banned: bool | None = None

    @field_validator("website", "github")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """验证 URL 格式"""
        if v and not v.startswith(("http://", "https://")):
            return f"https://{v}"
        return v


class UserDetailResponse(UserResponse):
    """
    用户详情响应模型

    包含更多详细信息，用于管理员查看。
    """

    bio: str | None = None
    website: str | None = None
    github: str | None = None
    qq: str | None = None
    avatar_source: str | None = None
    resolved_avatar_url: str | None = None
    posts_count: int = 0
    comments_count: int = 0
    is_banned: bool = False
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ==================== 分类相关模型 ====================


class CategoryBase(BaseModel):
    """
    分类基础模型
    """

    name: dict[str, str] = Field(
        ...,
        description="多语言分类名称，如 {'zh': '技术', 'en': 'Technology', 'ja': '技術', 'zh_Hant': '技術'}",
    )
    slug: str | None = Field(None, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: dict[str, str] | None = Field(None, description="多语言分类描述")
    icon: str | None = Field(None, max_length=50)
    color: str = Field(default="#3B82F6", max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v: str | None, info) -> str | None:
        """如果未提供 slug，则根据 name 的中文自动生成"""
        if v:
            return v
        if name := info.data.get("name"):
            zh_name = name.get("zh", "") if isinstance(name, dict) else str(name)
            if zh_name:
                return re.sub(r"[^a-z0-9]+", "-", zh_name.lower()).strip("-")
        return v


class CategoryCreate(CategoryBase):
    """分类创建模型"""

    pass


class CategoryUpdate(BaseModel):
    """分类更新模型"""

    name: dict[str, str] | None = None
    slug: str | None = Field(None, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: dict[str, str] | None = None
    icon: str | None = Field(None, max_length=50)
    color: str | None = Field(None, max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")
    cover_image: str | None = None


class CategoryResponse(BaseModel):
    """分类响应模型"""

    id: int
    name: dict[str, str]
    slug: str
    description: dict[str, str] | None = None
    icon: str | None = None
    color: str
    cover_image: str | None = None
    created_at: datetime
    post_count: int = 0

    model_config = {"from_attributes": True}


class CategoryLocalizedResponse(BaseModel):
    """
    分类本地化响应模型

    根据请求的语言返回对应语言的字段值
    """

    id: int
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    color: str
    cover_image: str | None = None
    created_at: datetime
    post_count: int = 0

    @classmethod
    def from_category(cls, category, lang: str = "zh") -> "CategoryLocalizedResponse":
        """从分类模型创建本地化响应"""
        return cls(
            id=category.id,
            name=get_i18n_value(category.name, lang),
            slug=category.slug,
            description=get_i18n_value(category.description, lang)
            if category.description
            else None,
            icon=category.icon,
            color=category.color,
            cover_image=category.cover_image,
            created_at=category.created_at,
            post_count=getattr(category, "post_count", 0),
        )


# ==================== 标签相关模型 ====================


class TagBase(BaseModel):
    """标签基础模型"""

    name: dict[str, str] = Field(..., description="多语言标签名称")
    slug: str | None = Field(None, max_length=100, pattern=r"^[a-z0-9-]+$")
    color: str = Field(default="#64748B", max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(None, max_length=50)
    is_active: bool = True


class TagCreate(TagBase):
    """标签创建模型"""

    pass


class TagUpdate(BaseModel):
    """标签更新模型"""

    name: dict[str, str] | None = None
    slug: str | None = Field(None, max_length=100)
    color: str | None = Field(None, max_length=20)
    icon: str | None = Field(None, max_length=50)
    is_active: bool | None = None


class TagResponse(BaseModel):
    """标签响应模型"""

    id: int
    name: dict[str, str]
    slug: str
    color: str
    icon: str | None = None
    is_active: bool
    created_at: datetime
    post_count: int = 0

    model_config = {"from_attributes": True}


class TagLocalizedResponse(BaseModel):
    """
    标签本地化响应模型

    根据请求的语言返回对应语言的字段值
    """

    id: int
    name: str
    slug: str
    color: str
    icon: str | None = None
    is_active: bool
    created_at: datetime
    post_count: int = 0

    @classmethod
    def from_tag(cls, tag, lang: str = "zh") -> "TagLocalizedResponse":
        """从标签模型创建本地化响应"""
        return cls(
            id=tag.id,
            name=get_i18n_value(tag.name, lang),
            slug=tag.slug,
            color=tag.color,
            icon=tag.icon,
            is_active=tag.is_active,
            created_at=tag.created_at,
            post_count=getattr(tag, "post_count", 0),
        )


# ==================== 文章相关模型 ====================


class PostBase(BaseModel):
    """文章基础模型"""

    title: dict[str, str] = Field(..., description="多语言文章标题")
    subtitle: dict[str, str] | None = Field(None, description="多语言副标题")
    slug: str | None = Field(None, max_length=200, pattern=r"^[a-z0-9-]+$")
    source: str = Field(default="原创", max_length=50)
    source_url: str | None = Field(None, max_length=500)
    content: dict[str, str] = Field(..., description="多语言文章内容")
    excerpt: dict[str, str] | None = Field(None, description="多语言摘要")
    cover_image: str | None = Field(None, max_length=500)
    category_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list)
    series_id: int | None = Field(None, description="所属系列 ID")
    series_order: int = Field(default=0, description="系列内排序")
    status: str = Field(default="draft", pattern="^(draft|published|scheduled)$")
    visibility: str = Field(
        default="public",
        pattern="^(public|password|private)$",
        max_length=10,
        description="可见性: public(公开)/password(密码保护)/private(私密仅作者可见)",
    )
    scheduled_at: datetime | None = Field(None, description="定时发布时间，status=scheduled 时生效")
    password: str | None = Field(None, max_length=100)
    view_password: str | None = Field(None, description="(保留字段，请勿使用明文)")
    encryption_enabled: bool = False
    encryption_salt: str | None = Field(None, max_length=128)
    encryption_verifier: str | None = Field(None, max_length=256)
    encryption_algorithm: str = Field(default="AES-256-GCM", max_length=50)
    encryption_hint: str | None = Field(None, max_length=200)
    is_pinned: bool = False
    allow_comments: bool = True
    meta_title: dict[str, str] | None = Field(None, description="多语言 SEO 标题")
    meta_description: dict[str, str] | None = Field(None, description="多语言 SEO 描述")
    meta_keywords: dict[str, str] | None = Field(None, description="多语言 SEO 关键词")


class PostCreate(PostBase):
    """文章创建模型"""

    pass


class PostUpdate(BaseModel):
    """文章更新模型"""

    title: dict[str, str] | None = None
    subtitle: dict[str, str] | None = None
    slug: str | None = Field(None, max_length=200)
    source: str | None = Field(None, max_length=50)
    source_url: str | None = None
    audio: str | None = None
    video: str | None = None
    video_url: str | None = None
    content: dict[str, str] | None = None
    excerpt: dict[str, str] | None = None
    cover_image: str | None = None
    category_id: int | None = None
    tag_ids: list[int] | None = None
    series_id: int | None = None
    series_order: int | None = None
    status: str | None = Field(None, pattern="^(draft|published|scheduled)$")
    visibility: str | None = Field(
        None, pattern="^(public|password|private)$", max_length=10
    )
    scheduled_at: datetime | None = None
    password: str | None = None
    view_password: str | None = None
    encryption_enabled: bool | None = None
    encryption_salt: str | None = Field(None, max_length=128)
    encryption_verifier: str | None = Field(None, max_length=256)
    encryption_algorithm: str | None = Field(None, max_length=50)
    encryption_hint: str | None = Field(None, max_length=200)
    is_pinned: bool | None = None
    allow_comments: bool | None = None
    meta_title: dict[str, str] | None = None
    meta_description: dict[str, str] | None = None
    meta_keywords: dict[str, str] | None = None


class BatchPostStatusUpdate(BaseModel):
    post_ids: list[int] = Field(..., min_length=1)
    status: Literal["draft", "published", "scheduled"]


class BatchPostStatusResponse(BaseResponse):
    data: dict[str, int]


class PostResponse(BaseModel):
    """文章响应模型"""

    id: int
    title: dict[str, str]
    subtitle: dict[str, str] | None = None
    slug: str
    source: str
    source_url: str | None = None
    audio: str | None = None
    video: str | None = None
    video_url: str | None = None
    content: dict[str, str]
    excerpt: dict[str, str] | None = None
    cover_image: str | None = None
    author: UserResponse
    category: CategoryResponse | None = None
    tags: list[TagResponse] = []
    status: str
    visibility: str
    views: int
    likes_count: int = 0
    is_pinned: bool
    allow_comments: bool
    comments_count: int = 0
    meta_title: dict[str, str] | None = None
    meta_description: dict[str, str] | None = None
    meta_keywords: dict[str, str] | None = None
    created_at: datetime
    published_at: datetime | None = None
    updated_at: datetime
    reading_time: int = 1

    model_config = {"from_attributes": True}


class PostEditResponse(BaseModel):
    """
    文章编辑响应模型

    返回完整的多语言内容，用于文章编辑场景
    """

    id: int
    title: dict[str, str]
    subtitle: dict[str, str] | None = None
    slug: str
    source: str
    source_url: str | None = None
    audio: str | None = None
    video: str | None = None
    video_url: str | None = None
    content: dict[str, str]
    excerpt: dict[str, str] | None = None
    cover_image: str | None = None
    status: str
    visibility: str
    has_password: bool = False
    published_at: datetime | None = None
    category: dict[str, Any] | None = None
    tags: list[dict[str, Any]] = []
    is_pinned: bool
    allow_comments: bool
    meta_description: dict[str, str] | None = None
    meta_title: dict[str, str] | None = None
    meta_keywords: dict[str, str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_post(cls, post) -> "PostEditResponse":
        """从文章模型创建编辑响应"""
        category = None
        if post.category:
            category = {"id": post.category.id}

        tags = [{"id": tag.id} for tag in post.tags]

        return cls(
            id=post.id,
            title=post.title or {},
            subtitle=post.subtitle,
            slug=post.slug or "",
            source=post.source or "原创",
            source_url=post.source_url,
            audio=post.audio,
            video=post.video,
            video_url=post.video_url,
            content=post.content or {},
            excerpt=post.excerpt,
            cover_image=post.cover_image,
            status=post.status or "draft",
            visibility=post.visibility or "public",
            has_password=bool(post.password),
            published_at=post.published_at,
            category=category,
            tags=tags,
            is_pinned=post.is_pinned or False,
            allow_comments=post.allow_comments if hasattr(post, "allow_comments") else True,
            meta_description=post.meta_description,
            meta_title=post.meta_title,
            meta_keywords=post.meta_keywords,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )


class PostLocalizedResponse(BaseModel):
    """
    文章本地化响应模型

    根据请求的语言返回对应语言的字段值
    """

    id: int
    title: str
    subtitle: str | None = None
    slug: str
    source: str
    source_url: str | None = None
    audio: str | None = None
    video: str | None = None
    video_url: str | None = None
    content: str
    excerpt: str | None = None
    cover_image: str | None = None
    author: UserResponse
    category: CategoryLocalizedResponse | None = None
    tags: list[TagLocalizedResponse] = []
    status: str
    visibility: str = "public"
    password: str | None = None
    views: int
    likes_count: int = 0
    is_pinned: bool
    allow_comments: bool
    comments_count: int = 0
    is_password_protected: bool = False
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    created_at: datetime
    published_at: datetime | None = None
    updated_at: datetime
    reading_time: int = 1

    @classmethod
    def from_post(
        cls, post, lang: str = "zh", likes_count: int = 0, comments_count: int = 0
    ) -> "PostLocalizedResponse":
        """从文章模型创建本地化响应"""
        category = None
        if post.category:
            category = CategoryLocalizedResponse.from_category(post.category, lang)

        tags = [TagLocalizedResponse.from_tag(tag, lang) for tag in post.tags]

        return cls(
            id=post.id,
            title=get_i18n_value(post.title, lang),
            subtitle=get_i18n_value(post.subtitle, lang) if post.subtitle else None,
            slug=post.slug,
            source=post.source,
            source_url=post.source_url,
            audio=post.audio,
            video=post.video,
            video_url=post.video_url,
            content=get_i18n_value(post.content, lang),
            excerpt=get_i18n_value(post.excerpt, lang) if post.excerpt else None,
            cover_image=post.cover_image,
            author=UserResponse.model_validate(post.author),
            category=category,
            tags=tags,
            status=post.status,
            views=post.views,
            likes_count=likes_count,
            is_pinned=post.is_pinned,
            allow_comments=post.allow_comments,
            comments_count=comments_count,
            meta_title=get_i18n_value(post.meta_title, lang) if post.meta_title else None,
            meta_description=get_i18n_value(post.meta_description, lang)
            if post.meta_description
            else None,
            meta_keywords=get_i18n_value(post.meta_keywords, lang) if post.meta_keywords else None,
            created_at=post.created_at,
            published_at=post.published_at,
            updated_at=post.updated_at,
            reading_time=cls._calculate_reading_time(get_i18n_value(post.content, lang)),
        )

    @staticmethod
    def _calculate_reading_time(content: str) -> int:
        """计算阅读时间（分钟）"""
        if not content:
            return 1
        word_count = len(content)
        return max(1, word_count // 500)


class PostListItem(BaseModel):
    """文章列表项模型"""

    id: int
    title: dict[str, str]
    subtitle: dict[str, str] | None = None
    slug: str
    excerpt: dict[str, str] | None = None
    cover_image: str | None = None
    author: UserResponse
    category: CategoryResponse | None = None
    tags: list[TagResponse] = []
    status: str
    views: int
    likes_count: int = 0
    is_pinned: bool
    created_at: datetime
    published_at: datetime | None = None
    reading_time: int = 1

    model_config = {"from_attributes": True}


class PostListItemLocalized(BaseModel):
    """文章列表项本地化模型"""

    id: int
    title: str
    subtitle: str | None = None
    slug: str
    excerpt: str | None = None
    cover_image: str | None = None
    author: UserResponse
    category: CategoryLocalizedResponse | None = None
    tags: list[TagLocalizedResponse] = []
    status: str
    views: int
    likes_count: int = 0
    comments_count: int = 0
    is_pinned: bool
    created_at: datetime
    published_at: datetime | None = None
    reading_time: int = 1

    @classmethod
    def from_post(cls, post, lang: str = "zh", comments_count: int = 0) -> "PostListItemLocalized":
        """从文章模型创建本地化列表项"""
        category = None
        if post.category:
            category = CategoryLocalizedResponse.from_category(post.category, lang)

        tags = [TagLocalizedResponse.from_tag(tag, lang) for tag in post.tags]

        excerpt = get_i18n_value(post.excerpt, lang) if post.excerpt else None

        return cls(
            id=post.id,
            title=get_i18n_value(post.title, lang),
            subtitle=get_i18n_value(post.subtitle, lang) if post.subtitle else None,
            slug=post.slug,
            excerpt=excerpt,
            cover_image=post.cover_image,
            author=UserResponse.model_validate(post.author),
            category=category,
            tags=tags,
            status=post.status,
            views=post.views,
            likes_count=len(post.likes) if post.likes else 0,
            comments_count=comments_count,
            is_pinned=post.is_pinned,
            created_at=post.created_at,
            published_at=post.published_at,
            reading_time=1,
        )


# ==================== 归档相关模型 ====================


class ArchivePostItem(BaseModel):
    """归档文章项模型"""

    id: int
    title: str
    slug: str
    created_at: datetime
    category: CategoryLocalizedResponse | None = None
    views: int = 0

    model_config = {"from_attributes": True}


class ArchiveMonthGroup(BaseModel):
    """归档月份分组模型"""

    year: int
    month: int
    count: int
    posts: list[ArchivePostItem]


class ArchiveYearGroup(BaseModel):
    """归档年份分组模型"""

    year: int
    count: int
    months: list[ArchiveMonthGroup]


# ==================== 评论相关模型 ====================


class CommentBase(BaseModel):
    """评论基础模型"""

    content: str = Field(..., min_length=2, max_length=3000)
    parent_id: int | None = None
    author_name: str | None = Field(None, min_length=2, max_length=30)
    author_email: EmailStr | None = Field(None, max_length=254)
    author_website: str | None = Field(None, max_length=200)
    hcaptcha_token: str | None = None

    @field_validator("author_website")
    @classmethod
    def _validate_website(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("网站必须以 http:// 或 https:// 开头")
        if len(v) > 200:
            raise ValueError("网站长度不能超过 200 字符")
        return v


class CommentCreate(CommentBase):
    """评论创建模型（游客或登录用户均可使用）"""

    qq: str | None = Field(None, max_length=20, description="评论者 QQ（可选）")
    github: str | None = Field(None, max_length=64, description="评论者 GitHub 用户名（可选）")
    # 与 ORM Comment.avatar_source 字段和对外 API 请求体保持一致；
    # 同时保留 author_avatar_source 作为向后兼容别名（deprecated）
    avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] = Field(
        "auto", description="头像来源"
    )
    author_avatar_source: (
        Literal["auto", "custom", "github", "qq", "gravatar"] | None
    ) = Field(
        None,
        description="【已废弃】请使用 avatar_source；旧调用方兼容位，若为非 None 会覆盖 avatar_source",
    )

    @model_validator(mode="after")
    def _merge_avatar_source_aliases(self) -> "CommentCreate":
        if self.author_avatar_source is not None and self.avatar_source == "auto":
            self.avatar_source = self.author_avatar_source  # type: ignore[assignment]
        return self


class CommentResponse(BaseModel):
    """评论响应模型（对外公开，已脱敏）"""

    id: int
    post_id: int
    user_id: int | None = None
    parent_id: int | None = None
    author_name: str
    author_avatar: str = ""
    author_website: str | None = None
    qq: str | None = None
    github: str | None = None
    avatar_source: str | None = None
    resolved_avatar_url: str | None = None
    content: str
    status: str = "pending"
    is_pinned: bool = False
    likes_count: int = 0
    reply_total: int = 0
    created_at: datetime
    replies: list["CommentResponse"] = []

    # 管理员视图扩展字段（前端 AdminCommentList 直接读取，可 None）
    post_ref: dict | None = None
    parent_ref: dict | None = None
    user_ref: dict | None = None

    model_config = {"from_attributes": True}


class CommentPagedResponse(BaseModel):
    """分页评论列表响应"""

    items: list[CommentResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)


class CommentBatchAction(BaseModel):
    """管理员批量评论操作"""

    ids: list[int] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(approve|reject|spam|delete)$")


# ==================== 页面相关模型 ====================


class PageBase(BaseModel):
    """页面基础模型"""

    title: dict[str, str] = Field(..., description="多语言页面标题")
    slug: str = Field(..., max_length=200, pattern=r"^[a-z0-9-]+$")
    content: dict[str, str] = Field(..., description="多语言页面内容")
    status: str = Field(default="published", pattern="^(draft|published)$")


class PageCreate(PageBase):
    """页面创建模型"""

    pass


class PageUpdate(BaseModel):
    """页面更新模型"""

    title: dict[str, str] | None = None
    slug: str | None = Field(None, max_length=200)
    content: dict[str, str] | None = None
    status: str | None = Field(None, pattern="^(draft|published)$")


class PageResponse(BaseModel):
    """页面响应模型"""

    id: int
    title: dict[str, str]
    slug: str
    content: dict[str, str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PageLocalizedResponse(BaseModel):
    """页面本地化响应模型"""

    id: int
    title: str
    slug: str
    content: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_page(cls, page, lang: str = "zh") -> "PageLocalizedResponse":
        """从页面模型创建本地化响应"""
        return cls(
            id=page.id,
            title=get_i18n_value(page.title, lang),
            slug=page.slug,
            content=get_i18n_value(page.content, lang),
            status=page.status,
            created_at=page.created_at,
            updated_at=page.updated_at,
        )


# ==================== 导航相关模型 ====================


class NavigationBase(BaseModel):
    """导航基础模型"""

    title: dict[str, str] = Field(..., description="多语言导航标题")
    url: str = Field(..., max_length=200)
    icon: str | None = Field(None, max_length=100, description="图标名称")
    parent_id: int | None = Field(None, description="父导航ID")
    location: str = Field(default="header", pattern="^(header|footer|sidebar)$")
    order: int = Field(default=0, ge=0)
    is_active: bool = True
    target_blank: bool = False


class NavigationCreate(NavigationBase):
    """导航创建模型"""

    pass


class NavigationUpdate(BaseModel):
    """导航更新模型"""

    title: dict[str, str] | None = None
    url: str | None = Field(None, max_length=200)
    icon: str | None = Field(None, max_length=100)
    parent_id: int | None = None
    location: str | None = Field(None, pattern="^(header|footer|sidebar)$")
    order: int | None = Field(None, ge=0)
    is_active: bool | None = None
    target_blank: bool | None = None


class NavigationResponse(BaseModel):
    """导航响应模型"""

    id: int
    title: dict[str, str]
    url: str
    icon: str | None = None
    parent_id: int | None = None
    location: str
    order: int
    is_active: bool
    target_blank: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class NavigationLocalizedResponse(BaseModel):
    """导航本地化响应模型"""

    id: int
    title: str
    url: str
    location: str
    order: int
    is_active: bool
    target_blank: bool
    created_at: datetime

    @classmethod
    def from_navigation(cls, nav, lang: str = "zh") -> "NavigationLocalizedResponse":
        """从导航模型创建本地化响应"""
        return cls(
            id=nav.id,
            title=get_i18n_value(nav.title, lang),
            url=nav.url,
            location=nav.location,
            order=nav.order,
            is_active=nav.is_active,
            target_blank=nav.target_blank,
            created_at=nav.created_at,
        )


# ==================== 友情链接相关模型 ====================


class FriendLinkBase(BaseModel):
    """友情链接基础模型"""

    name: dict[str, str] | str = Field(..., description="网站名称，支持字符串或多语言格式")
    url: str = Field(..., max_length=500)
    description: dict[str, str] | str | None = Field(
        None, description="网站描述，支持字符串或多语言格式"
    )
    logo: str | None = Field(None, max_length=500)
    order: int = Field(default=0, ge=0)
    is_active: bool = True
    target_blank: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_i18n_fields(cls, data):
        """将字符串字段转换为多语言格式"""
        if isinstance(data, dict):
            if "name" in data and isinstance(data["name"], str):
                data["name"] = {"zh": data["name"], "en": data["name"]}
            if "description" in data and isinstance(data["description"], str):
                data["description"] = {"zh": data["description"], "en": data["description"]}
        return data


class FriendLinkCreate(FriendLinkBase):
    """友情链接创建模型"""

    pass


class FriendLinkUpdate(BaseModel):
    """友情链接更新模型"""

    name: dict[str, str] | str | None = None
    url: str | None = Field(None, max_length=500)
    description: dict[str, str] | str | None = None
    logo: str | None = Field(None, max_length=500)
    order: int | None = Field(None, ge=0)
    is_active: bool | None = None
    target_blank: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_i18n_fields(cls, data):
        """将字符串字段转换为多语言格式"""
        if isinstance(data, dict):
            if "name" in data and isinstance(data["name"], str):
                data["name"] = {"zh": data["name"], "en": data["name"]}
            if "description" in data and isinstance(data["description"], str):
                data["description"] = {"zh": data["description"], "en": data["description"]}
        return data


class FriendLinkResponse(BaseModel):
    """友情链接响应模型"""

    id: int
    name: dict[str, str]
    url: str
    description: dict[str, str] | None = None
    logo: str | None = None
    order: int
    is_active: bool
    target_blank: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FriendLinkLocalizedResponse(BaseModel):
    """友情链接本地化响应模型"""

    id: int
    name: str
    url: str
    description: str | None = None
    logo: str | None = None
    order: int
    is_active: bool
    target_blank: bool
    created_at: datetime

    @classmethod
    def from_friend_link(cls, link, lang: str = "zh") -> "FriendLinkLocalizedResponse":
        """从友链模型创建本地化响应"""
        return cls(
            id=link.id,
            name=get_i18n_value(link.name, lang),
            url=link.url,
            description=get_i18n_value(link.description, lang) if link.description else None,
            logo=link.logo,
            order=link.order,
            is_active=link.is_active,
            target_blank=link.target_blank,
            created_at=link.created_at,
        )


# ==================== 通知相关模型 ====================


class NotificationResponse(BaseModel):
    """通知响应模型"""

    id: int
    title: dict[str, str]
    message: dict[str, str]
    level: str
    link: str | None = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationLocalizedResponse(BaseModel):
    """通知本地化响应模型"""

    id: int
    title: str
    message: str
    level: str
    link: str | None = None
    is_read: bool
    created_at: datetime

    @classmethod
    def from_notification(cls, notification, lang: str = "zh") -> "NotificationLocalizedResponse":
        """从通知模型创建本地化响应"""
        return cls(
            id=notification.id,
            title=get_i18n_value(notification.title, lang),
            message=get_i18n_value(notification.message, lang),
            level=notification.level,
            link=notification.link,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )


# ==================== 站点配置相关模型 ====================


class SiteConfigResponse(BaseModel):
    """站点配置响应模型"""

    # 基础信息
    site_name: str
    site_description: str
    site_keywords: str
    site_author: str
    site_email: str
    site_logo: str | None = None
    site_favicon: str | None = None
    site_icon: str | None = None

    # 页脚设置
    footer_text: str | None = None
    footer_slogan: str | None = None
    copyright_text: str | None = None
    icp_number: str | None = None
    police_icp_number: str | None = None

    # 社交媒体链接
    github_url: str | None = None
    x_url: str | None = None
    bilibili_url: str | None = None
    weibo_url: str | None = None
    zhihu_url: str | None = None
    youtube_url: str | None = None
    linkedin_url: str | None = None
    telegram_url: str | None = None

    # 联系方式
    contact_email: str | None = None
    contact_qq: str | None = None
    contact_wechat: str | None = None

    # 功能开关
    enable_comments: bool = True
    enable_registration: bool = True
    enable_rss_feed: bool = True
    enable_search: bool = True
    enable_sitemap: bool = True
    enable_guestbook: bool = True
    enable_dark_mode: bool = True
    enable_reading_time: bool = True
    enable_word_count: bool = True
    enable_like_button: bool = True
    enable_share_buttons: bool = True
    enable_toc: bool = True
    # OOBE 种子写的独立能力开关（与 settings_groups 字段并存，保证前端直接可用）
    enable_bing_wallpaper: bool = True
    enable_pagefind_search: bool = True
    enable_encrypted_posts: bool = False
    enable_music_player: bool = True
    # 兼容别名：前端有些地方读 enable_rss（与 enable_rss_feed 等价）
    enable_rss: bool = True
    # 默认封面图（OOBE 种子里写 default_cover_image）
    default_cover_image: str = ""

    # 分页设置
    pagination_page_size: int = 12
    pagination_max_page_size: int = 100

    # 外观设置
    code_theme: str = "github"
    code_theme_dark: str = "github-dark"
    default_theme: str = "system"
    primary_color: str = "#3B82F6"
    accent_color: str = "#0284C7"
    theme_primary: str = "#0EA5A9"
    theme_accent: str = "#0284C7"
    font_family: str | None = None
    default_og_image: str | None = None
    site_subtitle: str = ""

    # 维护模式
    maintenance_mode: bool = False
    maintenance_message: str | None = None
    maintenance_end_time: str | None = None

    # 默认图片
    default_post_cover: str | None = None
    default_avatar: str | None = None
    default_category_cover: str | None = None

    # SEO 设置
    google_analytics_id: str | None = None
    baidu_analytics_id: str | None = None
    google_site_verification: str | None = None
    baidu_site_verification: str | None = None
    robots_txt: str | None = None

    # 安全设置
    require_email_verification: bool = False
    allow_password_reset: bool = True
    session_timeout: int = 3600
    max_login_attempts: int = 5
    login_lockout_duration: int = 1800

    # 邮件设置（只读，不返回敏感信息）
    email_configured: bool = False
    email_from: str | None = None
    email_from_name: str | None = None

    # 文件上传设置
    max_upload_size: int = 10485760
    allowed_image_types: str = "jpg,jpeg,png,gif,webp,svg"
    allowed_file_types: str = "pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar"

    # 评论设置
    comment_require_approval: bool = False
    comment_allow_guest: bool = False
    comment_max_length: int = 1000
    comment_antispam: bool = True

    # 自定义代码
    custom_header_code: str | None = None
    custom_footer_code: str | None = None
    custom_css: str | None = None
    custom_js: str | None = None

    # 音乐播放器设置
    music_enabled: bool = True
    music_show_in_navbar: bool = True
    music_show_in_sidebar: bool = True
    music_mode: str = "meting"
    music_volume: float = 0.7
    music_play_mode: str = "list"
    music_show_lyrics: bool = True
    music_meting_api: str = ""
    music_meting_server: str = "netease"
    music_meting_type: str = "playlist"
    music_meting_id: str = ""

    # 壁纸/Banner设置
    wallpaper_mode: str = "banner"
    wallpaper_player_enable: bool = True
    wallpaper_desktop: str = ""
    wallpaper_mobile: str = ""
    wallpaper_video: str = ""
    wallpaper_use_bing: bool = True
    wallpaper_bing_days: int = 30
    wallpaper_dim_opacity: float = 0.2
    wallpaper_home_title: str = "Welcome"
    wallpaper_home_subtitle: str = ""

    # 关于页面内容（支持 Markdown）
    about_content: str = ""

    # 友链申请区域自定义 HTML 内容（留空则使用前端默认模板）
    friends_apply_html: str = ""

    # 作者/侧边栏资料设置
    author_name: str = ""
    author_bio: str = ""
    author_avatar: str = ""
    author_links_json: str = "[]"

    # 侧边栏卡片显隐设置
    sidebar_show_profile: bool = True
    sidebar_show_categories: bool = True
    sidebar_show_tags: bool = True
    sidebar_show_recent_posts: bool = True
    sidebar_show_recent_comments: bool = True
    sidebar_show_tag_cloud: bool = True
    sidebar_show_site_info: bool = True
    sidebar_show_music: bool = True
    sidebar_show_statistics: bool = True
    sidebar_show_dynamics: bool = True
    sidebar_widget_order: list[str] = [
        "profile",
        "site_info",
        "statistics",
        "dynamics",
        "music",
        "categories",
        "tags",
        "recent_posts",
        "recent_comments",
    ]

    # 站点URL和运行信息
    site_url: str = ""
    site_start_date: str = "2025-01-01"

    # 页脚自定义HTML
    footer_custom_html: str = ""

    # 友情链接页面配置
    friends_page_title: str = ""
    friends_page_description: str = ""
    friends_page_show_comment: bool = True
    friends_page_show_custom_content: bool = True

    # 动态页面配置
    dynamic_page_title: str = ""
    dynamic_page_description: str = ""
    dynamic_page_items_per_page: int = 10
    dynamic_page_show_comment: bool = True

    # 赞助页面配置
    sponsor_page_title: str = ""
    sponsor_page_description: str = ""
    sponsor_page_usage: str = ""
    sponsor_methods_json: str = "[]"
    sponsor_show_sponsors_list: bool = True
    sponsor_page_show_comment: bool = True

    # ========== 页面开关配置 ==========
    page_friends_enabled: bool = True
    page_sponsor_enabled: bool = True
    page_guestbook_enabled: bool = True
    page_bangumi_enabled: bool = True
    page_gallery_enabled: bool = True
    page_anime_enabled: bool = True
    page_dynamic_enabled: bool = True

    # ========== 导航栏显示配置 ==========
    category_bar_enabled: bool = True

    # ========== 归档页配置 ==========
    archive_fold_old_articles: bool = True

    # ========== 文章列表布局配置 ==========
    post_list_default_mode: str = "list"
    post_list_mobile_mode: str = "grid"
    post_list_description_lines: int = 2
    post_list_show_stats_icons: bool = True
    post_list_tags_position: str = "bottom"

    # ========== 文章详情页配置 ==========
    post_show_last_modified: bool = True
    post_outdated_threshold_days: int = 30
    post_enable_share_poster: bool = True
    post_generate_og_images: bool = False

    # ========== 封面图配置 ==========
    cover_enable_in_post: bool = True
    cover_enable_overlay: bool = True
    cover_show_loading: bool = False
    cover_random_enable: bool = False
    cover_random_apis_json: str = "[]"

    # ========== 许可证配置 ==========
    license_enable: bool = True
    license_name: str = "CC BY-NC-SA 4.0"
    license_url: str = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    license_icon: str = ""

    # ========== 评论系统配置 ==========
    comment_system_type: str = "none"
    comment_twikoo_env_id: str = ""
    comment_twikoo_lang: str = "zh-CN"
    comment_twikoo_visitor_count: bool = True
    comment_twikoo_js_url: str = "https://cdn.jsdelivr.net/npm/twikoo@1.7.14/dist/twikoo.min.js"
    comment_twikoo_css_url: str = ""
    comment_waline_server_url: str = ""
    comment_waline_lang: str = "zh-CN"
    comment_waline_emoji_json: str = '["https://unpkg.com/@waline/emojis@1.4.0/weibo","https://unpkg.com/@waline/emojis@1.4.0/bilibili"]'
    comment_waline_login_mode: str = "enable"
    comment_waline_visitor_count: bool = True
    comment_artalk_server: str = ""
    comment_artalk_locale: str = "zh-CN"
    comment_artalk_visitor_count: bool = True
    comment_giscus_repo: str = ""
    comment_giscus_repo_id: str = ""
    comment_giscus_category: str = "General"
    comment_giscus_category_id: str = ""
    comment_giscus_mapping: str = "title"
    comment_giscus_strict: str = "0"
    comment_giscus_reactions_enabled: str = "1"
    comment_giscus_emit_metadata: str = "1"
    comment_giscus_input_position: str = "top"
    comment_giscus_lang: str = "zh-CN"
    comment_giscus_loading: str = "lazy"
    comment_disqus_shortname: str = ""

    # ========== Bangumi配置 ==========
    bangumi_user_id: str = ""
    bangumi_mode: str = "dynamic"
    bangumi_api_url: str = "https://bgmapi.anibt.net"
    bangumi_subject_base_url: str = "https://bgmmi.anibt.net/subject/"
    bangumi_category_order_json: str = '["anime","book","music","game"]'

    # ========== 追番配置 ==========
    anime_bilibili_uid: str = ""
    anime_tmdb_api_key: str = ""
    anime_tmdb_list_id: str = ""

    # ========== 分页配置 ==========
    pagination_posts_per_page: int = 10

    # ========== 图像优化配置 ==========
    image_opt_formats: str = "webp"
    image_opt_quality: int = 85
    image_opt_no_referrer_json: str = '["*.hdslb.com","*.bilibili.com"]'

    # ========== 樱花特效配置 ==========
    sakura_enable: bool = False
    sakura_count: int = 21
    sakura_min_scale: float = 0.5
    sakura_max_scale: float = 1.1
    sakura_min_opacity: float = 0.3
    sakura_max_opacity: float = 0.9
    sakura_z_index: int = 100

    # ========== 看板娘/Spine模型配置 ==========
    pio_spine_enable: bool = False
    pio_spine_model_path: str = ""
    pio_spine_scale: float = 1.0
    pio_spine_position_corner: str = "bottom-left"
    pio_spine_width: int = 135
    pio_spine_height: int = 165
    pio_spine_z_index: int = 1000

    # ========== Mermaid图表配置 ==========
    mermaid_theme: str = "default"
    mermaid_security_level: str = "strict"

    # ========== PlantUML配置 ==========
    plantuml_server_url: str = "https://www.plantuml.com/plantuml"


class SiteConfigUpdate(BaseModel):
    """站点配置更新模型"""

    # 基础信息
    site_name: str | None = Field(None, max_length=100)
    site_description: str | None = Field(None, max_length=500)
    site_keywords: str | None = Field(None, max_length=500)
    site_author: str | None = Field(None, max_length=100)
    site_email: str | None = Field(None, max_length=200)
    site_logo: str | None = Field(None, max_length=500)
    site_favicon: str | None = Field(None, max_length=500)
    site_icon: str | None = Field(None, max_length=500)

    # 页脚设置
    footer_text: str | None = Field(None, max_length=500)
    footer_slogan: str | None = Field(None, max_length=200)
    copyright_text: str | None = Field(None, max_length=200)
    icp_number: str | None = Field(None, max_length=50)
    police_icp_number: str | None = Field(None, max_length=50)

    # 社交媒体链接
    github_url: str | None = Field(None, max_length=500)
    x_url: str | None = Field(None, max_length=500)
    bilibili_url: str | None = Field(None, max_length=500)
    weibo_url: str | None = Field(None, max_length=500)
    zhihu_url: str | None = Field(None, max_length=500)
    youtube_url: str | None = Field(None, max_length=500)
    linkedin_url: str | None = Field(None, max_length=500)
    telegram_url: str | None = Field(None, max_length=500)

    # 联系方式
    contact_email: str | None = Field(None, max_length=200)
    contact_qq: str | None = Field(None, max_length=50)
    contact_wechat: str | None = Field(None, max_length=100)

    # 功能开关
    enable_comments: bool | None = None
    enable_registration: bool | None = None
    enable_rss_feed: bool | None = None
    enable_search: bool | None = None
    enable_sitemap: bool | None = None
    enable_guestbook: bool | None = None
    enable_dark_mode: bool | None = None
    enable_reading_time: bool | None = None
    enable_word_count: bool | None = None
    enable_like_button: bool | None = None
    enable_share_buttons: bool | None = None
    enable_toc: bool | None = None

    # 分页设置
    pagination_page_size: int | None = Field(None, ge=1, le=100)
    pagination_max_page_size: int | None = Field(None, ge=10, le=500)

    # 外观设置
    code_theme: str | None = Field(None, max_length=50)
    code_theme_dark: str | None = Field(None, max_length=50)
    default_theme: str | None = Field(None, max_length=20)
    primary_color: str | None = Field(None, max_length=20)
    accent_color: str | None = Field(None, max_length=20)
    theme_primary: str | None = Field(None, max_length=20)
    theme_accent: str | None = Field(None, max_length=20)
    font_family: str | None = Field(None, max_length=100)
    default_og_image: str | None = Field(None, max_length=500)
    site_subtitle: str | None = Field(None, max_length=200)

    # 维护模式
    maintenance_mode: bool | None = None
    maintenance_message: str | None = Field(None, max_length=500)
    maintenance_end_time: str | None = Field(None, max_length=50)

    # 默认图片
    default_post_cover: str | None = Field(None, max_length=500)
    default_avatar: str | None = Field(None, max_length=500)
    default_category_cover: str | None = Field(None, max_length=500)

    # SEO 设置
    google_analytics_id: str | None = Field(None, max_length=50)
    baidu_analytics_id: str | None = Field(None, max_length=50)
    google_site_verification: str | None = Field(None, max_length=100)
    baidu_site_verification: str | None = Field(None, max_length=100)
    robots_txt: str | None = Field(None, max_length=5000)

    # 安全设置
    require_email_verification: bool | None = None
    allow_password_reset: bool | None = None
    session_timeout: int | None = Field(None, ge=300, le=86400)
    max_login_attempts: int | None = Field(None, ge=1, le=20)
    login_lockout_duration: int | None = Field(None, ge=60, le=86400)

    # 文件上传设置
    max_upload_size: int | None = Field(None, ge=1024, le=104857600)
    allowed_image_types: str | None = Field(None, max_length=500)
    allowed_file_types: str | None = Field(None, max_length=500)

    # 评论设置
    comment_require_approval: bool | None = None
    comment_allow_guest: bool | None = None
    comment_max_length: int | None = Field(None, ge=100, le=10000)
    comment_antispam: bool | None = None

    # 自定义代码
    custom_header_code: str | None = Field(None, max_length=10000)
    custom_footer_code: str | None = Field(None, max_length=10000)
    custom_css: str | None = Field(None, max_length=50000)
    custom_js: str | None = Field(None, max_length=50000)

    # 音乐播放器设置
    music_enabled: bool | None = None
    music_show_in_navbar: bool | None = None
    music_show_in_sidebar: bool | None = None
    music_mode: str | None = Field(None, max_length=20)
    music_volume: float | None = Field(None, ge=0, le=1)
    music_play_mode: str | None = Field(None, max_length=20)
    music_show_lyrics: bool | None = None
    music_meting_api: str | None = Field(None, max_length=500)
    music_meting_server: str | None = Field(None, max_length=20)
    music_meting_type: str | None = Field(None, max_length=20)
    music_meting_id: str | None = Field(None, max_length=100)

    # 壁纸/Banner设置
    wallpaper_mode: str | None = Field(None, max_length=20)
    wallpaper_player_enable: bool | None = None
    wallpaper_desktop: str | None = Field(None, max_length=1000)
    wallpaper_mobile: str | None = Field(None, max_length=1000)
    wallpaper_video: str | None = Field(None, max_length=1000)
    wallpaper_use_bing: bool | None = None
    wallpaper_bing_days: int | None = Field(None, ge=1, le=30)
    wallpaper_dim_opacity: float | None = Field(None, ge=0, le=1)
    wallpaper_home_title: str | None = Field(None, max_length=200)
    wallpaper_home_subtitle: str | None = Field(None, max_length=500)

    # 关于页面内容
    about_content: str | None = Field(None, max_length=50000)

    # 友链申请区域自定义 HTML 内容
    friends_apply_html: str | None = Field(None, max_length=50000)

    # 站点URL和运行信息
    site_url: str | None = Field(None, max_length=500)
    site_start_date: str | None = Field(None, max_length=20)

    # 页脚自定义HTML
    footer_custom_html: str | None = Field(None, max_length=50000)

    # 友情链接页面配置
    friends_page_title: str | None = Field(None, max_length=200)
    friends_page_description: str | None = Field(None, max_length=500)
    friends_page_show_comment: bool | None = None
    friends_page_show_custom_content: bool | None = None

    # 动态页面配置
    dynamic_page_title: str | None = Field(None, max_length=200)
    dynamic_page_description: str | None = Field(None, max_length=500)
    dynamic_page_items_per_page: int | None = Field(None, ge=1, le=100)
    dynamic_page_show_comment: bool | None = None

    # 赞助页面配置
    sponsor_page_title: str | None = Field(None, max_length=200)
    sponsor_page_description: str | None = Field(None, max_length=500)
    sponsor_page_usage: str | None = Field(None, max_length=2000)
    sponsor_methods_json: str | None = Field(None, max_length=50000)
    sponsor_show_sponsors_list: bool | None = None
    sponsor_page_show_comment: bool | None = None

    # ========== 页面开关配置 ==========
    page_friends_enabled: bool | None = None
    page_sponsor_enabled: bool | None = None
    page_guestbook_enabled: bool | None = None
    page_bangumi_enabled: bool | None = None
    page_gallery_enabled: bool | None = None
    page_anime_enabled: bool | None = None
    page_dynamic_enabled: bool | None = None

    # ========== 导航栏显示配置 ==========
    category_bar_enabled: bool | None = None

    # ========== 归档页配置 ==========
    archive_fold_old_articles: bool | None = None

    # ========== 文章列表布局配置 ==========
    post_list_default_mode: str | None = Field(None, max_length=50)
    post_list_mobile_mode: str | None = Field(None, max_length=50)
    post_list_description_lines: int | None = None
    post_list_show_stats_icons: bool | None = None
    post_list_tags_position: str | None = Field(None, max_length=50)

    # ========== 文章详情页配置 ==========
    post_show_last_modified: bool | None = None
    post_outdated_threshold_days: int | None = None
    post_enable_share_poster: bool | None = None
    post_generate_og_images: bool | None = None

    # ========== 封面图配置 ==========
    cover_enable_in_post: bool | None = None
    cover_enable_overlay: bool | None = None
    cover_show_loading: bool | None = None
    cover_random_enable: bool | None = None
    cover_random_apis_json: str | None = Field(None, max_length=50000)

    # ========== 许可证配置 ==========
    license_enable: bool | None = None
    license_name: str | None = Field(None, max_length=200)
    license_url: str | None = Field(None, max_length=500)
    license_icon: str | None = Field(None, max_length=500)

    # ========== 评论系统配置 ==========
    comment_system_type: str | None = Field(None, max_length=50)
    comment_twikoo_env_id: str | None = Field(None, max_length=200)
    comment_twikoo_lang: str | None = Field(None, max_length=50)
    comment_twikoo_visitor_count: bool | None = None
    comment_twikoo_js_url: str | None = Field(None, max_length=500)
    comment_twikoo_css_url: str | None = Field(None, max_length=500)
    comment_waline_server_url: str | None = Field(None, max_length=500)
    comment_waline_lang: str | None = Field(None, max_length=50)
    comment_waline_emoji_json: str | None = Field(None, max_length=50000)
    comment_waline_login_mode: str | None = Field(None, max_length=50)
    comment_waline_visitor_count: bool | None = None
    comment_artalk_server: str | None = Field(None, max_length=500)
    comment_artalk_locale: str | None = Field(None, max_length=50)
    comment_artalk_visitor_count: bool | None = None
    comment_giscus_repo: str | None = Field(None, max_length=200)
    comment_giscus_repo_id: str | None = Field(None, max_length=200)
    comment_giscus_category: str | None = Field(None, max_length=100)
    comment_giscus_category_id: str | None = Field(None, max_length=200)
    comment_giscus_mapping: str | None = Field(None, max_length=50)
    comment_giscus_strict: str | None = Field(None, max_length=10)
    comment_giscus_reactions_enabled: str | None = Field(None, max_length=10)
    comment_giscus_emit_metadata: str | None = Field(None, max_length=10)
    comment_giscus_input_position: str | None = Field(None, max_length=50)
    comment_giscus_lang: str | None = Field(None, max_length=50)
    comment_giscus_loading: str | None = Field(None, max_length=50)
    comment_disqus_shortname: str | None = Field(None, max_length=200)

    # ========== Bangumi配置 ==========
    bangumi_user_id: str | None = Field(None, max_length=200)
    bangumi_mode: str | None = Field(None, max_length=50)
    bangumi_api_url: str | None = Field(None, max_length=500)
    bangumi_subject_base_url: str | None = Field(None, max_length=500)
    bangumi_category_order_json: str | None = Field(None, max_length=50000)

    # ========== 追番配置 ==========
    anime_bilibili_uid: str | None = Field(None, max_length=200)
    anime_tmdb_api_key: str | None = Field(None, max_length=200)
    anime_tmdb_list_id: str | None = Field(None, max_length=200)

    # ========== 分页配置 ==========
    pagination_posts_per_page: int | None = None

    # ========== 图像优化配置 ==========
    image_opt_formats: str | None = Field(None, max_length=100)
    image_opt_quality: int | None = None
    image_opt_no_referrer_json: str | None = Field(None, max_length=50000)

    # ========== 樱花特效配置 ==========
    sakura_enable: bool | None = None
    sakura_count: int | None = None
    sakura_min_scale: float | None = None
    sakura_max_scale: float | None = None
    sakura_min_opacity: float | None = None
    sakura_max_opacity: float | None = None
    sakura_z_index: int | None = None

    # ========== 看板娘/Spine模型配置 ==========
    pio_spine_enable: bool | None = None
    pio_spine_model_path: str | None = Field(None, max_length=500)
    pio_spine_scale: float | None = None
    pio_spine_position_corner: str | None = Field(None, max_length=50)
    pio_spine_width: int | None = None
    pio_spine_height: int | None = None
    pio_spine_z_index: int | None = None

    # ========== Mermaid图表配置 ==========
    mermaid_theme: str | None = Field(None, max_length=50)
    mermaid_security_level: str | None = Field(None, max_length=50)

    # ========== PlantUML配置 ==========
    plantuml_server_url: str | None = Field(None, max_length=500)


class SiteSettingGroup(BaseModel):
    """站点设置分组"""

    name: str
    label: str
    description: str | None = None
    icon: str | None = None
    settings: list["SiteSettingItem"]


class SiteSettingItem(BaseModel):
    """站点设置项"""

    key: str
    label: str
    description: str | None = None
    type: str
    value: str | int | bool | float | None
    default: str | int | bool | float | None = None
    options: list[dict[str, str]] | None = None
    placeholder: str | None = None
    required: bool = False
    min_value: int | None = None
    max_value: int | None = None
    pattern: str | None = None


class SiteConfigFullResponse(BaseModel):
    """完整站点配置响应（包含分组信息）"""

    groups: list[SiteSettingGroup]
    last_updated: str | None = None


# ==================== 投票相关模型 ====================


class PollBase(BaseModel):
    """投票基础模型"""

    title: str = Field(..., max_length=200, min_length=1)
    description: str | None = Field(None, max_length=500)
    is_active: bool = True
    allow_multiple: bool = False
    show_results: bool = True


class PollCreate(PollBase):
    """投票创建模型"""

    choices: list[str] = Field(..., min_length=2, max_length=20)


class PollResponse(PollBase):
    """投票响应模型"""

    id: int
    choices: list["PollChoiceResponse"]
    total_votes: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PollChoiceResponse(BaseModel):
    """投票选项响应模型"""

    id: int
    text: str
    order: int
    votes_count: int = 0

    model_config = {"from_attributes": True}


class VoteCreate(BaseModel):
    """投票创建模型"""

    choice_ids: list[int] = Field(..., min_length=1)


# ==================== 留言板相关模型（Task 6 新版） ====================


class GuestbookEntryBase(BaseModel):
    """留言基础模型"""

    content: str = Field(..., min_length=2, max_length=3000)
    author_name: str | None = Field(None, min_length=2, max_length=30)
    author_email: EmailStr | None = Field(None, max_length=254)
    author_website: str | None = Field(None, max_length=200)

    @field_validator("author_website")
    @classmethod
    def _validate_website(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("网站必须以 http:// 或 https:// 开头")
        if len(v) > 200:
            raise ValueError("网站长度不能超过 200 字符")
        return v


class GuestbookEntryCreate(GuestbookEntryBase):
    """留言创建模型（游客或登录用户均可使用）"""

    qq: str | None = Field(None, max_length=20, description="评论者 QQ（可选）")
    github: str | None = Field(None, max_length=64, description="评论者 GitHub 用户名（可选）")
    author_avatar_source: Literal["auto","custom","github","qq","gravatar"] = Field("auto", description="头像来源")


class GuestbookEntryResponse(BaseModel):
    """留言响应模型（对外公开，已脱敏）"""

    id: int
    user_id: int | None = None
    author_name: str
    author_avatar: str = ""
    author_website: str | None = None
    qq: str | None = None
    github: str | None = None
    avatar_source: str | None = None
    resolved_avatar_url: str | None = None
    content: str
    status: str = "pending"
    is_pinned: bool = False
    is_featured: bool = False
    likes_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class GuestbookEntryPagedResponse(BaseModel):
    """分页留言列表响应"""

    items: list[GuestbookEntryResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)


class GuestbookBatchAction(BaseModel):
    """管理员批量留言操作"""

    ids: list[int] = Field(..., min_length=1, max_length=500)
    action: str = Field(
        ...,
        pattern="^(approve|reject|spam|pin|feature|trash|restore|delete)$",
    )


import sys as _sys  # noqa: E402

_STRICT_EXTRA_FORBID = {"strict": True, "extra": "forbid"}
for _name in list(globals().keys()):
    _obj = globals()[_name]
    if (
        isinstance(_obj, type)
        and issubclass(_obj, BaseModel)
        and _obj is not BaseModel
        and _obj.__module__ == _sys.modules[__name__].__name__
    ):
        _existing = _obj.model_config if isinstance(_obj.model_config, dict) else {}
        _merged = {**_existing, **_STRICT_EXTRA_FORBID}
        try:
            _obj.model_config = _merged
        except Exception:
            pass
    del _name, _obj


# 重建模型以解决循环引用
UserResponse.model_rebuild()
CommentResponse.model_rebuild()
PostResponse.model_rebuild()
PostLocalizedResponse.model_rebuild()
PostListItemLocalized.model_rebuild()
CategoryLocalizedResponse.model_rebuild()
TagLocalizedResponse.model_rebuild()
PageLocalizedResponse.model_rebuild()
NavigationLocalizedResponse.model_rebuild()
FriendLinkLocalizedResponse.model_rebuild()
NotificationLocalizedResponse.model_rebuild()
ActivityResponse.model_rebuild()
ActivityLocalizedResponse.model_rebuild()
