"""
导入导出 API

支持文章、分类、标签等数据的导入导出。
"""

import asyncio
import io
import json
import zipfile
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import invalidate_cache
from backend.models.blog import Category, Post, Tag
from backend.models.log import OperationLog
from backend.schemas import raw_content_response
from backend.utils.compat import UTC, parse_utc_date, timedelta

# 注意：main.py 以 prefix="/api/admin" 挂载本路由（与 admin_tools.py 一致，
# router 自身不再带 /admin 前缀，否则会拼出 /api/admin/admin/* 导致前端 404）。
router = APIRouter(tags=["导入导出"])

# 备份恢复的体积闸门（详见 backup_restore 内的三层校验）：
# 备份 ZIP 体积小但解压后可膨胀上千倍，必须同时限制压缩包本体、单条目与解压总量。
MAX_BACKUP_BYTES = 20 * 1024 * 1024  # 压缩包本体上限
MAX_BACKUP_ENTRY_BYTES = 100 * 1024 * 1024  # 单个 JSON 条目解压后上限
MAX_BACKUP_UNCOMPRESSED_BYTES = 300 * 1024 * 1024  # 全部条目解压后总量上限


async def _invalidate_content_caches(*extra_prefixes: str) -> None:
    """导入 / 备份恢复之后统一失效内容缓存。

    这两条路径会新增或整篇覆盖文章、分类、标签，却走不到 blog.py 写侧的失效逻辑；
    不清的话前台最长 600s 仍展示导入前的内容。文章详情缓存键是
    ``post:{slug}:{language}``，不在 ``posts`` 前缀下，所以两个前缀都要清。
    """
    for prefix in ("posts", "post:", "categories", "tags", *extra_prefixes):
        await invalidate_cache(prefix)


# ==================== 导出 API ====================


