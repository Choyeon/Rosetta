"""
博客管理 API

提供文章、分类、标签、评论的 CRUD 操作。
支持多语言内容返回和智能缓存。

缓存策略：
- 文章列表：5 分钟
- 文章详情：10 分钟
- 分类列表：10 分钟
- 标签列表：10 分钟
"""

import json
import math
import re
from datetime import datetime
from types import SimpleNamespace

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from backend.core.auth import DB, CurrentStaff, CurrentUser, CurrentUserOptional
from backend.core.cache import (
    CACHE_KEY_CATEGORIES,
    CACHE_KEY_TAGS,
    CACHE_TTL,
    cache,
    invalidate_cache,
    invalidate_post_detail_cache,
    make_cache_key,
)
from backend.core.concurrency import concurrent_query
from backend.core.config import settings
from backend.core.i18n import (
    get_i18n_value,
    get_language_from_request,
)
from backend.core.plugin_bus import bus
from backend.services.content_renderer import (
    render_content,
    render_excerpt,
    render_post_fields,
    render_title,
)
from backend.services.post_cache import (
    invalidate_post_aggregate_caches,
    invalidate_post_caches_by_slugs,
)
from backend.services.post_revision import (
    has_content_change,
    snapshot_post_revision,
)

# 20 curated tag colors — modern palette with balanced saturation for light/dark modes.
_TAG_PALETTE = [
    "#3B82F6",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#EC4899",
    "#06B6D4",
    "#84CC16",
    "#F97316",
    "#6366F1",
    "#14B8A6",
    "#E11D48",
    "#0EA5E9",
    "#A855F7",
    "#22C55E",
    "#D946EF",
    "#0891B2",
    "#CA8A04",
    "#DC2626",
    "#7C3AED",
]
from backend.models.blog import Category, Comment, Post, Tag, post_likes, post_tags
from backend.models.log import TrashItem
from backend.models.user import User, UserPreference
from backend.schemas import (
    BaseResponse,
    BatchPostStatusResponse,
    BatchPostStatusUpdate,
    CategoryCreate,
    CategoryLocalizedResponse,
    CategoryResponse,
    CategoryUpdate,
    CommentCreate,
    CommentResponse,
    PaginatedResponse,
    PostCreate,
    PostEditResponse,
    PostListItemLocalized,
    PostLocalizedResponse,
    PostUpdate,
    TagCreate,
    TagLocalizedResponse,
    TagResponse,
    TagUpdate,
    raw_content_response,
)
from backend.schemas.blog_reads import (
    ArchiveMonthGroup,
    ArchiveMonthPage,
    ArchiveStats,
    PostAdjacentResponse,
    SiteStats,
    UserBlogStatsResponse,
)
from backend.services.comment_service import _comment_to_response
from backend.utils.compat import UTC, parse_utc_date, timedelta
from backend.utils.reading_time import compute_reading_time_from_content

router = APIRouter(tags=["博客"])


# OOBE 状态判断统一委托给 backend.core.deps，避免各模块重复定义常量导致
# 状态源不一致（以及测试时无法统一重定向路径）。

# ── RSS / Sitemap 共享工具 ───────────────────────────────────────────────

from datetime import timezone as _tz

from backend.core.deps import is_oobe_complete  # noqa: E402
from backend.core.partial_update import apply_partial_update

_RSS_NS = "http://www.w3.org/2005/Atom"
_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
_DC_NS = "http://purl.org/dc/elements/1.1/"
_MEDIA_NS = "http://search.yahoo.com/mrss/"


def _public_site_url() -> str:
    """对外站点根 URL（去尾斜杠）。RSS/Sitemap 中的绝对 URL 一律基于它。"""
    return (getattr(settings, "site_url", None) or "http://localhost:3000").rstrip("/")


