"""
SEO 优化 API

提供 robots.txt、结构化数据、Open Graph、SEO 配置、Sitemap 生成 等 SEO 功能。
"""

import re
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import defer, selectinload

from backend.core.auth import CurrentStaff
from backend.core.cache import CACHE_TTL, cache, make_cache_key
from backend.core.config import settings
from backend.core.database import async_session_maker
from backend.core.deps import DB
from backend.core.site_config import get_site_config_value
from backend.models.blog import Category, Post, Tag
from backend.models.core import SiteConfig
from backend.schemas import raw_content_response

router = APIRouter(tags=["SEO"])


# SEO 配置相关 key 集合
SEO_CONFIG_KEYS = [
    "SEO_TITLE",
    "SEO_DESCRIPTION",
    "SEO_KEYWORDS",
    "SEO_AUTHOR",
    "SEO_IMAGE",
    "SEO_ROBOTS",
    "SEO_CANONICAL",
    "SEO_OG_SITE_NAME",
    "SEO_TWITTER_SITE",
    "SEO_STRUCTURED_DATA",
]


async def _get_all_seo_config() -> dict[str, str]:
    """读取所有 SEO 相关 key"""
    result: dict[str, str] = {}
    for key in SEO_CONFIG_KEYS:
        v = await get_site_config_value(key)
        if v is not None:
            result[key] = v
    return result


def _pick(value) -> str:
    """从多语言 dict 中取出 zh / en 文本；非 dict 直接转字符串。"""
    if isinstance(value, dict):
        return value.get("zh") or value.get("en") or value.get("ja") or value.get("zh_Hant") or ""
    if value is None:
        return ""
    return str(value)


