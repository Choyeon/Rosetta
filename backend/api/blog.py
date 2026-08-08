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

import math
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff, CurrentUser, CurrentUserOptional
from backend.core.cache import CACHE_TTL, cache, invalidate_cache, make_cache_key
from backend.core.concurrency import concurrent_query
from backend.core.config import settings
from backend.core.i18n import (
    get_i18n_value,
    get_language_from_request,
)
from backend.models.blog import Category, Comment, Post, Tag, post_likes, post_tags
from backend.models.user import User
from backend.schemas import (
    BaseResponse,
    CategoryCreate,
    CategoryLocalizedResponse,
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
    TagUpdate,
)
from backend.utils.compat import UTC

router = APIRouter(tags=["博客"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OOBE_LOCK_FILE = BASE_DIR / ".oobe_complete"
CONFIG_FILE = BASE_DIR / "rosetta.json"


def is_oobe_complete() -> bool:
    return OOBE_LOCK_FILE.exists() and CONFIG_FILE.exists()


def generate_rss_feed(posts: list[Post], language: str, site_url: str, site_title: str) -> str:
    """生成 RSS 2.0 格式的订阅源"""
    from xml.etree.ElementTree import Element, SubElement, tostring

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = site_title
    SubElement(channel, "link").text = site_url
    SubElement(channel, "description").text = f"{site_title} - RSS 订阅"
    SubElement(channel, "language").text = language
    SubElement(channel, "lastBuildDate").text = datetime.now(UTC).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    for post in posts:
        item = SubElement(channel, "item")
        title = get_i18n_value(post.title, language)
        SubElement(item, "title").text = title
        SubElement(item, "link").text = f"{site_url}/post/{post.slug}"
        SubElement(item, "guid", isPermaLink="true").text = f"{site_url}/post/{post.slug}"

        if post.published_at:
            pub_date = post.published_at
        else:
            pub_date = post.created_at
        SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

        if post.excerpt:
            description = get_i18n_value(post.excerpt, language)
        else:
            content = get_i18n_value(post.content, language)
            description = content[:200] + "..." if len(content) > 200 else content
        SubElement(item, "description").text = description

        if post.cover_image:
            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", post.cover_image)
            enclosure.set("type", "image/jpeg")

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")


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


def calculate_reading_time(content: str) -> int:
    """计算阅读时间（分钟）"""
    chinese_chars = len(re.findall(r"[\u4e00-\u9fa5]", content))
    english_words = len(re.findall(r"[a-zA-Z0-9]+", content))
    minutes = (chinese_chars / 300) + (english_words / 150)
    return max(1, math.ceil(minutes))


async def _get_post_list_cache_key(
    language: str,
    page: int,
    page_size: int,
    category: str | None,
    tag: str | None,
    search: str | None,
    status_filter: str | None,
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
    ]
    return make_cache_key(*parts)


def _build_author_data(author: User | None) -> dict | None:
    """构建作者数据字典"""
    if not author:
        return None
    return {
        "id": author.id,
        "username": author.username,
        "nickname": author.nickname,
        "avatar": author.avatar,
        "email": author.email,
        "bio": author.bio,
        "website": author.website,
        "github": author.github,
        "cover_image": author.cover_image,
        "is_active": author.is_active,
        "is_staff": author.is_staff,
        "is_superuser": author.is_superuser,
        "title": author.title,
        "created_at": author.created_at,
        "last_login": author.last_login,
    }


def _build_post_list_item_from_row(
    row: tuple,
    language: str,
) -> PostListItemLocalized:
    """从查询结果行构建文章列表项（优化版，避免 N+1 查询）"""
    post = row.Post
    likes_count = row.likes_count or 0
    comments_count = row.comments_count or 0

    content = get_i18n_value(post.content, language)

    return PostListItemLocalized(
        id=post.id,
        title=get_i18n_value(post.title, language),
        subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
        slug=post.slug,
        excerpt=get_i18n_value(post.excerpt, language) if post.excerpt else None,
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
        reading_time=calculate_reading_time(content),
    )


async def _build_post_list_item(
    post: Post,
    db: DB,
    language: str,
) -> dict:
    """从 Post 对象构建文章列表项（用于点赞列表等场景）"""
    from backend.models.blog import Comment, post_likes

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

    content = get_i18n_value(post.content, language)

    return {
        "id": post.id,
        "title": get_i18n_value(post.title, language),
        "subtitle": get_i18n_value(post.subtitle, language) if post.subtitle else None,
        "slug": post.slug,
        "excerpt": get_i18n_value(post.excerpt, language) if post.excerpt else None,
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
        "reading_time": calculate_reading_time(content),
    }


# ==================== 文章接口 ====================


@router.get(
    "/posts",
    response_model=PaginatedResponse,
    summary="文章列表",
    description="获取文章列表，支持分类、标签筛选和关键词搜索。支持多语言返回。",
)
async def list_posts(
    request: Request,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=1000, description="每页数量"),
    category: str | None = Query(None, description="分类 slug"),
    tag: str | None = Query(None, description="标签 slug"),
    search: str | None = Query(None, description="搜索关键词"),
    status_filter: str | None = Query(None, alias="status", description="文章状态（需管理员权限）"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
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

    is_admin = (
        status_filter and current_user and (current_user.is_staff or current_user.is_superuser)
    )
    use_cache = not is_admin and not search

    if use_cache:
        cache_key = await _get_post_list_cache_key(
            language, page, page_size, category, tag, search, status_filter
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
        )
        .outerjoin(likes_subq, Post.id == likes_subq.c.post_id)
        .outerjoin(comments_subq, Post.id == comments_subq.c.post_id)
    )

    if is_admin:
        query = query.where(Post.status == status_filter)
    else:
        query = query.where(
            Post.status == "published",
            (Post.published_at.is_(None) | (Post.published_at <= func.now())),
        )

    if category:
        query = query.join(Category).where(Category.slug == category)

    if tag:
        query = query.join(Post.tags).where(Tag.slug == tag)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                cast(Post.title["zh"], String).ilike(search_term),
                cast(Post.title["en"], String).ilike(search_term),
                cast(Post.content["zh"], String).ilike(search_term),
                cast(Post.content["en"], String).ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .order_by(Post.is_pinned.desc(), Post.published_at.desc())
    )

    result = await db.execute(query)
    rows = result.unique().all()

    items = [_build_post_list_item_from_row(row, language) for row in rows]

    response = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )

    if use_cache:
        await cache.set(cache_key, response.model_dump(mode="json"), CACHE_TTL["post_list"])

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
    for post in result["items"]:
        likes_count, comments_count = await concurrent_query(
            db.scalar(
                select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post.id)
            ),
            db.scalar(
                select(func.count()).where(Comment.post_id == post.id, Comment.active.is_(True))
            ),
        )

        content = get_i18n_value(post.content, language)

        items.append(
            PostListItemLocalized(
                id=post.id,
                title=get_i18n_value(post.title, language),
                subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
                slug=post.slug,
                excerpt=get_i18n_value(post.excerpt, language) if post.excerpt else None,
                cover_image=post.cover_image,
                author=_build_author_data(post.author),
                category=CategoryLocalizedResponse.from_category(post.category, language)
                if post.category
                else None,
                tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
                status=post.status,
                views=post.views,
                likes_count=likes_count or 0,
                comments_count=comments_count or 0,
                is_pinned=post.is_pinned,
                created_at=post.created_at,
                published_at=post.published_at,
                reading_time=calculate_reading_time(content),
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
    for post in posts:
        likes_count, comments_count = await concurrent_query(
            db.scalar(
                select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post.id)
            ),
            db.scalar(
                select(func.count()).where(Comment.post_id == post.id, Comment.active.is_(True))
            ),
        )

        content = get_i18n_value(post.content, language)

        items.append(
            PostListItemLocalized(
                id=post.id,
                title=get_i18n_value(post.title, language),
                subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
                slug=post.slug,
                excerpt=get_i18n_value(post.excerpt, language) if post.excerpt else None,
                cover_image=post.cover_image,
                author=_build_author_data(post.author),
                category=CategoryLocalizedResponse.from_category(post.category, language)
                if post.category
                else None,
                tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
                status=post.status,
                views=post.views,
                likes_count=likes_count or 0,
                comments_count=comments_count or 0,
                is_pinned=post.is_pinned,
                created_at=post.created_at,
                published_at=post.published_at,
                reading_time=calculate_reading_time(content),
            )
        )

    return items


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
    password: str | None = Query(None, description="文章访问密码"),
    current_user: CurrentUserOptional = None,
):
    """获取文章详情，支持多语言和缓存
    智能识别 slug：纯数字自动按 ID 查询，否则按 slug 查询。
    """
    language = get_language_from_request(request, lang)

    cache_key = make_cache_key("post", slug, language)

    slug_is_numeric = slug.isdigit()

    def _build_query(by_id: bool):
        stmt = (
            select(Post)
            .options(
                selectinload(Post.author).selectinload(User.title),
                selectinload(Post.category),
                selectinload(Post.tags),
            )
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

    # 检查定时发布时间
    if post.status == "published" and post.published_at:
        if not (
            current_user
            and (
                current_user.id == post.author_id
                or current_user.is_staff
                or current_user.is_superuser
            )
        ):
            from datetime import datetime

            if post.published_at > datetime.now():
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
        elif password:
            # 验证密码
            from passlib.context import CryptContext

            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            can_access_content = pwd_context.verify(password, post.password)
        else:
            can_access_content = False

    current_views = post.views

    await db.execute(update(Post).where(Post.id == post.id).values(views=Post.views + 1))

    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.author).selectinload(User.title),
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        .where(Post.id == post.id)
        .execution_options(populate_existing=True)
    )
    post = result.scalar_one()
    post.views = current_views

    # 在后续并发查询/修改之前，预先加载所有要访问的列，避免 expire 后触发隐式 lazy-load
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

    # 并发获取点赞数和评论数
    likes_count, comments_count = await concurrent_query(
        db.scalar(
            select(func.count()).select_from(post_likes).where(post_likes.c.post_id == _id)
        ),
        db.scalar(select(func.count()).where(Comment.post_id == _id, Comment.active.is_(True))),
    )

    likes_count = likes_count or 0
    comments_count = comments_count or 0

    # 根据权限决定返回的内容
    if is_password_protected and not can_access_content:
        # 加密文章但无权限，返回基本信息但隐藏内容
        content = ""
        excerpt = get_i18n_value(_excerpt_i18n, language) if _excerpt_i18n else None
    else:
        content = get_i18n_value(_content_i18n, language)
        excerpt = get_i18n_value(_excerpt_i18n, language) if _excerpt_i18n else None

    response = PostLocalizedResponse(
        id=_id,
        title=get_i18n_value(_title_i18n, language),
        subtitle=get_i18n_value(_subtitle_i18n, language) if _subtitle_i18n else None,
        slug=_slug,
        source=_source,
        source_url=_source_url,
        audio=_audio if can_access_content else None,
        video=_video if can_access_content else None,
        video_url=_video_url if can_access_content else None,
        content=content,
        excerpt=excerpt,
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
        meta_keywords=get_i18n_value(_meta_keywords_i18n, language) if _meta_keywords_i18n else None,
        created_at=_created_at,
        published_at=_published_at,
        updated_at=_updated_at,
        reading_time=calculate_reading_time(content) if content else 0,
    )

    # 只有非加密或已授权的文章才缓存
    if not is_password_protected or can_access_content:
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
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = pwd_context.hash(post_data.password)

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
    )

    if status_value == "published":
        post.published_at = datetime.now(UTC)
        post.scheduled_at = None
    elif status_value == "scheduled":
        post.published_at = None

    db.add(post)
    await db.flush()

    if post_data.tag_ids:
        tags = await db.execute(select(Tag).where(Tag.id.in_(post_data.tag_ids)))
        post.tags = list(tags.scalars().all())

    await invalidate_cache("posts")

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
    return response


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

    update_data = post_data.model_dump(
        exclude_unset=True, exclude={"tag_ids", "password", "view_password"}
    )

    if post_data.password is not None:
        if post_data.password:
            from passlib.context import CryptContext

            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            post.password = pwd_context.hash(post_data.password)
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

    for field, value in update_data.items():
        setattr(post, field, value)

    if post_data.tag_ids is not None:
        tags = await db.execute(select(Tag).where(Tag.id.in_(post_data.tag_ids)))
        post.tags = list(tags.scalars().all())

    await db.flush()

    await cache.delete(make_cache_key("post", post.slug, language))
    await invalidate_cache("posts")

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

    return PostLocalizedResponse.from_post(
        post, language, likes_count=likes_count, comments_count=comments_count
    )