def _ensure_aware(dt: datetime | None) -> datetime | None:
    """无时区的 datetime 一律假定为 UTC。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_tz.utc)
    return dt


def _rfc822(dt: datetime | None) -> str | None:
    """RFC 822 日期（RSS pubDate/lastBuildDate 要求），例：Wed, 02 Oct 2024 13:00:00 +0000。"""
    aware = _ensure_aware(dt)
    if aware is None:
        return None
    return aware.strftime("%a, %d %b %Y %H:%M:%S %z")


def _cdata(text: str) -> str:
    """安全包裹 CDATA；内容若含 ``]]>`` 需拆分转义，避免提前闭合。"""
    safe = (text or "").replace("]]>", "]]&gt;")
    return f"<![CDATA[{safe}]]>"


def _absolute_media(url: str | None, site_url: str) -> str | None:
    """把相对媒体路径转成绝对 URL。"""
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("/"):
        return site_url + url
    return site_url + "/" + url


def _rss_language(code: str) -> str:
    """内部语言码 → RSS 语言码（下划线改连字符）。"""
    return (code or "en").replace("_", "-")


async def generate_rss_feed(
    posts: list[Post], language: str, site_url: str, site_title: str
) -> str:
    """生成 RSS 2.0 订阅源（最佳实践版）。

    - Atom ``self`` 自链接（feed validator 必需）
    - 每篇包含 ``description``（摘要）与 ``content:encoded``（完整正文）
    - HTML 内容一律 CDATA 包裹，避免转义问题
    - ``dc:creator`` 作者、``category`` 分类、``enclosure`` + ``media:content`` 封面
    - ``lastBuildDate`` 取最新文章时间，而非服务器当前时间

    正文/摘要走统一渲染管线（短代码 + ``the_content`` / ``the_excerpt`` filter），
    与文章详情口径一致，插件的正文过滤器在订阅源里同样生效。刻意不触发
    ``post.rendered`` action：一次抓取最多涉及 ``limit``（≤100）篇文章，
    逐篇发通知会让订阅端点变成副作用风暴，且结果还会被缓存 300s。
    """
    site_url = site_url.rstrip("/")
    rss_lang = _rss_language(language)
    now_rfc = _rfc822(datetime.now(_tz.utc))

    # 最新一篇的发布时间作为 lastBuildDate
    newest: datetime | None = None
    for p in posts:
        candidate = p.published_at or p.created_at
        if candidate is not None and (newest is None or candidate > newest):
            newest = candidate

    lines: list[str] = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(
        '<rss version="2.0" '
        f'xmlns:atom="{_RSS_NS}" '
        f'xmlns:content="{_CONTENT_NS}" '
        f'xmlns:dc="{_DC_NS}" '
        f'xmlns:media="{_MEDIA_NS}">'
    )
    lines.append("  <channel>")
    lines.append(f"    <title>{_xml_escape(site_title)}</title>")
    lines.append(f"    <link>{_xml_escape(site_url)}/</link>")
    lines.append(f"    <description>{_cdata(f'{site_title} 最新文章')}</description>")
    lines.append(f"    <language>{rss_lang}</language>")
    # Atom self 链接：指向本 feed 的稳定 URL
    lines.append(
        f'    <atom:link href="{_xml_escape(site_url)}/rss.xml" '
        'rel="self" type="application/rss+xml" />'
    )
    if newest is not None:
        lines.append(f"    <lastBuildDate>{_rfc822(newest)}</lastBuildDate>")
    if now_rfc:
        lines.append(f"    <pubDate>{now_rfc}</pubDate>")
    lines.append("    <generator>Rosetta Blog</generator>")
    lines.append("    <docs>https://www.rssboard.org/rss-specification</docs>")
    lines.append("    <ttl>60</ttl>")

    for post in posts:
        # 标题同样过 the_title 链：详情有后缀而 feed 没有，会让订阅端与站内显示分叉。
        title = (
            await render_title(get_i18n_value(post.title, language), post=post, language=language)
            or post.slug
        )
        link = f"{site_url}/posts/{post.slug}"
        pub_dt = post.published_at or post.created_at

        # 摘要：优先 excerpt，否则从正文截取纯文本
        raw_excerpt = get_i18n_value(post.excerpt, language)
        full_html = await render_content(
            get_i18n_value(post.content, language) or "", post=post, language=language
        )
        if raw_excerpt:
            excerpt_html = await render_excerpt(raw_excerpt, post=post, language=language)
        else:
            text_only = re.sub(r"<[^>]+>", "", full_html).strip()
            excerpt_html = (text_only[:200] + "…") if len(text_only) > 200 else text_only

        lines.append("    <item>")
        lines.append(f"      <title>{_cdata(title)}</title>")
        lines.append(f"      <link>{_xml_escape(link)}</link>")
        lines.append(f'      <guid isPermaLink="true">{_xml_escape(link)}</guid>')
        if pub_dt is not None:
            lines.append(f"      <pubDate>{_rfc822(pub_dt)}</pubDate>")
        lines.append(f"      <description>{_cdata(excerpt_html)}</description>")
        lines.append(f"      <content:encoded>{_cdata(full_html)}</content:encoded>")

        # 作者：RSS <author> 需要邮箱，使用 dc:creator 输出名字更通用
        author_name = None
        if post.author is not None:
            author_name = post.author.nickname or post.author.username
        if author_name:
            lines.append(f"      <dc:creator>{_cdata(author_name)}</dc:creator>")

        # 分类
        cat_name = None
        if post.category is not None:
            cat_name = get_i18n_value(post.category.name, language) or post.category.slug
        if cat_name:
            lines.append(f"      <category>{_cdata(cat_name)}</category>")

        # 封面：enclosure（RSS 2.0）+ media:content（MRSS，阅读器友好）
        cover = _absolute_media(post.cover_image, site_url)
        if cover:
            lines.append(
                f'      <enclosure url="{_xml_escape(cover)}" length="0" type="image/jpeg" />'
            )
            lines.append(
                f'      <media:content url="{_xml_escape(cover)}" type="image/jpeg" medium="image" />'
            )

        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines)


def generate_slug(title: str) -> str:
    """
    生成 SEO 友好的 slug

    - 中文转拼音
    - 小写字母
    - 连字符分隔
    - 去除特殊字符
    - 限制长度 100 字符
    """
    import uuid

    from pypinyin import lazy_pinyin

    # 中文转拼音
    if re.search(r"[\u4e00-\u9fa5]", title):
        pinyin_list = lazy_pinyin(title)
        slug = "-".join(pinyin_list)
    else:
        slug = title.lower()

    # 清理特殊字符
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")

    # 限制长度
    if len(slug) > 100:
        slug = slug[:100].rstrip("-")

    # 空 slug 处理
    if not slug:
        slug = uuid.uuid4().hex[:8]

    return slug


async def _get_post_list_cache_key(
    language: str,
    page: int,
    page_size: int,
    category: str | None,
    tag: str | None,
    search: str | None,
    status_filter: str | None,
    author: str | None = None,
) -> str:
    """生成文章列表缓存键"""
    parts = [
        "posts",
        language,
        f"p{page}",
        f"ps{page_size}",
        f"c{category or 'all'}",
        f"t{tag or 'all'}",
        f"s{search or 'none'}",
        f"st{status_filter or 'published'}",
        # 作者归档必须自成一条键：少了这一段，A 作者的列表会被当作全站/其他作者的结果命中。
        f"a{author or 'all'}",
    ]
    return make_cache_key(*parts)


def _build_author_data(author: User | None) -> dict | None:
    """构建作者数据字典"""
    if not author:
        return None
    # 序列化头衔为纯 dict（避免 SQLAlchemy ORM 对象在 JSON 序列化时出问题）
    title_data = None
    if author.title:
        title_data = {
            "id": author.title.id,
            "name": author.title.name,
            "icon": author.title.icon,
            "color": author.title.color,
            "description": author.title.description,
        }
    return {
        # 字段清单必须与 schemas.PublicUserResponse 对齐：
        # email / qq / is_active / is_staff / is_superuser / role / last_login
        # 属于账号隐私与权限信息，文章列表与详情是匿名可访的公开端点，一律不外发。
        "id": author.id,
        "username": author.username,
        "nickname": author.nickname,
        "avatar": author.avatar,
        "bio": author.bio,
        "website": author.website,
        "github": author.github,
        "cover_image": author.cover_image,
        "created_at": author.created_at,
        "title": title_data,
    }


async def _build_post_list_item_from_row(
    row: tuple,
    language: str,
) -> PostListItemLocalized:
    """从查询结果行构建文章列表项（优化版，避免 N+1 查询）。

    注意：列表查询应 defer(Post.content)，reading_time 直接取持久化列。
    摘要走统一渲染管线（短代码 + ``the_excerpt`` filter），与详情口径一致。
    """
    post = row.Post
    likes_count = row.likes_count or 0
    comments_count = row.comments_count or 0

    raw_excerpt = get_i18n_value(post.excerpt, language) if post.excerpt else None
    excerpt = await render_excerpt(raw_excerpt, post=post, language=language)

    return PostListItemLocalized(
        id=post.id,
        title=await render_title(
            get_i18n_value(post.title, language), post=post, language=language
        ),
        subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
        slug=post.slug,
        excerpt=excerpt,
        cover_image=post.cover_image,
        author=_build_author_data(post.author),
        category=CategoryLocalizedResponse.from_category(post.category, language)
        if post.category
        else None,
        tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
        status=post.status,
        views=post.views,
        likes_count=likes_count,
        comments_count=comments_count,
        is_pinned=post.is_pinned,
        created_at=post.created_at,
        published_at=post.published_at,
        reading_time=post.reading_time or 1,
    )


async def _build_post_list_item(
    post: Post,
    db: DB,
    language: str,
    *,
    likes_count: int | None = None,
    comments_count: int | None = None,
) -> dict:
    """从 Post 对象构建文章列表项（用于点赞列表等场景）。

    若传入 ``likes_count`` / ``comments_count`` 则直接使用（批量预取场景），
    否则回退到当场补查（两条 count，顺序执行）。
    """
    from backend.models.blog import Comment, post_likes

    if likes_count is None or comments_count is None:
        likes_count, comments_count = await concurrent_query(
            db.scalar(
                select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post.id)
            ),
            db.scalar(
                select(func.count())
                .select_from(Comment)
                .where(Comment.post_id == post.id, Comment.active.is_(True))
            ),
        )

    likes_count = likes_count or 0
    comments_count = comments_count or 0

    raw_excerpt = get_i18n_value(post.excerpt, language) if post.excerpt else None
    excerpt = await render_excerpt(raw_excerpt, post=post, language=language)

    return {
        "id": post.id,
        "title": await render_title(
            get_i18n_value(post.title, language), post=post, language=language
        ),
        "subtitle": get_i18n_value(post.subtitle, language) if post.subtitle else None,
        "slug": post.slug,
        "excerpt": excerpt,
        "cover_image": post.cover_image,
        "author": _build_author_data(post.author),
        "category": CategoryLocalizedResponse.from_category(post.category, language).model_dump()
        if post.category
        else None,
        "tags": [TagLocalizedResponse.from_tag(t, language).model_dump() for t in post.tags],
        "status": post.status,
        "views": post.views,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "is_pinned": post.is_pinned,
        "created_at": post.created_at,
        "published_at": post.published_at,
        "reading_time": post.reading_time or 1,
    }


# ==================== 文章接口 ====================


@router.get(
    "/posts",
    response_model=PaginatedResponse,
    summary="文章列表",
    description=(
        "获取文章列表，支持分类、标签、作者（用户名）筛选和关键词搜索。支持多语言返回。"
        "`author` 走作者归档口径：作者不存在返回空页（不 404，让资料接口负责 404）；"
        "作者把 `show_posts` 关掉后，非本人/非管理员同样返回空页（与 "
        "`GET /users/{user_id}/posts` 同一道隐私闸门）。"
    ),
)
async def list_posts(
    request: Request,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=200, description="每页数量"),
    category: str | None = Query(None, description="分类 slug"),
    tag: str | None = Query(None, description="标签 slug"),
    author: str | None = Query(None, max_length=150, description="作者用户名（作者归档）"),
    search: str | None = Query(None, description="搜索关键词"),
    status_filter: str | None = Query(None, alias="status", description="文章状态（需管理员权限）"),
    post_type: str | None = Query(None, description="内容类型（自定义文章类型 key，默认 post）"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
    created_start: str | None = Query(
        None, alias="created_start", description="创建开始日期 ISO（含边界）"
    ),
    created_end: str | None = Query(
        None, alias="created_end", description="创建结束日期 ISO（含边界）"
    ),
    current_user: CurrentUserOptional = None,
):
    """获取文章列表，支持多语言和缓存

    优化：使用子查询批量统计点赞数和评论数，避免 N+1 查询
    """
    if not is_oobe_complete():
        return PaginatedResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
        )

    language = get_language_from_request(request, lang)

    is_admin = bool(current_user and (current_user.is_staff or current_user.is_superuser))

    # 作者归档闸门（与 GET /users/{user_id}/posts 同一口径）：
    #   用户名查无此人 → 空页（404 由资料接口负责，列表不替它表态）；
    #   作者关了 show_posts → 非本人、非管理员同样空页；
    #   作者关了 public_profile → 同样空页：他的 /authors/<u> 主页对访客是 404、
    #   也已从 sitemap 剔除，留着这份列表等于给一个"不存在"的归档继续供数据。
    # 无偏好行按"可见"处理，和 UserPreference 的建表默认一致。
    author_id: int | None = None
    if author:
        author_id = await db.scalar(select(User.id).where(User.username == author))
        if author_id is None:
            return PaginatedResponse(
                items=[], total=0, page=page, page_size=page_size, total_pages=0
            )
        switches = (
            await db.execute(
                select(UserPreference.show_posts, UserPreference.public_profile).where(
                    UserPreference.user_id == author_id
                )
            )
        ).first()
        archive_hidden = switches is not None and (
            switches.show_posts is False or switches.public_profile is False
        )
        is_self = bool(current_user and current_user.id == author_id)
        if archive_hidden and not is_self and not is_admin:
            return PaginatedResponse(
                items=[], total=0, page=page, page_size=page_size, total_pages=0
            )

    # Admin 传 status=all 或不传 status → 返回全部状态；普通用户始终只看 published
    admin_all_statuses = is_admin and (not status_filter or status_filter == "all")
    # 本人看自己的归档页会绕过隐私闸门，这条结果不能进公共缓存（缓存键不含查看者）。
    viewer_is_author = bool(author_id and current_user and current_user.id == author_id)
    use_cache = (
        not is_admin
        and not search
        and not created_start
        and not created_end
        and not viewer_is_author
    )

    if use_cache:
        cache_key = await _get_post_list_cache_key(
            language, page, page_size, category, tag, search, status_filter, author
        )
        cached = await cache.get(cache_key)
        if cached:
            return cached

    likes_subq = (
        select(post_likes.c.post_id, func.count().label("count"))
        .group_by(post_likes.c.post_id)
        .subquery()
    )

    comments_subq = (
        select(Comment.post_id, func.count().label("count"))
        .where(Comment.active.is_(True))
        .group_by(Comment.post_id)
        .subquery()
    )

    query = (
        select(
            Post,
            func.coalesce(likes_subq.c.count, 0).label("likes_count"),
            func.coalesce(comments_subq.c.count, 0).label("comments_count"),
        )
        .options(
            selectinload(Post.author).selectinload(User.title),
            selectinload(Post.category),
            selectinload(Post.tags),
            # 列表接口不展示正文，defer 大字段减少 DB I/O 与网络传输
            defer(Post.content),
            defer(Post.encrypted_content),
            defer(Post.meta_fields),
            defer(Post.meta_title),
            defer(Post.meta_description),
            defer(Post.meta_keywords),
        )
        .outerjoin(likes_subq, Post.id == likes_subq.c.post_id)
        .outerjoin(comments_subq, Post.id == comments_subq.c.post_id)
    )

    if is_admin:
        if not admin_all_statuses:
            query = query.where(Post.status == status_filter)
        # admin_all_statuses=True → 不加 status 过滤，返回全部状态
    else:
        query = query.where(
            Post.status == "published",
            (Post.published_at.is_(None) | (Post.published_at <= func.now())),
        )

    if category:
        query = query.join(Category).where(Category.slug == category)

    if tag:
        query = query.join(Post.tags).where(Tag.slug == tag)

    # 作者归档：用已解析的 author_id 过滤（走 idx 已有的 author_id 列，不再 JOIN users）
    if author_id is not None:
        query = query.where(Post.author_id == author_id)

    # 内容类型过滤：不传时默认只列博客文章（post），保持向后兼容
    if post_type:
        query = query.where(Post.post_type == post_type)
    else:
        query = query.where(Post.post_type == "post")

    # 创建日期范围过滤
    from_dt = parse_utc_date(created_start)
    to_dt = parse_utc_date(created_end)
    if from_dt:
        query = query.where(Post.created_at >= from_dt)
    if to_dt:
        # 结束日期扩展到当天 23:59:59.999 以包含整天
        from backend.utils.compat import timedelta as _td

        end_of_day = to_dt + _td(days=1) - _td(microseconds=1)
        query = query.where(Post.created_at <= end_of_day)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                cast(Post.title["zh"], String).ilike(search_term),
                cast(Post.title["en"], String).ilike(search_term),
                cast(Post.content["zh"], String).ilike(search_term),
                cast(Post.content["en"], String).ilike(search_term),
                cast(Post.excerpt["zh"], String).ilike(search_term),
                cast(Post.excerpt["en"], String).ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    if search and total > 0:
        # —— BM25 搜索重排：粗召回（至少 page*page_size*4，最少 50，上限 200）→ 打分 → 分页切片 ——
        from backend.services.recommendation import RecommendationService

        search_candidates_cap = min(total, max(50, page * page_size * 4))
        if search_candidates_cap > 200:
            search_candidates_cap = 200

        coarse_q = query.order_by(Post.is_pinned.desc(), Post.published_at.desc()).limit(
            search_candidates_cap
        )
        coarse_result = await db.execute(coarse_q)
        coarse_rows = coarse_result.unique().all()
        coarse_posts = [row.Post for row in coarse_rows]

        rec_svc = RecommendationService(db)
        scored = await rec_svc.search_rerank(search, coarse_posts, language)
        # 先按 BM25 分数降序，同分保留原时间新鲜度相对顺序（is_pinned 仍优先——在 coarse_rows 先头保持）
        row_by_post_id = {row.Post.id: row for row in coarse_rows}
        scored.sort(
            key=lambda pair: (
                -pair[1],
                pair[0].is_pinned is False,
                -(pair[0].published_at or pair[0].created_at).timestamp()
                if (pair[0].published_at or pair[0].created_at)
                else 0,
            )
        )

        start = (page - 1) * page_size
        end = start + page_size
        page_post_rows = [row_by_post_id[p.id] for p, _score in scored[start:end]]
        items = [await _build_post_list_item_from_row(row, language) for row in page_post_rows]
    else:
        query = (
            query.offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(Post.is_pinned.desc(), Post.published_at.desc())
        )

        result = await db.execute(query)
        rows = result.unique().all()

        items = [await _build_post_list_item_from_row(row, language) for row in rows]

    response = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )

    ttl_key = "search_results" if search else "post_list"
    if use_cache:
        await cache.set(
            cache_key,
            response.model_dump(mode="json"),
            CACHE_TTL.get(ttl_key, CACHE_TTL["post_list"]),
        )

    return response


# ==================== 推荐系统接口 ====================


@router.get(
    "/posts/recommended",
    response_model=PaginatedResponse,
    summary="推荐文章列表",
    description="获取推荐文章列表，基于浏览量、点赞数、评论数、时间衰减和标签匹配的综合算法。",
)
async def get_recommended_posts(
    request: Request,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=100, description="每页数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
    current_user: CurrentUserOptional = None,
):
    """
    获取推荐文章列表

    推荐算法权重：
    - 浏览量: 30%
    - 点赞数: 20%
    - 评论数: 15%
    - 时间衰减: 25%
    - 标签匹配: 10%（基于用户浏览历史）
    """
    from backend.services.recommendation import RecommendationService

    language = get_language_from_request(request, lang)
    user_id = current_user.id if current_user else None

    service = RecommendationService(db)
    result = await service.get_recommended_posts(
        user_id=user_id,
        page=page,
        page_size=page_size,
    )

    items = []
    posts_list = result["items"]
    # 批量聚合 likes / comments（单次 SQL 汇总，避免逐篇 N+1 查询）
    ids = [p.id for p in posts_list]
    if ids:
        likes_raw = await db.execute(
            select(post_likes.c.post_id, func.count())
            .where(post_likes.c.post_id.in_(ids))
            .group_by(post_likes.c.post_id)
        )
        likes_map = {pid: cnt for pid, cnt in likes_raw.fetchall()}
        comments_raw = await db.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(ids), Comment.active.is_(True))
            .group_by(Comment.post_id)
        )
        comments_map = {pid: cnt for pid, cnt in comments_raw.fetchall()}
    else:
        likes_map, comments_map = {}, {}

    for post in posts_list:
        raw_excerpt = get_i18n_value(post.excerpt, language) if post.excerpt else None
        excerpt = await render_excerpt(raw_excerpt, post=post, language=language)

        items.append(
            PostListItemLocalized(
                id=post.id,
                title=await render_title(
                    get_i18n_value(post.title, language), post=post, language=language
                ),
                subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
                slug=post.slug,
                excerpt=excerpt,
                cover_image=post.cover_image,
                author=_build_author_data(post.author),
                category=CategoryLocalizedResponse.from_category(post.category, language)
                if post.category
                else None,
                tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
                status=post.status,
                views=post.views,
                likes_count=likes_map.get(post.id, 0),
                comments_count=comments_map.get(post.id, 0),
                is_pinned=post.is_pinned,
                created_at=post.created_at,
                published_at=post.published_at,
                reading_time=post.reading_time or 1,
            )
        )

    return PaginatedResponse(
        items=[item.model_dump() for item in items],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.get(
    "/posts/{post_id}/similar",
    response_model=list[PostListItemLocalized],
    summary="相似文章推荐",
    description="获取与当前文章相似的推荐文章，基于标签和分类匹配。",
)
async def get_similar_posts(
    post_id: int,
    request: Request,
    db: DB,
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取相似文章推荐"""
    from backend.services.recommendation import RecommendationService

    language = get_language_from_request(request, lang)

    service = RecommendationService(db)
    posts = await service.get_similar_posts(post_id=post_id, limit=limit)

    items = []
    # 批量聚合 likes / comments（单次 SQL 汇总，避免逐篇 N+1 查询）
    ids = [p.id for p in posts]
    if ids:
        likes_raw = await db.execute(
            select(post_likes.c.post_id, func.count())
            .where(post_likes.c.post_id.in_(ids))
            .group_by(post_likes.c.post_id)
        )
        likes_map = {pid: cnt for pid, cnt in likes_raw.fetchall()}
        comments_raw = await db.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(ids), Comment.active.is_(True))
            .group_by(Comment.post_id)
        )
        comments_map = {pid: cnt for pid, cnt in comments_raw.fetchall()}
    else:
        likes_map, comments_map = {}, {}

    for post in posts:
        raw_excerpt = get_i18n_value(post.excerpt, language) if post.excerpt else None
        excerpt = await render_excerpt(raw_excerpt, post=post, language=language)

        items.append(
            PostListItemLocalized(
                id=post.id,
                title=await render_title(
                    get_i18n_value(post.title, language), post=post, language=language
                ),
                subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
                slug=post.slug,
                excerpt=excerpt,
                cover_image=post.cover_image,
                author=_build_author_data(post.author),
                category=CategoryLocalizedResponse.from_category(post.category, language)
                if post.category
                else None,
                tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
                status=post.status,
                views=post.views,
                likes_count=likes_map.get(post.id, 0),
                comments_count=comments_map.get(post.id, 0),
                is_pinned=post.is_pinned,
                created_at=post.created_at,
                published_at=post.published_at,
                reading_time=post.reading_time or 1,
            )
        )

    return items


