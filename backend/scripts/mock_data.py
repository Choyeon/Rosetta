"""
Rosetta 模拟/种子数据入口（重构版）。

原文件 2736 LOC，问题：
    - 自己维护 5 分类 / 12 标签 / 5 篇模板文章（与 oobe_seed_data.py 的 8/24/32 重复）
    - 内联生成函数三份展开（generate_all_mock_data / generate_oobe_mock_data / minimal fallback）
    - 留言板、动态、分类创建等代码无复用

重构后：
    - 工厂与本地化文本完全下沉到 _seed_shared.SeedContext 和 backend/data/*.json
    - 此文件保留三个对上游完全兼容的入口签名 + CLI main：
        1. generate_all_mock_data(...)          —— backend/api/admin.py:848 调用
        2. generate_oobe_mock_data(db, admin_id)—— backend/api/oobe.py:675/1280 调用
        3. generate_oobe_mock_data_minimal(...) —— 当 JSON 失败时的 fallback
        4. CLI:  python -m backend.scripts.mock_data   —— 生成轻量开发 mock 数据
"""

from __future__ import annotations

import asyncio
import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from backend.scripts._seed_shared import SeedContext, SeedResult, UTC

log = logging.getLogger(__name__)


# ==========================================================================
# Entry 1: generate_all_mock_data (后台 Admin 一键生成开发 mock)
# ==========================================================================


