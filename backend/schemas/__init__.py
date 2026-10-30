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
# ruff: noqa: F401,E402  —— 整个文件是 schemas 统一再导出的 Hub；按功能分组 import 分布在多段。

import re
from datetime import datetime
from typing import Annotated, Any, Dict, Generic, List, Literal, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from backend.schemas._slug import CONTENT_SLUG_PATTERN

# 仅校验"格式合法"，不评判域名是否可解析 / 是否为 special-use 域名。
# Pydantic EmailStr 默认会做 DNS 可达性与 special-use 域名（.local / example.com 等）
# 校验，导致 UserResponse 等响应模型在序列化存储值（如 dev 环境的 .local 邮箱）时
# 抛 500，使后台用户列表整页崩溃。应用层只需要格式校验即可。
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _relaxed_email_validator(value: str) -> str:
    if not isinstance(value, str) or not _EMAIL_RE.match(value):
        raise ValueError("邮箱格式无效")
    return value


RelaxedEmailStr = Annotated[
    str,
    # User.email 是 String(254)。正则只保证格式，不保证长度；
    # 把上限并进类型本身，避免某个新端点漏写 max_length 而把超长邮箱写进库里
    # （MySQL 截断 / PostgreSQL·SQLite 长度约束报错，都是 500）。
    # 254 = RFC 5321 单段 path 上限，也是常见邮箱长度上限。
    StringConstraints(max_length=254),
    AfterValidator(_relaxed_email_validator),
]

from backend.core.i18n import LANGUAGE_CODES, get_i18n_value, normalize_language
from backend.models.core import FriendLink
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
from backend.schemas.extensions import (
    BulkOperationOut,
    PluginActivateIn,
    PluginBase,
    PluginBulkIn,
    PluginConfigIn,
    PluginInstallFrom,
    PluginOut,
    ThemeActivateIn,
    ThemeBase,
    ThemeModsIn,
    ThemeOut,
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


# ==================== 校验口径单源 ====================
# 下面三条规则原先各自内联在 4 份 password/new_password 与 5 份
# website/github/author_website 的 field_validator 里，逐字相同。改一次口径要动 9 个地方，
# 漏一处就出现"注册要求 8 位 + 大写、改密码只查长度"这类同字段不同 schema 互相判逆。
# 装饰器仍按 schema 声明（Pydantic 需要它绑定具体字段名），但**规则只在这里改**。

# 这两条叶子模块导入都要在**定义期**取值（field_validator 的装饰器要函数、字段注解要 `I18nDict`），
# 所以它们不能住在正在执行的包 __init__ 里：
# - `_url_policy` 是第三档（只挡可执行协议）规则的唯一清单，这里只做 re-export；
# - `_i18n_dict` 的口径与禁令见它自己的模块文档。
from backend.schemas._i18n_dict import I18nDict
from backend.schemas._url_policy import reject_pseudo_url_scheme as _reject_pseudo_url_scheme

# 访客身份字段（评论 / 留言板的 `qq` / `github`）的形态与头像解析器共用一份定义，
# 真源在 `backend/utils/ugc_fields.py`（理由见那里的注释）。
from backend.utils.ugc_fields import GITHUB_USERNAME_PATTERN as _GITHUB_USERNAME_PATTERN
from backend.utils.ugc_fields import QQ_PATTERN as _QQ_PATTERN


def _normalize_optional_url(v: str | None) -> str | None:
    """缺 scheme 的 URL 补 https://；空值原样返回。"""
    if v and not v.startswith(("http://", "https://")):
        return f"https://{v}"
    return v


def _require_absolute_url(v: str | None, *, max_len: int = 200) -> str | None:
    """**不补 scheme，直接拒**，并限长。

    与 `_normalize_optional_url` 是两条不同策略，不是重复实现：用户填的
    "example.com/a" 自动补成 https 会静默改写一个点不进任何地方的地址，而这里存下的
    链接是要渲染到访客页面上的，猜错 scheme 等于替作者伪造一条出站链接。注册资料走宽容档，
    公开展示的链接走严格档。

    `javascript:` / `data:` 这类伪协议只有在这一档才被挡住——它们不以 http 开头，
    宽容档会把它补成 `https://javascript:...`（无害但坏链），而严格档直接拒。
    凡是最终会进 `<a href>` 的列都要走这条口，写口的拒绝只是第一道，渲染侧还得再判一次
    （库里可能躺着绕过本 schema 写入的历史行，例如导入工具直接落 ORM）。

    默认 200 对应留言/评论的作者网站字段（字段本身也是 `max_length=200`，所以判不到；
    留着是给下一个不带长度约束的字段兜底，不要当成"已经校验过长度"）。
    """
    if v is None or v == "":
        return None
    if not v.startswith(("http://", "https://")):
        raise ValueError("链接必须以 http:// 或 https:// 开头")
    if len(v) > max_len:
        raise ValueError(f"链接长度不能超过 {max_len} 字符")
    return v


def _check_password_strength(v: str) -> str:
    """密码强度：至少 8 位，且含大写、小写与数字。"""
    if len(v) < 8:
        raise ValueError("密码长度必须至少 8 个字符")
    if not any(c.isupper() for c in v):
        raise ValueError("密码必须包含至少一个大写字母")
    if not any(c.islower() for c in v):
        raise ValueError("密码必须包含至少一个小写字母")
    if not any(c.isdigit() for c in v):
        raise ValueError("密码必须包含至少一个数字")
    return v


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


def raw_content_response(media_type: str, description: str, *, binary: bool = False) -> dict:
    """给"返回非 JSON 原文"的端点生成 `responses` 声明（只影响 OpenAPI，不改运行时行为）。

    RSS / Sitemap / 主题 CSS / 图片流 / 压缩包下载这些端点没有 JSON 模型可套，
    FastAPI 默认按 `application/json` 出文档，等于文档里根本查不到真实媒体类型。
    """
    schema = {"type": "string", "format": "binary"} if binary else {"type": "string"}
    return {200: {"description": description, "content": {media_type: {"schema": schema}}}}


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
    page_size: int = Field(..., ge=1, le=200, description="每页大小")
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
    email: RelaxedEmailStr = Field(..., description="邮箱地址")
    nickname: str | None = Field(None, max_length=50, description="昵称")
    bio: str | None = Field(None, max_length=500, description="个人简介")
    website: str | None = Field(None, max_length=200, description="个人网站")
    github: str | None = Field(None, max_length=200, description="GitHub 主页")
    qq: str | None = Field(None, max_length=20, description="QQ 号（可选，用于头像识别）")
    avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] = Field(
        "auto", description="头像来源"
    )

    @field_validator("website", "github")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """验证 URL 格式（口径单源见 _normalize_optional_url）"""
        return _normalize_optional_url(v)


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
        """验证密码强度（口径单源见 _check_password_strength）"""
        return _check_password_strength(v)


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
    avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] | None = None
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
    avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] | None = None
    avatar: str | None = Field(None, max_length=500)