@router.get(
    "/posts/hot",
    response_model=list[PostListItemLocalized],
    summary="热门文章（HackerNews 风格热榜）",
    description="按 HackerNews 公式的综合热度排序：（浏览 + 点赞×10 + 评论×20）/(发布小时+2)^1.8。",
)
async def list_hot_posts(
    request: Request,
    db: DB,
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    days: int = Query(30, ge=1, le=365, description="时间窗口（天）"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """HN 风格热榜（走推荐服务的热榜缓存）。"""
    from backend.services.recommendation import RecommendationService

    language = get_language_from_request(request, lang)
    service = RecommendationService(db)
    posts = await service.get_hot_posts(limit=limit, days=days)

    # 批量聚合 likes / comments（推荐服务没返回这些，单次 SQL 汇总即可）
    ids = [p.id for p in posts]
    if ids:
        likes_raw = await db.execute(
            select(post_likes.c.post_id, func.count())
            .where(post_likes.c.post_id.in_(ids))
            .group_by(post_likes.c.post_id)
        )
        likes_map = {pid: cnt for pid, cnt in likes_raw.fetchall()}
        comments_raw = await db.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(ids), Comment.active.is_(True))
            .group_by(Comment.post_id)
        )
        comments_map = {pid: cnt for pid, cnt in comments_raw.fetchall()}
    else:
        likes_map, comments_map = {}, {}

    items: list[PostListItemLocalized] = []
    for post in posts:
        raw_excerpt = get_i18n_value(post.excerpt, language) if post.excerpt else None
        excerpt = await render_excerpt(raw_excerpt, post=post, language=language)
        items.append(
            PostListItemLocalized(
                id=post.id,
                title=await render_title(
                    get_i18n_value(post.title, language), post=post, language=language
                ),
                subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
                slug=post.slug,
                excerpt=excerpt,
                cover_image=post.cover_image,
                author=_build_author_data(post.author),
                category=CategoryLocalizedResponse.from_category(post.category, language)
                if post.category
                else None,
                tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
                status=post.status,
                views=post.views,
                likes_count=int(likes_map.get(post.id, 0) or 0),
                comments_count=int(comments_map.get(post.id, 0) or 0),
                is_pinned=post.is_pinned,
                created_at=post.created_at,
                published_at=post.published_at,
                reading_time=post.reading_time or 1,
            )
        )
    return items