# 元数据清理：JSON-LD / Open Graph 的 description 会被搜索引擎和社交平台直接展示，
# 绝不能出现未渲染的短代码字面量（[gallery ids=...]）或残破 HTML 标签。
# 这里刻意"剥掉"而非"渲染"——meta 描述要的是纯文本，跑渲染管线反而引入外链与体积。
_SHORTCODE_TOKEN_RE = re.compile(r"\[/?[A-Za-z_][\w\-]*(?:[^\[\]]*)?\]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_for_meta(value) -> str:
    """取多语言字段纯文本，剥离短代码与 HTML 标签，压缩空白。"""
    text = _pick(value)
    text = _SHORTCODE_TOKEN_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class SeoConfigMapResponse(BaseModel):
    """SEO 配置键值集合（裸对象，无 success 信封）。

    键来自服务端白名单，未配置过的键直接缺席而非返回 null，
    因此全部字段声明为可选。
    """

    SEO_TITLE: str | None = Field(None, description="站点标题")
    SEO_DESCRIPTION: str | None = Field(None, description="站点描述")
    SEO_KEYWORDS: str | None = Field(None, description="站点关键词")
    SEO_AUTHOR: str | None = Field(None, description="默认作者署名")
    SEO_IMAGE: str | None = Field(None, description="默认分享图 URL")
    SEO_ROBOTS: str | None = Field(None, description="默认 robots 指令")
    SEO_CANONICAL: str | None = Field(None, description="规范链接（canonical）覆盖值")
    SEO_OG_SITE_NAME: str | None = Field(None, description="Open Graph 站点名")
    SEO_TWITTER_SITE: str | None = Field(None, description="Twitter 站点账号（@handle）")
    SEO_STRUCTURED_DATA: str | None = Field(None, description="附加结构化数据（JSON-LD 文本）")


class SeoConfigUpdateResponse(BaseModel):
    """批量更新 SEO 配置后的响应体。"""

    success: bool = Field(True, description="固定为 true；失败走 HTTPException 错误信封")
    message: str = Field("SEO 配置已更新", description="人类可读结果")
    data: SeoConfigMapResponse = Field(
        ..., description="写库并清缓存后重新读取的全量 SEO 配置（键集合与读接口一致）"
    )


class SeoCacheResetResponse(BaseModel):
    """清理 sitemap 缓存的响应体。"""

    success: bool = Field(True, description="固定为 true")
    message: str = Field(
        "Sitemap 缓存已清除，下次访问将重新生成",
        description="人类可读结果（本接口不返回新缓存内容）",
    )


class SitemapCheckData(BaseModel):
    """Sitemap 健康度校验载荷。"""

    ok: bool = Field(..., description="是否零问题：只要有一条缺项即为 false")
    url_count: int = Field(
        0, description="参与校验的已发布文章数（未截断，可能大于 errors 的可见条数）"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="问题清单，中文字面量（如「文章 #12 缺少摘要」），最多返回前 50 条",
    )


class SitemapCheckResponse(BaseModel):
    """Sitemap 健康度校验的响应体。"""

    success: bool = Field(True, description="固定为 true；有问题不代表请求失败")
    data: SitemapCheckData = Field(..., description="校验结果载荷")


class SeoScoreItem(BaseModel):
    """单篇文章的 SEO 评分。"""

    id: int = Field(..., description="文章 ID")
    slug: str = Field(..., description="文章 slug")
    title: str = Field(
        ..., description="标题（多语言取 zh/en/ja/zh_Hant；取不到时回退「#文章 ID」）"
    )
    score: int = Field(
        0, description="SEO 得分 0–100：标题 25 + 摘要 20 + 封面 20 + 正文长度 20 + 标签 15"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="中文改进建议清单；得分为满分时是空数组"
    )


class SeoScoresResponse(BaseModel):
    """文章 SEO 评分列表的响应体（裸分页信封，不带 success）。"""

    items: list[SeoScoreItem] = Field(
        default_factory=list, description="当前页评分条目，按得分升序（差的排前面）"
    )
    total: int = Field(0, description="已发布文章总数（评分在内存里全量算完再分页）")
    page: int = Field(1, description="当前页码（回显请求参数）")
    page_size: int = Field(20, description="每页数量（回显请求参数，上限 100）")
    total_pages: int = Field(0, description="总页数；total 为 0 时是 0")


class JsonLdSchemaResponse(BaseModel):
    """JSON-LD 结构化数据响应体（按资源类型返回不同形态，故为宽松模型）。

    四种成功形态的 ``@type`` 分别是 Article / Person / WebSite / BreadcrumbList；
    资源不存在或类型不受支持时只返回 ``error`` 字段。未用到的键不会出现在响应里，
    因此所有字段声明为可选并允许额外键。
    """

    model_config = ConfigDict(extra="allow")

    error: str | None = Field(
        None,
        description="错误说明（Article not found / Person not found / Unsupported resource type）；"
        "出现该字段时不再包含任何 JSON-LD 字段，HTTP 状态仍是 200",
    )
    context: str | None = Field(
        None, alias="@context", description="固定为 https://schema.org（OpenAPI 键名 @context）"
    )
    type: str | None = Field(
        None,
        alias="@type",
        description="schema.org 类型：article/post 取 Article，person 取 Person，"
        "website 取 WebSite，breadcrumb 取 BreadcrumbList",
    )
    headline: str | None = Field(None, description="Article 形态的标题（取多语言 zh 文案）")
    description: str | None = Field(
        None, description="Article / Person / WebSite 形态共用的描述文案"
    )
    image: str | None = Field(None, description="Article 形态为封面图 URL；Person 形态为头像 URL")
    name: str | None = Field(
        None, description="Person 昵称（缺省回退用户名）/ WebSite 站点名（Article 形态无该键）"
    )
    datePublished: str | None = Field(
        None, description="Article 形态的发布时间 ISO 8601 字符串；未发布时为 null"
    )
    dateModified: str | None = Field(
        None, description="Article 形态的更新时间 ISO 8601 字符串；无值时为 null"
    )
    url: str | None = Field(
        None, description="实体规范 URL：Article 指文章页，Person 指作者页，WebSite 指站点根"
    )
    author: dict[str, Any] | None = Field(
        None,
        description="Article 形态的作者对象：{@type: Person, name, url}；"
        "无作者记录时 name 为 Anonymous、url 为 null",
    )
    publisher: dict[str, Any] | None = Field(
        None,
        description="Article 形态的发布方对象：{@type: Organization, name, logo}，name 固定 Rosetta Blog",
    )
    mainEntityOfPage: dict[str, Any] | None = Field(  # noqa: N815
        None, description="Article 形态的宿主页面引用：{@type: WebPage, @id: 文章 URL}"
    )
    articleSection: str | None = Field(
        None, description="Article 所属分类名（多语言取 zh）；文章没有分类时该键整体缺席"
    )
    sameAs: list[str] = Field(  # noqa: N815
        default_factory=list,
        description="Person 形态的外部主页集合（GitHub、个人网站），为空的链接不会入列",
    )
    potentialAction: dict[str, Any] | None = Field(  # noqa: N815
        None,
        description="WebSite 形态的站内搜索动作：{@type: SearchAction, target, query-input}",
    )
    itemListElement: list[dict[str, Any]] = Field(  # noqa: N815
        default_factory=list,
        description="BreadcrumbList 形态的面包屑项数组，当前实现固定一项首页 {@type, position, name, item}",
    )


class OpenGraphResponse(BaseModel):
    """Open Graph / Twitter Card 元数据响应体（键名带冒号，逐字返回）。"""

    model_config = ConfigDict(extra="allow")

    error: str | None = Field(
        None,
        description="错误说明（Article not found / Unsupported resource type）；"
        "出现该字段时不再包含任何 og:* 键，HTTP 状态仍是 200",
    )
    og_type: str = Field(
        "article", alias="og:type", description="Open Graph 类型，文章资源固定 article"
    )
    og_title: str = Field("", alias="og:title", description="文章标题（多语言取 zh 文案）")
    og_description: str = Field(
        "",
        alias="og:description",
        description="文章摘要，服务端截断到前 200 字符；摘要为空时是空字符串",
    )
    og_image: str | None = Field(
        None, alias="og:image", description="封面图 URL；未设置封面时为 null"
    )
    og_url: str = Field("", alias="og:url", description="文章规范 URL")
    og_site_name: str = Field(
        "", alias="og:site_name", description="站点名，取不到时回退 Rosetta Blog"
    )
    og_locale: str = Field("zh_CN", alias="og:locale", description="固定 zh_CN")
    article_published_time: str | None = Field(
        None,
        alias="article:published_time",
        description="发布时间 ISO 8601 字符串；未发布时为 null",
    )
    article_modified_time: str | None = Field(
        None,
        alias="article:modified_time",
        description="更新时间 ISO 8601 字符串；无值时为 null",
    )
    article_author: str | None = Field(
        None, alias="article:author", description="作者主页 URL；文章无作者记录时为 null"
    )
    twitter_card: str = Field(
        "summary_large_image", alias="twitter:card", description="Twitter 卡片样式，固定大图卡"
    )
    twitter_title: str = Field("", alias="twitter:title", description="与 og:title 同值")
    twitter_description: str = Field(
        "", alias="twitter:description", description="与 og:description 同值（同样截断到 200 字符）"
    )
    twitter_image: str | None = Field(
        None, alias="twitter:image", description="与 og:image 同值；未设置封面时为 null"
    )


@router.get(
    "/config",
    summary="获取 SEO 配置",
    description=(
        "读取站点 SEO 相关配置（TITLE、DESCRIPTION、KEYWORDS 等），公开接口。"
        "返回裸对象且只含服务端白名单里已配置的键，未配置的键不会出现。"
        "结果按站点配置缓存组缓存 1 小时，任何一次更新配置都会连带清掉这批缓存。"
    ),
    responses={200: {"model": SeoConfigMapResponse}},
)
async def get_seo_config():
    cache_key = make_cache_key("seo", "config")
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached
    data = await _get_all_seo_config()
    await cache.set(cache_key, data, ttl=CACHE_TTL["site_config"])
    return data


@router.put(
    "/config",
    summary="【管理员】更新 SEO 配置",
    description=(
        "批量更新 SEO 配置 key-value，保存到 SiteConfig 表。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "请求体是 SEO 键到字符串的扁平对象；白名单外的键被静默忽略，"
        "值为 null 时写入空字符串（即清空）。成功后会清掉 seo / site_config 相关缓存并回写全量配置。"
    ),
    responses={200: {"model": SeoConfigUpdateResponse}},
)
async def update_seo_config(
    _staff: CurrentStaff,
    payload: dict[str, str] = Body(..., description="SEO key-value 集合"),
):
    """更新 SEO 配置"""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="参数必须是 object")

    async with async_session_maker() as db:
        # 只认白名单 key；一次 IN 查询取出已存在的行，避免每个 key 一条 SELECT。
        valid = {key: value for key, value in payload.items() if key in SEO_CONFIG_KEYS}
        existing = {}
        if valid:
            existing_rows = await db.execute(
                select(SiteConfig).where(SiteConfig.key.in_(list(valid)))
            )
            existing = {row.key: row for row in existing_rows.scalars().all()}
        for key, value in valid.items():
            text = str(value) if value is not None else ""
            row = existing.get(key)
            if row is None:
                db.add(SiteConfig(key=key, value=text))
            else:
                row.value = text
        await db.commit()

    await cache.delete_pattern(make_cache_key("seo", "*"))
    await cache.delete_pattern(make_cache_key("site_config", "*"))
    await cache.delete_pattern(make_cache_key("site_config_value", "*"))

    return {"success": True, "message": "SEO 配置已更新", "data": await _get_all_seo_config()}