async def generate_all_mock_data(
    db,
    posts_count: int = 20,
    categories_count: int = 5,
    tags_count: int = 10,
    users_count: int = 5,
    comments_count: int = 50,
    reset: bool = False,
) -> dict:
    """生成面向开发/演示的随机模拟数据（Admin 面板接口专用）。

    - 数据采用随机生成，保证每次运行都会有新内容；
    - 非幂等设计：每一次调用都会 INSERT 新记录（与上游行为一致）；
    - reset=True 会清空文章/分类/标签/评论/普通用户再重建；管理员保留。
    """
    from backend.core.auth import get_password_hash
    from backend.models.blog import Category, Comment, Post, Tag
    from backend.models.user import User

    # ---------- reset ----------
    if reset:
        for tbl in (Comment, Post, Category, Tag):
            await db.execute(tbl.__table__.delete())
        await db.execute(User.__table__.delete().where(User.username != "admin"))
        await db.flush()

    # ---------- 管理员 ----------
    admin = (await db.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
    if admin is None:
        admin = User(
            username="admin",
            email="admin@rosetta.dev",
            password_hash=get_password_hash("admin123"),
            nickname="Administrator",
            is_active=True,
            is_staff=True,
            is_superuser=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(admin)
        await db.flush()

    rng = random.Random()
    now = datetime.now(UTC)

    # ---------- 分类 (categories_count 个，简易 i18n) ----------
    cat_cn_pool = ["技术", "生活", "随笔", "教程", "分享", "读书", "旅行", "美食", "职场", "日记"]
    cat_en_pool = ["Technology", "Life", "Essay", "Tutorial", "Share", "Books", "Travel", "Food", "Career", "Diary"]
    cat_pool = list(zip(cat_cn_pool, cat_en_pool))
    cats: list[Category] = []
    for i in range(min(max(1, categories_count), len(cat_pool))):
        cn, en = cat_pool[i]
        c = Category(
            name={"zh": cn, "en": en, "ja": cn, "zh_Hant": cn},
            slug=f"category-{i + 1}-{''.join(rng.choices(string.ascii_lowercase, k=4))}",
            description={
                "zh": f"{cn}分类", "en": f"{en} category",
                "ja": f"{cn}カテゴリ", "zh_Hant": f"{cn}分類",
            },
            color="#6366F1",
            icon="heroicons:code-bracket",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(c)
        cats.append(c)
    await db.flush()

    # ---------- 标签 ----------
    tag_cn = ["Python", "JavaScript", "Vue", "FastAPI", "Docker", "Linux", "Rust",
              "算法", "数据库", "前端", "后端", "AI", "CSS", "Go", "TypeScript"]
    tags: list[Tag] = []
    for i in range(min(max(1, tags_count), len(tag_cn))):
        name = tag_cn[i]
        color = "#{:06x}".format(rng.randint(0x222222, 0xBBBBBB))
        t = Tag(
            name={"zh": name, "en": name, "ja": name, "zh_Hant": name},
            slug=f"tag-{i + 1}-{name.lower()}",
            color=color,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(t)
        tags.append(t)
    await db.flush()

    # ---------- 普通用户 (users_count 个，作为评论作者来源) ----------
    normal_users: list[User] = []
    for i in range(max(0, users_count)):
        u_name = f"user_{i + 1}_{''.join(rng.choices(string.ascii_lowercase, k=4))}"
        u = User(
            username=u_name,
            email=f"u{i + 1}@example.com",
            password_hash=get_password_hash("password123"),
            nickname=f"用户{i + 1}",
            bio=f"这是由 mock 脚本生成的用户#{i + 1}",
            avatar_source="auto",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            created_at=now,
            updated_at=now,
        )
        db.add(u)
        normal_users.append(u)
    await db.flush()

    # ---------- 文章 ----------
    created_posts = 0
    created_views = 0
    created_post_ids: list[int] = []
    for i in range(max(1, posts_count)):
        cat = cats[i % len(cats)]
        title_zh = f"示例文章 #{i + 1}：{rng.choice(['深入理解', '快速上手', '实战经验', '踩坑记录', '最佳实践'])}" \
                   + rng.choice(tag_cn[:tags_count])
        content_md = (
            f"# {title_zh}\n\n"
            f"这是自动生成的示例文章 **#{i + 1}**，作者演示内容。\n\n"
            f"## 小节一：背景\n\n"
            f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            f"这里是正文内容的占位，共 {rng.randint(400, 1200)} 字占位。\n\n"
            f"## 小节二：示例代码\n\n"
            "```python\nfor i in range(5):\n    print(i)\n```\n\n"
            f"## 小节三：总结\n\n"
            f"感谢阅读，欢迎评论互动。\n"
        )
        p = Post(
            title={"zh": title_zh, "en": f"Sample Post #{i + 1}", "ja": title_zh, "zh_Hant": title_zh},
            slug=f"sample-post-{i + 1}-{''.join(rng.choices(string.ascii_lowercase, k=6))}",
            source="原创",
            excerpt={"zh": f"这是示例文章 #{i + 1} 的摘要。", "en": f"Summary of post #{i + 1}"},
            content={"zh": content_md, "en": content_md, "ja": content_md, "zh_Hant": content_md},
            cover_image=None,
            author_id=admin.id,
            category_id=cat.id,
            status="published",
            visibility="public",
            views=rng.randint(0, 999),
            is_pinned=(i == 0),
            allow_comments=True,
            published_at=now - timedelta(days=rng.randint(0, 90)),
            created_at=now,
            updated_at=now,
        )
        n_tags = rng.randint(1, min(4, len(tags)))
        p.tags = rng.sample(tags, k=n_tags)
        db.add(p)
        created_posts += 1
        created_views += p.views
    await db.flush()
    # Fetch back PKs
    recent = list((await db.execute(
        select(Post).order_by(Post.id.desc()).limit(created_posts)
    )).scalars().all())
    created_post_ids = [p.id for p in recent]

    # ---------- 评论（按 comments_count 总目标分配，均匀分摊到文章） ----------
    created_comments = 0
    all_commentators: list[User] = [admin, *normal_users] or [admin]
    target_pp = max(1, comments_count // max(1, created_posts))
    for pid in created_post_ids:
        for _ in range(target_pp):
            commentator = rng.choice(all_commentators)
            c = Comment(
                post_id=pid,
                user_id=commentator.id,
                parent_id=None,
                author_name=commentator.nickname or commentator.username,
                author_email=commentator.email,
                author_ip=f"10.0.{rng.randint(1, 254)}.{rng.randint(1, 254)}",
                content=rng.choice([
                    "写得很详细，学习了～", "感谢分享！", "刚好我遇到同样的问题，mark 一下。",
                    "作者这个思路非常赞。", "我觉得第三点可以再展开讲讲？",
                    "Great article, thanks!", "顶一下，期待后续。", "代码片段复制即用，省了我半天，感谢！",
                ]),
                status="approved",
                active=True,
                likes_count=rng.randint(0, 12),
                created_at=now - timedelta(days=rng.randint(0, 30), hours=rng.randint(0, 23)),
                updated_at=now,
            )
            db.add(c)
            created_comments += 1
    await db.flush()
    await db.commit()

    return {
        "categories": len(cats),
        "tags": len(tags),
        "users": len(normal_users),
        "posts": created_posts,
        "comments": created_comments,
        "views": created_views,
        "admin": f"{admin.username}(id={admin.id})",
    }


# ==========================================================================
# Entry 2: generate_oobe_mock_data (OOBE 真正的生产级种子入口)
# ==========================================================================


async def generate_oobe_mock_data(db, admin_id: int) -> dict:
    """OOBE 第五步一键注入：真实感种子数据。

    原 680+ 行内联代码（分类、标签、32 篇文章、评论、25 条动态、留言板 各写一遍 ORM 插入）
    统一委托给 SeedContext.run_seed，幂等 + 可测 + 可传自定义时钟。
    """
    from backend.models.user import User

    admin = await db.get(User, int(admin_id))
    if admin is None:
        # 兜底：找任意管理员
        admin = (await db.execute(select(User).where(User.is_superuser.is_(True)).limit(1))).scalar_one_or_none()
    if admin is None:
        return {
            "categories": 0, "tags": 0, "posts": 0, "comments": 0,
            "activities": 0, "guestbook_entries": 0, "views": 0,
            "error": f"admin_id={admin_id} not found",
        }

    try:
        ctx = SeedContext(db, lang="zh")
    except Exception as exc:  # noqa: BLE001 —— JSON 缺失或损坏时 fallback 到最小兼容版本
        log.warning("SeedContext 初始化失败，fallback 到 generate_oobe_mock_data_minimal: %s", exc)
        return await generate_oobe_mock_data_minimal(db, admin_id)

    try:
        result: SeedResult = await ctx.run_seed(
            author=admin,
            include_posts=True,
            include_comments=True,
            include_activities=True,
            include_guestbook=True,
            include_galleries=True,
            include_pages=True,
            include_navigation=False,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("generate_oobe_mock_data 执行失败（降级到 minimal）：%s", exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return await generate_oobe_mock_data_minimal(db, admin_id)

    # 汇总统计视图数（为了与旧返回键保持兼容）
    views_total = 0
    for p in ctx._posts.values():
        views_total += int(getattr(p, "views", 0) or 0)

    details = result.details
    return {
        "categories": details.get("categories", {}).get("created", 0),
        "tags": details.get("tags", {}).get("created", 0),
        "posts": details.get("posts", {}).get("created", 0),
        "comments": details.get("comments", {}).get("created", 0),
        "activities": details.get("activities", {}).get("created", 0),
        "guestbook_entries": details.get("guestbooks", {}).get("created", 0),
        "galleries_albums": details.get("galleries_albums", {}).get("created", 0),
        "galleries_photos": details.get("galleries_photos", {}).get("created", 0),
        "pages": details.get("pages", {}).get("created", 0),
        "views": views_total,
        "skipped_categories": details.get("categories", {}).get("skipped", 0),
        "skipped_tags": details.get("tags", {}).get("skipped", 0),
        "skipped_posts": details.get("posts", {}).get("skipped", 0),
    }


# ==========================================================================
# Entry 3: generate_oobe_mock_data_minimal (fallback — 零 JSON 依赖)
# ==========================================================================


async def create_sample_guestbook_entries(db, admin_id: int) -> int:
    """独立的最小化留言板生成：1 条管理员置顶 + 2 条普通访客（无需 JSON 文件）。"""
    from backend.models.guestbook import GuestbookEntry

    existing = (await db.execute(select(GuestbookEntry.id).limit(1))).scalar_one_or_none()
    if existing is not None:
        return 0
    now = datetime.now(UTC)
    admin_row = GuestbookEntry(
        user_id=admin_id,
        author_name="Choyeon",
        author_email="choyeon@foxmail.com",
        author_website="https://rosetta.choyeon.cc",
        author_ip="127.0.0.1",
        github="Choyeon",
        avatar_source="github",
        content=(
            "欢迎来到 Rosetta！这是使用最小兼容模式生成的示例留言。"
            "正常模式下会有更丰富的多语言示例内容。"
        ),
        status="approved",
        active=True,
        is_pinned=True,
        likes_count=3,
        created_at=now,
        updated_at=now,
    )
    v1 = GuestbookEntry(
        author_name="访客A",
        author_email="visitor1@example.com",
        author_ip="10.0.0.11",
        avatar_source="auto",
        content="欢迎上线！博客整体风格挺清爽的，加油！",
        status="approved",
        active=True,
        likes_count=0,
        created_at=now,
        updated_at=now,
    )
    v2 = GuestbookEntry(
        author_name="访客B",
        author_email="visitor2@example.com",
        author_ip="10.0.0.12",
        avatar_source="auto",
        content="第一次来这里，找 RSS 订阅入口没找到，请问在哪里看？",
        status="approved",
        active=True,
        likes_count=0,
        created_at=now,
        updated_at=now,
    )
    for row in (admin_row, v1, v2):
        db.add(row)
    await db.flush()
    return 3


async def generate_oobe_mock_data_minimal(db, admin_id: int) -> dict:
    """当 SeedContext/JSON 不可用时的最小兼容 fallback（1 cat + 3 tag + 1 post + ~3 guestbook）。"""
    from backend.models.blog import Category, Post, Tag

    created_cats = 0
    oobe_categories = [
        {
            "name": {"zh": "技术", "en": "Technology", "ja": "技術", "zh_Hant": "技術"},
            "slug": "technology",
            "description": {
                "zh": "技术相关文章",
                "en": "Technology related articles",
                "ja": "技術関連の記事",
                "zh_Hant": "技術相關文章",
            },
            "color": "#3B82F6",
            "icon": "heroicons:code-bracket",
        },
    ]
    tech_category = None
    for cat_data in oobe_categories:
        existing = (await db.execute(select(Category).where(Category.slug == cat_data["slug"]))).scalar_one_or_none()
        if existing:
            if cat_data["slug"] == "technology":
                tech_category = existing
            continue
        c = Category(**cat_data, is_active=True, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        db.add(c)
        created_cats += 1
        if cat_data["slug"] == "technology":
            tech_category = c
    await db.flush()

    created_tags = 0
    oobe_tags = [
        {"name": {"zh": "Python", "en": "Python", "ja": "Python", "zh_Hant": "Python"},
         "slug": "python", "color": "#3776AB"},
        {"name": {"zh": "JavaScript", "en": "JavaScript", "ja": "JavaScript", "zh_Hant": "JavaScript"},
         "slug": "javascript", "color": "#F7DF1E"},
        {"name": {"zh": "Vue", "en": "Vue", "ja": "Vue", "zh_Hant": "Vue"},
         "slug": "vue", "color": "#4FC08D"},
    ]
    tag_objs: list[Tag] = []
    for td in oobe_tags:
        existing = (await db.execute(select(Tag).where(Tag.slug == td["slug"]))).scalar_one_or_none()
        if not existing:
            existing = Tag(**td, is_active=True, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
            db.add(existing)
            created_tags += 1
        tag_objs.append(existing)
    await db.flush()

    created_posts = 0
    hello_slug = "hello-world-oobe"
    hello_post = (await db.execute(select(Post).where(Post.slug == hello_slug))).scalar_one_or_none()
    if not hello_post:
        content = (
            "# Hello World\n\n欢迎使用 **Rosetta** 博客平台！\n\n"
            "这是最小化种子数据生成的示例文章。\n\n## 下一步\n\n"
            "1. 访问管理后台撰写真实文章\n2. 在站点设置中修改网站名称与描述\n\n祝写作愉快！\n"
        )
        hp = Post(
            title={"zh": "Hello World", "en": "Hello World", "ja": "Hello World", "zh_Hant": "Hello World"},
            slug=hello_slug,
            excerpt={"zh": "欢迎使用 Rosetta 博客平台！", "en": "Welcome to Rosetta!",
                     "ja": "Rosetta へようこそ！", "zh_Hant": "歡迎使用 Rosetta 部落格平台！"},
            content={"zh": content, "en": content, "ja": content, "zh_Hant": content},
            author_id=int(admin_id),
            category_id=tech_category.id if tech_category else None,
            status="published",
            allow_comments=True,
            is_pinned=False,
            views=12,
            published_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        if tag_objs:
            hp.tags = tag_objs
        db.add(hp)
        created_posts += 1
        await db.flush()

    created_guestbook = 0
    try:
        created_guestbook = await create_sample_guestbook_entries(db, admin_id)
    except Exception:  # noqa: BLE001
        created_guestbook = 0

    await db.commit()
    return {
        "categories": created_cats,
        "tags": created_tags,
        "posts": created_posts,
        "comments": 0,
        "activities": 0,
        "guestbook_entries": created_guestbook,
    }


# ==========================================================================
# 开发者快捷入口：直接 python -m backend.scripts.mock_data
# ==========================================================================


async def create_mock_data(num_posts: int = 20, num_users: int = 10, num_comments: int = 50) -> dict:
    from backend.core.database import async_session_factory
    async with async_session_factory() as session:
        return await generate_all_mock_data(
            session,
            posts_count=num_posts,
            categories_count=5,
            tags_count=10,
            users_count=num_users,
            comments_count=num_comments,
            reset=False,
        )


async def main() -> None:
    """CLI 入口：等价于旧脚本 `python -m backend.scripts.mock_data`。"""
    import argparse

    parser = argparse.ArgumentParser(description="Rosetta mock data generator")
    parser.add_argument("--posts", type=int, default=20)
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--comments", type=int, default=50)
    parser.add_argument("--reset", action="store_true", help="Clear old mock rows before inserting")
    parser.add_argument("--oobe", action="store_true",
                        help="Run OOBE seed (requires admin_id via --admin-id)")
    parser.add_argument("--admin-id", type=int, default=1)
    args = parser.parse_args()

    from backend.core.database import async_session_factory, init_db

    await init_db()
    async with async_session_factory() as db:
        if args.oobe:
            result = await generate_oobe_mock_data(db, admin_id=args.admin_id)
            print("[OOBE mock]", result)
        else:
            result = await generate_all_mock_data(
                db,
                posts_count=args.posts,
                categories_count=5,
                tags_count=10,
                users_count=args.users,
                comments_count=args.comments,
                reset=args.reset,
            )
            print("[Mock data]", result)


if __name__ == "__main__":
    asyncio.run(main())