@router.get(
    "/posts/{slug}/adjacent",
    summary="上一篇/下一篇",
    description="按发布时间线获取当前公开文章的上一篇（更早）与下一篇（更晚），仅包含已发布且已到发布时间的文章。",
    responses={200: {"model": PostAdjacentResponse}},
)
async def get_post_adjacent(
    slug: str,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取同时间线上的相邻文章（用于文章详情页上下篇导航）。"""
    from datetime import datetime

    language = get_language_from_request(request, lang)

    published_key = func.coalesce(Post.published_at, Post.created_at)

    # 锚点行只需要 (id, published_at, created_at)：整行 select(Post) 会把
    # content / content_html 这些大字段一起拖过来，而本端点每次文章页渲染都要跑一遍。
    def _anchor_stmt(by_id: bool):
        cond = Post.id == int(slug) if by_id else Post.slug == slug
        return select(Post.id, Post.published_at, Post.created_at).where(
            cond, Post.status == "published"
        )

    row = (await db.execute(_anchor_stmt(False))).first()
    if row is None and slug.isdigit():
        row = (await db.execute(_anchor_stmt(True))).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    post_id, anchor = row[0], (row[1] or row[2])
    # "已到达发布时间"的判定只取一次 now：两侧各取一次会让上下篇边界在同一请求内漂移。
    now = datetime.now()

    async def _neighbor(older: bool) -> dict | None:
        if older:
            cond = (published_key < anchor) | ((published_key == anchor) & (Post.id < post_id))
            order = published_key.desc()
        else:
            cond = (published_key > anchor) | ((published_key == anchor) & (Post.id > post_id))
            order = published_key.asc()
        row = (
            await db.execute(
                select(Post.slug, Post.title)
                .where(
                    Post.status == "published",
                    published_key <= now,
                    cond,
                )
                .order_by(order)
                .limit(1)
            )
        ).first()
        if row is None:
            return None
        # 上下篇标题同为读者侧显示面：不过 the_title 链会与详情页分叉。
        return {
            "slug": row[0],
            "title": await render_title(get_i18n_value(row[1], language), language=language),
        }

    return {
        "success": True,
        "data": {
            "previous": await _neighbor(older=True),
            "next": await _neighbor(older=False),
        },
    }


@router.get(
    "/posts/{slug}",
    response_model=PostLocalizedResponse,
    summary="文章详情",
    description="根据 slug 获取文章详情，自动增加阅读量。支持多语言返回。加密文章需要提供密码。",
)
async def get_post(
    slug: str,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
    x_post_password: str | None = Header(
        None, alias="X-Post-Password", description="文章访问密码（推荐通过 Header 传输）"
    ),
    password: str | None = Query(
        None,
        description="文章访问密码（兼容旧参数，建议改用 X-Post-Password Header）",
        deprecated=True,
    ),
    current_user: CurrentUserOptional = None,
):
    """获取文章详情，支持多语言和缓存
    智能识别 slug：纯数字自动按 ID 查询，否则按 slug 查询。
    """
    language = get_language_from_request(request, lang)

    cache_key = make_cache_key("post", slug, language)

    slug_is_numeric = slug.isdigit()

    # 缓存读：本端点是全站 QPS 最高的查询，此前只写不读（每次请求跑完整查询图 + 渲染管线，
    # 再白白 SET 一次）。命中条件被刻意压到最窄，任何一条不满足即回落到完整路径：
    #   - 匿名访客：作者/编辑要能即时看到草稿与排期预览，登录态一律走慢路径；
    #   - 按 slug 取：数字 ID 形式的 URL 与规范 slug 同文不同键，写侧无法被 update 精确失效；
    #   - 仅"公开可见"内容：见函数末尾的写侧门禁，读写两侧口径必须一致。
    # 计数不落缓存是刻意保留的实时项：voting/评论写入不会失效本键，若沿用缓存值会出现
    # "点赞后计数十分钟不动"。views 只能取缓存快照（DB 侧仍是原子自增），与列表页既有口径一致。
    if current_user is None and not slug_is_numeric:
        cached = await cache.get(cache_key)
        if isinstance(cached, dict) and cached.get("id") is not None:
            post_id = cached["id"]
            likes_count, comments_count = await concurrent_query(
                db.scalar(
                    select(func.count())
                    .select_from(post_likes)
                    .where(post_likes.c.post_id == post_id)
                ),
                db.scalar(
                    select(func.count()).where(Comment.post_id == post_id, Comment.active.is_(True))
                ),
            )
            await db.execute(update(Post).where(Post.id == post_id).values(views=Post.views + 1))
            # 浅拷贝后再改：MemoryCacheBackend 直接返回存储对象引用，就地写回会污染缓存
            result = dict(cached)
            result["likes_count"] = likes_count or 0
            result["comments_count"] = comments_count or 0
            return result

    def _build_query(by_id: bool):
        stmt = select(Post).options(
            selectinload(Post.author).selectinload(User.title),
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        if by_id:
            return stmt.where(Post.id == int(slug))
        return stmt.where(Post.slug == slug)

    query = _build_query(False)
    result = await db.execute(query)
    post = result.scalar_one_or_none()

    # 找不到且 slug 是纯数字时，降级用 ID 查询（兼容旧链接和用 ID 生成的 URL）
    if not post and slug_is_numeric:
        try:
            query2 = _build_query(True)
            result2 = await db.execute(query2)
            post = result2.scalar_one_or_none()
        except (ValueError, OverflowError):
            post = None

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if post.status != "published":
        if not current_user or (
            current_user.id != post.author_id
            and not current_user.is_staff
            and not current_user.is_superuser
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在",
            )

    # 检查定时发布时间（aware/naive 双兼容：_ensure_aware 统一口径，
    # 直接和 datetime.now() 比较在带时区的 published_at 上会 TypeError）
    if post.status == "published" and post.published_at:
        if not (
            current_user
            and (
                current_user.id == post.author_id
                or current_user.is_staff
                or current_user.is_superuser
            )
        ):
            if _ensure_aware(post.published_at) > datetime.now(_tz.utc):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="文章不存在",
                )

    # 检查文章是否加密
    is_password_protected = bool(post.password)
    can_access_content = True

    if is_password_protected:
        # 作者和管理员可以跳过密码验证
        if current_user and (
            current_user.id == post.author_id or current_user.is_staff or current_user.is_superuser
        ):
            can_access_content = True
        elif x_post_password or password:
            # 验证密码（argon2id + bcrypt 双识别，平滑升级）；Header 优先，Query 兼容
            from backend.core.auth import averify_password as verify_post_password

            provided_password = x_post_password or password
            can_access_content = await verify_post_password(provided_password, post.password)
        else:
            can_access_content = False

    current_views = post.views

    # 浏览数在 DB 侧原子自增。synchronize_session=False 让 ORM 不去回灌/失效该属性，
    # 于是上面对 post 的整套 eager-load（author→title / category / tags）保持已加载状态。
    # 旧实现在这里又跑了一次 "select Post + 3 组 selectinload(populate_existing)"，
    # 只为把 views 恢复成进入时的值——每次文章浏览凭空多出 4 次往返。
    await db.execute(
        update(Post)
        .where(Post.id == post.id)
        .values(views=Post.views + 1)
        .execution_options(synchronize_session=False)
    )
    post.views = current_views

    # 在后续查询/修改之前，预先加载所有要访问的列，避免 expire 后触发隐式 lazy-load
    _id = post.id
    _slug = post.slug
    _source = post.source
    _source_url = post.source_url
    _audio = post.audio
    _video = post.video
    _video_url = post.video_url
    _cover_image = post.cover_image
    _status = post.status
    _views = post.views
    _is_pinned = post.is_pinned
    _allow_comments = post.allow_comments
    _created_at = post.created_at
    _published_at = post.published_at
    _updated_at = post.updated_at
    _password = post.password
    _author = post.author
    _category = post.category
    _tags = list(post.tags)
    _title_i18n = post.title
    _subtitle_i18n = post.subtitle
    _excerpt_i18n = post.excerpt
    _content_i18n = post.content
    _meta_title_i18n = post.meta_title
    _meta_description_i18n = post.meta_description
    _meta_keywords_i18n = post.meta_keywords
    _reading_time = post.reading_time

    # 补查点赞数和评论数（两条 count 顺序执行）
    likes_count, comments_count = await concurrent_query(
        db.scalar(select(func.count()).select_from(post_likes).where(post_likes.c.post_id == _id)),
        db.scalar(select(func.count()).where(Comment.post_id == _id, Comment.active.is_(True))),
    )

    likes_count = likes_count or 0
    comments_count = comments_count or 0

    # 根据权限决定返回的内容
    raw_title = get_i18n_value(_title_i18n, language)
    if is_password_protected and not can_access_content:
        # 加密文章但无权限，返回基本信息但隐藏内容
        raw_content = ""
        raw_excerpt = get_i18n_value(_excerpt_i18n, language) if _excerpt_i18n else None
        render_body = False
    else:
        raw_content = get_i18n_value(_content_i18n, language)
        raw_excerpt = get_i18n_value(_excerpt_i18n, language) if _excerpt_i18n else None
        render_body = True

    # 统一内容渲染管线（插件扩展点）：短代码 + the_title / the_content / the_excerpt，
    # 完成后触发 post.rendered。渲染结果随响应一并缓存。
    rendered = await render_post_fields(
        title=raw_title,
        content=raw_content,
        excerpt=raw_excerpt,
        post=post,
        language=language,
        render_body=render_body,
    )

    response = PostLocalizedResponse(
        id=_id,
        title=rendered.title,
        subtitle=get_i18n_value(_subtitle_i18n, language) if _subtitle_i18n else None,
        slug=_slug,
        source=_source,
        source_url=_source_url,
        audio=_audio if can_access_content else None,
        video=_video if can_access_content else None,
        video_url=_video_url if can_access_content else None,
        content=rendered.content,
        excerpt=rendered.excerpt,
        cover_image=_cover_image,
        author=_build_author_data(_author),
        category=CategoryLocalizedResponse.from_category(_category, language)
        if _category
        else None,
        tags=[TagLocalizedResponse.from_tag(t, language) for t in _tags],
        status=_status,
        views=_views,
        likes_count=likes_count,
        is_pinned=_is_pinned,
        allow_comments=_allow_comments,
        comments_count=comments_count,
        is_password_protected=is_password_protected,
        meta_title=get_i18n_value(_meta_title_i18n, language) if _meta_title_i18n else None,
        meta_description=get_i18n_value(_meta_description_i18n, language)
        if _meta_description_i18n
        else None,
        meta_keywords=get_i18n_value(_meta_keywords_i18n, language)
        if _meta_keywords_i18n
        else None,
        created_at=_created_at,
        published_at=_published_at,
        updated_at=_updated_at,
        reading_time=_reading_time or 1,
    )

    # 缓存写：只存"匿名访客看到的公开全文"，与函数开头的读侧门禁严格对齐。
    # 旧条件 `not is_password_protected or can_access_content` 会把作者/管理员用密码打开的
    # 明文内容写进共享键位——一旦读侧生效就是越权泄露，因此这里收紧为：
    # 匿名 + 无密码 + 已发布。登录态与加密文一律不进缓存。
    if current_user is None and not slug_is_numeric and not is_password_protected:
        await cache.set(cache_key, response.model_dump(mode="json"), CACHE_TTL["post_detail"])

    return response


@router.post(
    "/posts",
    response_model=PostLocalizedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建文章",
    description="创建新文章，需要管理员权限。支持多语言内容。可设置访问密码。",
)
async def create_post(
    request: Request,
    post_data: PostCreate,
    current_user: CurrentStaff,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """创建文章，支持多语言"""
    language = get_language_from_request(request, lang)

    zh_title = (
        post_data.title.get("zh", "") if isinstance(post_data.title, dict) else post_data.title
    )
    slug = post_data.slug or generate_slug(zh_title)

    existing = await db.execute(select(Post).where(Post.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 处理密码加密
    password = None
    if post_data.password:
        from backend.core.auth import aget_password_hash as hash_post_password

        password = await hash_post_password(post_data.password)

    status_value = post_data.status
    scheduled_at_value = post_data.scheduled_at
    if status_value == "scheduled" and scheduled_at_value is not None:
        if scheduled_at_value.tzinfo is None:
            scheduled_at_value = scheduled_at_value.replace(tzinfo=UTC)
        if scheduled_at_value <= datetime.now(UTC):
            status_value = "published"

    post = Post(
        title=post_data.title,
        subtitle=post_data.subtitle,
        slug=slug,
        source=post_data.source,
        source_url=post_data.source_url,
        content=post_data.content,
        excerpt=post_data.excerpt,
        cover_image=post_data.cover_image,
        author_id=current_user.id,
        category_id=post_data.category_id,
        status=status_value,
        scheduled_at=scheduled_at_value if status_value != "published" else None,
        password=password,
        is_pinned=post_data.is_pinned,
        allow_comments=post_data.allow_comments,
        series_id=post_data.series_id,
        series_order=post_data.series_order,
        encryption_enabled=bool(post_data.encryption_enabled),
        encryption_salt=post_data.encryption_salt,
        encryption_verifier=post_data.encryption_verifier,
        encryption_algorithm=post_data.encryption_algorithm or "AES-256-GCM",
        encryption_hint=post_data.encryption_hint,
        meta_title=post_data.meta_title,
        meta_description=post_data.meta_description,
        meta_keywords=post_data.meta_keywords,
        reading_time=compute_reading_time_from_content(post_data.content),
    )

    if status_value == "published":
        post.published_at = datetime.now(UTC)
        post.scheduled_at = None
    elif status_value == "scheduled":
        post.published_at = None

    db.add(post)
    await db.flush()
    await db.refresh(post)

    if post_data.tag_ids:
        tags = await db.execute(select(Tag).where(Tag.id.in_(post_data.tag_ids)))
        tag_list = list(tags.scalars().all())
        try:
            post.tags.clear()
        except Exception:
            post.tags = []
        post.tags.extend(tag_list)
        await db.flush()
        await db.refresh(post)

    await invalidate_cache("posts")
    await invalidate_post_aggregate_caches()

    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.author).selectinload(User.title),
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        .where(Post.id == post.id)
    )
    post = result.scalar_one()

    response = PostLocalizedResponse.from_post(post, language, likes_count=0, comments_count=0)
    response.is_password_protected = bool(password)
    await bus.do_action("post.created", post, current_user=current_user, db=db)
    if status_value == "published":
        # 新文章直接发布 → 通知搜索引擎 / 订阅等插件
        await bus.do_action("post.published", post.id, post=post, current_user=current_user, db=db)
    return response


@router.post(
    "/posts/batch-status",
    response_model=BatchPostStatusResponse,
    summary="批量更新文章状态",
    description="批量更新当前用户可操作文章的状态，仅作者或超级管理员可操作。",
)
async def batch_update_post_status(
    post_data: BatchPostStatusUpdate,
    current_user: CurrentStaff,
    db: DB,
):
    result = await db.execute(select(Post).where(Post.id.in_(post_data.post_ids)))
    posts = [
        post
        for post in result.scalars().all()
        if post.author_id == current_user.id or current_user.is_superuser
    ]
    now = datetime.now(UTC)

    for post in posts:
        post.status = post_data.status
        if post_data.status == "published":
            post.scheduled_at = None
            if not post.published_at:
                post.published_at = now
        elif post_data.status == "draft":
            post.scheduled_at = None

    await db.flush()

    for post in posts:
        await invalidate_post_detail_cache(post.slug)
    await invalidate_cache("posts")
    await invalidate_post_aggregate_caches()
    # 与单篇 update_post 同构发钩子：批量路径原先静默，导致 Webhook/插件监听只在
    # 「一篇一篇改」时收到事件，改成批量就全丢。
    for post in posts:
        await bus.do_action("post.updated", post, current_user=current_user, db=db)
        if post_data.status == "published":
            await bus.do_action(
                "post.published", post.id, post=post, current_user=current_user, db=db
            )

    return BatchPostStatusResponse(
        message="文章状态已批量更新",
        data={"updated_count": len(posts)},
    )


@router.put(
    "/posts/{post_id}",
    response_model=PostLocalizedResponse,
    summary="更新文章",
    description="更新文章内容，仅作者或超级管理员可操作。支持多语言内容。可设置访问密码。",
)
async def update_post(
    post_id: int,
    request: Request,
    post_data: PostUpdate,
    current_user: CurrentStaff,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """更新文章，支持多语言"""
    language = get_language_from_request(request, lang)

    result = await db.execute(
        select(Post).options(selectinload(Post.tags)).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此文章",
        )

    # 记录更新前状态，用于识别「草稿/定时 → 已发布」的发布流转
    previous_status = post.status
    # 详情缓存键含 slug：改名后旧 slug 的键必须还能清掉，所以先把改名前的 slug 存下来
    previous_slug = post.slug

    update_data = post_data.model_dump(
        exclude_unset=True, exclude={"tag_ids", "password", "view_password"}
    )

    if post_data.password is not None:
        if post_data.password:
            from backend.core.auth import aget_password_hash as hash_post_password

            post.password = await hash_post_password(post_data.password)
        else:
            post.password = None

    new_status = update_data.get("status")
    scheduled_at = update_data.pop("scheduled_at", None)
    if new_status == "scheduled" and scheduled_at is not None:
        if isinstance(scheduled_at, datetime) and scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        if scheduled_at <= now:
            new_status = "published"
            update_data["status"] = "published"
            post.scheduled_at = None
        else:
            post.scheduled_at = scheduled_at
    elif new_status == "scheduled" and scheduled_at is None and post.scheduled_at:
        if post.scheduled_at <= datetime.now(UTC):
            new_status = "published"
            update_data["status"] = "published"
    elif new_status == "published":
        post.scheduled_at = None

    if new_status == "published" and not post.published_at:
        post.published_at = datetime.now(UTC)

    if "encryption_enabled" in update_data and not update_data["encryption_enabled"]:
        post.encryption_salt = None
        post.encryption_verifier = None
        post.encryption_hint = None

    # 内容/标题/摘要真的变了才落快照：编辑器每次 PUT 整份表单，只比键存在会造出
    # 一堆与上一版字节相同的空版本。快照记录的是「改动前」的状态，故必须在赋值之前。
    if has_content_change(post, update_data):
        await snapshot_post_revision(
            db,
            post=post,
            author_id=current_user.id,
            change_summary=(
                "编辑保存"
                if new_status in (None, previous_status)
                else f"{previous_status} → {new_status} 变更前"
            ),
        )

    apply_partial_update(post, update_data)

    # 内容变更时重算 reading_time（列表接口据此 defer(content) 避免加载大字段）
    if "content" in update_data:
        post.reading_time = compute_reading_time_from_content(post.content)

    if post_data.tag_ids is not None:
        tags = await db.execute(select(Tag).where(Tag.id.in_(post_data.tag_ids)))
        tag_list = list(tags.scalars().all())
        try:
            post.tags.clear()
        except Exception:
            post.tags = []
        post.tags.extend(tag_list)

    await db.flush()
    await db.refresh(post)

    # 详情缓存按 post:{slug}:{language} 分语言写入（见 get_post），只删当前请求语言会让
    # 其余语言最长 600s 返回旧内容；改名时旧 slug 的键同样要清，故一并传入。
    await invalidate_post_detail_cache(previous_slug, post.slug)
    await invalidate_cache("posts")
    await invalidate_post_aggregate_caches()

    likes_count = (
        await db.scalar(
            select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post.id)
        )
        or 0
    )

    comments_count = (
        await db.scalar(
            select(func.count()).where(Comment.post_id == post.id, Comment.active.is_(True))
        )
        or 0
    )

    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.author).selectinload(User.title),
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        .where(Post.id == post_id)
    )
    post = result.scalar_one()

    await bus.do_action("post.updated", post, current_user=current_user, db=db)
    if post.status == "published" and previous_status != "published":
        # 由草稿 / 定时 / 待审流转到已发布 → 触发发布钩子（搜索引擎 ping、推送等）
        await bus.do_action("post.published", post.id, post=post, current_user=current_user, db=db)
    return PostLocalizedResponse.from_post(
        post, language, likes_count=likes_count, comments_count=comments_count
    )


@router.delete(
    "/posts/{post_id}",
    response_model=BaseResponse,
    summary="删除文章",
    description="将文章移入回收站（30 天后自动清除），仅作者或超级管理员可操作。",
)
async def delete_post(post_id: int, current_user: CurrentStaff, db: DB):
    """删除文章"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此文章",
        )

    # slug 要在删除前取：db.delete 后实例已过期，再读属性会对已删行发出 SELECT
    deleted_slug = post.slug
    # 与批删（advanced.py batch action=delete）同构：先落回收站快照再删原行，
    # 否则单删是物理删除、批删可恢复——同一入口两种语义，用户数据会真丢。
    trash_item = TrashItem(
        resource_type="post",
        resource_id=post.id,
        resource_data=json.dumps(
            {
                "title": post.title,
                "slug": post.slug,
                "content": post.content,
                "excerpt": post.excerpt,
                "cover_image": post.cover_image,
                "author_id": post.author_id,
                "category_id": post.category_id,
                "status": post.status,
                "views": post.views,
            }
        ),
        deleted_by_id=current_user.id,
        auto_delete_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(trash_item)
    await db.delete(post)
    # 详情缓存独立于 posts 前缀：不清的话删除后 600s 内匿名 GET /posts/{slug} 仍返回旧正文
    await invalidate_post_detail_cache(deleted_slug)
    await invalidate_cache("posts")
    await invalidate_post_aggregate_caches()
    await bus.do_action("post.deleted", post, current_user=current_user, db=db)

    return BaseResponse(message="文章已移入回收站")


@router.post(
    "/posts/{post_id}/like",
    response_model=BaseResponse,
    summary="点赞/取消点赞",
    description="切换文章点赞状态。",
)
async def toggle_like(post_id: int, current_user: CurrentUser, db: DB):
    """点赞/取消点赞"""
    result = await db.execute(
        select(Post).options(selectinload(Post.likes)).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if current_user in post.likes:
        post.likes.remove(current_user)
        await invalidate_cache("posts")
        return BaseResponse(message="已取消点赞")
    else:
        post.likes.append(current_user)
        await invalidate_cache("posts")
        return BaseResponse(message="点赞成功")


# ==================== 分类接口 ====================


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="分类列表",
    description="获取所有分类及其文章数量（返回多语言原始dict，前端自行本地化显示）。",
)
async def list_categories(
    request: Request,
    db: DB,
    lang: str | None = Query(
        None, description="语言代码（zh/en/ja/zh_Hant），保留参数，返回时不裁剪语言"
    ),
):
    """获取分类列表，返回 i18n 原始 dict 供后台编辑 / 前端 getLocalized 统一处理"""
    if not is_oobe_complete():
        return []

    # 统一返回完整 i18n dict（不再按 lang 裁剪），前后端都能正确渲染
    cache_key = CACHE_KEY_CATEGORIES
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(
            Category,
            func.count(Post.id).filter(Post.status == "published").label("post_count"),
        )
        .outerjoin(Post, Category.id == Post.category_id)
        .group_by(Category.id)
        .order_by(Category.created_at)
    )
    rows = result.all()

    items = [
        CategoryResponse(
            id=row.Category.id,
            name=row.Category.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
            slug=row.Category.slug,
            description=row.Category.description or None,
            icon=row.Category.icon,
            color=row.Category.color,
            cover_image=row.Category.cover_image,
            created_at=row.Category.created_at,
            post_count=row.post_count or 0,
        )
        for row in rows
    ]

    await cache.set(
        cache_key, [item.model_dump(mode="json") for item in items], CACHE_TTL["categories"]
    )

    return items