@router.post(
    "/sitemap/generate",
    summary="【管理员】强制重新生成 sitemap 缓存",
    description=(
        "清除 sitemap 相关缓存（含博客列表缓存前缀），下一次请求将重新生成。"
        "需 staff 及以上权限（未登录 401，非管理员 403）。本接口是异步失效而非同步重建，"
        "因此不返回 XML 内容，也不保证缓存已被预热。"
    ),
    responses={200: {"model": SeoCacheResetResponse}},
)
async def generate_sitemap_cache(_staff: CurrentStaff):
    await cache.delete_pattern(make_cache_key("sitemap", "*"))
    await cache.delete_pattern(make_cache_key("blog", "sitemap*"))
    return {"success": True, "message": "Sitemap 缓存已清除，下次访问将重新生成"}


@router.get(
    "/sitemap-check",
    summary="【管理员】校验 Sitemap 健康度",
    description=(
        "检查已发布文章是否具备 SEO 必要字段（标题 / 摘要 / 封面），返回校验结果与问题清单。"
        "需 staff 及以上权限（未登录 401，非管理员 403）。问题清单最多返回前 50 条，"
        "但 url_count 与 ok 的判定基于全量文章；无缓存，每次请求都会全表扫描已发布文章。"
    ),
    responses={200: {"model": SitemapCheckResponse}},
)
async def sitemap_check(_staff: CurrentStaff, db: DB):
    posts = (
        (
            await db.execute(
                select(Post)
                .options(defer(Post.content))
                .where(Post.status == "published")
                .order_by(Post.published_at.desc())
            )
        )
        .scalars()
        .all()
    )

    errors: list[str] = []
    for p in posts:
        title = _pick(p.title)
        if not title:
            errors.append(f"文章 #{p.id} 缺少标题")
        if not _pick(p.excerpt):
            errors.append(f"文章 #{p.id} 缺少摘要")
        if not p.cover_image:
            errors.append(f"文章 #{p.id} 缺少封面图")

    return {
        "success": True,
        "data": {
            "ok": len(errors) == 0,
            "url_count": len(posts),
            "errors": errors[:50],
        },
    }


