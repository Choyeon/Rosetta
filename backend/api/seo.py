"""
SEO 优化 API

提供 robots.txt、结构化数据、Open Graph、SEO 配置、Sitemap 生成 等 SEO 功能。
"""

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.auth import CurrentStaff
from backend.core.cache import CACHE_TTL, cache, make_cache_key
from backend.core.config import settings
from backend.core.database import async_session_maker
from backend.core.deps import DB
from backend.core.site_config import get_site_config_value
from backend.models.blog import Category, Post, Tag
from backend.models.core import SiteConfig

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


@router.get(
    "/config",
    summary="获取 SEO 配置",
    description="读取站点 SEO 相关配置（TITLE、DESCRIPTION、KEYWORDS 等），公开接口。",
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
    description="批量更新 SEO 配置 key-value，保存到 SiteConfig 表。",
)
async def update_seo_config(
    _staff: CurrentStaff,
    payload: dict[str, str] = Body(..., description="SEO key-value 集合"),
):
    """更新 SEO 配置"""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="参数必须是 object")

    async with async_session_maker() as db:
        for key, value in payload.items():
            if key not in SEO_CONFIG_KEYS:
                continue
            result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
            row = result.scalar_one_or_none()
            if row is None:
                db.add(SiteConfig(key=key, value=str(value) if value is not None else ""))
            else:
                row.value = str(value) if value is not None else ""
        await db.commit()

    await cache.delete_pattern(make_cache_key("seo", "*"))
    await cache.delete_pattern(make_cache_key("site_config", "*"))
    await cache.delete_pattern(make_cache_key("site_config_value", "*"))

    return {"success": True, "message": "SEO 配置已更新", "data": await _get_all_seo_config()}


@router.post(
    "/sitemap/generate",
    summary="【管理员】强制重新生成 sitemap 缓存",
    description="清除 sitemap 相关缓存，下一次请求将重新生成。",
)
async def generate_sitemap_cache(_staff: CurrentStaff):
    await cache.delete_pattern(make_cache_key("sitemap", "*"))
    await cache.delete_pattern(make_cache_key("blog", "sitemap*"))
    return {"success": True, "message": "Sitemap 缓存已清除，下次访问将重新生成"}


@router.get(
    "/sitemap-check",
    summary="【管理员】校验 Sitemap 健康度",
    description="检查已发布文章是否具备 SEO 必要字段（标题 / 摘要 / 封面），返回校验结果与问题清单。",
)
async def sitemap_check(_staff: CurrentStaff, db: DB):
    posts = (
        await db.execute(
            select(Post).where(Post.status == "published").order_by(Post.published_at.desc())
        )
    ).scalars().all()

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
    description="对已发布文章进行 SEO 评分（标题长度、摘要、封面、内容长度、标签），分页返回。",
)
async def seo_scores(
    _staff: CurrentStaff,
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    posts = (
        await db.execute(
            select(Post)
            .options(selectinload(Post.tags))
            .where(Post.status == "published")
            .order_by(Post.published_at.desc())
        )
    ).scalars().all()

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
    description="从 SEO 模块对外暴露统一 sitemap 路径，避免前端路由不一致。",
    response_class=Response,
)
async def seo_sitemap(db: DB):
    """与 blog.py 中 get_sitemap 相同逻辑，提供 /api/seo/sitemap.xml 路径"""
    from backend.api.blog import generate_sitemap as _gen

    cache_key = make_cache_key("seo", "sitemap")
    cached = await cache.get(cache_key)
    if cached:
        return Response(content=cached, media_type="application/xml")

    posts = (await db.execute(
        select(Post).where(Post.status == "published").order_by(Post.published_at.desc())
    )).scalars().all()
    categories = (await db.execute(select(Category))).scalars().all()
    tags = (await db.execute(select(Tag).where(Tag.is_active.is_(True)))).scalars().all()

    site_url = settings.site_url
    content = _gen(posts, categories, tags, site_url)
    await cache.set(cache_key, content, ttl=3600)
    return Response(content=content, media_type="application/xml")


@router.get(
    "/robots.txt",
    summary="robots.txt",
    description="动态生成 robots.txt 文件。",
    response_class=PlainTextResponse,
)
async def get_robots_txt():
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
        # 生成默认 robots.txt（与前端 /sitemap.xml Nitro 路由对齐）
        site_url = getattr(settings, "site_url", None) or "http://localhost:3000"
        robots_content = f"""User-agent: *
Allow: /

# 禁止访问管理后台
Disallow: /admin/
Disallow: /api/admin/

# 禁止访问用户私密页面
Disallow: /users/me/

# Sitemap（前端 Nitro server route 根级映射，非 /api 嵌套）
Sitemap: {site_url}/sitemap.xml

# Crawl-delay
Crawl-delay: 1
"""

    # 缓存 1 小时
    await cache.set("robots_txt", robots_content, 3600)

    return PlainTextResponse(content=robots_content)


@router.get(
    "/schema/{resource_type}/{resource_id}",
    summary="结构化数据",
    description="获取资源的 JSON-LD 结构化数据。",
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

            site_url = (
                getattr(settings, "site_url", "http://localhost:4321")
            )

            # 构建 Article 结构化数据
            schema = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": post.title.get("zh", "") if post.title else "",
                "description": post.excerpt.get("zh", "") if post.excerpt else "",
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

            site_url = (
                getattr(settings, "site_url", "http://localhost:4321")
            )

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
    description="获取资源的 Open Graph 元数据。",
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

            title = post.title.get("zh", "") if post.title else ""
            description = post.excerpt.get("zh", "") if post.excerpt else ""

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