@router.get(
    "/categories/slug/{slug}",
    response_model=CategoryResponse,
    summary="获取分类详情",
    description="根据 slug 获取分类详情（返回完整 i18n dict）。",
)
async def get_category_by_slug(
    slug: str,
    db: DB,
):
    """按 slug 获取分类"""
    result = await db.execute(select(Category).where(Category.slug == slug))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在",
        )

    post_count = await db.scalar(select(func.count()).where(Post.category_id == category.id)) or 0

    return CategoryResponse(
        id=category.id,
        name=category.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        slug=category.slug,
        description=category.description or None,
        icon=category.icon,
        color=category.color,
        cover_image=category.cover_image,
        created_at=category.created_at,
        post_count=post_count,
    )


async def _category_post_slugs(db: AsyncSession, category_id: int) -> list[str]:
    rows = await db.execute(select(Post.slug).where(Post.category_id == category_id))
    return list(rows.scalars().all())


async def _tag_post_slugs(db: AsyncSession, tag_id: int) -> list[str]:
    rows = await db.execute(
        select(Post.slug)
        .join(post_tags, post_tags.c.post_id == Post.id)
        .where(post_tags.c.tag_id == tag_id)
    )
    return list(rows.scalars().all())


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建分类",
    description="创建新分类，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。",
)
async def create_category(
    request: Request,
    data: CategoryCreate,
    current_user: CurrentStaff,
    db: DB,
):
    """创建分类，支持多语言，返回原始 i18n dict"""

    zh_name = data.name.get("zh", "") if isinstance(data.name, dict) else data.name
    slug = data.slug or generate_slug(zh_name)

    existing = await db.execute(select(Category).where(Category.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分类别名已存在",
        )

    category = Category(
        name=data.name,
        slug=slug,
        description=data.description,
        icon=data.icon,
        color=data.color,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)

    await invalidate_cache("categories")

    return CategoryResponse(
        id=category.id,
        name=category.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        slug=category.slug,
        description=category.description or None,
        icon=category.icon,
        color=category.color,
        cover_image=category.cover_image,
        created_at=category.created_at,
        post_count=0,
    )


# ==================== 标签接口 ====================


@router.get(
    "/tags",
    response_model=list[TagResponse],
    summary="标签列表",
    description="获取所有激活的标签及其文章数量（返回多语言原始dict）。",
)
async def list_tags(
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="保留参数，返回时不裁剪语言"),
):
    """获取标签列表，统一返回原始 i18n dict

    优化：使用 GROUP BY 批量统计文章数，避免 N+1 查询
    """
    if not is_oobe_complete():
        return []

    cache_key = CACHE_KEY_TAGS
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(
            Tag,
            func.count(post_tags.c.post_id).label("post_count"),
        )
        .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
        .where(Tag.is_active.is_(True))
        .group_by(Tag.id)
        .order_by(Tag.created_at)
    )
    rows = result.all()

    items = [
        TagResponse(
            id=row.Tag.id,
            name=row.Tag.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
            slug=row.Tag.slug,
            color=row.Tag.color,
            icon=row.Tag.icon,
            is_active=row.Tag.is_active,
            created_at=row.Tag.created_at,
            post_count=row.post_count or 0,
        )
        for row in rows
    ]

    await cache.set(cache_key, [item.model_dump(mode="json") for item in items], CACHE_TTL["tags"])

    return items


@router.get(
    "/tags/slug/{slug}",
    response_model=TagResponse,
    summary="获取标签详情",
    description="根据 slug 获取标签详情（返回完整 i18n dict）。",
)
async def get_tag_by_slug(
    slug: str,
    db: DB,
):
    """按 slug 获取标签"""
    result = await db.execute(select(Tag).where(Tag.slug == slug))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )

    post_count = (
        await db.scalar(
            select(func.count()).select_from(post_tags).where(post_tags.c.tag_id == tag.id)
        )
        or 0
    )

    return TagResponse(
        id=tag.id,
        name=tag.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        slug=tag.slug,
        color=tag.color,
        icon=tag.icon,
        is_active=tag.is_active,
        created_at=tag.created_at,
        post_count=post_count,
    )