def _build_zip(entries: list[tuple[str, object]]) -> bytes:
    """把 (文件名, 内容) 列表打成 ZIP 字节。

    内容可以是已序列化好的字符串，也可以是待 ``json.dumps`` 的对象。
    JSON 序列化 + ZIP_DEFLATED 压缩都是 CPU 密集操作，整站备份时会占用
    事件循环几十秒，因此本函数**只允许**通过 ``asyncio.to_thread`` 调用，
    且入参必须是与 ORM 会话无关的纯 Python 结构。
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries:
            text = (
                payload
                if isinstance(payload, str)
                else json.dumps(payload, ensure_ascii=False, indent=2)
            )
            zf.writestr(name, text)
    return buffer.getvalue()


def _extract_import_payloads(content: bytes) -> tuple[list, list, list]:
    """解析 Rosetta 导出 ZIP，返回 ``(posts, categories, tags)``。

    解压 + ``json.loads`` 属于 CPU/IO 密集操作，调用方一律走
    ``asyncio.to_thread``。上传内容不可信，因此这里把结构校验做完：
    后面取 ``row["slug"]`` 的地方才不会把一份畸形 ZIP 变成 500。
    """
    with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
        names = set(zf.namelist())

        def read_json(name: str) -> list:
            if name not in names:
                return []
            payload = json.loads(zf.read(name).decode("utf-8"))
            if not isinstance(payload, list):
                raise ValueError(f"{name} 顶层结构必须是数组")
            for index, row in enumerate(payload):
                if not isinstance(row, dict):
                    raise ValueError(f"{name} 第 {index + 1} 条不是对象")
            return payload

        posts_data = read_json("posts.json")
        categories_data = read_json("categories.json")
        tags_data = read_json("tags.json")

    # 分类/标签后续直接取 ["slug"]，缺键必须在这里就拒绝
    for name, rows in (("categories.json", categories_data), ("tags.json", tags_data)):
        for index, row in enumerate(rows):
            if not str(row.get("slug") or "").strip():
                raise ValueError(f"{name} 第 {index + 1} 条缺少 slug")

    # 文章的 category 允许缺省，但给了就必须是对象（后续要 .get("slug")）
    for index, row in enumerate(posts_data):
        category = row.get("category")
        if category is not None and not isinstance(category, dict):
            raise ValueError(f"posts.json 第 {index + 1} 条的 category 必须是对象")

    return posts_data, categories_data, tags_data


@router.get(
    "/export/posts",
    summary="导出文章",
    description=(
        "导出所有文章为 JSON 格式（Rosetta 原生 JSON ZIP）。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "format 仅支持 json，未实现格式明确 400。"
        "默认只导已发布文章，include_drafts=true 时含草稿（scope=published 又把范围收窄回已发布）；"
        "from/to 按创建时间过滤（含边界，只给日期时上界补足到当天 23:59:59）；"
        "include_content=false 可只导元数据不带正文。"
        "包内是 posts.json / categories.json / tags.json 三个 UTF-8 JSON 文件。"
    ),
    responses=raw_content_response(
        "application/zip", "导出结果 zip 压缩包（二进制流下载）。", binary=True
    ),
    response_class=Response,
)
async def export_posts(
    db: DB,
    current_user: CurrentStaff,
    include_drafts: bool = False,
    include_content: bool = True,
    scope: str | None = Query(None, description="范围过滤：published=仅已发布，其余视为 all"),
    from_date: str | None = Query(None, alias="from", description="开始日期 ISO（含边界）"),
    to_date: str | None = Query(None, alias="to", description="结束日期 ISO（含边界）"),
    format: str = Query(
        "json",
        description="导出格式：当前仅实现 json；wordpress/halo/typecho 未实现，传入会得到 400 而非静默降级。",
    ),
) -> StreamingResponse:
    """
    导出文章数据

    返回一个 ZIP 文件，包含：
    - posts.json: 文章列表
    - categories.json: 分类列表
    - tags.json: 标签列表
    """
    # 诚实契约：导出器今天只产出 JSON ZIP，未声明的 format 会被静默丢弃，
    # 用户选了未实现格式却拿到 JSON 包属于"假装成功"，这里显式 400。
    if format != "json":
        hint = "；Markdown 请使用 /admin/export/markdown 端点" if format == "markdown" else ""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"暂不支持的导出格式：{format}{hint}。当前仅支持 json。",
        )

    # 查询文章
    query = select(Post).options(selectinload(Post.category), selectinload(Post.tags))
    if not include_drafts or scope == "published":
        query = query.where(Post.status == "published")

    from_dt = parse_utc_date(from_date)
    to_dt = parse_utc_date(to_date)
    if from_dt:
        query = query.where(Post.created_at >= from_dt)
    if to_dt:
        if to_dt.hour == 0 and to_dt.minute == 0 and to_dt.second == 0:
            to_dt = to_dt + timedelta(days=1) - timedelta(microseconds=1)
        query = query.where(Post.created_at <= to_dt)

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
            "has_password": bool(post.password),
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

    # 创建 ZIP 文件（序列化 + 压缩放线程池，避免阻塞事件循环）
    zip_entries: list[tuple[str, object]] = [
        ("posts.json", posts_data),
        ("categories.json", categories_data),
        ("tags.json", tags_data),
        (
            "export_info.json",
            {
                "exported_at": datetime.now(UTC).isoformat(),
                "exported_by": current_user.username,
                "posts_count": len(posts_data),
                "include_drafts": include_drafts,
                "include_content": include_content,
            },
        ),
    ]
    zip_buffer = io.BytesIO(await asyncio.to_thread(_build_zip, zip_entries))
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
    description=(
        "将文章导出为 Markdown 文件。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "只导已发布文章（无草稿开关），每篇一个 ``<slug>.md``，正文前拼 YAML frontmatter"
        "（title / slug / date / category / tags / cover，空字段整行省略），"
        "并附一个 README.md 记录导出时间与篇数。"
        "lang 选择 frontmatter 与正文取用的语言变体，取不到时回退 zh。"
        "from/to 按创建时间过滤（含边界）；不含图片资产，压缩包是纯文本。"
    ),
    responses=raw_content_response(
        "application/zip", "Markdown 导出包（含图片资产的 zip）。", binary=True
    ),
    response_class=Response,
)
async def export_markdown(
    db: DB,
    current_user: CurrentStaff,
    lang: str = "zh",
    from_date: str | None = Query(None, alias="from", description="开始日期 ISO（含边界）"),
    to_date: str | None = Query(None, alias="to", description="结束日期 ISO（含边界）"),
) -> StreamingResponse:
    """
    导出文章为 Markdown 格式

    每篇文章一个 .md 文件，包含 frontmatter。
    """
    # 查询已发布文章
    query = (
        select(Post)
        .where(Post.status == "published")
        .options(selectinload(Post.category), selectinload(Post.tags))
    )
    from_dt = parse_utc_date(from_date)
    to_dt = parse_utc_date(to_date)
    if from_dt:
        query = query.where(Post.created_at >= from_dt)
    if to_dt:
        if to_dt.hour == 0 and to_dt.minute == 0 and to_dt.second == 0:
            to_dt = to_dt + timedelta(days=1) - timedelta(microseconds=1)
        query = query.where(Post.created_at <= to_dt)
    query = query.order_by(Post.created_at.desc())

    result = await db.execute(query)
    posts = result.unique().scalars().all()

    # 创建 ZIP 文件：先在事件循环里拼好 Markdown 文本，再交线程池压缩
    md_entries: list[tuple[str, object]] = []
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

        md_entries.append((f"{post.slug}.md", frontmatter + content))

    # 添加导出信息
    md_entries.append(
        (
            "README.md",
            f"# Rosetta Blog Export\n\nExported at: {datetime.now(UTC).isoformat()}\nTotal posts: {len(posts)}\n",
        )
    )

    zip_buffer = io.BytesIO(await asyncio.to_thread(_build_zip, md_entries))
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
    """导入结果

    文章导入、Markdown 导入与全站恢复三个端点共用该结构：
    成功与失败都以 200 返回，由 ``success`` 区分，故 ``errors`` 只承载逐条失败明细。
    """

    success: bool = Field(..., description="本次导入整体是否成功；false 时 message 说明失败原因")
    message: str = Field(..., description="人类可读汇总文案（含创建/跳过/失败计数）")
    created_count: int = Field(
        0, description="新建或被覆盖更新的条目数；单文件 Markdown 导入成功时为 1"
    )
    skipped_count: int = Field(
        0, description="按策略跳过的条目数（同 slug 已存在、恢复策略为 skip_existing 等）"
    )
    error_count: int = Field(0, description="逐条解析或写库失败的条目数；计数是全量的")
    errors: list[str] = Field(
        default_factory=list,
        description="失败明细（每条一个中文短句）：文章导入最多回传前 10 条，全站恢复最多回传前 20 条",
    )


class BackupInfoResponse(BaseModel):
    """全站备份前的数据统计预览。"""

    counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "各内容模型的行数。键固定为 posts / categories / tags / comments / users / media / "
            "friend_links / navigations / pages / announcements / hero_slides / site_config，"
            "文章系列模型可用时额外多一个 post_series 键"
        ),
    )
    total: int = Field(0, description="counts 各值之和，即整站记录总条数")
    queried_at: str = Field(..., description="统计时刻的 UTC ISO 8601 时间字符串")
    queried_by: str = Field(..., description="发起本次统计的登录用户名")


def _overwrite_post_from_import(post: Post, post_data: dict, category: Category | None) -> None:
    """用导入载荷覆盖既有文章字段。

    有意保留原作者与密码：备份中的 password hash 不可信，作者也不应因
    导入者不同而被悄悄改写（与 /backup/restore 的 overwrite 策略一致）。
    """
    post.title = post_data.get("title", post.title)
    post.subtitle = post_data.get("subtitle", post.subtitle)
    post.content = post_data.get("content", post.content)
    post.excerpt = post_data.get("excerpt", post.excerpt)
    post.cover_image = post_data.get("cover_image", post.cover_image)
    post.source = post_data.get("source", post.source)
    post.source_url = post_data.get("source_url", post.source_url)
    post.status = post_data.get("status", post.status)
    post.views = post_data.get("views", post.views)
    post.is_pinned = post_data.get("is_pinned", post.is_pinned)
    post.allow_comments = post_data.get("allow_comments", post.allow_comments)
    if category is not None:
        post.category_id = category.id


@router.post(
    "/import/posts",
    summary="导入文章",
    description=(
        "从 Rosetta 导出的 JSON ZIP（posts/categories/tags.json）导入文章。"
        "需 staff 及以上权限（未登录 401，非管理员 403）。"
        "skip_existing=true 跳过同名 slug；false 覆盖更新既有文章，但覆盖时有意保留原作者与密码 hash。"
        "format 仅支持 json，其它取值 400。压缩包解析不出 posts.json 时 400。"
        "成功与失败都以 200 返回，由 success 与 errors 判定逐条结果；"
        "errors 只回传前 10 条，error_count 才是全量失败数。导入后会写一条后台操作日志并失效内容缓存。"
    ),
    responses={200: {"model": ImportResult}},
)
async def import_posts(
    db: DB,
    current_user: CurrentStaff,
    file: UploadFile = File(...),
    skip_existing: bool = True,
    format: str = Query(
        "json",
        description="导入格式：当前仅实现 json（Rosetta ZIP）；wordpress/halo/typecho 未实现，传入会得到 400。",
    ),
):
    """
    导入文章数据

    接受 ZIP 文件，包含 posts.json、categories.json、tags.json
    """
    # 与导出侧同理：importer 只认 Rosetta JSON ZIP，未实现格式必须 400，
    # 不能让前端 format 下拉的选择不被消费（静默按 json 解析失败更难排查）。
    if format != "json":
        hint = "；Markdown 请使用 /admin/import/markdown 端点" if format == "markdown" else ""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"暂不支持的导入格式：{format}{hint}。当前仅支持 json。",
        )

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传 ZIP 文件",
        )

    try:
        content = await file.read()
        posts_data, categories_data, tags_data = await asyncio.to_thread(
            _extract_import_payloads, content
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解析文件失败: {str(e)}",
        )

    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []

    # 批量预查已存在的分类 / 标签 slug，避免循环内逐条 SELECT
    existing_cat_slugs: set[str] = set()
    if categories_data:
        result = await db.execute(
            select(Category.slug).where(Category.slug.in_([c["slug"] for c in categories_data]))
        )
        existing_cat_slugs = {row[0] for row in result.fetchall()}

    existing_tag_slugs: set[str] = set()
    if tags_data:
        result = await db.execute(
            select(Tag.slug).where(Tag.slug.in_([t["slug"] for t in tags_data]))
        )
        existing_tag_slugs = {row[0] for row in result.fetchall()}

    # 导入分类
    category_map = {}  # old_id -> new_category
    for cat_data in categories_data:
        try:
            if cat_data["slug"] in existing_cat_slugs:
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
            if tag_data["slug"] in existing_tag_slugs:
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

    # 文章导入前：批量预查已存在的文章（含整对象，覆盖模式需要）、分类、标签，消除循环内 N+1
    # tags/category 必须一并 eager load：覆盖分支要给这两个集合赋值，
    # 未加载的属性在 async 会话里触发懒加载 = MissingGreenlet。
    post_slugs = [p["slug"] for p in posts_data if p.get("slug")]
    existing_posts: dict[str, Post] = {}
    if post_slugs:
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.tags), selectinload(Post.category))
            .where(Post.slug.in_(post_slugs))
        )
        existing_posts = {p.slug: p for p in result.scalars().all()}

    # 分类 slug -> Category（含本次新创建的）
    all_cat_slugs = {p["category"]["slug"] for p in posts_data if p.get("category", {}).get("slug")}
    category_by_slug: dict[str, Category] = {}
    if all_cat_slugs:
        result = await db.execute(select(Category).where(Category.slug.in_(all_cat_slugs)))
        category_by_slug = {c.slug: c for c in result.scalars().all()}

    # 标签 slug -> Tag（含本次新创建的）
    all_tag_slugs = {t.get("slug") for p in posts_data for t in p.get("tags", []) if t.get("slug")}
    tag_by_slug: dict[str, Tag] = {}
    if all_tag_slugs:
        result = await db.execute(select(Tag).where(Tag.slug.in_(all_tag_slugs)))
        tag_by_slug = {t.slug: t for t in result.scalars().all()}

    # 导入文章
    for post_data in posts_data:
        try:
            # 获取分类（从预查字典中取，不再逐条查询）
            category = None
            cat_slug = post_data.get("category", {}).get("slug")
            if cat_slug:
                category = category_by_slug.get(cat_slug)

            # 检查是否已存在：skip_existing=True 跳过；False 覆盖更新
            # （后台"覆盖已有同 slug 文章"选项承诺的就是 overwrite，
            #  旧实现只记 error 不覆盖，属于虚假承诺）
            existing_post = existing_posts.get(post_data["slug"])
            if existing_post is not None:
                if skip_existing:
                    skipped_count += 1
                    continue
                _overwrite_post_from_import(existing_post, post_data, category)
                existing_post.tags = [
                    tag_by_slug[t["slug"]]
                    for t in post_data.get("tags", [])
                    if t.get("slug") and t["slug"] in tag_by_slug
                ]
                await db.flush()
                await db.refresh(existing_post)
                created_count += 1
                continue

            # 创建文章
            # 标签必须在构造器里一次性传入：flush 之后再 post.tags.append() 会去
            # 加载尚未载入的集合，async 会话直接抛 MissingGreenlet，
            # 表现为"带标签的 ZIP 一条都导不进来"（旧实现的必崩点）。
            tag_objects = [
                tag_by_slug[t["slug"]]
                for t in post_data.get("tags", [])
                if t.get("slug") and t["slug"] in tag_by_slug
            ]
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
                password=None,  # 不信任备份中的密码 hash，新文章不写入
                author_id=current_user.id,
                category_id=category.id if category else None,
                tags=tag_objects,
            )
            db.add(post)
            await db.flush()

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
    await _invalidate_content_caches()

    return ImportResult(
        success=True,
        message=(
            f"导入完成：创建/更新 {created_count} 篇，跳过 {skipped_count} 篇，"
            f"失败 {error_count} 篇"
        ),
        created_count=created_count,
        skipped_count=skipped_count,
        error_count=error_count,
        errors=errors[:10],  # 只返回前 10 个错误
    )


@router.post(
    "/import/markdown",
    summary="导入 Markdown",
    description=(
        "导入单个 Markdown 文件为文章。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "上传内容按 UTF-8 文本解析：必须是以 --- 包裹的 frontmatter，"
        "取其中的 title 与 slug（缺 slug 时由标题小写转写生成），正文落为 zh 变体；"
        "default_category 参数当前实现未参与写库。导入的文章一律是草稿状态，不会直接上线。"
        "未提供文件名时 400；slug 已存在或解析不到 frontmatter 时返回 200 且 success=false（不抛 4xx），"
        "调用方须读 success 判定结果。"
    ),
    responses={200: {"model": ImportResult}},
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
            await _invalidate_content_caches()

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
    description=(
        "返回当前数据库各项数据统计，用于备份前预览。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "每个模型一条 COUNT 查询，无缓存；文章系列模型不可用时 counts 里没有对应键。"
    ),
    responses={200: {"model": BackupInfoResponse}},
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
    description=(
        "导出整站数据为 ZIP 文件，包含所有内容模型及 manifest.json。"
        "需 staff 及以上权限（未登录 401，非管理员 403）。"
        "包内按模型分文件（文章、分类、标签、评论、用户、媒体、友情链接、导航、页面、公告、"
        "首屏轮播、站点配置，文章系列可用时另有一份），时间统一序列化为 ISO 字符串；"
        "manifest.json 记录备份版本、生成时间、导出者与每张表的条数。"
        "注意：备份的是数据库行（含媒体记录），不打包磁盘上的媒体文件本体；"
        "整包在内存里组装后流式下发，大站慎用。导入本包请用全站恢复接口。"
    ),
    responses=raw_content_response(
        "application/zip", "全站备份 zip（数据库转储 + 媒体目录）。", binary=True
    ),
    response_class=Response,
)
async def backup_full(
    db: DB,
    current_user: CurrentStaff,
) -> StreamingResponse:
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
            "has_password": bool(p.password),
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

    # === 打包 ZIP（整站备份数据量大，序列化 + 压缩走线程池） ===
    backup_entries: list[tuple[str, object]] = [
        ("manifest.json", manifest),
        ("posts.json", posts_data),
        ("categories.json", categories_data),
        ("tags.json", tags_data),
        ("comments.json", comments_data),
        ("users.json", users_data),
        ("media.json", media_data),
        ("friend_links.json", friend_links_data),
        ("navigations.json", navigations_data),
        ("pages.json", pages_data),
        ("announcements.json", announcements_data),
        ("hero_slides.json", hero_slides_data),
        ("site_config.json", site_config_data),
    ]
    if PostSeries is not None:
        backup_entries.append(("post_series.json", post_series_data))

    zip_buffer = io.BytesIO(await asyncio.to_thread(_build_zip, backup_entries))
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
    description=(
        "上传全站备份 ZIP 恢复整站数据。需 staff 及以上权限（未登录 401，非管理员 403）。"
        "文件名必须以 .zip 结尾，否则 400；压缩包本身解析失败也是 400。"
        "缺某个 JSON 分项不报错、按空集合跳过，因此请确认包来自全站备份接口。"
        "按外键依赖顺序导入（站点配置 → 用户 → 分类/标签 → …… → 文章 → 评论 → 媒体）。"
        "是否已存在按自然键判断：站点配置看 key、用户看 username、分类/标签/页面/文章看 slug、"
        "媒体看存储路径。策略 skip_existing（默认）把已存在条目计为跳过；"
        "overwrite 覆盖可写字段并计入 created_count，但用户是分脱敏恢复（不还原密码，"
        "新用户用占位密码与邮箱），文章的密码 hash 也不信任备份值。"
        "完成后连带失效内容、站点配置、导航、友情链接等缓存。"
        "结果以 200 返回，success 恒为 true，逐条失败看 error_count 与 errors（最多回传前 20 条）。"
    ),
    responses={200: {"model": ImportResult}},
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

    # 解压炸弹防护：文件名后缀不足以证明内容安全，ZIP 的压缩比可达 1000:1，
    # 一个几百 KB 的备份包解压后能吃满内存。三层限额：
    #   1) 压缩包本体体积上限（与 media 上传同口径，统一 20MB）
    #   2) 单条目解压后体积上限
    #   3) 全部条目解压后总体积上限
    # 恢复是 staff-only 但不能因此假设"可信"——备份包常来自第三方迁移。
    try:
        content = await file.read()
        if len(content) > MAX_BACKUP_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"备份文件不能超过 {MAX_BACKUP_BYTES // (1024 * 1024)}MB",
            )
        zip_buffer = io.BytesIO(content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            infos = zf.infolist()
            total_uncompressed = sum(i.file_size for i in infos)
            if total_uncompressed > MAX_BACKUP_UNCOMPRESSED_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=(
                        "备份包解压后体积过大（疑似压缩炸弹）："
                        f"{total_uncompressed // (1024 * 1024)}MB > "
                        f"{MAX_BACKUP_UNCOMPRESSED_BYTES // (1024 * 1024)}MB"
                    ),
                )
            names = set(zf.namelist())

            def _read(name: str, default):
                if name in names:
                    info = zf.getinfo(name)
                    if info.file_size > MAX_BACKUP_ENTRY_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=(
                                f"备份条目 {name} 过大："
                                f"{info.file_size // (1024 * 1024)}MB，已拒绝导入"
                            ),
                        )
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
    except HTTPException:
        # 体积校验产生的 413 必须原样抛出，不能被下面兜底改成 400 的"解析失败"
        raise
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
                    # 不信任备份中的 password hash：已存在文章保留库中原值
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
                password=None,  # 不信任备份中的密码 hash，新文章不写入
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
                # 标签必须在构造器里传入：flush 之后 post.tags.append() 要加载未载入
                # 的集合，async 会话直接抛 MissingGreenlet（与 /import/posts 同一缺陷）
                tags=[slug_to_tag[s] for s in item.get("tag_slugs", []) if s in slug_to_tag],
            )
            db.add(post)
            await db.flush()

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
    # 整站恢复触及文章之外的站点配置/导航/友情链接/相册，这些缓存同样要一起失效，
    # 否则"恢复完成"后前台仍会按备份前的配置渲染。
    await _invalidate_content_caches(
        "site_config", "navigations", "friend_links", "gallery", "activities"
    )

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