@router.delete(
    "/posts/{post_id}",
    response_model=BaseResponse,
    summary="删除文章",
    description="删除文章，仅作者或超级管理员可操作。",
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

    await db.delete(post)
    await invalidate_cache("posts")

    return BaseResponse(message="文章已删除")


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
    response_model=list[CategoryLocalizedResponse],
    summary="分类列表",
    description="获取所有分类及其文章数量。支持多语言返回。",
)
async def list_categories(
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取分类列表，支持多语言和缓存

    优化：使用 GROUP BY 批量统计文章数，避免 N+1 查询
    """
    if not is_oobe_complete():
        return []

    language = get_language_from_request(request, lang)

    cache_key = make_cache_key("categories", language)
    cached = await cache.get(cache_key)
    if cached:
        # 直接返回缓存的列表，不需要再验证
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
        CategoryLocalizedResponse(
            id=row.Category.id,
            name=get_i18n_value(row.Category.name, language),
            slug=row.Category.slug,
            description=get_i18n_value(row.Category.description, language)
            if row.Category.description
            else None,
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
    response_model=CategoryLocalizedResponse,
    summary="获取分类详情",
    description="根据 slug 获取分类详情。",
)
async def get_category_by_slug(
    slug: str,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """按 slug 获取分类"""
    language = get_language_from_request(request, lang)

    result = await db.execute(select(Category).where(Category.slug == slug))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在",
        )

    post_count = await db.scalar(select(func.count()).where(Post.category_id == category.id)) or 0

    return CategoryLocalizedResponse(
        id=category.id,
        name=get_i18n_value(category.name, language),
        slug=category.slug,
        description=get_i18n_value(category.description, language)
        if category.description
        else None,
        icon=category.icon,
        color=category.color,
        cover_image=category.cover_image,
        created_at=category.created_at,
        post_count=post_count,
    )


@router.post(
    "/categories",
    response_model=CategoryLocalizedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建分类",
    description="创建新分类，需要管理员权限。支持多语言内容。",
)
async def create_category(
    request: Request,
    data: CategoryCreate,
    current_user: CurrentStaff,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """创建分类，支持多语言"""
    language = get_language_from_request(request, lang)

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

    await invalidate_cache("categories")

    return CategoryLocalizedResponse(
        id=category.id,
        name=get_i18n_value(category.name, language),
        slug=category.slug,
        description=get_i18n_value(category.description, language)
        if category.description
        else None,
        icon=category.icon,
        color=category.color,
        cover_image=category.cover_image,
        created_at=category.created_at,
        post_count=0,
    )


# ==================== 标签接口 ====================


@router.get(
    "/tags",
    response_model=list[TagLocalizedResponse],
    summary="标签列表",
    description="获取所有激活的标签及其文章数量。支持多语言返回。",
)
async def list_tags(
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取标签列表，支持多语言和缓存

    优化：使用 GROUP BY 批量统计文章数，避免 N+1 查询
    """
    if not is_oobe_complete():
        return []

    language = get_language_from_request(request, lang)

    cache_key = make_cache_key("tags", language)
    cached = await cache.get(cache_key)
    if cached:
        # 直接返回缓存的列表，不需要再验证
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
        TagLocalizedResponse(
            id=row.Tag.id,
            name=get_i18n_value(row.Tag.name, language),
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
    response_model=TagLocalizedResponse,
    summary="获取标签详情",
    description="根据 slug 获取标签详情。",
)
async def get_tag_by_slug(
    slug: str,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """按 slug 获取标签"""
    language = get_language_from_request(request, lang)

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

    return TagLocalizedResponse(
        id=tag.id,
        name=get_i18n_value(tag.name, language),
        slug=tag.slug,
        color=tag.color,
        icon=tag.icon,
        is_active=tag.is_active,
        created_at=tag.created_at,
        post_count=post_count,
    )


@router.post(
    "/tags",
    response_model=TagLocalizedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建标签",
    description="创建新标签，需要管理员权限。支持多语言内容。",
)
async def create_tag(
    request: Request,
    data: TagCreate,
    current_user: CurrentStaff,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """创建标签，支持多语言"""
    language = get_language_from_request(request, lang)

    zh_name = data.name.get("zh", "") if isinstance(data.name, dict) else data.name
    slug = data.slug or generate_slug(zh_name)

    existing = await db.execute(select(Tag).where(Tag.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标签别名已存在",
        )

    tag = Tag(
        name=data.name,
        slug=slug,
        color=data.color,
        icon=data.icon,
        is_active=data.is_active,
    )
    db.add(tag)
    await db.flush()

    await invalidate_cache("tags")

    return TagLocalizedResponse(
        id=tag.id,
        name=get_i18n_value(tag.name, language),
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
    """获取文章评论"""
    result = await db.execute(
        select(Comment)
        .options(
            selectinload(Comment.user).selectinload(User.title),
            selectinload(Comment.replies).selectinload(Comment.user).selectinload(User.title),
        )
        .where(Comment.post_id == post_id, Comment.active.is_(True), Comment.parent_id.is_(None))
        .order_by(Comment.created_at.desc())
    )
    comments = result.scalars().unique().all()

    def build_comment_tree(comment: Comment) -> CommentResponse:
        """递归构建评论树"""
        replies = [build_comment_tree(r) for r in comment.replies if r.active]
        return CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            user=comment.user,
            parent_id=comment.parent_id,
            content=comment.content,
            active=comment.active,
            created_at=comment.created_at,
            replies=replies,
        )

    return [build_comment_tree(c) for c in comments]


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
    )
    db.add(comment)
    await db.flush()

    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        user=current_user,
        parent_id=comment.parent_id,
        content=comment.content,
        active=comment.active,
        created_at=comment.created_at,
        replies=[],
    )


# ==================== 归档 API ====================


@router.get(
    "/archive",
    summary="文章归档",
    description="按年月分组获取已发布文章的归档列表。",
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

    # 设置缓存
    await cache.set(cache_key, archive_data, CACHE_TTL["categories"])

    return archive_data


@router.get(
    "/archive/stats",
    summary="归档统计",
    description="获取归档统计信息，包括总文章数、年份数等。",
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
    posts_result = await db.execute(
        select(Post.content).where(*published_filter)
    )
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

    await cache.set(cache_key, archive_data, CACHE_TTL["categories"])

    return archive_data


@router.get(
    "/archive/{year}/{month}",
    summary="按年月获取归档",
    description="获取指定年月的文章归档。",
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
                "category": category_data,
                "views": post.views,
            }
        )

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
    response_model=CategoryLocalizedResponse,
    summary="更新分类",
    description="更新分类信息，需要管理员权限。",
)
async def update_category(
    category_id: int,
    request: Request,
    data: CategoryUpdate,
    current_user: CurrentStaff,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """更新分类"""
    language = get_language_from_request(request, lang)

    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.flush()
    await invalidate_cache("categories")

    post_count = await db.scalar(select(func.count()).where(Post.category_id == category.id)) or 0

    return CategoryLocalizedResponse(
        id=category.id,
        name=get_i18n_value(category.name, language),
        slug=category.slug,
        description=get_i18n_value(category.description, language)
        if category.description
        else None,
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
    description="删除分类，需要管理员权限。",
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

    await db.delete(category)
    await invalidate_cache("categories")

    return BaseResponse(message="分类已删除")


# ==================== 标签管理接口 ====================


@router.put(
    "/tags/{tag_id}",
    response_model=TagLocalizedResponse,
    summary="更新标签",
    description="更新标签信息，需要管理员权限。",
)
async def update_tag(
    tag_id: int,
    request: Request,
    data: TagUpdate,
    current_user: CurrentStaff,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """更新标签"""
    language = get_language_from_request(request, lang)

    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)

    await db.flush()
    await invalidate_cache("tags")

    post_count = (
        await db.scalar(
            select(func.count()).select_from(post_tags).where(post_tags.c.tag_id == tag.id)
        )
        or 0
    )

    return TagLocalizedResponse(
        id=tag.id,
        name=get_i18n_value(tag.name, language),
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
    description="删除标签，需要管理员权限。",
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

    await db.delete(tag)
    await invalidate_cache("tags")

    return BaseResponse(message="标签已删除")


# ==================== 文章按ID获取接口 ====================


@router.get(
    "/posts/id/{post_id}",
    response_model=PostLocalizedResponse,
    summary="按ID获取文章",
    description="根据文章ID获取文章详情，用于编辑等场景。",
)
async def get_post_by_id(
    post_id: int,
    request: Request,
    db: DB,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
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

    content = get_i18n_value(post.content, language)

    return PostLocalizedResponse(
        id=post.id,
        title=get_i18n_value(post.title, language),
        subtitle=get_i18n_value(post.subtitle, language) if post.subtitle else None,
        slug=post.slug,
        source=post.source,
        source_url=post.source_url,
        audio=post.audio,
        video=post.video,
        video_url=post.video_url,
        content=content,
        excerpt=get_i18n_value(post.excerpt, language) if post.excerpt else None,
        cover_image=post.cover_image,
        author=_build_author_data(post.author),
        category=CategoryLocalizedResponse.from_category(post.category, language)
        if post.category
        else None,
        tags=[TagLocalizedResponse.from_tag(t, language) for t in post.tags],
        status=post.status,
        visibility=post.visibility or "public",
        password=post.password,
        views=post.views,
        likes_count=likes_count,
        is_pinned=post.is_pinned,
        allow_comments=post.allow_comments,
        comments_count=comments_count,
        meta_title=get_i18n_value(post.meta_title, language) if post.meta_title else None,
        meta_description=get_i18n_value(post.meta_description, language)
        if post.meta_description
        else None,
        meta_keywords=get_i18n_value(post.meta_keywords, language) if post.meta_keywords else None,
        created_at=post.created_at,
        published_at=post.published_at,
        updated_at=post.updated_at,
        reading_time=calculate_reading_time(content),
    )


@router.get(
    "/posts/{post_id}",
    response_model=PostEditResponse,
    summary="获取文章用于编辑",
    description="根据文章ID获取完整的多语言内容，用于文章编辑页面。",
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

    items = []
    for post in posts:
        item = await _build_post_list_item(post, db, language)
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
        "posts": posts_count,
        "comments": comments_count,
        "likes": likes_received,
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
                        "title": get_i18n_value(post.title, language),
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

    return {"message": "阅读历史已清空"}


@router.get(
    "/rss",
    summary="RSS 订阅",
    description="获取 RSS 2.0 格式的文章订阅源。",
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

    query = (
        select(Post)
        .where(Post.status == "published")
        .order_by(Post.is_pinned.desc(), Post.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    posts = result.scalars().all()

    site_url = settings.site_url
    site_title = settings.app_name
    rss_content = generate_rss_feed(posts, language, site_url, site_title)

    return Response(content=rss_content, media_type="application/rss+xml")


def generate_sitemap(
    posts: list[Post], categories: list[Category], tags: list[Tag], site_url: str
) -> str:
    """生成 Sitemap XML"""
    from xml.etree.ElementTree import Element, SubElement, tostring

    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for post in posts:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{site_url}/post/{post.slug}"
        if post.updated_at:
            SubElement(url, "lastmod").text = post.updated_at.strftime("%Y-%m-%d")
        SubElement(url, "changefreq").text = "weekly"
        SubElement(url, "priority").text = "0.8"

    for category in categories:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{site_url}/category/{category.slug}"
        SubElement(url, "changefreq").text = "weekly"
        SubElement(url, "priority").text = "0.6"

    for tag in tags:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{site_url}/tag/{tag.slug}"
        SubElement(url, "changefreq").text = "monthly"
        SubElement(url, "priority").text = "0.5"

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(urlset, encoding="unicode")


@router.get(
    "/sitemap.xml",
    summary="Sitemap",
    description="获取站点地图 XML。",
)
async def get_sitemap(
    db: DB,
):
    """获取 Sitemap XML"""
    from fastapi.responses import Response

    from backend.core.config import settings

    posts_result = await db.execute(
        select(Post).where(Post.status == "published").order_by(Post.published_at.desc())
    )
    posts = posts_result.scalars().all()

    categories_result = await db.execute(select(Category))
    categories = categories_result.scalars().all()

    tags_result = await db.execute(select(Tag).where(Tag.is_active.is_(True)))
    tags = tags_result.scalars().all()

    site_url = settings.site_url
    sitemap_content = generate_sitemap(posts, categories, tags, site_url)

    return Response(content=sitemap_content, media_type="application/xml")