@router.post(
    "/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建标签",
    description="创建新标签，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。",
)
async def create_tag(
    request: Request,
    data: TagCreate,
    current_user: CurrentStaff,
    db: DB,
):
    """创建标签，返回原始 i18n dict"""

    zh_name = data.name.get("zh", "") if isinstance(data.name, dict) else data.name
    slug = data.slug or generate_slug(zh_name)

    existing = await db.execute(select(Tag).where(Tag.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标签别名已存在",
        )

    color = data.color
    if color is None:
        used = await db.execute(select(Tag.color).where(Tag.color.isnot(None)))
        used_counts: dict[str, int] = {}
        for (c,) in used.all():
            used_counts[c] = used_counts.get(c, 0) + 1
        color = min(_TAG_PALETTE, key=lambda c: used_counts.get(c, 0))

    tag = Tag(
        name=data.name,
        slug=slug,
        color=color,
        icon=data.icon,
        is_active=data.is_active,
    )
    db.add(tag)
    await db.flush()
    await db.refresh(tag)

    await invalidate_cache("tags")

    return TagResponse(
        id=tag.id,
        name=tag.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        slug=tag.slug,
        color=tag.color,
        icon=tag.icon,
        is_active=tag.is_active,
        created_at=tag.created_at,
        post_count=0,
    )


# ==================== 评论接口 ====================


@router.get(
    "/posts/{post_id}/comments",
    response_model=list[CommentResponse],
    summary="评论列表",
    description="获取文章的评论树形结构。",
)
async def list_comments(post_id: int, db: DB):
    """获取文章评论（树形结构）。

    一次性扁平查询所有相关评论 + eager-load user，避免 ORM 多级 replies
    关系 lazy-load 触发 async greenlet 同步 IO 错误。
    """
    # 1) 取所有目标 post 下激活的评论，eager-load user（一次性，不分层）
    all_stmt = (
        select(Comment)
        .options(
            selectinload(Comment.user).selectinload(User.title),
        )
        .where(Comment.post_id == post_id, Comment.active.is_(True))
    )
    all_res = await db.execute(all_stmt)
    all_comments: list[Comment] = list(all_res.scalars().all())

    # 2) 按 parent_id 分组到内存映射，完全不访问 .replies 关系属性
    by_parent: dict[int | None, list[Comment]] = {}
    for c in all_comments:
        by_parent.setdefault(c.parent_id, []).append(c)

    # 3) 递归构造树（纯内存操作，无 SQL 触发）
    def build(parent_pid: int | None) -> list[CommentResponse]:
        nodes = by_parent.get(parent_pid, [])
        result: list[CommentResponse] = []
        # 按创建时间倒序
        for c in sorted(nodes, key=lambda x: x.created_at, reverse=True):
            children = build(c.id)
            resp = _comment_to_response(c, reply_total=len(children))
            resp.replies = children
            result.append(resp)
        return result

    return build(None)


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发表评论",
    description="在文章下发表评论，支持回复。",
)
async def create_comment(
    post_id: int,
    data: CommentCreate,
    current_user: CurrentUser,
    db: DB,
):
    """发表评论"""
    if not settings.enable_comments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="评论功能已关闭",
        )

    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    if not post.allow_comments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该文章禁止评论",
        )

    if data.parent_id:
        parent_result = await db.execute(
            select(Comment).where(Comment.id == data.parent_id, Comment.post_id == post_id)
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父评论不存在",
            )

    comment = Comment(
        post_id=post_id,
        user_id=current_user.id,
        parent_id=data.parent_id,
        content=data.content,
        active=not settings.comment_require_approval,
        # 从登录态回填 author 字段：兼容 Comment NOT NULL 约束与对外响应
        author_name=getattr(current_user, "nickname", None)
        or getattr(current_user, "username", "匿名"),
        author_email=getattr(current_user, "email", None),
        author_website=None,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    return _comment_to_response(comment)


# ==================== 归档 API ====================


async def _render_archive_post_titles(posts: list[dict], *, language: str) -> None:
    """就地给归档条目的每篇标题补上 the_title 渲染链。

    三个归档出口（`/archive` · `/archive/{year}` · `/archive/{year}/{month}`）此前直出
    i18n dict 里的裸字符串，而列表 / RSS / 详情页都过 `render_title`。挂上标题类插件
    （hello-rosetta 追加 `· hello`）后，同一篇文章在归档入口不带后缀、在列表带——
    插件对同一篇内容呈现两套标题，违背 the_title 契约。
    必须在写响应缓存之前调用，否则缓存里固化的就是旧钩子集的口径。
    """
    for item in posts:
        ref = SimpleNamespace(id=item.get("id"), slug=item.get("slug"))
        item["title"] = await render_title(item["title"], post=ref, language=language)


@router.get(
    "/archive",
    summary="文章归档",
    description="按年月分组获取已发布文章的归档列表。",
    responses={200: {"model": list[ArchiveMonthGroup]}},
)
async def get_archive(
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码：zh/en/ja/zh_Hant"),
    limit_per_month: int = Query(50, ge=1, le=100, description="每月最多返回的文章数"),
):
    """
    获取文章归档

    按年月分组返回已发布文章列表，支持多语言和缓存。

    性能优化：
    - 使用缓存减少数据库查询
    - 使用 joinedload 预加载分类
    - 支持多语言内容

    返回格式：
    [
      {
        "year": 2025,
        "month": 2,
        "count": 15,
        "posts": [
          {
            "id": 1,
            "title": "文章标题",
            "slug": "post-slug",
            "created_at": "2025-02-18T10:00:00Z",
            "category": {"id": 1, "name": "分类名", "color": "#3B82F6"},
            "views": 100
          }
        ]
      }
    ]
    """
    language = get_language_from_request(request, lang)

    # 检查缓存
    cache_key = make_cache_key("archive", language, f"limit_{limit_per_month}")
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # 使用仓储层查询
    from backend.repositories.post import PostRepository

    repo = PostRepository(db)
    archive_data = await repo.get_archive_data(language, limit_per_month)
    # 仓储给的是 i18n dict 里的裸字符串，进缓存前必须过一遍 the_title 链。
    await _render_archive_post_titles(
        [post for group in archive_data for post in group["posts"]], language=language
    )

    # 设置缓存
    await cache.set(cache_key, archive_data, CACHE_TTL["categories"])

    return archive_data


@router.get(
    "/archive/stats",
    summary="归档统计",
    description="获取归档统计信息，包括总文章数、年份数等。",
    responses={200: {"model": ArchiveStats}},
)
async def get_archive_stats(
    db: DB,
):
    """
    获取归档统计信息

    返回：
    - total_posts: 总文章数
    - total_years: 总年份数
    - years: 年份列表
    - year_stats: 每年文章数统计
    """
    cache_key = make_cache_key("archive_stats")
    cached = await cache.get(cache_key)
    if cached:
        return cached

    from backend.repositories.post import PostRepository

    repo = PostRepository(db)
    stats = await repo.get_archive_stats()

    await cache.set(cache_key, stats, CACHE_TTL["categories"])

    return stats


def _count_words_in_content(content: str) -> int:
    """
    计算内容字数

    算法与前端 SiteStats.astro 保持一致：
    - 移除代码块和内联代码
    - 统计中文字符数 + 英文字符数
    """
    if not content:
        return 0

    text = re.sub(r"```[\s\S]*?```", "", content)  # 移除代码块
    text = re.sub(r"`[^`]*`", "", text)  # 移除内联代码
    text = re.sub(r"\s+", " ", text).strip()  # 合并空白
    chinese_chars = re.findall(r"[\u4e00-\u9fa5]", text)
    english_chars = re.findall(r"[a-zA-Z]", text)
    return len(chinese_chars) + len(english_chars)


@router.get(
    "/site-stats",
    summary="站点统计",
    description="获取站点公开统计信息：总字数、文章数、分类数、标签数。",
    responses={200: {"model": SiteStats}},
)
async def get_site_stats(
    db: DB,
):
    """
    获取站点统计信息

    返回：
    - total_words: 已发布文章总字数（中文字符 + 英文字符，已剔除代码块）
    - total_posts: 已发布文章数
    - total_categories: 至少包含一篇已发布文章的分类数
    - total_tags: 已发布文章使用过的不同标签数
    """
    cache_key = make_cache_key("site_stats")
    cached = await cache.get(cache_key)
    if cached:
        return cached

    published_filter = (
        Post.status == "published",
        (Post.published_at.is_(None) | (Post.published_at <= func.now())),
    )

    # 总字数 + 总文章数：一次查询拿到所有已发布文章的内容
    posts_result = await db.execute(select(Post.content).where(*published_filter))
    contents = posts_result.scalars().all()
    total_posts = len(contents)
    total_words = 0
    # 逐篇处理，避免内存和类型问题（Post.content 可能为 dict、str、None）
    for c in contents:
        text: str = ""
        if isinstance(c, dict):
            # 多语言 dict：优先 zh，否则取第一个非空值，否则空串
            text = c.get("zh") or next((v for v in c.values() if v), "") or ""
        elif isinstance(c, str):
            text = c
        # None / 其他类型统一视为空串
        total_words += _count_words_in_content(text)

    # 至少有一篇已发布文章的分类数
    total_categories = (
        await db.scalar(
            select(func.count(func.distinct(Post.category_id))).where(
                *published_filter, Post.category_id.is_not(None)
            )
        )
        or 0
    )

    # 已发布文章使用过的不同标签数
    total_tags = (
        await db.scalar(
            select(func.count(func.distinct(post_tags.c.tag_id)))
            .select_from(post_tags)
            .join(Post, Post.id == post_tags.c.post_id)
            .where(*published_filter)
        )
        or 0
    )

    stats = {
        "total_words": total_words,
        "total_posts": total_posts,
        "total_categories": total_categories,
        "total_tags": total_tags,
    }

    await cache.set(cache_key, stats, CACHE_TTL["categories"])

    return stats


@router.get(
    "/archive/{year}",
    summary="按年份获取归档",
    description="获取指定年份的文章归档。",
    responses={200: {"model": list[ArchiveMonthGroup]}},
)
async def get_archive_by_year(
    year: int,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码"),
):
    """
    获取指定年份的归档

    Args:
        year: 年份

    Returns:
        该年份的归档数据
    """
    language = get_language_from_request(request, lang)

    cache_key = make_cache_key("archive", str(year), language)
    cached = await cache.get(cache_key)
    if cached:
        return cached

    from sqlalchemy import extract

    query = (
        select(Post)
        .where(
            Post.status == "published",
            extract("year", Post.published_at) == year,
        )
        .options(selectinload(Post.category))
        .order_by(Post.published_at.desc())
    )

    result = await db.execute(query)
    posts = result.scalars().all()

    # 按月份分组
    month_map: dict[int, list] = {}
    for post in posts:
        if not post.published_at:
            continue
        month = post.published_at.month
        if month not in month_map:
            month_map[month] = []

        title = post.title.get(language, post.title.get("zh", "")) if post.title else ""

        category_data = None
        if post.category:
            category_name = (
                post.category.name.get(language, post.category.name.get("zh", ""))
                if post.category.name
                else ""
            )
            category_data = {
                "id": post.category.id,
                "name": category_name,
                "color": post.category.color,
            }

        month_map[month].append(
            {
                "id": post.id,
                "title": title,
                "slug": post.slug,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                # 分组/排序按 published_at，显示口径必须同源（WordPress 用发布日期）
                "published_at": (post.published_at or post.created_at).isoformat()
                if (post.published_at or post.created_at)
                else None,
                "category": category_data,
                "views": post.views,
            }
        )

    # 转换为列表格式
    archive_data = []
    for month in sorted(month_map.keys(), reverse=True):
        archive_data.append(
            {
                "year": year,
                "month": month,
                "count": len(month_map[month]),
                "posts": month_map[month],
            }
        )

    await _render_archive_post_titles(
        [post for month_group in archive_data for post in month_group["posts"]],
        language=language,
    )
    await cache.set(cache_key, archive_data, CACHE_TTL["categories"])

    return archive_data


@router.get(
    "/archive/{year}/{month}",
    summary="按年月获取归档",
    description="获取指定年月的文章归档。",
    responses={200: {"model": ArchiveMonthPage}},
)
async def get_archive_by_month(
    year: int,
    month: int,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取指定年月的归档

    Args:
        year: 年份
        month: 月份

    Returns:
        该年月的归档数据（分页）
    """
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="月份必须在 1-12 之间",
        )

    language = get_language_from_request(request, lang)

    from sqlalchemy import extract

    query = (
        select(Post)
        .where(
            Post.status == "published",
            extract("year", Post.published_at) == year,
            extract("month", Post.published_at) == month,
        )
        .options(selectinload(Post.category))
    )

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页查询
    query = query.order_by(Post.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    posts = result.scalars().all()

    # 转换数据
    posts_data = []
    for post in posts:
        title = post.title.get(language, post.title.get("zh", "")) if post.title else ""

        category_data = None
        if post.category:
            category_name = (
                post.category.name.get(language, post.category.name.get("zh", ""))
                if post.category.name
                else ""
            )
            category_data = {
                "id": post.category.id,
                "name": category_name,
                "color": post.category.color,
            }

        posts_data.append(
            {
                "id": post.id,
                "title": title,
                "slug": post.slug,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                # 分组/排序按 published_at，显示口径必须同源（WordPress 用发布日期）
                "published_at": (post.published_at or post.created_at).isoformat()
                if (post.published_at or post.created_at)
                else None,
                "category": category_data,
                "views": post.views,
            }
        )

    await _render_archive_post_titles(posts_data, language=language)

    return {
        "year": year,
        "month": month,
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
        "posts": posts_data,
    }


# ==================== 分类管理接口 ====================


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="更新分类",
    description=(
        "更新分类信息，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。"
        "改名/改色会同步失效该分类下所有文章的详情缓存（`post:{slug}:{lang}`）与列表/RSS 缓存，"
        "避免前台文章页在 TTL 内继续显示旧分类名/颜色。"
    ),
)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: CurrentStaff,
    db: DB,
):
    """更新分类，返回原始 i18n dict"""

    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    apply_partial_update(category, update_data)

    await db.flush()
    await db.refresh(category)
    await invalidate_cache("categories")

    affected_slugs = await _category_post_slugs(db, category.id)
    await invalidate_post_caches_by_slugs(affected_slugs)

    post_count = len(affected_slugs)

    return CategoryResponse(
        id=category.id,
        name=category.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        slug=category.slug,
        description=category.description or None,
        icon=category.icon,
        color=category.color,
        cover_image=category.cover_image,
        created_at=category.created_at,
        post_count=post_count,
    )


@router.delete(
    "/categories/{category_id}",
    response_model=BaseResponse,
    summary="删除分类",
    description=(
        "删除分类，需要管理员权限。删除会把该分类下文章的 category_id 置空（SET NULL），"
        "并失效这些文章的详情/列表/RSS 缓存，使前台立即回落到「无分类」而非旧分类。"
    ),
)
async def delete_category(
    category_id: int,
    current_user: CurrentStaff,
    db: DB,
):
    """删除分类"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在",
        )

    # 删除会把文章的 category_id 置空（SET NULL），故必须在 delete 前抓出受影响 slug。
    affected_slugs = await _category_post_slugs(db, category.id)

    await db.delete(category)
    await invalidate_cache("categories")
    await invalidate_post_caches_by_slugs(affected_slugs)

    return BaseResponse(message="分类已删除")


# ==================== 标签管理接口 ====================


@router.put(
    "/tags/{tag_id}",
    response_model=TagResponse,
    summary="更新标签",
    description=(
        "更新标签信息，需要管理员权限。返回完整 i18n dict 供 I18nTabsEditor 回填。"
        "改名/改色会失效所有引用该标签的文章详情缓存与列表/RSS 缓存。"
    ),
)
async def update_tag(
    tag_id: int,
    data: TagUpdate,
    current_user: CurrentStaff,
    db: DB,
):
    """更新标签，返回原始 i18n dict"""

    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    apply_partial_update(tag, update_data)

    await db.flush()
    await db.refresh(tag)
    await invalidate_cache("tags")

    affected_slugs = await _tag_post_slugs(db, tag.id)
    await invalidate_post_caches_by_slugs(affected_slugs)

    post_count = len(affected_slugs)

    return TagResponse(
        id=tag.id,
        name=tag.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        slug=tag.slug,
        color=tag.color,
        icon=tag.icon,
        is_active=tag.is_active,
        created_at=tag.created_at,
        post_count=post_count,
    )


@router.delete(
    "/tags/{tag_id}",
    response_model=BaseResponse,
    summary="删除标签",
    description=(
        "删除标签，需要管理员权限。删除会 CASCADE 清空 post_tags 关联，"
        "并失效原引用该标签文章的详情/列表/RSS 缓存。"
    ),
)
async def delete_tag(
    tag_id: int,
    current_user: CurrentStaff,
    db: DB,
):
    """删除标签"""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )

    # 删除标签会 CASCADE 清空 post_tags 关联，故必须在 delete 前抓出受影响 slug。
    affected_slugs = await _tag_post_slugs(db, tag.id)

    await db.delete(tag)
    await invalidate_cache("tags")
    await invalidate_post_caches_by_slugs(affected_slugs)

    return BaseResponse(message="标签已删除")


# ==================== 文章按ID获取接口 ====================


@router.get(
    "/posts/id/{post_id}",
    response_model=PostLocalizedResponse,
    summary="按ID获取文章",
    description=(
        "根据文章ID获取文章详情。可见性口径与 slug 详情端点一致："
        "草稿/未到排期时间的文章仅作者与职员可见；加密文章需通过 "
        "X-Post-Password 验证才返回正文；密码散列永不出现在响应中。"
    ),
)
async def get_post_by_id(
    post_id: int,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
    x_post_password: str | None = Header(
        None, alias="X-Post-Password", description="文章访问密码（加密文章必需）"
    ),
    current_user: CurrentUserOptional = None,
):
    """按ID获取文章详情"""
    language = get_language_from_request(request, lang)

    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.author).selectinload(User.title),
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        .where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    # 可见性门禁必须与 GET /posts/{slug} 同口径。本端点匿名可访，
    # 旧实现一条检查都没有：草稿可按 ID 直读，加密文章明文连带密码散列一起外泄。
    is_owner_or_staff = bool(
        current_user
        and (
            current_user.id == post.author_id or current_user.is_staff or current_user.is_superuser
        )
    )
    if post.status != "published" and not is_owner_or_staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )
    if (
        post.status == "published"
        and _ensure_aware(post.published_at)
        and _ensure_aware(post.published_at) > datetime.now(_tz.utc)
        and not is_owner_or_staff
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    is_password_protected = bool(post.password)
    can_access_content = True
    if is_password_protected and not is_owner_or_staff:
        if x_post_password:
            # 验证密码（argon2id + bcrypt 双识别，平滑升级）
            from backend.core.auth import averify_password

            can_access_content = await averify_password(x_post_password, post.password)
        else:
            can_access_content = False

    likes_count = (
        await db.scalar(
            select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post.id)
        )
        or 0
    )

    comments_count = (
        await db.scalar(
            select(func.count()).where(Comment.post_id == post.id, Comment.active.is_(True))
        )
        or 0
    )

    raw_content = "" if not can_access_content else get_i18n_value(post.content, language)
    raw_excerpt = get_i18n_value(post.excerpt, language) if post.excerpt else None

    # 统一内容渲染管线（插件扩展点）：短代码 + the_title / the_content / the_excerpt，
    # 完成后触发 post.rendered。与详情端点共用同一入口，不再散落 do_shortcode。
    rendered = await render_post_fields(
        title=get_i18n_value(post.title, language),
        content=raw_content,
        excerpt=raw_excerpt,
        post=post,
        language=language,
        render_body=can_access_content,
    )

    return PostLocalizedResponse(
        id=post.id,
        title=rendered.title,
        subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
        slug=post.slug,
        source=post.source,
        source_url=post.source_url,
        audio=post.audio if can_access_content else None,
        video=post.video if can_access_content else None,
        video_url=post.video_url if can_access_content else None,
        content=rendered.content,
        excerpt=rendered.excerpt,
        cover_image=post.cover_image,
        author=_build_author_data(post.author),
        category=CategoryLocalizedResponse.from_category(post.category, language)
        if post.category
        else None,
        tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
        status=post.status,
        visibility=post.visibility or "public",
        views=post.views,
        likes_count=likes_count,
        is_pinned=post.is_pinned,
        allow_comments=post.allow_comments,
        comments_count=comments_count,
        is_password_protected=is_password_protected,
        meta_title=get_i18n_value(post.meta_title, language) if post.meta_title else None,
        meta_description=get_i18n_value(post.meta_description, language)
        if post.meta_description
        else None,
        meta_keywords=get_i18n_value(post.meta_keywords, language) if post.meta_keywords else None,
        created_at=post.created_at,
        published_at=post.published_at,
        updated_at=post.updated_at,
        reading_time=post.reading_time or 1,
    )