class UserResponse(UserBase):
    """
    用户响应模型

    用于返回用户信息。
    """

    # 响应模型只用于序列化已存在的用户数据，不应拒绝历史上已写入的短用户名
    # （如 2 字符用户名），因此覆盖 UserBase 的输入级约束，避免列表/详情接口 500。
    username: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="用户名",
    )

    id: int
    avatar: str | None = None
    cover_image: str | None = None
    is_active: bool
    is_staff: bool
    is_superuser: bool
    role: str | None = None
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
    name: I18nDict
    color: str
    icon: str | None = None
    description: I18nDict | None = None

    model_config = {"from_attributes": True}


class PublicUserResponse(BaseModel):
    """
    公开作者卡片模型（用于文章 / 相册等资源的 ``author`` 字段）。

    与 :class:`UserResponse` 的差别就是本模型**没有**的那些字段：
    ``email``、``qq``、``is_active`` / ``is_staff`` / ``is_superuser``、``role``、``last_login``。
    这些字段曾经随每一次文章列表 / 详情响应公开下发，等于把全站作者的邮箱（可用于撞库与
    密码重置轰炸）以及"谁是管理员/超级用户"的映射白送给匿名爬虫——用户偏好里已经存在
    ``show_email`` 开关，说明邮箱本就按私密处理。后台与"我"的接口继续用
    :class:`UserResponse` / :class:`UserDetailResponse`，只有**挂在资源上的第三人作者信息**走这里。

    ``website`` / ``github`` 同样不在本模型里，理由与邮箱同族而更直接：偏好里有
    ``show_social_links``，而每一篇文章/动态/相册都内嵌这张卡片，读取口是匿名且带响应缓存的。
    把它留在这里等于给那个开关留一条"换个路由就绕过"的旁路（``apply_social_privacy`` 只管
    作者资料口），而全站没有任何消费方渲染 ``author.website`` / ``author.github``——
    社交链接的唯一展示面是作者主页 ``/authors/<username>``。

    新增字段前请先确认它对匿名访客无害。
    """

    id: int
    username: str
    nickname: str | None = None
    avatar: str | None = None
    cover_image: str | None = None
    bio: str | None = None
    avatar_source: str | None = None
    resolved_avatar_url: str | None = None
    title: UserTitleResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthorProfileResponse(PublicUserResponse):
    """第三人作者资料口（``GET /api/users/{user_id}``、``GET /api/users/username/{username}``）的投影。

    继承 :class:`PublicUserResponse` 而不是 :class:`UserResponse`，为的是**结构性地**拿掉
    ``qq`` / ``is_active`` / ``is_staff`` / ``is_superuser`` / ``role`` / ``last_login``：
    那六个字段属账号隐私与权限信息（``PublicUserResponse`` 的文档早已判明），但这两条口
    一直直接回 ``UserResponse``，于是"文章卡片不发的字段，换个路由照样摊给匿名爬虫"。
    线上实测（2026-10-30）匿名 ``GET /users/username/<作者>`` 原样回显真实 QQ 号、
    ``is_superuser: true`` 与 ``role: "super_admin"`` —— 前者是可直接联系的个人信息，
    后者等于替撞库与定向钓鱼标出管理员账号，``last_login`` 还会告诉外界这个账号何时活动过。

    只补三个**由隐私开关治理**的字段：``email``（``show_email``，默认拒绝，非本人非 staff 遮蔽）、
    ``website`` / ``github``（``show_social_links``，默认允许，关掉即 null 让整段不渲染）。
    ``email`` 保持必填是刻意的：服务层对"非本人 + 关了公开"返回的精简 dict 不含 email，
    一旦 ``_profile_is_hidden`` 闸门被放宽，缺失的必填字段会立刻 500 而不是静默回 null，
    把"隐私闸门没了"变成响亮的失败（口径同原 ``GET /users/{user_id}`` 的注释）。

    本模型的消费方只有前台 ``/authors/<username>``（``pages/authors/[username].vue``
    的 ``AuthorProfile`` 接口）；本人看自己要什么字段走 ``/users/me``，后台走
    ``/admin/users/{id}``（``UserDetailResponse``，仍带 qq 与角色）。
    """

    email: str
    website: str | None = None
    github: str | None = None

    model_config = {"from_attributes": True}


