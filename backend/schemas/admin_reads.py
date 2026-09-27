"""后台 / 跨端点复用响应体的**纯文档模型**。

这些类只用于在路由装饰器里写 `responses={200: {"model": ...}}`：
该路径只生成 OpenAPI schema，**不参与运行时序列化，也不会过滤响应体字段**，
因此对 handler 的实际返回零影响（对比 `response_model=`——那会校验并裁剪字段，
对返回裸 dict 的端点是线上事故）。

字段全部逐一对齐各 handler 真实 `return` 语句里的键与运行时类型，
不臆造、不"看起来应该有"；日期字段建模为 `str | None`，因为响应里
放的是 handler 手工 `isoformat()` 后的字符串（或 None），不是 datetime。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserTitleBadgeDoc(BaseModel):
    """用户头衔徽章的对外投影（评论列表 / 仪表盘热评用户 / 称号查询共用形态）。

    与 ``backend.schemas.UserTitleResponse`` 字段一致，但全部放宽为可选：
    各处投影代码不同（stats 不输出 description、admin 评论列表不输出 description），
    以"最宽公约数"如实建模，避免文档比真实响应更严格。
    """

    id: int = Field(..., description="头衔 ID")
    name: dict[str, str] = Field(
        ..., description="头衔名称：多语言 dict（存 JSON 列，如 {'zh': '管理员', 'en': 'Admin'}）"
    )
    color: str | None = Field(
        None, description="显示颜色（十六进制字符串，写入侧按 hex 正则校验），缺失时可为 null"
    )
    icon: str | None = Field(
        None, description="图标（预设 ID 或 emoji，纯文本，禁止标记语言），未设置时为 null"
    )
    description: dict[str, str] | None = Field(
        None,
        description="头衔描述：多语言 dict 或 null（仅 GET /users/{user_id}/title 端点输出该字段）",
    )


class CommentUserRefDoc(BaseModel):
    """评论管理视图里嵌套的用户摘要（``UserResponse.model_dump()`` 的投影）。

    即 ``backend.schemas.UserResponse`` 的字典形态：管理员视图不遮蔽邮箱
    （apply_email_privacy 只对非 staff 生效），datetime 字段在 model_dump 后
    仍是 datetime 对象，最终由 FastAPI 序列化为 ISO 8601 字符串。
    """

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(
        ...,
        description="邮箱（管理员视图为明文；UserResponse 构建链本身不做隐私遮蔽）",
    )
    nickname: str | None = Field(None, description="昵称，未设置时为 null")
    bio: str | None = Field(None, description="个人简介")
    website: str | None = Field(None, description="个人网站 URL")
    github: str | None = Field(None, description="GitHub 主页 URL")
    qq: str | None = Field(None, description="QQ 号（用于头像识别）")
    avatar_source: str = Field(
        "auto", description="头像来源：auto / custom / github / qq / gravatar 之一"
    )
    avatar: str | None = Field(None, description="自定义头像 URL，未设置时为 null")
    cover_image: str | None = Field(None, description="用户主页封面图 URL")
    is_active: bool = Field(..., description="账号是否激活")
    is_staff: bool = Field(..., description="是否管理员")
    is_superuser: bool = Field(..., description="是否超级管理员")
    role: str | None = Field(None, description="RBAC 角色名，历史数据可能为 null")
    title: UserTitleBadgeDoc | None = Field(None, description="用户当前头衔徽章，无头衔时为 null")
    resolved_avatar_url: str | None = Field(
        None, description="经 avatar_resolver 统一解析后的最终头像 URL"
    )
    created_at: str = Field(
        ..., description="注册时间（模型里是 datetime，HTTP 响应中序列化为 ISO 8601 字符串）"
    )
    last_login: str | None = Field(
        None, description="最后登录时间（同上，序列化为 ISO 8601 字符串），从未登录为 null"
    )


class CommentPostRefDoc(BaseModel):
    """评论管理视图里嵌套的文章摘要（仅 id/slug/title 三字段投影）。"""

    id: int = Field(..., description="文章 ID")
    slug: str | None = Field(None, description="文章 slug（getattr 防御式读取，理论缺失为 null）")
    title: str = Field(
        ...,
        description="文章标题纯文本：JSON 多语言列取 zh 键，非 dict 或缺失时 str() 兜底，可能为空串",
    )


class CommentParentRefDoc(BaseModel):
    """评论管理视图里嵌套的父评论摘要。"""

    id: int = Field(..., description="父评论 ID")
    nickname: str | None = Field(
        None,
        description="父评论作者昵称：优先父评论自身 author_name，回退其关联用户 nickname，两者皆空为 null",
    )
