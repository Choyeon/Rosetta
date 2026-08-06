"""
导入导出 API

支持文章、分类、标签等数据的导入导出。
"""

import io
import json
import zipfile
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff
from backend.models.blog import Category, Post, Tag
from backend.models.log import OperationLog
from backend.utils.compat import UTC

router = APIRouter(tags=["导入导出"])


# ==================== 导出 API ====================


@router.get(
    "/export/posts",
    summary="导出文章",
    description="导出所有文章为 JSON 格式。",
)
async def export_posts(
    db: DB,
    current_user: CurrentStaff,
    include_drafts: bool = False,
    include_content: bool = True,
):
    """
    导出文章数据

    返回一个 ZIP 文件，包含：
    - posts.json: 文章列表
    - categories.json: 分类列表
    - tags.json: 标签列表
    """
    # 查询文章
    query = select(Post).options(selectinload(Post.category), selectinload(Post.tags))
    if not include_drafts:
        query = query.where(Post.status == "published")

    result = await db.execute(query.order_by(Post.created_at.desc()))
    posts = result.unique().scalars().all()

    # 查询分类
    categories_result = await db.execute(select(Category))
    categories = categories_result.scalars().all()

    # 查询标签
    tags_result = await db.execute(select(Tag))
    tags = tags_result.scalars().all()

    # 构建导出数据
    posts_data = []
    for post in posts:
        post_dict = {
            "id": post.id,
            "title": post.title,
            "slug": post.slug,
            "subtitle": post.subtitle,
            "excerpt": post.excerpt,
            "cover_image": post.cover_image,
            "source": post.source,
            "source_url": post.source_url,
            "status": post.status,
            "views": post.views,
            "is_pinned": post.is_pinned,
            "allow_comments": post.allow_comments,
            "password": post.password,
            "category": {"id": post.category.id, "slug": post.category.slug}
            if post.category
            else None,
            "tags": [{"id": t.id, "slug": t.slug} for t in post.tags],
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "published_at": post.published_at.isoformat() if post.published_at else None,
        }
        if include_content:
            post_dict["content"] = post.content
        posts_data.append(post_dict)

    categories_data = [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "icon": c.icon,
            "color": c.color,
            "cover_image": c.cover_image,
        }
        for c in categories
    ]

    tags_data = [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "color": t.color,
            "icon": t.icon,
        }
        for t in tags
    ]

    # 创建 ZIP 文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("posts.json", json.dumps(posts_data, ensure_ascii=False, indent=2))
        zf.writestr("categories.json", json.dumps(categories_data, ensure_ascii=False, indent=2))
        zf.writestr("tags.json", json.dumps(tags_data, ensure_ascii=False, indent=2))
        zf.writestr(
            "export_info.json",
            json.dumps(
                {
                    "exported_at": datetime.now(UTC).isoformat(),
                    "exported_by": current_user.username,
                    "posts_count": len(posts_data),
                    "include_drafts": include_drafts,
                    "include_content": include_content,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

    zip_buffer.seek(0)

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action="export",
        resource_type="post",
        detail=json.dumps(
            {
                "posts_count": len(posts_data),
                "include_drafts": include_drafts,
            }
        ),
    )
    db.add(log)
    await db.flush()

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=rosetta_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        },
    )


@router.get(
    "/export/markdown",
    summary="导出为 Markdown",
    description="将文章导出为 Markdown 文件。",
)
async def export_markdown(
    db: DB,
    current_user: CurrentStaff,
    lang: str = "zh",
):
    """
    导出文章为 Markdown 格式

    每篇文章一个 .md 文件，包含 frontmatter。
    """
    # 查询已发布文章
    result = await db.execute(
        select(Post)
        .where(Post.status == "published")
        .options(selectinload(Post.category), selectinload(Post.tags))
        .order_by(Post.created_at.desc())
    )
    posts = result.unique().scalars().all()

    # 创建 ZIP 文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for post in posts:
            # 获取标题和内容
            title = post.title.get(lang, post.title.get("zh", "")) if post.title else ""
            content = post.content.get(lang, post.content.get("zh", "")) if post.content else ""

            # 构建 frontmatter
            frontmatter = "---\n"
            frontmatter += f"title: {title}\n"
            frontmatter += f"slug: {post.slug}\n"
            frontmatter += f"date: {post.published_at.isoformat() if post.published_at else ''}\n"
            if post.category:
                cat_name = (
                    post.category.name.get(lang, post.category.name.get("zh", ""))
                    if post.category.name
                    else ""
                )
                frontmatter += f"category: {cat_name}\n"
            if post.tags:
                tag_names = [
                    t.name.get(lang, t.name.get("zh", "")) if t.name else "" for t in post.tags
                ]
                frontmatter += f"tags: [{', '.join(tag_names)}]\n"
            if post.cover_image:
                frontmatter += f"cover: {post.cover_image}\n"
            frontmatter += "---\n\n"

            # 完整内容
            full_content = frontmatter + content

            # 文件名
            filename = f"{post.slug}.md"
            zf.writestr(filename, full_content)

        # 添加导出信息
        zf.writestr(
            "README.md",
            f"# Rosetta Blog Export\n\nExported at: {datetime.now(UTC).isoformat()}\nTotal posts: {len(posts)}\n",
        )

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=rosetta_markdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        },
    )


# ==================== 导入 API ====================


class ImportResult(BaseModel):
    """导入结果"""

    success: bool
    message: str
    created_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = []


@router.post(
    "/import/posts",
    summary="导入文章",
    description="从 JSON 文件导入文章。",
)
async def import_posts(
    db: DB,
    current_user: CurrentStaff,
    file: UploadFile = File(...),
    skip_existing: bool = True,
):
    """
    导入文章数据

    接受 ZIP 文件，包含 posts.json、categories.json、tags.json
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传 ZIP 文件",
        )

    try:
        content = await file.read()
        zip_buffer = io.BytesIO(content)

        with zipfile.ZipFile(zip_buffer, "r") as zf:
            # 读取文件
            posts_json = (
                zf.read("posts.json").decode("utf-8") if "posts.json" in zf.namelist() else "[]"
            )
            categories_json = (
                zf.read("categories.json").decode("utf-8")
                if "categories.json" in zf.namelist()
                else "[]"
            )
            tags_json = (
                zf.read("tags.json").decode("utf-8") if "tags.json" in zf.namelist() else "[]"
            )

            posts_data = json.loads(posts_json)
            categories_data = json.loads(categories_json)
            tags_data = json.loads(tags_json)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解析文件失败: {str(e)}",
        )

    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []

    # 导入分类
    category_map = {}  # old_id -> new_category
    for cat_data in categories_data:
        try:
            existing = await db.execute(select(Category).where(Category.slug == cat_data["slug"]))
            if existing.scalar_one_or_none():
                continue

            category = Category(
                name=cat_data.get("name", {}),
                slug=cat_data["slug"],
                description=cat_data.get("description"),
                icon=cat_data.get("icon"),
                color=cat_data.get("color", "primary"),
                cover_image=cat_data.get("cover_image"),
            )
            db.add(category)
            await db.flush()
            category_map[cat_data["id"]] = category

        except Exception as e:
            errors.append(f"导入分类失败: {cat_data.get('slug', 'unknown')} - {str(e)}")

    # 导入标签
    tag_map = {}  # old_id -> new_tag
    for tag_data in tags_data:
        try:
            existing = await db.execute(select(Tag).where(Tag.slug == tag_data["slug"]))
            if existing.scalar_one_or_none():
                continue

            tag = Tag(
                name=tag_data.get("name", {}),
                slug=tag_data["slug"],
                color=tag_data.get("color", "#64748B"),
                icon=tag_data.get("icon"),
            )
            db.add(tag)
            await db.flush()
            tag_map[tag_data["id"]] = tag

        except Exception as e:
            errors.append(f"导入标签失败: {tag_data.get('slug', 'unknown')} - {str(e)}")

    # 导入文章
    for post_data in posts_data:
        try:
            # 检查是否已存在
            existing = await db.execute(select(Post).where(Post.slug == post_data["slug"]))
            if existing.scalar_one_or_none():
                if skip_existing:
                    skipped_count += 1
                    continue
                else:
                    error_count += 1
                    errors.append(f"文章已存在: {post_data['slug']}")
                    continue

            # 获取分类
            category = None
            if post_data.get("category"):
                cat_slug = post_data["category"].get("slug")
                if cat_slug:
                    cat_result = await db.execute(select(Category).where(Category.slug == cat_slug))
                    category = cat_result.scalar_one_or_none()

            # 创建文章
            post = Post(
                title=post_data.get("title", {}),
                slug=post_data["slug"],
                subtitle=post_data.get("subtitle"),
                content=post_data.get("content", {}),
                excerpt=post_data.get("excerpt"),
                cover_image=post_data.get("cover_image"),
                source=post_data.get("source", "原创"),
                source_url=post_data.get("source_url"),
                status=post_data.get("status", "draft"),
                views=post_data.get("views", 0),
                is_pinned=post_data.get("is_pinned", False),
                allow_comments=post_data.get("allow_comments", True),
                password=post_data.get("password"),
                author_id=current_user.id,
                category_id=category.id if category else None,
            )
            db.add(post)
            await db.flush()

            # 添加标签
            for tag_info in post_data.get("tags", []):
                tag_slug = tag_info.get("slug")
                if tag_slug:
                    tag_result = await db.execute(select(Tag).where(Tag.slug == tag_slug))
                    tag = tag_result.scalar_one_or_none()
                    if tag:
                        post.tags.append(tag)

            created_count += 1

        except Exception as e:
            error_count += 1
            errors.append(f"导入文章失败: {post_data.get('slug', 'unknown')} - {str(e)}")

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action="import",
        resource_type="post",
        detail=json.dumps(
            {
                "created_count": created_count,
                "skipped_count": skipped_count,
                "error_count": error_count,
            }
        ),
    )
    db.add(log)
    await db.flush()

    return ImportResult(
        success=True,
        message=f"导入完成：创建 {created_count} 篇，跳过 {skipped_count} 篇，失败 {error_count} 篇",
        created_count=created_count,
        skipped_count=skipped_count,
        error_count=error_count,
        errors=errors[:10],  # 只返回前 10 个错误
    )


@router.post(
    "/import/markdown",
    summary="导入 Markdown",
    description="从 Markdown 文件导入文章。",
)
async def import_markdown(
    db: DB,
    current_user: CurrentStaff,
    file: UploadFile = File(...),
    default_category: str | None = None,
):
    """
    导入 Markdown 文件

    支持 frontmatter 格式
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传文件",
        )

    content = (await file.read()).decode("utf-8")

    # 解析 frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_str = parts[1].strip()
            body = parts[2].strip()

            # 解析 frontmatter
            frontmatter = {}
            for line in frontmatter_str.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

            # 生成 slug
            import re

            title = frontmatter.get("title", "Untitled")
            slug = frontmatter.get("slug", re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"))

            # 检查是否已存在
            existing = await db.execute(select(Post).where(Post.slug == slug))
            if existing.scalar_one_or_none():
                return ImportResult(
                    success=False,
                    message=f"文章已存在: {slug}",
                )

            # 创建文章
            post = Post(
                title={"zh": title},
                slug=slug,
                content={"zh": body},
                status="draft",
                author_id=current_user.id,
            )
            db.add(post)
            await db.flush()

            return ImportResult(
                success=True,
                message=f"成功导入: {title}",
                created_count=1,
            )

    return ImportResult(
        success=False,
        message="无法解析 Markdown 文件，请确保包含 frontmatter",
    )


# ==================== 全站备份 API ====================


# 备份版本号，便于以后兼容性升级
BACKUP_VERSION = "1.0"

# 尝试导入 PostSeries 模型（可能不存在）
try:  # pragma: no cover - 视项目实际模型而定
    from backend.models.post_series import PostSeries  # type: ignore
except Exception:  # noqa: BLE001
    PostSeries = None

from sqlalchemy import func as sa_func  # noqa: E402

from backend.models.announcement import Announcement  # noqa: E402
from backend.models.blog import Comment  # noqa: E402
from backend.models.core import (  # noqa: E402
    FriendLink,
    Media,
    Navigation,
    Page,
    SiteConfig,
)
from backend.models.hero import HeroSlide  # noqa: E402
from backend.models.user import User  # noqa: E402


def _iso(dt) -> str | None:
    """安全地将 datetime 转为 ISO 字符串"""
    return dt.isoformat() if dt else None


def _parse_dt(value):
    """将 ISO 字符串解析为带时区的 datetime，失败返回 None"""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


@router.get(
    "/backup/info",
    summary="备份信息",
    description="返回当前数据库各项数据统计，用于备份前预览。",
)
async def backup_info(
    db: DB,
    current_user: CurrentStaff,
):
    """获取备份数据统计信息"""

    async def _count(model):
        result = await db.execute(select(sa_func.count()).select_from(model))
        return int(result.scalar() or 0)

    counts = {
        "posts": await _count(Post),
        "categories": await _count(Category),
        "tags": await _count(Tag),
        "comments": await _count(Comment),
        "users": await _count(User),
        "media": await _count(Media),
        "friend_links": await _count(FriendLink),
        "navigations": await _count(Navigation),
        "pages": await _count(Page),
        "announcements": await _count(Announcement),
        "hero_slides": await _count(HeroSlide),
        "site_config": await _count(SiteConfig),
    }
    if PostSeries is not None:
        counts["post_series"] = await _count(PostSeries)

    return {
        "counts": counts,
        "total": sum(counts.values()),
        "queried_at": datetime.now(UTC).isoformat(),
        "queried_by": current_user.username,
    }


@router.get(
    "/backup/full",
    summary="全站备份",
    description="导出整站数据为 ZIP 文件，包含所有内容模型及 manifest.json。",
)
async def backup_full(
    db: DB,
    current_user: CurrentStaff,
):
    """全站备份：导出为 ZIP，内含各模型的 JSON 文件与 manifest.json"""
    # === 查询所有数据（预加载关联，避免 N+1） ===
    posts_result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.category),
            selectinload(Post.tags),
            selectinload(Post.author),
        )
        .order_by(Post.created_at.asc())
    )
    posts = posts_result.unique().scalars().all()

    categories_result = await db.execute(select(Category).order_by(Category.id))
    categories = categories_result.scalars().all()

    tags_result = await db.execute(select(Tag).order_by(Tag.id))
    tags = tags_result.scalars().all()

    comments_result = await db.execute(select(Comment).order_by(Comment.created_at.asc()))
    comments = comments_result.scalars().all()

    users_result = await db.execute(select(User).order_by(User.id))
    users = users_result.scalars().all()

    media_result = await db.execute(select(Media).order_by(Media.id))
    media = media_result.scalars().all()

    friend_links_result = await db.execute(select(FriendLink).order_by(FriendLink.order))
    friend_links = friend_links_result.scalars().all()

    navigations_result = await db.execute(select(Navigation).order_by(Navigation.order))
    navigations = navigations_result.scalars().all()

    pages_result = await db.execute(select(Page).order_by(Page.id))
    pages = pages_result.scalars().all()

    announcements_result = await db.execute(select(Announcement).order_by(Announcement.sort_order))
    announcements = announcements_result.scalars().all()

    hero_slides_result = await db.execute(select(HeroSlide).order_by(HeroSlide.sort_order))
    hero_slides = hero_slides_result.scalars().all()

    site_config_result = await db.execute(select(SiteConfig).order_by(SiteConfig.key))
    site_configs = site_config_result.scalars().all()

    # 用于评论关联还原
    post_slug_map = {p.id: p.slug for p in posts}
    user_username_map = {u.id: u.username for u in users}

    # === 序列化 ===
    posts_data = [
        {
            "id": p.id,
            "title": p.title,
            "subtitle": p.subtitle,
            "slug": p.slug,
            "source": p.source,
            "source_url": p.source_url,
            "audio": p.audio,
            "video": p.video,
            "video_url": p.video_url,
            "content": p.content,
            "excerpt": p.excerpt,
            "cover_image": p.cover_image,
            "author_username": p.author.username if p.author else None,
            "category_slug": p.category.slug if p.category else None,
            "tag_slugs": [t.slug for t in p.tags],
            "status": p.status,
            "visibility": p.visibility,
            "password": p.password,
            "views": p.views,
            "is_pinned": p.is_pinned,
            "allow_comments": p.allow_comments,
            "meta_title": p.meta_title,
            "meta_description": p.meta_description,
            "meta_keywords": p.meta_keywords,
            "series_id": p.series_id,
            "series_order": p.series_order,
            "encrypted_content": p.encrypted_content,
            "encryption_enabled": p.encryption_enabled,
            "encryption_hint": p.encryption_hint,
            "scheduled_at": _iso(p.scheduled_at),
            "created_at": _iso(p.created_at),
            "published_at": _iso(p.published_at),
            "updated_at": _iso(p.updated_at),
        }
        for p in posts
    ]

    categories_data = [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "icon": c.icon,
            "color": c.color,
            "cover_image": c.cover_image,
        }
        for c in categories
    ]

    tags_data = [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "color": t.color,
            "icon": t.icon,
            "is_active": t.is_active,
        }
        for t in tags
    ]

    comments_data = [
        {
            "id": c.id,
            "post_slug": post_slug_map.get(c.post_id),
            "user_username": user_username_map.get(c.user_id),
            "parent_id": c.parent_id,
            "content": c.content,
            "active": c.active,
            "created_at": _iso(c.created_at),
        }
        for c in comments
    ]

    # users：脱敏，不含密码
    users_data = [
        {
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "avatar": u.avatar,
            "bio": u.bio,
            "created_at": _iso(u.created_at),
        }
        for u in users
    ]

    media_data = [
        {
            "id": m.id,
            "file": m.file,
            "filename": m.filename,
            "file_type": m.file_type,
            "file_size": m.file_size,
            "title": m.title,
            "alt_text": m.alt_text,
            "description": m.description,
            "uploaded_by_username": None,  # 媒体上传者关系可选，留空避免 N+1
            "created_at": _iso(m.created_at),
            "updated_at": _iso(m.updated_at),
        }
        for m in media
    ]

    friend_links_data = [
        {
            "id": f.id,
            "name": f.name,
            "url": f.url,
            "description": f.description,
            "logo": f.logo,
            "order": f.order,
            "is_active": f.is_active,
            "target_blank": f.target_blank,
        }
        for f in friend_links
    ]

    navigations_data = [
        {
            "id": n.id,
            "title": n.title,
            "url": n.url,
            "location": n.location,
            "order": n.order,
            "is_active": n.is_active,
            "target_blank": n.target_blank,
        }
        for n in navigations
    ]

    pages_data = [
        {
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "content": p.content,
            "status": p.status,
            "created_at": _iso(p.created_at),
            "updated_at": _iso(p.updated_at),
        }
        for p in pages
    ]

    announcements_data = [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "type": a.type,
            "is_active": a.is_active,
            "is_dismissible": a.is_dismissible,
            "start_time": _iso(a.start_time),
            "end_time": _iso(a.end_time),
            "sort_order": a.sort_order,
            "created_at": _iso(a.created_at),
            "updated_at": _iso(a.updated_at),
        }
        for a in announcements
    ]

    hero_slides_data = [
        {
            "id": h.id,
            "title": h.title,
            "subtitle": h.subtitle,
            "media_type": h.media_type,
            "media_url": h.media_url,
            "poster_url": h.poster_url,
            "overlay_opacity": h.overlay_opacity,
            "overlay_color": h.overlay_color,
            "cta_text": h.cta_text,
            "cta_url": h.cta_url,
            "cta_secondary_text": h.cta_secondary_text,
            "cta_secondary_url": h.cta_secondary_url,
            "text_align": h.text_align,
            "text_color": h.text_color,
            "is_active": h.is_active,
            "sort_order": h.sort_order,
            "start_time": _iso(h.start_time),
            "end_time": _iso(h.end_time),
            "created_at": _iso(h.created_at),
            "updated_at": _iso(h.updated_at),
        }
        for h in hero_slides
    ]

    site_config_data = [
        {
            "id": s.id,
            "key": s.key,
            "value": s.value,
            "description": s.description,
        }
        for s in site_configs
    ]

    post_series_data: list = []
    if PostSeries is not None:
        ps_result = await db.execute(select(PostSeries).order_by(PostSeries.id))
        post_series_list = ps_result.scalars().all()
        for ps in post_series_list:
            row = {}
            for col in PostSeries.__table__.columns:
                row[col.name] = getattr(ps, col.name)
            # datetime 转 ISO
            for k, v in list(row.items()):
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
            post_series_data.append(row)

    manifest = {
        "version": BACKUP_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "exported_by": current_user.username,
        "counts": {
            "posts": len(posts_data),
            "categories": len(categories_data),
            "tags": len(tags_data),
            "comments": len(comments_data),
            "users": len(users_data),
            "media": len(media_data),
            "friend_links": len(friend_links_data),
            "navigations": len(navigations_data),
            "pages": len(pages_data),
            "announcements": len(announcements_data),
            "hero_slides": len(hero_slides_data),
            "site_config": len(site_config_data),
            "post_series": len(post_series_data),
        },
    }

    # === 打包 ZIP ===
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("posts.json", json.dumps(posts_data, ensure_ascii=False, indent=2))
        zf.writestr("categories.json", json.dumps(categories_data, ensure_ascii=False, indent=2))
        zf.writestr("tags.json", json.dumps(tags_data, ensure_ascii=False, indent=2))
        zf.writestr("comments.json", json.dumps(comments_data, ensure_ascii=False, indent=2))
        zf.writestr("users.json", json.dumps(users_data, ensure_ascii=False, indent=2))
        zf.writestr("media.json", json.dumps(media_data, ensure_ascii=False, indent=2))
        zf.writestr(
            "friend_links.json", json.dumps(friend_links_data, ensure_ascii=False, indent=2)
        )
        zf.writestr("navigations.json", json.dumps(navigations_data, ensure_ascii=False, indent=2))
        zf.writestr("pages.json", json.dumps(pages_data, ensure_ascii=False, indent=2))
        zf.writestr(
            "announcements.json", json.dumps(announcements_data, ensure_ascii=False, indent=2)
        )
        zf.writestr("hero_slides.json", json.dumps(hero_slides_data, ensure_ascii=False, indent=2))
        zf.writestr("site_config.json", json.dumps(site_config_data, ensure_ascii=False, indent=2))
        if PostSeries is not None:
            zf.writestr(
                "post_series.json", json.dumps(post_series_data, ensure_ascii=False, indent=2)
            )

    zip_buffer.seek(0)

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action="backup",
        resource_type="site",
        detail=json.dumps({"counts": manifest["counts"]}),
    )
    db.add(log)
    await db.flush()

    filename = f"rosetta_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/backup/restore",
    summary="全站恢复",
    description="上传 ZIP 备份文件恢复整站数据。策略：skip_existing（默认）或 overwrite。",
)
async def backup_restore(
    db: DB,
    current_user: CurrentStaff,
    file: UploadFile = File(...),
    strategy: str = "skip_existing",
):
    """全站恢复：按依赖顺序导入 ZIP 中的各 JSON 文件"""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传 ZIP 备份文件",
        )

    overwrite = strategy == "overwrite"

    try:
        content = await file.read()
        zip_buffer = io.BytesIO(content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            names = set(zf.namelist())

            def _read(name: str, default):
                if name in names:
                    return json.loads(zf.read(name).decode("utf-8"))
                return default

            manifest = _read("manifest.json", {})
            site_config_data = _read("site_config.json", [])
            users_data = _read("users.json", [])
            categories_data = _read("categories.json", [])
            tags_data = _read("tags.json", [])
            navigations_data = _read("navigations.json", [])
            friend_links_data = _read("friend_links.json", [])
            pages_data = _read("pages.json", [])
            post_series_data = _read("post_series.json", [])
            posts_data = _read("posts.json", [])
            comments_data = _read("comments.json", [])
            announcements_data = _read("announcements.json", [])
            hero_slides_data = _read("hero_slides.json", [])
            media_data = _read("media.json", [])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解析备份文件失败: {str(e)}",
        )

    created_count = 0
    skipped_count = 0
    error_count = 0
    errors: list[str] = []

    def _created():
        nonlocal created_count
        created_count += 1

    def _skipped():
        nonlocal skipped_count
        skipped_count += 1

    def _err(msg: str):
        nonlocal error_count
        error_count += 1
        errors.append(msg)

    # === 1. site_config ===
    for item in site_config_data:
        try:
            existing = await db.execute(select(SiteConfig).where(SiteConfig.key == item["key"]))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                if overwrite:
                    existing_obj.value = item.get("value", existing_obj.value)
                    existing_obj.description = item.get("description", existing_obj.description)
                    _created()
                else:
                    _skipped()
                continue
            db.add(
                SiteConfig(
                    key=item["key"],
                    value=item.get("value", ""),
                    description=item.get("description"),
                )
            )
            _created()
        except Exception as e:
            _err(f"站点配置 {item.get('key', 'unknown')} 导入失败: {e}")

    # === 2. users（脱敏恢复，无密码；新用户使用占位密码与邮箱） ===
    username_to_user: dict[str, User] = {}
    for item in users_data:
        try:
            username = item.get("username")
            if not username:
                _err("用户缺少 username 字段，已跳过")
                continue
            existing = await db.execute(select(User).where(User.username == username))
            existing_user = existing.scalar_one_or_none()
            if existing_user:
                username_to_user[username] = existing_user
                if overwrite:
                    existing_user.nickname = item.get("nickname", existing_user.nickname)
                    existing_user.avatar = item.get("avatar", existing_user.avatar)
                    existing_user.bio = item.get("bio", existing_user.bio)
                    _created()
                else:
                    _skipped()
                continue
            # 新用户：生成占位邮箱与不可登录的密码哈希
            placeholder_email = f"{username}@restored.local"
            # 避免邮箱冲突
            email_check = await db.execute(select(User).where(User.email == placeholder_email))
            if email_check.scalar_one_or_none():
                placeholder_email = f"{username}_{item.get('id', '')}@restored.local"
            new_user = User(
                username=username,
                email=placeholder_email,
                password_hash="!restored-no-login",
                nickname=item.get("nickname"),
                avatar=item.get("avatar"),
                bio=item.get("bio"),
                created_at=_parse_dt(item.get("created_at")),
            )
            db.add(new_user)
            await db.flush()
            username_to_user[username] = new_user
            _created()
        except Exception as e:
            _err(f"用户 {item.get('username', 'unknown')} 导入失败: {e}")

    # === 3. categories ===
    slug_to_category: dict[str, Category] = {}
    for item in categories_data:
        try:
            slug = item.get("slug")
            existing = await db.execute(select(Category).where(Category.slug == slug))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                slug_to_category[slug] = existing_obj
                if overwrite:
                    existing_obj.name = item.get("name", existing_obj.name)
                    existing_obj.description = item.get("description", existing_obj.description)
                    existing_obj.icon = item.get("icon", existing_obj.icon)
                    existing_obj.color = item.get("color", existing_obj.color)
                    existing_obj.cover_image = item.get("cover_image", existing_obj.cover_image)
                    _created()
                else:
                    _skipped()
                continue
            cat = Category(
                name=item.get("name", {}),
                slug=slug,
                description=item.get("description"),
                icon=item.get("icon"),
                color=item.get("color", "primary"),
                cover_image=item.get("cover_image"),
            )
            db.add(cat)
            await db.flush()
            slug_to_category[slug] = cat
            _created()
        except Exception as e:
            _err(f"分类 {item.get('slug', 'unknown')} 导入失败: {e}")

    # === 4. tags ===
    slug_to_tag: dict[str, Tag] = {}
    for item in tags_data:
        try:
            slug = item.get("slug")
            existing = await db.execute(select(Tag).where(Tag.slug == slug))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                slug_to_tag[slug] = existing_obj
                if overwrite:
                    existing_obj.name = item.get("name", existing_obj.name)
                    existing_obj.color = item.get("color", existing_obj.color)
                    existing_obj.icon = item.get("icon", existing_obj.icon)
                    existing_obj.is_active = item.get("is_active", existing_obj.is_active)
                    _created()
                else:
                    _skipped()
                continue
            tag = Tag(
                name=item.get("name", {}),
                slug=slug,
                color=item.get("color", "#64748B"),
                icon=item.get("icon"),
                is_active=item.get("is_active", True),
            )
            db.add(tag)
            await db.flush()
            slug_to_tag[slug] = tag
            _created()
        except Exception as e:
            _err(f"标签 {item.get('slug', 'unknown')} 导入失败: {e}")

    # === 5. navigations ===
    for item in navigations_data:
        try:
            url = item.get("url")
            title = item.get("title", {})
            existing = await db.execute(
                select(Navigation).where(Navigation.url == url, Navigation.title == title)
            )
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                if overwrite:
                    existing_obj.location = item.get("location", existing_obj.location)
                    existing_obj.order = item.get("order", existing_obj.order)
                    existing_obj.is_active = item.get("is_active", existing_obj.is_active)
                    existing_obj.target_blank = item.get("target_blank", existing_obj.target_blank)
                    _created()
                else:
                    _skipped()
                continue
            db.add(
                Navigation(
                    title=title,
                    url=url,
                    location=item.get("location", "header"),
                    order=item.get("order", 0),
                    is_active=item.get("is_active", True),
                    target_blank=item.get("target_blank", False),
                )
            )
            _created()
        except Exception as e:
            _err(f"导航 {item.get('url', 'unknown')} 导入失败: {e}")

    # === 6. friend_links ===
    for item in friend_links_data:
        try:
            url = item.get("url")
            existing = await db.execute(select(FriendLink).where(FriendLink.url == url))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                if overwrite:
                    existing_obj.name = item.get("name", existing_obj.name)
                    existing_obj.description = item.get("description", existing_obj.description)
                    existing_obj.logo = item.get("logo", existing_obj.logo)
                    existing_obj.order = item.get("order", existing_obj.order)
                    existing_obj.is_active = item.get("is_active", existing_obj.is_active)
                    existing_obj.target_blank = item.get("target_blank", existing_obj.target_blank)
                    _created()
                else:
                    _skipped()
                continue
            db.add(
                FriendLink(
                    name=item.get("name", {}),
                    url=url,
                    description=item.get("description"),
                    logo=item.get("logo"),
                    order=item.get("order", 0),
                    is_active=item.get("is_active", True),
                    target_blank=item.get("target_blank", False),
                )
            )
            _created()
        except Exception as e:
            _err(f"友链 {item.get('url', 'unknown')} 导入失败: {e}")

    # === 7. pages ===
    slug_to_page: dict[str, Page] = {}
    for item in pages_data:
        try:
            slug = item.get("slug")
            existing = await db.execute(select(Page).where(Page.slug == slug))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                slug_to_page[slug] = existing_obj
                if overwrite:
                    existing_obj.title = item.get("title", existing_obj.title)
                    existing_obj.content = item.get("content", existing_obj.content)
                    existing_obj.status = item.get("status", existing_obj.status)
                    _created()
                else:
                    _skipped()
                continue
            page = Page(
                title=item.get("title", {}),
                slug=slug,
                content=item.get("content", {}),
                status=item.get("status", "published"),
            )
            db.add(page)
            await db.flush()
            slug_to_page[slug] = page
            _created()
        except Exception as e:
            _err(f"页面 {item.get('slug', 'unknown')} 导入失败: {e}")

    # === 8. post_series（仅当模型存在） ===
    # 旧 series id -> 新 series 对象，用于后续 Post.series_id 映射
    series_id_map: dict[int, PostSeries] = {}
    series_slug_map: dict[str, PostSeries] = {}
    if PostSeries is not None and post_series_data:
        for item in post_series_data:
            try:
                old_id = item.get("id")
                slug = item.get("slug")
                # 先按 slug 查找是否已存在（避免重复导入）
                existing_series = None
                if slug:
                    existed = await db.execute(select(PostSeries).where(PostSeries.slug == slug))
                    existing_series = existed.scalar_one_or_none()

                if existing_series:
                    if overwrite:
                        # 更新现有系列
                        for k, v in item.items():
                            if k in ("id", "created_at"):
                                continue
                            if hasattr(existing_series, k) and v is not None:
                                setattr(
                                    existing_series, k, _parse_dt(v) if k in ("updated_at",) else v
                                )
                        await db.flush()
                        _created()
                    else:
                        _skipped()
                    if old_id is not None:
                        series_id_map[old_id] = existing_series
                    if slug:
                        series_slug_map[slug] = existing_series
                else:
                    # 创建新系列（排除 id 和 created_at，让数据库自增）
                    create_data = {k: v for k, v in item.items() if k not in ("id", "created_at")}
                    # 处理 datetime 字段
                    if "updated_at" in create_data:
                        create_data["updated_at"] = _parse_dt(create_data["updated_at"])
                    new_series = PostSeries(**create_data)
                    db.add(new_series)
                    await db.flush()
                    if old_id is not None:
                        series_id_map[old_id] = new_series
                    if slug:
                        series_slug_map[slug] = new_series
                    _created()
            except Exception as e:
                _err(f"文章系列 id={item.get('id')} 导入失败: {e}")

    # === 9. posts ===
    slug_to_post: dict[str, Post] = {}
    for item in posts_data:
        try:
            slug = item.get("slug")
            existing = await db.execute(select(Post).where(Post.slug == slug))
            existing_post = existing.scalar_one_or_none()
            if existing_post:
                slug_to_post[slug] = existing_post
                if overwrite:
                    existing_post.title = item.get("title", existing_post.title)
                    existing_post.subtitle = item.get("subtitle", existing_post.subtitle)
                    existing_post.source = item.get("source", existing_post.source)
                    existing_post.source_url = item.get("source_url", existing_post.source_url)
                    existing_post.audio = item.get("audio", existing_post.audio)
                    existing_post.video = item.get("video", existing_post.video)
                    existing_post.video_url = item.get("video_url", existing_post.video_url)
                    existing_post.content = item.get("content", existing_post.content)
                    existing_post.excerpt = item.get("excerpt", existing_post.excerpt)
                    existing_post.cover_image = item.get("cover_image", existing_post.cover_image)
                    existing_post.status = item.get("status", existing_post.status)
                    existing_post.visibility = item.get("visibility", existing_post.visibility)
                    existing_post.password = item.get("password", existing_post.password)
                    existing_post.views = item.get("views", existing_post.views)
                    existing_post.is_pinned = item.get("is_pinned", existing_post.is_pinned)
                    existing_post.allow_comments = item.get(
                        "allow_comments", existing_post.allow_comments
                    )
                    existing_post.meta_title = item.get("meta_title", existing_post.meta_title)
                    existing_post.meta_description = item.get(
                        "meta_description", existing_post.meta_description
                    )
                    existing_post.meta_keywords = item.get(
                        "meta_keywords", existing_post.meta_keywords
                    )
                    existing_post.encrypted_content = item.get(
                        "encrypted_content", existing_post.encrypted_content
                    )
                    existing_post.encryption_enabled = item.get(
                        "encryption_enabled", existing_post.encryption_enabled
                    )
                    existing_post.encryption_hint = item.get(
                        "encryption_hint", existing_post.encryption_hint
                    )
                    existing_post.scheduled_at = _parse_dt(item.get("scheduled_at"))
                    existing_post.published_at = _parse_dt(item.get("published_at"))
                    # 更新分类
                    cat_slug = item.get("category_slug")
                    if cat_slug and cat_slug in slug_to_category:
                        existing_post.category_id = slug_to_category[cat_slug].id
                    # 更新标签
                    existing_post.tags = [
                        slug_to_tag[t] for t in item.get("tag_slugs", []) if t in slug_to_tag
                    ]
                    _created()
                else:
                    _skipped()
                continue

            # 解析作者
            author_username = item.get("author_username")
            author = None
            if author_username:
                author = username_to_user.get(author_username)
            if author is None:
                author = current_user  # 回退到当前管理员

            cat_slug = item.get("category_slug")
            category = slug_to_category.get(cat_slug) if cat_slug else None

            # 解析旧 series_id 到新 series
            new_series_id = None
            old_series_id = item.get("series_id")
            if old_series_id is not None and old_series_id in series_id_map:
                new_series_id = series_id_map[old_series_id].id

            post = Post(
                title=item.get("title", {}),
                subtitle=item.get("subtitle"),
                slug=slug,
                source=item.get("source", "原创"),
                source_url=item.get("source_url"),
                audio=item.get("audio"),
                video=item.get("video"),
                video_url=item.get("video_url"),
                content=item.get("content", {}),
                excerpt=item.get("excerpt"),
                cover_image=item.get("cover_image"),
                author_id=author.id,
                category_id=category.id if category else None,
                status=item.get("status", "draft"),
                visibility=item.get("visibility", "public"),
                password=item.get("password"),
                views=item.get("views", 0),
                is_pinned=item.get("is_pinned", False),
                allow_comments=item.get("allow_comments", True),
                meta_title=item.get("meta_title"),
                meta_description=item.get("meta_description"),
                meta_keywords=item.get("meta_keywords"),
                series_id=new_series_id,
                series_order=item.get("series_order", 0),
                encrypted_content=item.get("encrypted_content"),
                encryption_enabled=item.get("encryption_enabled", False),
                encryption_hint=item.get("encryption_hint"),
                scheduled_at=_parse_dt(item.get("scheduled_at")),
                published_at=_parse_dt(item.get("published_at")),
            )
            db.add(post)
            await db.flush()

            # 关联标签
            for t_slug in item.get("tag_slugs", []):
                t = slug_to_tag.get(t_slug)
                if t:
                    post.tags.append(t)

            slug_to_post[slug] = post
            _created()
        except Exception as e:
            _err(f"文章 {item.get('slug', 'unknown')} 导入失败: {e}")

    # === 10. comments（含嵌套回复；保留 parent_id 旧→新映射） ===
    old_id_to_comment: dict[int, Comment] = {}
    # 先创建无 parent 的，再创建有 parent 的，简化嵌套处理
    pending_with_parent = [c for c in comments_data if c.get("parent_id")]
    no_parent = [c for c in comments_data if not c.get("parent_id")]

    async def _import_comment(item):
        post_slug = item.get("post_slug")
        post = slug_to_post.get(post_slug) if post_slug else None
        if post is None:
            # 文章未导入，跳过
            _err(f"评论 id={item.get('id')} 找不到文章 {post_slug}")
            return
        username = item.get("user_username")
        user = username_to_user.get(username) if username else None
        if user is None:
            user = current_user
        parent_old = item.get("parent_id")
        parent = old_id_to_comment.get(parent_old) if parent_old else None
        comment = Comment(
            post_id=post.id,
            user_id=user.id,
            parent_id=parent.id if parent else None,
            content=item.get("content", ""),
            active=item.get("active", True),
            created_at=_parse_dt(item.get("created_at")),
        )
        db.add(comment)
        await db.flush()
        if item.get("id") is not None:
            old_id_to_comment[item["id"]] = comment
        _created()

    for item in no_parent:
        try:
            await _import_comment(item)
        except Exception as e:
            _err(f"评论 id={item.get('id')} 导入失败: {e}")
    # 多轮处理嵌套回复，直到无新增
    remaining = pending_with_parent
    while remaining:
        next_round: list = []
        progressed = False
        for item in remaining:
            parent_old = item.get("parent_id")
            if parent_old in old_id_to_comment:
                try:
                    await _import_comment(item)
                    progressed = True
                except Exception as e:
                    _err(f"评论 id={item.get('id')} 导入失败: {e}")
            else:
                next_round.append(item)
        if not progressed:
            # 父评论缺失，无法导入
            for item in next_round:
                _err(f"评论 id={item.get('id')} 父评论 {item.get('parent_id')} 缺失，已跳过")
            break
        remaining = next_round

    # === 11. announcements ===
    for item in announcements_data:
        try:
            title = item.get("title")
            existing = await db.execute(select(Announcement).where(Announcement.title == title))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                if overwrite:
                    existing_obj.content = item.get("content", existing_obj.content)
                    existing_obj.type = item.get("type", existing_obj.type)
                    existing_obj.is_active = item.get("is_active", existing_obj.is_active)
                    existing_obj.is_dismissible = item.get(
                        "is_dismissible", existing_obj.is_dismissible
                    )
                    existing_obj.start_time = _parse_dt(item.get("start_time"))
                    existing_obj.end_time = _parse_dt(item.get("end_time"))
                    existing_obj.sort_order = item.get("sort_order", existing_obj.sort_order)
                    _created()
                else:
                    _skipped()
                continue
            db.add(
                Announcement(
                    title=title,
                    content=item.get("content", ""),
                    type=item.get("type", "info"),
                    is_active=item.get("is_active", True),
                    is_dismissible=item.get("is_dismissible", True),
                    start_time=_parse_dt(item.get("start_time")),
                    end_time=_parse_dt(item.get("end_time")),
                    sort_order=item.get("sort_order", 0),
                )
            )
            _created()
        except Exception as e:
            _err(f"公告 {item.get('title', 'unknown')} 导入失败: {e}")

    # === 12. hero_slides ===
    for item in hero_slides_data:
        try:
            media_url = item.get("media_url")
            existing = await db.execute(select(HeroSlide).where(HeroSlide.media_url == media_url))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                if overwrite:
                    existing_obj.title = item.get("title", existing_obj.title)
                    existing_obj.subtitle = item.get("subtitle", existing_obj.subtitle)
                    existing_obj.media_type = item.get("media_type", existing_obj.media_type)
                    existing_obj.poster_url = item.get("poster_url", existing_obj.poster_url)
                    existing_obj.overlay_opacity = item.get(
                        "overlay_opacity", existing_obj.overlay_opacity
                    )
                    existing_obj.overlay_color = item.get(
                        "overlay_color", existing_obj.overlay_color
                    )
                    existing_obj.cta_text = item.get("cta_text", existing_obj.cta_text)
                    existing_obj.cta_url = item.get("cta_url", existing_obj.cta_url)
                    existing_obj.cta_secondary_text = item.get(
                        "cta_secondary_text", existing_obj.cta_secondary_text
                    )
                    existing_obj.cta_secondary_url = item.get(
                        "cta_secondary_url", existing_obj.cta_secondary_url
                    )
                    existing_obj.text_align = item.get("text_align", existing_obj.text_align)
                    existing_obj.text_color = item.get("text_color", existing_obj.text_color)
                    existing_obj.is_active = item.get("is_active", existing_obj.is_active)
                    existing_obj.sort_order = item.get("sort_order", existing_obj.sort_order)
                    existing_obj.start_time = _parse_dt(item.get("start_time"))
                    existing_obj.end_time = _parse_dt(item.get("end_time"))
                    _created()
                else:
                    _skipped()
                continue
            db.add(
                HeroSlide(
                    title=item.get("title"),
                    subtitle=item.get("subtitle"),
                    media_type=item.get("media_type", "image"),
                    media_url=media_url,
                    poster_url=item.get("poster_url"),
                    overlay_opacity=item.get("overlay_opacity", 40),
                    overlay_color=item.get("overlay_color", "#000000"),
                    cta_text=item.get("cta_text"),
                    cta_url=item.get("cta_url"),
                    cta_secondary_text=item.get("cta_secondary_text"),
                    cta_secondary_url=item.get("cta_secondary_url"),
                    text_align=item.get("text_align", "center"),
                    text_color=item.get("text_color", "light"),
                    is_active=item.get("is_active", True),
                    sort_order=item.get("sort_order", 0),
                    start_time=_parse_dt(item.get("start_time")),
                    end_time=_parse_dt(item.get("end_time")),
                )
            )
            _created()
        except Exception as e:
            _err(f"Hero 幻灯片 {item.get('media_url', 'unknown')} 导入失败: {e}")

    # === 13. media ===
    for item in media_data:
        try:
            file_path = item.get("file")
            existing = await db.execute(select(Media).where(Media.file == file_path))
            existing_obj = existing.scalar_one_or_none()
            if existing_obj:
                if overwrite:
                    existing_obj.filename = item.get("filename", existing_obj.filename)
                    existing_obj.file_type = item.get("file_type", existing_obj.file_type)
                    existing_obj.file_size = item.get("file_size", existing_obj.file_size)
                    existing_obj.title = item.get("title", existing_obj.title)
                    existing_obj.alt_text = item.get("alt_text", existing_obj.alt_text)
                    existing_obj.description = item.get("description", existing_obj.description)
                    _created()
                else:
                    _skipped()
                continue
            db.add(
                Media(
                    file=file_path,
                    filename=item.get("filename"),
                    file_type=item.get("file_type", "other"),
                    file_size=item.get("file_size", 0),
                    title=item.get("title"),
                    alt_text=item.get("alt_text"),
                    description=item.get("description"),
                )
            )
            _created()
        except Exception as e:
            _err(f"媒体 {item.get('file', 'unknown')} 导入失败: {e}")

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action="restore",
        resource_type="site",
        detail=json.dumps(
            {
                "strategy": strategy,
                "created_count": created_count,
                "skipped_count": skipped_count,
                "error_count": error_count,
                "manifest": manifest,
            }
        ),
    )
    db.add(log)
    await db.flush()

    return ImportResult(
        success=True,
        message=(
            f"恢复完成：创建/更新 {created_count} 项，跳过 {skipped_count} 项，失败 {error_count} 项"
        ),
        created_count=created_count,
        skipped_count=skipped_count,
        error_count=error_count,
        errors=errors[:20],
    )