class UserPreferenceResponse(BaseModel):
    """
    用户偏好设置响应模型

    只有本人接口（``GET/PUT /users/me/preferences``）用这一模型；
    匿名可读的 ``GET /users/username/{username}/preferences`` 走
    ``UserPreferencesPublicDoc`` 的裸 dict，不含 ``notify_by_email``。
    """

    public_profile: bool
    show_email: bool
    show_posts: bool
    show_comments: bool
    show_stats: bool
    show_social_links: bool
    theme: str
    # 邮件通知开关落在 User 表（评论邮件扇出读 User.notify_by_email），不在 UserPreference 列里，
    # 所以只能由端点从 User 行显式补进响应；默认值与列的 server_default 同为 true。
    notify_by_email: bool = Field(
        True,
        description="是否接收评论交互的邮件通知（站点未开启通知邮件或未配 SMTP 时本来就不发）",
    )

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
    show_social_links: bool | None = None
    theme: str | None = None
    notify_by_email: bool | None = None


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
        """验证密码强度（口径单源见 _check_password_strength）"""
        return _check_password_strength(v)


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
        """验证密码强度（口径单源见 _check_password_strength）"""
        return _check_password_strength(v)


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
    email: RelaxedEmailStr = Field(..., description="邮箱地址")
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
    is_staff: bool = Field(default=False, description="是否为管理员（兼容字段，创建后会同步 role）")
    role: str | None = Field(
        None,
        description="RBAC 角色：super_admin/admin/editor/author/contributor/subscriber。为空时由 is_staff/is_superuser 派生。",
    )
    is_active: bool = Field(default=True, description="是否激活")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度（口径单源见 _check_password_strength）"""
        return _check_password_strength(v)

    @field_validator("website", "github")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """验证 URL 格式（口径单源见 _normalize_optional_url）"""
        return _normalize_optional_url(v)


class AdminUserUpdateFull(BaseModel):
    """
    管理员完整更新用户模型

    用于管理员更新用户的所有信息。
    """

    username: str | None = Field(
        None, min_length=1, max_length=150, description="用户名（可选，留空则不修改）"
    )
    email: RelaxedEmailStr | None = None
    nickname: str | None = Field(None, max_length=50)
    bio: str | None = Field(None, max_length=500)
    website: str | None = Field(None, max_length=200)
    github: str | None = Field(None, max_length=200)
    avatar: str | None = Field(None, max_length=500)
    cover_image: str | None = Field(None, max_length=500)
    is_staff: bool | None = None
    is_active: bool | None = None
    is_banned: bool | None = None
    qq: str | None = Field(
        None,
        max_length=20,
        description="QQ 号；UserDetailResponse 会回显该字段，此处必须可写，否则管理员改 QQ 静默失效",
    )
    avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] | None = Field(
        None,
        description="头像来源，取值与 /api/media/avatar 解析器白名单一致",
    )
    role: str | None = Field(
        None,
        description="RBAC 角色：super_admin/admin/editor/author/contributor/subscriber。为空时不变更。",
    )

    @field_validator("website", "github")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """验证 URL 格式（口径单源见 _normalize_optional_url）"""
        return _normalize_optional_url(v)


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


class UserListItem(BaseModel):
    """用户列表投影（``GET /api/users/``）。

    列表响应**刻意不复用** ``UserResponse``：一条 ``UserResponse`` 含
    ``email`` + ``bio``（最长 500 字符）+ ``qq`` / ``github`` / ``website``，
    按 ``page_size=100`` 计算，一页就要把这些字段整体搬 100 份，
    而列表界面一个都不显示。宽响应在列表端点上是纯粹的带宽与序列化浪费，
    同时把本该只在详情页出现的联系方式摊给了每一个能过鉴权的人。

    需要完整字段时走 ``GET /users/{id}``（``UserResponse``）；
    需要管理字段（封禁态、文章/评论计数）时走 ``GET /admin/users``（``AdminUserListItem``）。
    """

    id: int
    username: str
    nickname: str | None = None
    avatar: str | None = None
    resolved_avatar_url: str | None = None
    role: str | None = None
    title: "UserTitleResponse | None" = None
    is_active: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthorDirectoryItem(BaseModel):
    """作者目录投影（``GET /api/users/authors``，前台 `/authors` 页）。

    与 ``UserListItem`` 的取舍同源（头像 / 昵称 / 头衔照搬），再加三项目录页真正要读的：
    ``bio``（卡片摘要，Text 列）、``post_count``（**只算匿名可见的已发布文章**）与
    ``last_published_at``（「最近更新」）。刻意不含 email / website / github / qq ——
    目录不是名片墙，联系方式只留在作者主页（那里的字段集另有隐私开关兜底）。
    """

    id: int
    username: str
    nickname: str | None = None
    avatar: str | None = None
    resolved_avatar_url: str | None = None
    title: "UserTitleResponse | None" = None
    bio: str | None = None
    post_count: int = 0
    last_published_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserListItem(UserListItem):
    """后台用户管理列表投影（``GET /api/admin/users``）。

    在上一条 slim 列表的基础上补齐**管理动作真正需要**的字段：

    - ``email``：封禁/重置密码前需要确认账号归属，后台必须可读；
      前台资料接口仍然按 ``UserPreference.show_email`` 遮蔽，两条路径互不打通。
    - ``is_banned`` / ``is_active`` / ``is_staff`` / ``is_superuser``：列表页的状态徽章
      与封禁开关直接绑定这些字段，缺一个就会出现「封禁了但开关还是关」的假状态。
    - ``posts_count`` / ``comments_count``：删号前要看有没有内容，用两条 GROUP BY 批量算。
    - ``last_login``：判断僵尸号。

    **不包含** ``bio`` / ``website`` / ``github`` / ``qq`` / ``cover_image`` / ``avatar_source``
    —— 这些只在 ``GET /admin/users/{id}``（``UserDetailResponse``）和编辑页里出现。
    """

    email: str | None = None
    is_staff: bool = False
    is_superuser: bool = False
    is_banned: bool = False
    title_id: int | None = None
    last_login: datetime | None = None
    posts_count: int = 0
    comments_count: int = 0

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
    slug: str | None = Field(None, max_length=100, pattern=CONTENT_SLUG_PATTERN)
    description: dict[str, str] | None = Field(None, description="多语言分类描述")
    icon: str | None = Field(None, max_length=50)
    color: str = Field(default="#3B82F6", max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")
    # 创建口也必须能定封面：CategoryUpdate 早有这一项，CategoryBase 却漏了它，
    # 于是"新建分类"永远拿不到封面、只能建完再 PUT 补一次。这与 is_active 当年的
    # 「只能创建时定」是同一族陷阱的反向版本（这里是「创建时定不了」）。
    cover_image: str | None = Field(None, max_length=500)

    @field_validator("cover_image", mode="before")
    @classmethod
    def _blank_cover_image_to_none(cls, v: str | None) -> str | None:
        """空串归 None：库里留着 `""` 时前台拿到的是 `src=""`（一次 404 + 一个破图框），
        而不是"这个分类没有封面"。"""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    # 与 TagBase.is_active 同族：停用 = 公开列表与 sitemap 不再出现（直接 URL 仍可访问，
    # 已发布文章的分类链接不能断）。缺字段等于"创建即默认启用且无法在建分类时停用"。
    is_active: bool = True

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
    slug: str | None = Field(None, max_length=100, pattern=CONTENT_SLUG_PATTERN)
    description: dict[str, str] | None = None
    icon: str | None = Field(None, max_length=50)
    color: str | None = Field(None, max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")
    # 长度约束必须与 CategoryBase 同数：列是 String(500)，SQLite 不拦（静默存下超长串），
    # PG 则在 flush 时抛 value too long → HTTP 500。
    cover_image: str | None = Field(None, max_length=500)
    is_active: bool | None = None

    @field_validator("cover_image", mode="before")
    @classmethod
    def _blank_cover_image_to_none(cls, v: str | None) -> str | None:
        """与 CategoryBase 同口径：空串归 None（= 清掉封面）。"""
        if isinstance(v, str) and not v.strip():
            return None
        return v


class CategoryResponse(BaseModel):
    """分类响应模型"""

    id: int
    name: I18nDict
    slug: str
    description: I18nDict | None = None
    icon: str | None = None
    color: str
    cover_image: str | None = None
    is_active: bool
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
    slug: str | None = Field(None, max_length=100, pattern=CONTENT_SLUG_PATTERN)
    color: str | None = Field(default=None, max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")
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
    name: I18nDict
    slug: str
    color: str | None = None
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
    color: str | None = None
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
    slug: str | None = Field(None, max_length=200, pattern=CONTENT_SLUG_PATTERN)
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
    post_type: str = Field(
        default="post",
        max_length=50,
        pattern=r"^[a-z][a-z0-9_-]{0,49}$",
        description="内容类型 key（默认 post；其它值必须有对应的 content_types 定义）",
    )
    meta_fields: dict[str, Any] | None = Field(
        None,
        description="自定义内容类型字段值，落库前按 content_types.fields 定义校验（见 content_type_service）",
    )

    @field_validator("source_url")
    @classmethod
    def _validate_source_url(cls, v: str | None) -> str | None:
        """原文链接会渲染成访客页面上的 `<a href>`，所以走严格档（口径单源见 _require_absolute_url）。"""
        return _require_absolute_url(v, max_len=500)


class PostCreate(PostBase):
    """文章创建模型"""

    pass


class PostUpdate(BaseModel):
    """文章更新模型"""

    title: dict[str, str] | None = None
    subtitle: dict[str, str] | None = None
    slug: str | None = Field(None, max_length=200)
    source: str | None = Field(None, max_length=50)
    source_url: str | None = Field(None, max_length=500)
    audio: str | None = Field(None, max_length=500)
    video: str | None = Field(None, max_length=500)
    video_url: str | None = Field(None, max_length=500)
    content: dict[str, str] | None = None
    excerpt: dict[str, str] | None = None
    cover_image: str | None = Field(None, max_length=500)
    category_id: int | None = None
    tag_ids: list[int] | None = None
    series_id: int | None = None
    series_order: int | None = None
    status: str | None = Field(None, pattern="^(draft|published|scheduled)$")
    visibility: str | None = Field(None, pattern="^(public|password|private)$", max_length=10)
    scheduled_at: datetime | None = None
    password: str | None = Field(None, max_length=100)
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
    # post_type 允许出现在更新体里是为了支持"把这篇改成另一种内容类型"；
    # 校验与合并（只改 meta_fields 时按库存值补 post_type）在 api/blog.py 里做。
    post_type: str | None = Field(None, max_length=50, pattern=r"^[a-z][a-z0-9_-]{0,49}$")
    meta_fields: dict[str, Any] | None = None

    @field_validator("source_url")
    @classmethod
    def _validate_source_url(cls, v: str | None) -> str | None:
        """与 PostBase 同档：空串归 None（= 清掉），非空必须是 http(s)（口径单源见 _require_absolute_url）。"""
        return _require_absolute_url(v, max_len=500)


class BatchPostStatusUpdate(BaseModel):
    post_ids: list[int] = Field(..., min_length=1)
    status: Literal["draft", "published", "scheduled"]


class BatchPostStatusResponse(BaseResponse):
    data: dict[str, int]


class PostResponse(BaseModel):
    """文章响应模型"""

    id: int
    title: I18nDict
    subtitle: I18nDict | None = None
    slug: str
    source: str
    source_url: str | None = None
    audio: str | None = None
    video: str | None = None
    video_url: str | None = None
    content: I18nDict
    excerpt: I18nDict | None = None
    cover_image: str | None = None
    author: PublicUserResponse
    category: CategoryResponse | None = None
    tags: list[TagResponse] = []
    status: str
    visibility: str
    views: int
    likes_count: int = 0
    is_pinned: bool
    allow_comments: bool
    comments_count: int = 0
    meta_title: I18nDict | None = None
    meta_description: I18nDict | None = None
    meta_keywords: I18nDict | None = None
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
    title: I18nDict
    subtitle: I18nDict | None = None
    slug: str
    source: str
    source_url: str | None = None
    audio: str | None = None
    video: str | None = None
    video_url: str | None = None
    content: I18nDict
    excerpt: I18nDict | None = None
    cover_image: str | None = None
    status: str
    visibility: str
    has_password: bool = False
    # 编辑器要能还原已存的提示：不回填的话每次 PUT 都会把提示提交成空串清掉。
    encryption_hint: str | None = None
    published_at: datetime | None = None
    scheduled_at: datetime | None = None
    category: dict[str, Any] | None = None
    tags: list[dict[str, Any]] = []
    # 编辑器必须能还原「这篇属于哪个系列的第几章」：不回填就等于每次 PUT 都把
    # series_id 提交成 null，系列页的章节目录会在一次普通编辑后清空。
    series_id: int | None = None
    series_order: int | None = None
    is_pinned: bool
    allow_comments: bool
    meta_description: I18nDict | None = None
    meta_title: I18nDict | None = None
    meta_keywords: I18nDict | None = None
    post_type: str = "post"
    meta_fields: dict[str, Any] | None = None
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
            encryption_hint=post.encryption_hint if post.password else None,
            published_at=post.published_at,
            scheduled_at=post.scheduled_at,
            category=category,
            tags=tags,
            series_id=post.series_id,
            series_order=post.series_order,
            is_pinned=post.is_pinned or False,
            allow_comments=post.allow_comments if hasattr(post, "allow_comments") else True,
            meta_description=post.meta_description,
            meta_title=post.meta_title,
            meta_keywords=post.meta_keywords,
            post_type=post.post_type or "post",
            # 读侧比写侧宽：历史行里的 meta_fields 可能是裸字符串等脏形态，
            # 非 dict 一律按"没有扩展字段"处理，不让编辑页整页 500。
            meta_fields=post.meta_fields if isinstance(post.meta_fields, dict) else None,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )


class PostSeriesChapterRef(BaseModel):
    """系列内相邻章节的引用：只够渲染一条「上一章 / 下一章」链接。"""

    slug: str
    title: str


class PostSeriesBrief(BaseModel):
    """文章详情里的「所属系列」简报。

    只给详情页渲染一张卡片所需的几样东西：去哪儿（slug）、叫什么（本地化 title）、
    共几章（post_count）、本篇第几章（position，1 起；本篇不在公开章节列表里时为 None，
    例如作者预览草稿），以及按同一份章节顺序算出的相邻章节（prev / next，头尾各缺一条）。
    刻意不复用 `PostSeriesResponse`：那个口带 created_at / sort_order / is_active，
    详情页一个都不用，而详情是全站 QPS 最高的读口之一。
    """

    id: int
    slug: str
    title: str
    post_count: int = Field(0, description="系列内公开可见的章节数")
    position: int | None = Field(
        None, description="本篇在系列中的序位（1 起），不在公开列表中为 None"
    )
    prev: PostSeriesChapterRef | None = Field(None, description="系列内上一章（按章节顺序）")
    next: PostSeriesChapterRef | None = Field(None, description="系列内下一章（按章节顺序）")


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
    author: PublicUserResponse
    category: CategoryLocalizedResponse | None = None
    tags: list[TagLocalizedResponse] = []
    # 所属系列：详情页的系列卡片是公开页 /series 在站内唯一的入口（此前全站零 href）。
    # 系列未激活 / 文章不属于任何系列时为 None，页面据此整块不渲染。
    series: PostSeriesBrief | None = None
    status: str
    visibility: str = "public"
    password: str | None = None
    views: int
    likes_count: int = 0
    is_pinned: bool
    allow_comments: bool
    comments_count: int = 0
    is_password_protected: bool = False
    # 密码提示只在真有密码哈希时输出：公开文章带一个提示字段等于让爬虫以为
    # 有东西可解，而前台闸门页（pages/posts/[slug].vue 的 postEncryptionHint）
    # 读的正是这一条——写口 PostForm 早就存了 encryption_hint，此前只是没人回读。
    encryption_hint: str | None = None
    # 自定义内容类型：前台按 post_type 去 GET /api/content-types 查定义，
    # 只渲染"定义里存在且值非空"的键。读侧不按定义重校验（见 models/content_type.py）。
    post_type: str = "post"
    meta_fields: dict[str, Any] | None = None
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
        from backend.api._user_response_helper import build_public_user_response

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
            author=build_public_user_response(post.author),
            category=category,
            tags=tags,
            status=post.status,
            visibility=post.visibility or "public",
            views=post.views,
            likes_count=likes_count,
            is_pinned=post.is_pinned,
            allow_comments=post.allow_comments,
            comments_count=comments_count,
            encryption_hint=post.encryption_hint if post.password else None,
            post_type=post.post_type or "post",
            meta_fields=post.meta_fields if isinstance(post.meta_fields, dict) else None,
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


class PostListItemLocalized(BaseModel):
    """文章列表项本地化模型"""

    id: int
    title: str
    subtitle: str | None = None
    slug: str
    excerpt: str | None = None
    cover_image: str | None = None
    author: PublicUserResponse
    category: CategoryLocalizedResponse | None = None
    tags: list[TagLocalizedResponse] = []
    status: str
    # 后台列表要能一眼看出"这条对访客不存在"：私密档文章在公开口已被整条滤掉，
    # 只有列表带出 visibility 才谈得上审计。默认 public 与 Post 列默认一致。
    visibility: str = "public"
    views: int
    likes_count: int = 0
    comments_count: int = 0
    is_pinned: bool
    created_at: datetime
    published_at: datetime | None = None
    # 后台列表要回答"这条多久没动过了"，草稿/定时文章没有 published_at，
    # 只看 created_at 会误判成"刚建好就没管过"。公开列表同样带上，字段是加性的。
    updated_at: datetime | None = None
    reading_time: int = 1

    @classmethod
    def from_post(cls, post, lang: str = "zh", comments_count: int = 0) -> "PostListItemLocalized":
        """从文章模型创建本地化列表项"""
        category = None
        if post.category:
            category = CategoryLocalizedResponse.from_category(post.category, lang)

        tags = [TagLocalizedResponse.from_tag(tag, lang) for tag in post.tags]

        excerpt = get_i18n_value(post.excerpt, lang) if post.excerpt else None
        from backend.api._user_response_helper import build_public_user_response

        return cls(
            id=post.id,
            title=get_i18n_value(post.title, lang),
            subtitle=get_i18n_value(post.subtitle, lang) if post.subtitle else None,
            slug=post.slug,
            excerpt=excerpt,
            cover_image=post.cover_image,
            author=build_public_user_response(post.author),
            category=category,
            tags=tags,
            status=post.status,
            visibility=post.visibility or "public",
            views=post.views,
            likes_count=len(post.likes) if post.likes else 0,
            comments_count=comments_count,
            is_pinned=post.is_pinned,
            created_at=post.created_at,
            published_at=post.published_at,
            updated_at=getattr(post, "updated_at", None),
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


# ==================== 评论相关模型 ====================


class CommentBase(BaseModel):
    """评论基础模型"""

    content: str = Field(..., min_length=2, max_length=3000)
    parent_id: int | None = None
    author_name: str | None = Field(None, min_length=2, max_length=30)
    author_email: RelaxedEmailStr | None = Field(None, max_length=254)
    author_website: str | None = Field(None, max_length=200)
    hcaptcha_token: str | None = None
    # 图形验证码（后台「功能开关 → 图形验证码」打开后，匿名提交必填）。
    # key 来自 GET /api/captcha，code 是用户输入的 4 位字符；两者一次性消费。
    captcha_key: str | None = Field(None, max_length=64, description="验证码 key")
    captcha_code: str | None = Field(None, max_length=10, description="验证码字符")

    @field_validator("content", mode="after")
    @classmethod
    def _reject_blank_content(cls, v: str) -> str:
        """min_length=2 挡不住 "   \n\n  " 这类纯空白：先 strip 再复检，
        防止无内容评论刷爆列表与通知。"""
        stripped = v.strip()
        if len(stripped) < 2:
            raise ValueError("评论内容不能为空白")
        return stripped

    @field_validator("author_website")
    @classmethod
    def _validate_website(cls, v: str | None) -> str | None:
        """口径单源见 _require_absolute_url"""
        return _require_absolute_url(v)


class CommentCreate(CommentBase):
    """评论创建模型（游客或登录用户均可使用）"""

    # 访客身份字段：形态与头像解析器同源（`utils.ugc_fields`），公开写入口必须先拒掉标记语言，
    # 否则"能写进库"与"能解析出头像"分叉，脏值还会被评论口当显示名原样发出去（§12.8）。
    qq: str | None = Field(
        None,
        max_length=11,
        pattern=_QQ_PATTERN,
        description="访客 QQ 号（可选，5–11 位数字）",
    )
    github: str | None = Field(
        None,
        max_length=39,
        pattern=_GITHUB_USERNAME_PATTERN,
        description="访客 GitHub 用户名（可选，只允许用户名形态，不接受 URL 与标记语言）",
    )
    # 与 ORM Comment.avatar_source 字段和对外 API 请求体保持一致；
    # 同时保留 author_avatar_source 作为向后兼容别名（deprecated）
    avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] = Field(
        "auto", description="头像来源"
    )
    author_avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] | None = Field(
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
    slug: str = Field(..., max_length=200, pattern=CONTENT_SLUG_PATTERN)
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
    title: I18nDict
    slug: str
    content: I18nDict
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
    title: I18nDict
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


_FRIEND_STATUS_PATTERN = f"^({'|'.join(FriendLink.VALID_STATUSES)})$"


def _status_to_active(status: str | None, is_active: bool | None) -> tuple[str, bool]:
    """status 和 is_active 双向归一化：以 status 为主，is_active 作为兼容镜像。

    档位清单与归一规则的单源在 `FriendLink`（模型列自己描述自己的域），
    这里只做转发——写口 pattern、公开谓词、导入工具三处必须同档，
    各写一份字面量的结局是"后台多一档、公开面永远查不出行"。
    """
    return FriendLink.normalize_status_active(status, is_active)


class FriendLinkBase(BaseModel):
    """友情链接基础模型"""

    name: dict[str, str] | str = Field(..., description="网站名称，支持字符串或多语言格式")
    url: str = Field(..., max_length=500)
    description: dict[str, str] | str | None = Field(
        None, description="网站描述，支持字符串或多语言格式"
    )
    logo: str | None = Field(None, max_length=500)
    order: int = Field(default=0, ge=0)
    status: str = Field(
        default=FriendLink.STATUS_PENDING,
        pattern=_FRIEND_STATUS_PATTERN,
        description="审核状态：pending待审核 / approved已通过 / rejected已拒绝",
    )
    is_active: bool = True
    target_blank: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_i18n_fields(cls, data):
        if isinstance(data, dict):
            if "name" in data and isinstance(data["name"], str):
                data["name"] = {"zh": data["name"], "en": data["name"]}
            if "description" in data and isinstance(data["description"], str):
                data["description"] = {"zh": data["description"], "en": data["description"]}
            st, act = _status_to_active(
                data.get("status") if "status" in data else None,
                data.get("is_active") if "is_active" in data else None,
            )
            data["status"] = st
            data["is_active"] = act
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
    status: str | None = Field(None, pattern=_FRIEND_STATUS_PATTERN)
    is_active: bool | None = None
    target_blank: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_i18n_fields(cls, data):
        if isinstance(data, dict):
            if "name" in data and isinstance(data["name"], str):
                data["name"] = {"zh": data["name"], "en": data["name"]}
            if "description" in data and isinstance(data["description"], str):
                data["description"] = {"zh": data["description"], "en": data["description"]}
            if "status" in data or "is_active" in data:
                st, act = _status_to_active(
                    data.get("status") if "status" in data else None,
                    data.get("is_active") if "is_active" in data else None,
                )
                data["status"] = st
                data["is_active"] = act
        return data


class FriendLinkResponse(BaseModel):
    """友情链接响应模型"""

    id: int
    name: I18nDict
    url: str
    description: I18nDict | None = None
    logo: str | None = None
    order: int
    status: str
    is_active: bool
    target_blank: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def sync_status_active(cls, data):
        """投影前把 status/is_active 重过一遍唯一归一函数。

        注意它只对齐两个字段，**不会把不合规的行从列表里摘掉**——所以公开口必须自己在
        SQL 上带 `FriendLink.publicly_visible()`，不能指望这一层当闸门。
        """
        if isinstance(data, dict):
            st, act = FriendLink.normalize_status_active(data.get("status"), data.get("is_active"))
            data["status"] = st
            data["is_active"] = act
        elif hasattr(data, "status"):
            st, act = FriendLink.normalize_status_active(
                getattr(data, "status", None), getattr(data, "is_active", False)
            )
            setattr(data, "status", st)
            setattr(data, "is_active", act)
        return data


class FriendLinkLocalizedResponse(BaseModel):
    """友情链接本地化响应模型"""

    id: int
    name: str
    url: str
    description: str | None = None
    logo: str | None = None
    order: int
    status: str
    is_active: bool
    target_blank: bool
    created_at: datetime

    @classmethod
    def from_friend_link(cls, link, lang: str = "zh") -> "FriendLinkLocalizedResponse":
        """从友链模型创建本地化响应"""
        st, act = FriendLink.normalize_status_active(
            getattr(link, "status", None), getattr(link, "is_active", False)
        )
        return cls(
            id=link.id,
            name=get_i18n_value(link.name, lang),
            url=link.url,
            description=get_i18n_value(link.description, lang) if link.description else None,
            logo=link.logo,
            order=link.order,
            status=st,
            is_active=act,
            target_blank=link.target_blank,
            created_at=link.created_at,
        )


# ==================== 搜索占位符模型 ====================


def _require_placeholder_text(value: dict[str, str]) -> dict[str, str]:
    """占位文本至少有一种语言非空；四语全空的行在前台等价于不存在，写入侧直接拒掉。"""
    cleaned = {k: str(v).strip() for k, v in value.items() if str(v).strip()}
    if not cleaned:
        raise ValueError("至少填写一种语言的占位文本")
    return cleaned


class SearchPlaceholderCreate(BaseModel):
    """搜索占位符创建模型"""

    text: I18nDict
    is_active: bool = True
    order: int = Field(default=0, ge=0)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value):
        return _require_placeholder_text(value)


class SearchPlaceholderUpdate(BaseModel):
    """搜索占位符更新模型"""

    text: I18nDict | None = None
    is_active: bool | None = None
    order: int | None = Field(None, ge=0)

    @field_validator("text")
    @classmethod
    def clean_optional_text(cls, value):
        return None if value is None else _require_placeholder_text(value)


class SearchPlaceholderResponse(BaseModel):
    """搜索占位符响应模型（后台口回完整四语 dict）"""

    id: int
    text: I18nDict
    is_active: bool
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== 通知相关模型 ====================


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
    # 关于页面内容（HTML 直接渲染版，站点设置 basic 组中以 HTML 编辑器维护）
    about_page_html: str = ""

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
    post_id: int | None = Field(
        None,
        description="绑定的文章 ID；None = 全站投票（挂在每篇文章下方），非 None = 只在该文章展示",
    )
    is_active: bool = True
    allow_multiple: bool = False
    show_results: bool = True


class PollUpdate(BaseModel):
    """投票更新模型（PUT /voting/polls/{id}）。

    全部可选：端点按 `model_fields_set` 只写调用方真正提交的键，缺省键保持原值。
    选项（choices）不在这里改——每个选项 id 都挂着 votes 行，替换选项等于删掉票数，
    所以编辑弹窗只暴露标题/说明/绑定文章/三个开关。
    """

    title: str | None = Field(None, max_length=200, min_length=1)
    description: str | None = Field(None, max_length=500)
    post_id: int | None = Field(None, description="None = 改回全站投票")
    is_active: bool | None = None
    allow_multiple: bool | None = None
    show_results: bool | None = None


class PollCreate(PollBase):
    """投票创建模型"""

    choices: list[str] = Field(
        ..., min_length=2, max_length=20, description="选项列表；每项 1-200 字符"
    )

    # Pydantic v2 无法直接对 list[str] 的元素加约束，用 field_validator 兜底
    from pydantic import field_validator

    @field_validator("choices", mode="after")
    @classmethod
    def _validate_choice_items(cls, v: list[str]) -> list[str]:
        for i, item in enumerate(v):
            if not item or len(item) > 200:
                raise ValueError(f"选项 {i + 1} 长度必须在 1-200 之间，当前 {len(item)}")
        return v


class PollResponse(PollBase):
    """投票响应模型"""

    id: int
    # 重声明为必填：PollBase 里它有默认值 None（创建时可以不绑定文章），但响应漏传
    # 一次就会把"绑定了文章"静默报成"全站投票"，前端据此渲染出的绑定关系是错的。
    post_id: int | None
    choices: list["PollChoiceResponse"]
    total_votes: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PollChoiceResponse(BaseModel):
    """投票选项响应模型"""

    id: int
    text: str
    order: int
    votes_count: int | None = Field(
        None, description="票数；show_results=False 且非 staff/superuser 时为 null"
    )

    model_config = {"from_attributes": True}


class VoteCreate(BaseModel):
    """投票创建模型"""

    choice_ids: list[int] = Field(..., min_length=1)


# ==================== 留言板相关模型（Task 6 新版） ====================


class GuestbookEntryBase(BaseModel):
    """留言基础模型"""

    content: str = Field(..., min_length=2, max_length=3000)
    author_name: str | None = Field(None, min_length=2, max_length=30)
    author_email: RelaxedEmailStr | None = Field(None, max_length=254)
    author_website: str | None = Field(None, max_length=200)
    # 图形验证码（与评论同一闸门，见 services/captcha_service.py）
    captcha_key: str | None = Field(None, max_length=64, description="验证码 key")
    captcha_code: str | None = Field(None, max_length=10, description="验证码字符")

    @field_validator("content", mode="after")
    @classmethod
    def _reject_blank_content(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 2:
            raise ValueError("留言内容不能为空白")
        return stripped

    @field_validator("author_website")
    @classmethod
    def _validate_website(cls, v: str | None) -> str | None:
        """口径单源见 _require_absolute_url"""
        return _require_absolute_url(v)


class GuestbookEntryCreate(GuestbookEntryBase):
    """留言创建模型（游客或登录用户均可使用）"""

    # 访客身份字段：形态与头像解析器同源（`utils.ugc_fields`），公开写入口必须先拒掉标记语言，
    # 否则"能写进库"与"能解析出头像"分叉，脏值还会被评论口当显示名原样发出去（§12.8）。
    qq: str | None = Field(
        None,
        max_length=11,
        pattern=_QQ_PATTERN,
        description="访客 QQ 号（可选，5–11 位数字）",
    )
    github: str | None = Field(
        None,
        max_length=39,
        pattern=_GITHUB_USERNAME_PATTERN,
        description="访客 GitHub 用户名（可选，只允许用户名形态，不接受 URL 与标记语言）",
    )
    author_avatar_source: Literal["auto", "custom", "github", "qq", "gravatar"] = Field(
        "auto", description="头像来源"
    )


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
    title: "UserTitleResponse | None" = None

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


from backend.schemas.strict_config import apply_strict_extra_forbid, finalize_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)


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

# 引用解析晚于加固的类，在这里补重建（见 strict_config 模块文档）
finalize_strict_extra_forbid()