@router.get(
    "/posts/{post_id}/edit",
    response_model=PostEditResponse,
    summary="获取文章用于编辑",
    description="根据文章ID获取完整的多语言内容，用于文章编辑页面。使用 /edit 后缀避免被 GET /posts/{slug} 路由遮蔽。",
)
async def get_post_for_edit(
    post_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """获取文章完整数据用于编辑"""
    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        .where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    return PostEditResponse.from_post(post)


# ==================== 用户相关接口 ====================


@router.get(
    "/users/me/comments",
    response_model=PaginatedResponse,
    summary="获取我的评论",
    description="获取当前用户发表的所有评论。",
)
async def get_my_comments(
    request: Request,
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取当前用户的评论"""
    language = get_language_from_request(request, lang)

    count_query = (
        select(func.count()).select_from(Comment).where(Comment.user_id == current_user.id)
    )
    total = await db.scalar(count_query) or 0

    query = (
        select(Comment)
        .options(selectinload(Comment.post), selectinload(Comment.user))
        .where(Comment.user_id == current_user.id)
        .order_by(Comment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    comments = result.scalars().all()

    items = []
    for comment in comments:
        post = comment.post
        post_title = get_i18n_value(post.title, language) if post else None
        items.append(
            {
                "id": comment.id,
                "content": comment.content,
                "post_id": comment.post_id,
                "post_title": post_title,
                "post_slug": post.slug if post else None,
                "active": comment.active,
                "created_at": comment.created_at,
            }
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/users/me/likes",
    response_model=PaginatedResponse,
    summary="获取我的点赞",
    description="获取当前用户点赞的所有文章。",
)
async def get_my_likes(
    request: Request,
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取当前用户点赞的文章"""
    language = get_language_from_request(request, lang)

    count_query = (
        select(func.count()).select_from(post_likes).where(post_likes.c.user_id == current_user.id)
    )
    total = await db.scalar(count_query) or 0

    query = (
        select(Post)
        .options(
            selectinload(Post.author).selectinload(User.title),
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        .join(post_likes, Post.id == post_likes.c.post_id)
        .where(post_likes.c.user_id == current_user.id)
        .order_by(Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    posts = result.scalars().unique().all()

    # 批量预取点赞数 / 评论数，避免循环内 N+1 查询
    ids = [p.id for p in posts]
    if ids:
        likes_raw = await db.execute(
            select(post_likes.c.post_id, func.count())
            .where(post_likes.c.post_id.in_(ids))
            .group_by(post_likes.c.post_id)
        )
        likes_map = {pid: cnt for pid, cnt in likes_raw.fetchall()}
        comments_raw = await db.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(ids), Comment.active.is_(True))
            .group_by(Comment.post_id)
        )
        comments_map = {pid: cnt for pid, cnt in comments_raw.fetchall()}
    else:
        likes_map, comments_map = {}, {}

    items = []
    for post in posts:
        item = await _build_post_list_item(
            post,
            db,
            language,
            likes_count=likes_map.get(post.id, 0),
            comments_count=comments_map.get(post.id, 0),
        )
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/users/me/stats",
    summary="获取我的统计",
    description="获取当前用户的文章数、评论数、获赞数统计。",
    responses={200: {"model": UserBlogStatsResponse}},
)
async def get_my_stats(
    current_user: CurrentUser,
    db: DB,
):
    """获取当前用户的统计数据"""
    posts_count = (
        await db.scalar(
            select(func.count()).select_from(Post).where(Post.author_id == current_user.id)
        )
        or 0
    )

    comments_count = (
        await db.scalar(
            select(func.count()).select_from(Comment).where(Comment.user_id == current_user.id)
        )
        or 0
    )

    likes_received = (
        await db.scalar(
            select(func.count())
            .select_from(post_likes)
            .join(Post, Post.id == post_likes.c.post_id)
            .where(Post.author_id == current_user.id)
        )
        or 0
    )

    return {
        "success": True,
        "data": {
            "posts": posts_count,
            "comments": comments_count,
            "likes": likes_received,
        },
        "message": "获取统计成功",
    }


@router.get(
    "/users/me/posts",
    response_model=PaginatedResponse,
    summary="获取我的文章",
    description="获取当前用户发表的所有文章，包括草稿。",
)
async def get_my_posts(
    request: Request,
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取当前用户的文章"""
    language = get_language_from_request(request, lang)

    count_query = select(func.count()).select_from(Post).where(Post.author_id == current_user.id)
    total = await db.scalar(count_query) or 0

    query = (
        select(Post)
        .options(selectinload(Post.category), selectinload(Post.tags))
        .where(Post.author_id == current_user.id)
        .order_by(Post.created_at.desc())
    )

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    posts = result.scalars().all()

    items = []
    for post in posts:
        items.append(
            {
                "id": post.id,
                "title": get_i18n_value(post.title, language),
                "slug": post.slug,
                "cover_image": post.cover_image,
                "status": post.status,
                "views": post.views,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "category": {
                    "id": post.category.id,
                    "name": get_i18n_value(post.category.name, language),
                    "slug": post.category.slug,
                }
                if post.category
                else None,
            }
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/users/me/history",
    response_model=PaginatedResponse,
    summary="获取阅读历史",
    description="获取当前用户的阅读历史记录。",
)
async def get_my_history(
    request: Request,
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取当前用户的阅读历史"""
    from backend.models.blog import PostViewHistory

    language = get_language_from_request(request, lang)

    count_query = (
        select(func.count())
        .select_from(PostViewHistory)
        .where(PostViewHistory.user_id == current_user.id)
    )
    total = await db.scalar(count_query) or 0

    query = (
        select(PostViewHistory)
        .options(selectinload(PostViewHistory.post).selectinload(Post.category))
        .where(PostViewHistory.user_id == current_user.id)
        .order_by(PostViewHistory.viewed_at.desc())
    )

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    histories = result.scalars().all()

    items = []
    for history in histories:
        post = history.post
        if post:
            items.append(
                {
                    "id": history.id,
                    "viewed_at": history.viewed_at.isoformat() if history.viewed_at else None,
                    "post": {
                        "id": post.id,
                        "title": await render_title(
                            get_i18n_value(post.title, language), post=post, language=language
                        ),
                        "slug": post.slug,
                        "cover_image": post.cover_image,
                        "views": post.views,
                        "category": {
                            "id": post.category.id,
                            "name": get_i18n_value(post.category.name, language),
                            "slug": post.category.slug,
                        }
                        if post.category
                        else None,
                    }
                    if post
                    else None,
                }
            )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.delete(
    "/users/me/history",
    summary="清空阅读历史",
    description="清空当前用户的阅读历史记录。",
    responses={200: {"model": BaseResponse}},
)
async def clear_my_history(
    current_user: CurrentUser,
    db: DB,
):
    """清空当前用户的阅读历史"""
    from backend.models.blog import PostViewHistory

    await db.execute(
        PostViewHistory.__table__.delete().where(PostViewHistory.user_id == current_user.id)
    )
    await db.flush()

    return {"success": True, "data": None, "message": "阅读历史已清空"}


async def _effective_site_meta() -> dict[str, str]:
    """RSS 需要的站点名/URL：以 /api/config 的构建结果为唯一权威（含分组 JSON 覆写，
    任一分组保存即失效，天然新鲜）。缓存未命中（冷启动首请求就是 /rss）时先自调用
    /api/config 顺带预热缓存，再读回——避免在别处复刻一套优先级逻辑造成口径漂移。"""
    from backend.core.cache import cache, make_cache_key

    site_name = site_url = ""
    try:
        cache_key = make_cache_key("site_config")
        cached = await cache.get(cache_key)
        if not isinstance(cached, dict):
            import httpx

            from backend.main import app as _app

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=_app), timeout=5, base_url="http://internal"
            ) as _c:
                await _c.get("/api/config")
            cached = await cache.get(cache_key)
        if isinstance(cached, dict):
            site_name = str(cached.get("site_name") or "")
            site_url = str(cached.get("site_url") or "")
    except Exception:  # 配置读取异常不阻断订阅源，回退 env 口径
        pass
    return {"site_name": site_name, "site_url": site_url}


@router.get(
    "/rss",
    summary="RSS 订阅",
    description="获取 RSS 2.0 格式的文章订阅源。",
    responses=raw_content_response("application/rss+xml", "RSS 2.0 XML 文档。"),
    response_class=Response,
)
async def get_rss_feed(
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
    limit: int = Query(20, ge=1, le=100, description="文章数量"),
):
    """获取 RSS 2.0 订阅源"""
    from fastapi.responses import Response

    from backend.core.config import settings

    language = get_language_from_request(request, lang)

    # RSS 是匿名+爬虫流量，内容却与"最新已发布文章"同频；列表缓存本来就是 300s 口径，
    # 这里同 TTL 顺带把订阅源的 DB 压力摊平。
    # 键刻意挂在 "posts:" 前缀下：文章的增删改统一走 invalidate_cache("posts")，
    # 换成独立的 "rss:" 前缀就再没人负责失效它，删掉的文章会一直挂在订阅源里。
    cache_key = make_cache_key("posts", "rss", language, str(limit))
    cached_xml = await cache.get(cache_key)
    if isinstance(cached_xml, str) and cached_xml:
        return Response(content=cached_xml, media_type="application/rss+xml")

    # generate_rss_feed 逐条读取 post.author.nickname / post.category.name；
    # 不预加载就是 1 + 2*limit 次隐式 IO（limit 最大 100），且 async 会话上的隐式
    # lazy-load 会抛 MissingGreenlet —— 匿名可访、无缓存、爬虫必到的入口。
    query = (
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category))
        .where(Post.status == "published")
        .order_by(Post.is_pinned.desc(), Post.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    posts = result.scalars().all()

    # 站点名/URL 取管理端配置（与 /api/config 权威同源），env settings 仅冷启动兜底——
    # 此前直接用 settings.app_name / site_url，admin 改站点名后订阅源标题仍是旧值，
    # 且 basic 分组 JSON 的覆写根本不参与（RSS 与前台/OG 口径分裂）。
    cfg = await _effective_site_meta()
    site_url = cfg["site_url"] or settings.site_url
    site_title = cfg["site_name"] or settings.app_name
    rss_content = await generate_rss_feed(posts, language, site_url, site_title)

    await cache.set(cache_key, rss_content, CACHE_TTL["post_list"])
    return Response(content=rss_content, media_type="application/rss+xml")


# Sitemap 每页最大 URL 数（sitemaps.org 协议建议单文件不超过 5 万，这里取保守值）
SITEMAP_PAGE_SIZE = 1000


def _xml_escape(text: str) -> str:
    """转义 XML 文本中的特殊字符。"""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


# Sitemap 协议常量
_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
_SITEMAP_IMG_NS = "http://www.google.com/schemas/sitemap-image/1.1"

# 固定公开路由：(路径, 更新频率, 优先级)。
# /search（noindex）、/login、/register、/oobe、/admin/** 一律不收录。
# 注意：`/categories` `/tags` `/series` 三个分类学根路径**不在**这里——它们由
# `generate_taxonomy_sitemap` 无条件输出（哪怕一个分类都没有）。在此重复会让
# sitemap 索引对同一 URL 提交两次，Search Console 直接报"重复网址"。
_STATIC_SITEMAP_ROUTES: list[tuple[str, str, str]] = [
    ("/", "daily", "1.0"),
    ("/posts", "daily", "0.9"),
    ("/posts/hot", "weekly", "0.6"),
    ("/archive", "monthly", "0.4"),
    ("/guestbook", "daily", "0.5"),
    ("/activity", "daily", "0.4"),
    ("/gallery", "weekly", "0.4"),
    ("/about", "monthly", "0.3"),
    ("/friends", "monthly", "0.3"),
]


def _iso8601(dt: datetime | None) -> str | None:
    """W3C Datetime（ISO 8601）；无时区则假定 UTC。"""
    aware = _ensure_aware(dt)
    if aware is None:
        return None
    return aware.isoformat(timespec="seconds")


def _sitemap_url(
    loc: str,
    *,
    lastmod: str | None = None,
    changefreq: str | None = None,
    priority: str | None = None,
    images: list[str] | None = None,
) -> str:
    """生成单个 ``<url>`` 条目。"""
    parts = ["  <url>", f"    <loc>{_xml_escape(loc)}</loc>"]
    if lastmod:
        parts.append(f"    <lastmod>{_xml_escape(lastmod)}</lastmod>")
    if changefreq:
        parts.append(f"    <changefreq>{changefreq}</changefreq>")
    if priority:
        parts.append(f"    <priority>{priority}</priority>")
    for img in images or []:
        if img:
            parts.append("    <image:image>")
            parts.append(f"      <image:loc>{_xml_escape(img)}</image:loc>")
            parts.append("    </image:image>")
    parts.append("  </url>")
    return "\n".join(parts)


def _wrap_urlset(body: str, *, with_image: bool) -> str:
    """用 urlset 外壳包裹条目正文。"""
    ns = f'<urlset xmlns="{_SITEMAP_NS}"'
    if with_image:
        ns += f' xmlns:image="{_SITEMAP_IMG_NS}"'
    ns += ">"
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{ns}\n{body}\n</urlset>'


def generate_sitemap(
    posts: list[Post],
    categories: list[Category],
    tags: list[Tag],
    site_url: str,
) -> str:
    """生成合并 Sitemap（文章+分类+标签，向后兼容）。"""
    site_url = site_url.rstrip("/")
    entries: list[str] = []
    for post in posts:
        cover = _absolute_media(post.cover_image, site_url)
        entries.append(
            _sitemap_url(
                f"{site_url}/posts/{post.slug}",
                lastmod=_iso8601(post.updated_at or post.published_at),
                changefreq="weekly",
                priority="0.8",
                images=[cover] if cover else None,
            )
        )
    for category in categories:
        entries.append(
            _sitemap_url(
                f"{site_url}/categories/{category.slug}",
                lastmod=_iso8601(getattr(category, "updated_at", None)),
                changefreq="weekly",
                priority="0.6",
            )
        )
    for tag in tags:
        entries.append(
            _sitemap_url(
                f"{site_url}/tags/{tag.slug}",
                lastmod=_iso8601(getattr(tag, "updated_at", None)),
                changefreq="monthly",
                priority="0.5",
            )
        )
    return _wrap_urlset("\n".join(entries), with_image=True)


def generate_post_sitemap_page(posts: list[Post], site_url: str) -> str:
    """生成单页文章 sitemap（含封面图，用于分页）。"""
    site_url = site_url.rstrip("/")
    entries: list[str] = []
    for post in posts:
        cover = _absolute_media(post.cover_image, site_url)
        entries.append(
            _sitemap_url(
                f"{site_url}/posts/{post.slug}",
                lastmod=_iso8601(post.updated_at or post.published_at),
                changefreq="weekly",
                priority="0.8",
                images=[cover] if cover else None,
            )
        )
    return _wrap_urlset("\n".join(entries), with_image=True)


def generate_taxonomy_sitemap(
    categories: list[Category],
    tags: list[Tag],
    site_url: str,
    series: list | None = None,
    authors: list[tuple[str, object]] | None = None,
) -> str:
    """生成分类 / 标签 / 系列 / 作者归档 sitemap（真实前端路由，合并文件）。

    ``authors`` 是 `(用户名, 最近发布时间)` 列表：作者主页 (`/authors/<username>`) 是
    SSR、可索引的落地页，只靠文章详情页的作者卡发现 URL 太弱——与年份归档同理，
    声明可索引的页面就该进 sitemap。清单由调用方按隐私开关（`show_posts`）与
    「确有已发布文章」过滤，本函数只负责拼 URL。
    """
    site_url = site_url.rstrip("/")
    entries: list[str] = [
        _sitemap_url(f"{site_url}/categories", changefreq="weekly", priority="0.5")
    ]
    for category in categories:
        entries.append(
            _sitemap_url(
                f"{site_url}/categories/{category.slug}",
                lastmod=_iso8601(getattr(category, "updated_at", None)),
                changefreq="weekly",
                priority="0.6",
            )
        )
    entries.append(_sitemap_url(f"{site_url}/tags", changefreq="weekly", priority="0.4"))
    for tag in tags:
        entries.append(
            _sitemap_url(
                f"{site_url}/tags/{tag.slug}",
                lastmod=_iso8601(getattr(tag, "updated_at", None)),
                changefreq="monthly",
                priority="0.5",
            )
        )
    entries.append(_sitemap_url(f"{site_url}/series", changefreq="weekly", priority="0.5"))
    for s in series or []:
        entries.append(
            _sitemap_url(
                f"{site_url}/series/{s.slug}",
                lastmod=_iso8601(getattr(s, "updated_at", None)),
                changefreq="weekly",
                priority="0.6",
            )
        )
    for username, lastmod in authors or []:
        entries.append(
            _sitemap_url(
                f"{site_url}/authors/{username}",
                lastmod=_iso8601(lastmod),
                changefreq="monthly",
                priority="0.4",
            )
        )
    return _wrap_urlset("\n".join(entries), with_image=False)


def generate_pages_sitemap(
    pages: list, site_url: str, archive_years: list[int] | None = None
) -> str:
    """生成固定公开路由 + 年份归档落地页 + 独立页面（``/page/<slug>``）sitemap。

    ``/archive/<year>`` 是 SSR、可分享且会被索引的年份落地页（页面注释即为此口径），
    只把 ``/archive`` 总览提交给爬虫会让这一级落地页失去唯一的外链发现入口——
    年份由调用方按已发布文章的 ``published_at`` 去重给出，不存在的年份不会凭空生成 URL。
    """
    site_url = site_url.rstrip("/")
    entries: list[str] = []
    for path, changefreq, priority in _STATIC_SITEMAP_ROUTES:
        entries.append(_sitemap_url(f"{site_url}{path}", changefreq=changefreq, priority=priority))
    for year in archive_years or []:
        entries.append(
            _sitemap_url(f"{site_url}/archive/{year}", changefreq="monthly", priority="0.4")
        )
    for page in pages:
        if getattr(page, "status", "published") != "published":
            continue
        entries.append(
            _sitemap_url(
                f"{site_url}/page/{page.slug}",
                lastmod=_iso8601(getattr(page, "updated_at", None)),
                changefreq="monthly",
                priority="0.5",
            )
        )
    return _wrap_urlset("\n".join(entries), with_image=False)


def generate_sitemap_index(entries: list[tuple[str, str]], site_url: str | None = None) -> str:
    """生成 sitemap 索引 XML。

    Args:
        entries: ``[(loc_url, lastmod_str), ...]``
        site_url: 仅为向后兼容保留；loc 已要求是绝对 URL。
    """
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<sitemapindex xmlns="{_SITEMAP_NS}">',
    ]
    for loc, lastmod in entries:
        parts.append("  <sitemap>")
        parts.append(f"    <loc>{_xml_escape(loc)}</loc>")
        if lastmod:
            parts.append(f"    <lastmod>{_xml_escape(lastmod)}</lastmod>")
        parts.append("  </sitemap>")
    parts.append("</sitemapindex>")
    return "\n".join(parts)