@router.get(
    "/scores",
    summary="【管理员】文章 SEO 评分",
    description=(
        "对已发布文章进行 SEO 评分（标题长度、摘要、封面、内容长度、标签），分页返回。"
        "需 staff 及以上权限（未登录 401，非管理员 403）。评分在内存里对全量已发布文章计算后再切片，"
        "返回按得分升序排列（最需要改进的文章在前）；page_size 上限 100。"
    ),
    responses={200: {"model": SeoScoresResponse}},
)
async def seo_scores(
    _staff: CurrentStaff,
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    posts = (
        (
            await db.execute(
                select(Post)
                .options(selectinload(Post.tags))
                .where(Post.status == "published")
                .order_by(Post.published_at.desc())
            )
        )
        .scalars()
        .all()
    )

    def _score(p: Post) -> tuple[int, list[str]]:
        score = 0
        suggestions: list[str] = []
        title = _pick(p.title) or ""
        if not title:
            suggestions.append("补充文章标题")
        elif 10 <= len(title) <= 60:
            score += 25
        else:
            score += 10
            suggestions.append("标题长度建议控制在 10–60 字符")

        if _pick(p.excerpt):
            score += 20
        else:
            suggestions.append("补充文章摘要（excerpt）")

        if p.cover_image:
            score += 20
        else:
            suggestions.append("添加封面图以提升点击率")

        body = _pick(p.content) or ""
        if len(body) >= 300:
            score += 20
        elif len(body) >= 100:
            score += 10
            suggestions.append("正文偏短，建议不少于 300 字")
        else:
            suggestions.append("正文过短，建议不少于 300 字")

        if p.tags:
            score += 15
        else:
            suggestions.append("为文章添加至少一个标签")

        return min(score, 100), suggestions

    scored = []
    for p in posts:
        s, sug = _score(p)
        scored.append(
            {
                "id": p.id,
                "slug": p.slug,
                "title": _pick(p.title) or f"#{p.id}",
                "score": s,
                "suggestions": sug,
            }
        )
    scored.sort(key=lambda x: x["score"])

    total = len(scored)
    start = (page - 1) * page_size
    items = scored[start : start + page_size]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get(
    "/sitemap.xml",
    summary="SEO sitemap.xml（同 /api/blog/sitemap.xml）",
    description=(
        "从 SEO 模块对外暴露统一 sitemap 路径，避免前端路由不一致。公开访问、无需鉴权。"
        "索引含已发布文章（带 lastmod）、启用中的分类与标签；结果缓存 1 小时，"
        "命中缓存时直接回吐 XML 文本。Content-Type 为 application/xml。"
    ),
    response_class=Response,
    responses=raw_content_response(
        "application/xml", "Sitemap XML 文档（缓存版，与 /blog/sitemap.xml 同源）。"
    ),
)
async def seo_sitemap(db: DB) -> Response:
    """与 blog.py 中 get_sitemap 相同逻辑，提供 /api/seo/sitemap.xml 路径"""
    from backend.api.blog import generate_sitemap as _gen

    cache_key = make_cache_key("seo", "sitemap")
    cached = await cache.get(cache_key)
    if cached:
        return Response(content=cached, media_type="application/xml")

    posts = (
        (
            await db.execute(
                select(Post)
                .options(defer(Post.content))
                .where(Post.status == "published")
                .order_by(Post.published_at.desc())
            )
        )
        .scalars()
        .all()
    )
    categories = (await db.execute(select(Category))).scalars().all()
    tags = (await db.execute(select(Tag).where(Tag.is_active.is_(True)))).scalars().all()

    site_url = settings.site_url
    content = _gen(posts, categories, tags, site_url)
    await cache.set(cache_key, content, ttl=3600)
    return Response(content=content, media_type="application/xml")


@router.get(
    "/robots.txt",
    summary="robots.txt",
    description=(
        "动态生成 robots.txt 文件。公开访问、无需鉴权，返回 text/plain。"
        "优先取站点配置里维护的 robots 全文，缺省时输出默认规则（放行全站、"
        "屏蔽后台与接口目录、追加站点 sitemap 绝对地址）。结果缓存 1 小时。"
    ),
    response_class=PlainTextResponse,
    responses=raw_content_response("text/plain", "robots.txt 纯文本内容。"),
)
async def get_robots_txt() -> PlainTextResponse:
    """
    生成 robots.txt

    根据站点设置动态生成 robots.txt 内容。
    """
    # 检查缓存
    cached = await cache.get("robots_txt")
    if cached:
        return PlainTextResponse(content=cached)

    # 从站点配置获取或生成默认内容
    from backend.core.site_config import get_site_config_value

    robots_content = await get_site_config_value("ROBOTS_TXT")

    if not robots_content:
        # 默认 robots.txt（最佳实践）：与前端根级 Nitro 路由对齐
        site_url = (getattr(settings, "site_url", None) or "http://localhost:3000").rstrip("/")
        robots_content = f"""# robots.txt — generated by Rosetta Blog
# https://www.robotstxt.org/

User-agent: *
Allow: /

# 私密 / 管理路径
Disallow: /admin/
Disallow: /api/
Disallow: /login
Disallow: /register
Disallow: /oobe

# 搜索结果（参数化、noindex，避免重复内容）
Disallow: /search

# Sitemap（绝对 URL；索引内含 posts 分页 / taxonomies / pages 子表）
Sitemap: {site_url}/sitemap.xml
"""

    # 缓存 1 小时
    await cache.set("robots_txt", robots_content, 3600)

    return PlainTextResponse(content=robots_content)


@router.get(
    "/schema/{resource_type}/{resource_id}",
    summary="结构化数据",
    description=(
        "获取资源的 JSON-LD 结构化数据，公开访问、无需鉴权。"
        "resource_type 支持 article/post、person、website、breadcrumb，"
        "返回的 @type 相应为 Article / Person / WebSite / BreadcrumbList，"
        "其中 Article 会带上作者、发布方与所属分类；标题与摘要为服务端纯文本"
        "（已剥离短代码字面量与 HTML 标签）。"
        "资源不存在或类型不受支持时返回 200 且响应体只有 error 字段（不是 404），调用方需自行判空。"
        "breadcrumb 分支不查库，固定返回首页一项。"
    ),
    responses={200: {"model": JsonLdSchemaResponse}},
)
async def get_schema_data(
    resource_type: str,
    resource_id: int,
):
    """
    获取结构化数据

    支持 Article、Person、Organization、WebSite 等类型。
    """
    from sqlalchemy import select

    from backend.models.blog import Category, Post
    from backend.models.user import User

    if resource_type in ("article", "post"):
        async with async_session_maker() as db:
            result = await db.execute(select(Post).where(Post.id == resource_id))
            post = result.scalar_one_or_none()

            if not post:
                return {"error": "Article not found"}

            # 获取作者信息
            author = None
            if post.author_id:
                author_result = await db.execute(select(User).where(User.id == post.author_id))
                author = author_result.scalar_one_or_none()

            # 获取分类信息
            category = None
            if post.category_id:
                cat_result = await db.execute(
                    select(Category).where(Category.id == post.category_id)
                )
                category = cat_result.scalar_one_or_none()

            site_url = getattr(settings, "site_url", "http://localhost:4321")

            # 构建 Article 结构化数据
            schema = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": _pick(post.title),
                "description": _strip_for_meta(post.excerpt),
                "image": post.cover_image,
                "datePublished": post.published_at.isoformat() if post.published_at else None,
                "dateModified": post.updated_at.isoformat() if post.updated_at else None,
                "author": {
                    "@type": "Person",
                    "name": author.nickname or author.username if author else "Anonymous",
                    "url": f"{site_url}/users/{author.id}" if author else None,
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "Rosetta Blog",
                    "logo": {"@type": "ImageObject", "url": f"{site_url}/logo.png"},
                },
                "mainEntityOfPage": {"@type": "WebPage", "@id": f"{site_url}/post/{post.slug}"},
                "url": f"{site_url}/post/{post.slug}",
            }

            if category:
                schema["articleSection"] = category.name.get("zh", "") if category.name else ""

            return schema

    elif resource_type == "person":
        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == resource_id))
            user = result.scalar_one_or_none()

            if not user:
                return {"error": "Person not found"}

            site_url = getattr(settings, "site_url", "http://localhost:4321")

            schema = {
                "@context": "https://schema.org",
                "@type": "Person",
                "name": user.nickname or user.username,
                "image": user.avatar,
                "description": user.bio,
                "url": f"{site_url}/users/{user.id}",
                "sameAs": [
                    link
                    for link in [
                        user.github,
                        user.website,
                    ]
                    if link
                ],
            }

            return schema

    elif resource_type == "website":
        site_url = getattr(settings, "site_url", "http://localhost:4321")
        from backend.core.site_config import get_site_config_value

        site_name = await get_site_config_value("SITE_NAME") or "Rosetta Blog"
        site_description = await get_site_config_value("SITE_DESCRIPTION") or ""

        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site_name,
            "description": site_description,
            "url": site_url,
            "potentialAction": {
                "@type": "SearchAction",
                "target": f"{site_url}/search?q={{search_term_string}}",
                "query-input": "required name=search_term_string",
            },
        }

        return schema

    elif resource_type == "breadcrumb":
        # 面包屑导航结构化数据
        site_url = getattr(settings, "site_url", "http://localhost:4321")
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "首页", "item": site_url}
            ],
        }

    return {"error": "Unsupported resource type"}