_XML_CACHE = "public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400"


@router.get(
    "/sitemap.xml",
    summary="Sitemap 索引",
    description="站点地图索引：列出 pages 静态表、posts 分页表、taxonomies 分类表。"
    "所有子表均指向对外站点域名（由 Nitro BFF 代理）。",
    responses=raw_content_response("application/xml", "Sitemap index XML 文档。"),
    response_class=Response,
)
async def get_sitemap_index(
    db: DB,
    request: Request,
):
    """获取 Sitemap 索引 XML。"""
    site_url = _public_site_url()
    today = datetime.now(_tz.utc).strftime("%Y-%m-%d")

    total_posts = (
        await db.execute(select(func.count()).select_from(Post).where(Post.status == "published"))
    ).scalar() or 0
    total_pages = max(1, (total_posts + SITEMAP_PAGE_SIZE - 1) // SITEMAP_PAGE_SIZE)

    entries: list[tuple[str, str]] = [(f"{site_url}/sitemap-pages.xml", today)]
    for page in range(1, total_pages + 1):
        entries.append((f"{site_url}/sitemap-posts.xml?page={page}", today))
    entries.append((f"{site_url}/sitemap-taxonomies.xml", today))

    content = generate_sitemap_index(entries, site_url)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Cache-Control": _XML_CACHE},
    )


@router.get(
    "/sitemap-posts.xml",
    summary="文章 Sitemap（分页）",
    description="按 page 参数返回单页文章 sitemap，每页最多 1000 条，含封面图。",
    responses=raw_content_response("application/xml", "urlset XML 文档。"),
    response_class=Response,
)
async def get_sitemap_posts(
    db: DB,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
):
    """获取分页文章 Sitemap XML。"""
    site_url = _public_site_url()
    offset = (page - 1) * SITEMAP_PAGE_SIZE
    posts_result = await db.execute(
        select(Post)
        .where(Post.status == "published")
        .order_by(Post.published_at.desc())
        .offset(offset)
        .limit(SITEMAP_PAGE_SIZE)
    )
    posts = posts_result.scalars().all()
    content = generate_post_sitemap_page(posts, site_url)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Cache-Control": _XML_CACHE},
    )


@router.get(
    "/sitemap-taxonomies.xml",
    summary="分类 / 标签 / 系列 / 作者归档 Sitemap",
    description=(
        "返回分类、标签、系列的索引页与详情页，外加作者归档落地页 "
        "`/authors/<username>`（合并文件）。作者清单只含「有已发布文章，且未关闭 "
        "`show_posts` / `public_profile`」的作者——空归档页与 404 页都不该出现在爬虫视野里。"
    ),
    responses=raw_content_response("application/xml", "urlset XML 文档。"),
    response_class=Response,
)
async def get_sitemap_taxonomies(
    db: DB,
):
    """获取分类 / 标签 / 系列 / 作者归档 Sitemap XML。"""
    from backend.models.post_series import PostSeries

    site_url = _public_site_url()
    categories = (await db.execute(select(Category))).scalars().all()
    tags = (await db.execute(select(Tag).where(Tag.is_active.is_(True)))).scalars().all()
    series = (
        (await db.execute(select(PostSeries).where(PostSeries.is_active.is_(True)))).scalars().all()
    )
    # 作者归档清单：一条分组查询同时拿到用户名与最近发布时间（不做 N+1），
    # 并在同一条语句里排除「关了 show_posts」与「关了 public_profile」的作者——
    # 前者的归档页对访客是空页，后者在 GET /users/username/{u} 上直接回 404，
    # 提交给爬虫等于承认一个没有内容（甚至不存在）的 URL。
    # post_type 口径与作者页读的那份列表一致。
    hidden_authors = select(UserPreference.user_id).where(
        or_(UserPreference.show_posts.is_(False), UserPreference.public_profile.is_(False))
    )
    author_rows = (
        await db.execute(
            select(User.username, func.max(Post.published_at))
            .join(Post, Post.author_id == User.id)
            .where(
                Post.status == "published",
                Post.post_type == "post",
                User.id.not_in(hidden_authors),
            )
            .group_by(User.username)
            .order_by(func.max(Post.published_at).desc())
        )
    ).all()
    authors = [(username, lastmod) for username, lastmod in author_rows if username]

    content = generate_taxonomy_sitemap(categories, tags, site_url, series=series, authors=authors)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Cache-Control": _XML_CACHE},
    )


@router.get(
    "/sitemap-pages.xml",
    summary="静态路由 / 独立页面 Sitemap",
    description="返回固定公开路由与已发布独立页面（/page/<slug>）。",
    responses=raw_content_response("application/xml", "urlset XML 文档。"),
    response_class=Response,
)
async def get_sitemap_pages(db: DB):
    """获取静态路由 / 独立页面 Sitemap XML。"""
    from sqlalchemy import extract

    from backend.models import Post
    from backend.models.core import Page

    site_url = _public_site_url()
    pages = (await db.execute(select(Page).where(Page.status == "published"))).scalars().all()
    year_rows = (
        (
            await db.execute(
                select(extract("year", Post.published_at))
                .where(Post.status == "published", Post.published_at.is_not(None))
                .distinct()
            )
        )
        .scalars()
        .all()
    )
    archive_years = sorted({int(row) for row in year_rows if row}, reverse=True)
    content = generate_pages_sitemap(pages, site_url, archive_years=archive_years)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Cache-Control": _XML_CACHE},
    )