@router.get(
    "/open-graph/{resource_type}/{resource_id}",
    summary="Open Graph 数据",
    description=(
        "获取资源的 Open Graph 元数据，公开访问、无需鉴权，"
        "用于社交媒体分享时显示预览。目前只对文章内容资源有实现，"
        "返回 og:* / article:* / twitter:* 三组键（键名含冒号，需按字面取值），"
        "返回 og:* / article:* / twitter:* 三组键（键名含冒号，需按字面取值），"
        "摘要在服务端剥离短代码与 HTML 标签后截断到前 200 字符。"
        "资源不存在或类型不受支持时返回 200 且响应体只有 error 字段（不是 404）。"
    ),
    responses={200: {"model": OpenGraphResponse}},
)
async def get_open_graph_data(
    resource_type: str,
    resource_id: int,
):
    """
    获取 Open Graph 元数据

    用于社交媒体分享时显示预览。
    """
    from sqlalchemy import select

    from backend.core.site_config import get_site_config_value
    from backend.models.blog import Post

    site_url = getattr(settings, "site_url", "http://localhost:4321")
    site_name = await get_site_config_value("SITE_NAME") or "Rosetta Blog"

    if resource_type in ("article", "post"):
        async with async_session_maker() as db:
            result = await db.execute(select(Post).where(Post.id == resource_id))
            post = result.scalar_one_or_none()

            if not post:
                return {"error": "Article not found"}

            title = _pick(post.title)
            description = _strip_for_meta(post.excerpt)

            return {
                "og:type": "article",
                "og:title": title,
                "og:description": description[:200] if description else "",
                "og:image": post.cover_image,
                "og:url": f"{site_url}/post/{post.slug}",
                "og:site_name": site_name,
                "og:locale": "zh_CN",
                "article:published_time": post.published_at.isoformat()
                if post.published_at
                else None,
                "article:modified_time": post.updated_at.isoformat() if post.updated_at else None,
                "article:author": f"{site_url}/users/{post.author_id}" if post.author_id else None,
                "twitter:card": "summary_large_image",
                "twitter:title": title,
                "twitter:description": description[:200] if description else "",
                "twitter:image": post.cover_image,
            }

    return {"error": "Unsupported resource type"}
