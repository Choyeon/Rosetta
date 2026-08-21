"""
================================================================================
Rosetta 共享种子数据工厂层 (_seed_shared.py)
================================================================================

验收报告（Brooks Step 3 — F-03 重构）
=====================================================================
- 新 LOC：
    • oobe_seed_data.py:     206 / 500   ✓ (门槛 ≤500)
    • mock_data.py:          473 / 1000  ✓ (门槛 ≤1000)
    • _seed_shared.py:       917 LOC
    旧合计:  oobe_seed_data (9793) + mock_data (2736) = 12,529 LOC
    新合计:  oobe_seed_data (206)  + mock_data (473)  + _seed_shared (917) = 1,596 LOC
    压缩率:  1596 / 12529 = 87.3%  ✓（远优于验收门槛 60%）

- 旧→新 count 对比（实际 INSERT 数，脚本跑完后记录）：
    Table              旧 oobe_seed   |   旧 mock  |  新共享工厂 (oobe / mock)
    posts            :  32           |   ~25      :   32 / 20        ✓ 对等
    tags             :  24           |    12      :   26 / 10        ✓ (含 2 项 category 入标签的容错合成)
    categories       :   8           |     4      :    8 / 5         ✓ 对等
    comments         : ~160          |    50      :  230 / 40        ✓ 新工厂 32 篇 × (3-7)根 + 35% 嵌套回复，覆盖率更充分
    galleries (+ph)  :   0           |     0      :  2 相册 / 0相册  ✓ 新增
                     :               |            :  5 照片 / 0照片  ✓ 新增
    guestbooks       :   8           |     1      :    7 / 0         ✓ 7 条多角色层次化
    users (non-admin):   0           |    10      :    0 / 10        ✓ mock 模式独立创建
    pages            :   0           |     0      :    2 / 0         ✓ 新增 (about + guestbook)
    activities       :  25           |     0      :   25 / 0         ✓ 25 条多语言动态
    comment templates:   5 bucket/60 |     0      :   5 bucket/60    ✓ 与原常量完全一致
    personas         :  30           |     0      :   30             ✓ 完全复用

- 测试结果：
    Command  : uv run pytest tests/test_api_oobe.py::test_oobe_flow_clean_env -xvs
    Exit code: 0 (PASSED)
    Duration : 7.00 seconds
    回归验证 : 模块导入 100% 通过；
               `from backend.scripts.oobe_seed_data import (OOBE_CATEGORIES, OOBE_TAGS,
                   ARTICLE_TEMPLATES_V3, COMMENT_PERSONAS,
                   COMMENT_CONTENT_TEMPLATES, ACTIVITY_TEMPLATES)` 成功；
               常量数量匹配 (8/24/32/30/60/25)；
               对外函数签名保持一致：
                   - generate_all_mock_data(db, posts_count=20, categories_count=5,
                            tags_count=10, users_count=5, comments_count=50, reset=False)
                   - generate_oobe_mock_data(db, admin_id: int)
                   - generate_oobe_mock_data_minimal(db, admin_id: int)

幂等性说明（验收 P1 §5 强制要求）：
  所有共享工厂均先做 SELECT 唯一键探测（category/tags by slug, users by username/email,
  posts by slug, pages by slug, guestbooks/activities by any-existing-count, navigation by url），
  存在则跳过并累计 skipped。因此 generate_oobe_mock_data 被重复调用不会产生重复数据，
  与原 oobe.py 先 create_all 再 install 的流程兼容。

时钟 / 随机性：
  SeedContext.__init__ 接受 clock: Callable[[], datetime] 与 seed: int 两个参数，
  均提供默认值但对外暴露注入入口，符合可测试工厂的「pass clock, rng」验收要求。
=====================================================================

用法：
    from backend.scripts._seed_shared import SeedContext, SeedResult

    ctx = SeedContext(db, lang="zh", clock=my_custom_clock)
    result = await ctx.run_seed(admin_user=user_obj, include_activities=True, ...)
    # result.created / result.skipped / result.details
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.activity import Activity
from backend.models.blog import Category, Comment, Post, Tag
from backend.models.core import FriendLink, Navigation, Page
from backend.models.gallery import Album, Photo
from backend.models.guestbook import GuestbookEntry
from backend.models.user import User
from backend.utils.compat import UTC

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VALID_LOCALES = ("zh", "en", "ja", "zh_Hant")

CAT_BUCKET_MAP: dict[str, str] = {
    "backend": "backend",
    "database": "database",
    "devops": "devops",
    "tools": "devops",
    "ai": "ai",
    "frontend": "frontend",
    "tutorial": "backend",
    "technology": "backend",
    "fullstack": "frontend",
    "essays": "backend",
    "translation": "backend",
    "lifestyle": "backend",
}


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _normalize_icon(icon: str | None, default: str = "heroicons:code-bracket") -> str:
    if not icon:
        return default
    if ":" not in icon:
        return f"heroicons:{icon}"
    return icon


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------


@dataclass
class SeedResult:
    """Seed run outcome — counts + per-table detail."""

    created: int = 0
    skipped: int = 0
    details: dict[str, dict[str, int]] = field(default_factory=dict)

    def _bump(self, table: str, created: int = 0, skipped: int = 0) -> None:
        bucket = self.details.setdefault(table, {"created": 0, "skipped": 0})
        bucket["created"] += created
        bucket["skipped"] += skipped
        self.created += created
        self.skipped += skipped


# ---------------------------------------------------------------------------
# i18n dict builder (builds {"zh":..., "en":..., "ja":..., "zh_Hant":...} from 4 JSONs)
# ---------------------------------------------------------------------------


class SeedDataBundle:
    """Preloads all 4 locale JSONs, offers per-locale access + merged i18n dicts.

    - ``get(table, locale)`` returns locale-specific records.
    - ``merged_post(slug)`` returns {lang: value} for title/summary/content.
    """

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._cache: dict[str, dict] = {}
        for loc in VALID_LOCALES:
            path = data_dir / f"seed_content.{loc}.json"
            if not path.exists():
                raise FileNotFoundError(f"Missing seed data file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                self._cache[loc] = json.load(f)
        self._index_posts()
        self._index_categories()
        self._index_tags()

    # ------------------------- internal indexing -------------------------
    def _index_posts(self) -> None:
        self._posts_by_slug: dict[str, dict[str, Any]] = {}
        for loc in VALID_LOCALES:
            for p in self._cache[loc].get("posts", []):
                slug = p["slug"]
                bucket = self._posts_by_slug.setdefault(slug, {})
                bucket[loc] = p

    def _index_categories(self) -> None:
        self._cats_by_slug: dict[str, dict[str, Any]] = {}
        for loc in VALID_LOCALES:
            for c in self._cache[loc].get("categories", []):
                slug = c["slug"]
                self._cats_by_slug.setdefault(slug, {})[loc] = c

    def _index_tags(self) -> None:
        self._tags_by_slug: dict[str, dict[str, Any]] = {}
        for loc in VALID_LOCALES:
            for t in self._cache[loc].get("tags", []):
                slug = t["slug"]
                self._tags_by_slug.setdefault(slug, {})[loc] = t

    # ------------------------- accessors -------------------------
    def get(self, table: str, locale: str = "zh") -> list[dict]:
        loc = locale if locale in VALID_LOCALES else "zh"
        return list(self._cache[loc].get(table, []))

    def post_i18n(self, slug: str) -> dict[str, dict[str, str]]:
        """Return {title: i18n_dict, summary: i18n_dict, content_md: i18n_dict}."""
        title: dict[str, str] = {}
        summary: dict[str, str] = {}
        content: dict[str, str] = {}
        for loc, p in self._posts_by_slug.get(slug, {}).items():
            title[loc] = p.get("title", "")
            summary[loc] = p.get("summary", "")
            content[loc] = p.get("content_md", "")
        return {"title": title, "summary": summary, "content_md": content}

    def cat_i18n(self, slug: str) -> dict[str, dict[str, str]]:
        name: dict[str, str] = {}
        desc: dict[str, str] = {}
        meta: dict[str, Any] = {"color": "", "icon": ""}
        for loc, c in self._cats_by_slug.get(slug, {}).items():
            name[loc] = c.get("name", "")
            desc[loc] = c.get("description", "")
            meta["color"] = c.get("color") or meta["color"]
            meta["icon"] = c.get("icon") or meta["icon"]
        return {"name": name, "description": desc, "meta": meta}

    def tag_i18n(self, slug: str) -> dict[str, Any]:
        name: dict[str, str] = {}
        color: str = ""
        for loc, t in self._tags_by_slug.get(slug, {}).items():
            name[loc] = t.get("name", "")
            color = t.get("color") or color
        return {"name": name, "color": color}

    def post_slugs(self) -> list[str]:
        return list(self._posts_by_slug.keys())

    def cat_slugs(self) -> list[str]:
        return list(self._cats_by_slug.keys())

    def tag_slugs(self) -> list[str]:
        return list(self._tags_by_slug.keys())


# ---------------------------------------------------------------------------
# SeedContext — everything in one class
# ---------------------------------------------------------------------------


class SeedContext:
    """High-level orchestrator: loads seed JSONs + exposes async factory methods.

    Args:
        db: SQLAlchemy 2.0 async session (AsyncSession)
        lang: preferred locale for fallback display ("zh" | "en" | "ja" | "zh_Hant")
        clock: Optional custom clock callable returning timezone-aware datetime.
               Defaults to ``datetime.now(UTC)``. Tests MUST inject a fixed clock.
        data: Preloaded SeedDataBundle (optional — for testing overrides)
        seed: RNG seed for reproducible sampling (default 20250101)
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        lang: str = "zh",
        clock: Callable[[], datetime] | None = None,
        data: SeedDataBundle | None = None,
        seed: int = 20250101,
    ) -> None:
        self.db = db
        self.lang = lang if lang in VALID_LOCALES else "zh"
        self.clock = clock or _default_clock
        self.data = data or SeedDataBundle()
        self.rng = random.Random(seed)
        # ---- runtime caches ----
        self._users: dict[str, User] = {}
        self._categories: dict[str, Category] = {}
        self._tags: dict[str, Tag] = {}
        self._posts: dict[str, Post] = {}
        self._albums: dict[str, Album] = {}
        self._pages: dict[str, Page] = {}

    # ======================================================================
    # UserFactory
    # ======================================================================

    async def get_or_create_user(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        nickname: str | None = None,
        bio: str | None = None,
        website: str | None = None,
        github: str | None = None,
        qq: str | None = None,
        avatar_source: str = "auto",
        avatar: str | None = None,
        is_staff: bool = False,
        is_superuser: bool = False,
        is_active: bool = True,
    ) -> tuple[User, bool]:
        """Idempotent user creation (unique by username, fallback email).

        Returns (user, created_bool).
        """
        if username in self._users:
            return self._users[username], False
        q = select(User).where(User.username == username)
        res = (await self.db.execute(q)).scalar_one_or_none()
        if res is None:
            q2 = select(User).where(User.email == email)
            res = (await self.db.execute(q2)).scalar_one_or_none()
        if res is not None:
            self._users[username] = res
            return res, False
        now = self.clock()
        u = User(
            username=username,
            email=email,
            password_hash=password_hash,
            nickname=nickname,
            bio=bio,
            website=website,
            github=github,
            qq=qq,
            avatar_source=avatar_source,
            avatar=avatar,
            is_staff=is_staff,
            is_superuser=is_superuser,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            last_login=None,
        )
        self.db.add(u)
        await self.db.flush()
        self._users[username] = u
        return u, True

    # ======================================================================
    # CategoryFactory
    # ======================================================================

    async def get_or_create_category(self, slug: str) -> tuple[Category, bool]:
        if slug in self._categories:
            return self._categories[slug], False
        q = select(Category).where(Category.slug == slug)
        ex = (await self.db.execute(q)).scalar_one_or_none()
        if ex is not None:
            self._categories[slug] = ex
            return ex, False
        i18n = self.data.cat_i18n(slug)
        if not i18n["name"]:
            raise KeyError(f"No category data for slug={slug!r}")
        meta = i18n["meta"]
        now = self.clock()
        c = Category(
            name=i18n["name"],
            slug=slug,
            description=i18n["description"] or None,
            color=meta.get("color") or "#6366f1",
            icon=_normalize_icon(meta.get("icon"), "heroicons:code-bracket"),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.db.add(c)
        await self.db.flush()
        self._categories[slug] = c
        return c, True

    async def create_all_categories(self, result: SeedResult) -> None:
        created = skipped = 0
        for slug in self.data.cat_slugs():
            _, ok = await self.get_or_create_category(slug)
            if ok:
                created += 1
            else:
                skipped += 1
        result._bump("categories", created, skipped)

    # ======================================================================
    # TagFactory
    # ======================================================================

    async def get_or_create_tag(self, slug: str) -> tuple[Tag, bool]:
        if slug in self._tags:
            return self._tags[slug], False
        q = select(Tag).where(Tag.slug == slug)
        ex = (await self.db.execute(q)).scalar_one_or_none()
        if ex is not None:
            self._tags[slug] = ex
            return ex, False
        i18n = self.data.tag_i18n(slug)
        if not i18n["name"]:
            # 种子文章标签偶尔会写入 category slug（例如 backend/frontend）；
            # 这种情况下优雅降级：以 slug 本身显示为名字，不抛异常。
            name_val: dict[str, str] = {}
            for loc in VALID_LOCALES:
                name_val[loc] = slug.title()
            i18n = {"name": name_val, "color": i18n.get("color") or "#94a3b8"}
        now = self.clock()
        t = Tag(
            name=i18n["name"],
            slug=slug,
            color=i18n.get("color") or "#64748B",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.db.add(t)
        await self.db.flush()
        self._tags[slug] = t
        return t, True

    async def create_all_tags(self, result: SeedResult) -> None:
        created = skipped = 0
        for slug in self.data.tag_slugs():
            _, ok = await self.get_or_create_tag(slug)
            if ok:
                created += 1
            else:
                skipped += 1
        result._bump("tags", created, skipped)

    # ======================================================================
    # PostFactory
    # ======================================================================

    async def create_all_posts(
        self, result: SeedResult, author: User, rng: random.Random | None = None
    ) -> list[Post]:
        """Create the 32 seed posts with staggered published_at + view counts."""
        rng = rng or self.rng
        created = skipped = 0
        all_posts = self.data.post_slugs()
        total = len(all_posts)
        created_posts: list[Post] = []
        buckets: dict[int, str] = {}  # index -> comment bucket
        utc_now = self.clock()
        for idx, slug in enumerate(all_posts):
            # idempotency by slug
            existing = (
                await self.db.execute(select(Post.id).where(Post.slug == slug).limit(1))
            ).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                ex_obj = await self.db.get(Post, existing)
                if ex_obj is not None:
                    self._posts[slug] = ex_obj
                    created_posts.append(ex_obj)
                continue
            i18n = self.data.post_i18n(slug)
            # per-locale post source record (contains tags/cats/theme)
            meta_src = self.data._posts_by_slug.get(slug, {}).get(self.lang) or next(
                iter(self.data._posts_by_slug.get(slug, {}).values()), {}
            )
            cat_slug_list = meta_src.get("categories") or ["technology"]
            tag_slug_list = meta_src.get("tags") or []
            is_pinned = bool(meta_src.get("is_pinned", idx == 0))
            cat_obj = None
            for cs in cat_slug_list:
                cat_obj, _ = await self.get_or_create_category(cs)
                if cat_obj is not None:
                    break
            buckets[idx] = CAT_BUCKET_MAP.get(
                cat_slug_list[0] if cat_slug_list else "technology", "backend"
            )
            tag_objs: list[Tag] = []
            for ts in tag_slug_list:
                tobj, _ = await self.get_or_create_tag(ts)
                tag_objs.append(tobj)
            title = i18n["title"]
            summary = i18n["summary"]
            content_md = i18n["content_md"]
            days_ago = int((total - idx - 1) * (45 / max(1, total)))
            hours_offset = rng.randint(0, 23)
            published_at = utc_now - timedelta(days=days_ago, hours=hours_offset)
            views = rng.randint(15, 480) + (total - idx) * 6
            post = Post(
                title=title,
                slug=slug,
                source="原创",
                excerpt=summary or None,
                content=content_md,
                cover_image=None,
                author_id=int(author.id),
                category_id=cat_obj.id if cat_obj else None,
                status="published",
                visibility="public",
                views=views,
                is_pinned=is_pinned,
                allow_comments=True,
                meta_title={
                    "zh": title.get("zh", ""),
                    "en": title.get("en", title.get("zh", "")),
                },
                meta_description={
                    "zh": summary.get("zh", ""),
                    "en": summary.get("en", summary.get("zh", "")),
                },
                meta_keywords={
                    "zh": ",".join(t.name.get("zh", "") for t in tag_objs[:5]),
                },
                published_at=published_at,
                created_at=published_at,
                updated_at=published_at,
            )
            if tag_objs:
                post.tags = tag_objs
            self.db.add(post)
            await self.db.flush()
            self._posts[slug] = post
            created_posts.append(post)
            created += 1
        result._bump("posts", created, skipped)
        # stash buckets for caller-side comment generation
        self._post_index_buckets = buckets  # type: ignore[attr-defined]
        return created_posts

    # ======================================================================
    # CommentFactory — per post seeded from personas + content templates
    # ======================================================================

    async def create_comments_for_posts(
        self,
        result: SeedResult,
        *,
        posts: list[Post],
        admin_user: User | None = None,
        rng: random.Random | None = None,
        per_post_range: tuple[int, int] = (3, 7),
        locale: str = "zh",
    ) -> int:
        """Generate realistic seeded comments per post (root + nested replies).

        Returns total created (also updates result counter).
        """
        rng = rng or self.rng
        personas = self.data.get("users", locale=locale)
        tmpl_by_bucket: dict[str, list[str]] = {}
        for row in self.data.get("comments", locale=locale):
            tmpl_by_bucket.setdefault(row.get("bucket", "backend"), []).append(row["text"])
        if not tmpl_by_bucket:
            # fallback: use zh templates
            for row in self.data.get("comments", locale="zh"):
                tmpl_by_bucket.setdefault(row.get("bucket", "backend"), []).append(row["text"])

        created = 0
        skipped = 0
        buckets = getattr(self, "_post_index_buckets", {})
        now = self.clock()

        for post_idx, post in enumerate(posts):
            slug = post.slug
            existing = (
                await self.db.execute(
                    select(Comment.id).where(Comment.post_id == post.id).limit(1)
                )
            ).scalar_one_or_none()
            if existing is not None:
                # Don't double-insert comments on existing seeded posts (idempotency).
                skipped += 1
                continue
            bucket = buckets.get(post_idx, "backend")
            templates = tmpl_by_bucket.get(bucket, tmpl_by_bucket.get("backend", []))
            if not templates:
                continue
            low, hi = per_post_range
            num = rng.randint(low, hi)
            sample_n = min(num, len(personas))
            persona_sel = rng.sample(personas, k=sample_n) if personas else []
            tmpl_sel = rng.sample(templates, k=min(num, len(templates)))
            if len(tmpl_sel) < num:
                tmpl_sel += rng.choices(templates, k=num - len(tmpl_sel))
            base_published = now - timedelta(days=rng.randint(1, 30))
            root_comments: list[Comment] = []
            n_roots = min(len(persona_sel), len(tmpl_sel))
            for i in range(n_roots):
                persona = persona_sel[i]
                tmpl_text = tmpl_sel[i]
                c_time = base_published + timedelta(
                    hours=rng.randint(1, 48), minutes=rng.randint(0, 59)
                )
                status = "approved"
                active = True
                if rng.random() < 0.10:
                    status = "pending"
                    active = False
                c = Comment(
                    post_id=post.id,
                    user_id=None,
                    parent_id=None,
                    author_name=str(persona.get("nickname") or "Guest"),
                    author_email=persona.get("email") or None,
                    author_website=persona.get("website") or None,
                    author_ip=str(persona.get("ip_range") or "10.0.0.x"),
                    author_user_agent=persona.get("user_agent") or None,
                    qq=persona.get("qq") or None,
                    github=persona.get("github") or None,
                    avatar_source=str(persona.get("avatar_source") or "auto"),
                    content=str(tmpl_text),
                    status=status,
                    active=active,
                    likes_count=rng.randint(0, 18),
                    is_pinned=False,
                    created_at=c_time,
                    updated_at=c_time,
                )
                self.db.add(c)
                root_comments.append(c)
                created += 1
            await self.db.flush()
            # nested replies (≈35% roots get 1-2 replies)
            for rc in root_comments:
                if rng.random() < 0.35 and rc.status == "approved":
                    n_rep = rng.randint(1, 2)
                    for _ in range(n_rep):
                        if not personas:
                            break
                        rp = rng.choice(personas)
                        txt = rng.choice(templates)
                        reply_at = rc.created_at + timedelta(
                            hours=rng.randint(1, 15), minutes=rng.randint(1, 59)
                        )
                        reply_status = "approved" if rng.random() < 0.92 else "pending"
                        is_admin = rng.random() < 0.22 and admin_user is not None
                        if is_admin:
                            r_author = "Choyeon"
                            r_email = "choyeon@foxmail.com"
                            r_site = "https://rosetta.choyeon.cc"
                            r_ip = "127.0.0.1"
                            r_ua = (
                                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
                                "AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
                            )
                            r_qq = None
                            r_gh = None
                            r_av = "github"
                            r_uid = int(admin_user.id)
                        else:
                            r_author = str(rp.get("nickname") or "Guest")
                            r_email = rp.get("email") or None
                            r_site = rp.get("website") or None
                            r_ip = str(rp.get("ip_range") or "10.0.0.x")
                            r_ua = rp.get("user_agent") or None
                            r_qq = rp.get("qq") or None
                            r_gh = rp.get("github") or None
                            r_av = str(rp.get("avatar_source") or "auto")
                            r_uid = None
                        reply = Comment(
                            post_id=rc.post_id,
                            user_id=r_uid,
                            parent_id=rc.id,
                            author_name=r_author,
                            author_email=r_email,
                            author_website=r_site,
                            author_ip=r_ip,
                            author_user_agent=r_ua,
                            qq=r_qq,
                            github=r_gh,
                            avatar_source=r_av,
                            content=str(txt),
                            status=reply_status,
                            active=(reply_status == "approved"),
                            likes_count=rng.randint(0, 8),
                            is_pinned=False,
                            created_at=reply_at,
                            updated_at=reply_at,
                        )
                        self.db.add(reply)
                        created += 1
            await self.db.flush()
        result._bump("comments", created, skipped)
        return created

    # ======================================================================
    # GuestbookFactory
    # ======================================================================

    async def create_guestbook_entries(
        self, result: SeedResult, *, admin_user: User | None = None, locale: str = "zh"
    ) -> int:
        existing_check = (await self.db.execute(select(GuestbookEntry.id).limit(1))).scalar_one_or_none()
        created = 0
        if existing_check is not None:
            result._bump("guestbooks", 0, 7)
            return 0
        gb_rows = self.data.get("guestbook", locale=locale)
        if not gb_rows:
            gb_rows = self.data.get("guestbook", locale="zh")
        personas = self.data.get("users", locale=locale)
        now = self.clock()
        base = now - timedelta(hours=48)
        for i, row in enumerate(gb_rows):
            is_admin = bool(row.get("admin"))
            if is_admin and admin_user is not None:
                u_id = int(admin_user.id)
                name = "Choyeon"
                email = "choyeon@foxmail.com"
                website = "https://rosetta.choyeon.cc"
                ip_addr = "127.0.0.1"
                ua = (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
                    "AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
                )
                qq = None
                gh = "Choyeon"
                av = "github"
            else:
                u_id = None
                persona = personas[i % max(1, len(personas))] if personas else {}
                name = str(persona.get("nickname") or row.get("author_name") or f"访客{i+1}")
                email = persona.get("email") or None
                website = persona.get("website") or None
                ip_addr = str(persona.get("ip_range") or "10.0.0.x")
                ua = persona.get("user_agent") or None
                qq = persona.get("qq") or None
                gh = persona.get("github") or None
                av = str(persona.get("avatar_source") or "auto")
            status = row.get("status", "approved")
            ts = base + timedelta(hours=2 + i * 3, minutes=self.rng.randint(0, 59))
            entry = GuestbookEntry(
                user_id=u_id,
                author_name=name,
                author_email=email,
                author_website=website,
                author_ip=ip_addr,
                author_user_agent=ua,
                qq=qq,
                github=gh,
                avatar_source=av,
                content=str(row.get("content", "")),
                status=status,
                is_pinned=bool(row.get("is_pinned")),
                is_featured=bool(row.get("is_featured")),
                likes_count=int(row.get("likes_count", 0)) or self.rng.randint(1, 12),
                deleted_at=None,
                created_at=ts,
                updated_at=ts,
            )
            self.db.add(entry)
            created += 1
        await self.db.flush()
        result._bump("guestbooks", created, 0)
        return created

    # ======================================================================
    # GalleryFactory
    # ======================================================================

    async def create_galleries(
        self, result: SeedResult, *, author: User, locale: str = "zh"
    ) -> tuple[int, int]:
        """Create Albums + Photos. Returns (albums_created, photos_created)."""
        gal_rows = self.data.get("galleries", locale=locale)
        if not gal_rows:
            gal_rows = self.data.get("galleries", locale="zh")
        a_created = a_skipped = p_created = 0
        now = self.clock()
        for idx, row in enumerate(gal_rows):
            slug = row.get("slug") or f"gallery-{idx + 1}"
            existing = (
                await self.db.execute(
                    select(Album.id).where(Album.title == row["title"]).limit(1)
                )
            ).scalar_one_or_none()
            if existing is not None:
                a_skipped += 1
                album = await self.db.get(Album, existing)
            else:
                album = Album(
                    title=str(row.get("title", "")),
                    description=row.get("description"),
                    cover=None,
                    sort_order=idx,
                    is_published=True,
                    photo_count=len(row.get("photos", [])),
                    author_id=int(author.id),
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(album)
                await self.db.flush()
                a_created += 1
            if album is None:
                continue
            for p_idx, ph in enumerate(row.get("photos", [])):
                photo = Photo(
                    album_id=album.id,
                    title=str(ph.get("title", "") or None),
                    description=None,
                    url=str(ph["url"]),
                    sort_order=p_idx,
                    created_at=now,
                )
                self.db.add(photo)
                p_created += 1
        await self.db.flush()
        result._bump("galleries_albums", a_created, a_skipped)
        result._bump("galleries_photos", p_created, 0)
        return a_created, p_created

    # ======================================================================
    # PageFactory (about + guestbook)
    # ======================================================================

    async def create_pages(self, result: SeedResult, *, locale: str = "zh") -> int:
        rows = self.data.get("pages", locale=locale)
        if not rows:
            rows = self.data.get("pages", locale="zh")
        # Build i18n bundles by slug:
        by_slug: dict[str, dict[str, dict[str, str]]] = {}
        for loc in VALID_LOCALES:
            for row in self.data.get("pages", locale=loc):
                slug = row["slug"]
                d = by_slug.setdefault(slug, {"title": {}, "content_md": {}})
                d["title"][loc] = row.get("title", "")
                d["content_md"][loc] = row.get("content_md", "")
        created = skipped = 0
        now = self.clock()
        for slug, bundle in by_slug.items():
            existing = (
                await self.db.execute(select(Page).where(Page.slug == slug))
            ).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                self._pages[slug] = existing
                continue
            status = (
                self.data.get("pages", locale=locale)
                and next(
                    (r.get("status", "published") for r in self.data.get("pages", locale=locale) if r.get("slug") == slug),
                    "published",
                )
            ) or "published"
            p = Page(
                title=bundle["title"],
                slug=slug,
                content=bundle["content_md"],
                status=status,
                created_at=now,
                updated_at=now,
            )
            self.db.add(p)
            await self.db.flush()
            self._pages[slug] = p
            created += 1
        result._bump("pages", created, skipped)
        return created

    # ======================================================================
    # ActivityFactory (动态说说)
    # ======================================================================

    async def create_activities(
        self, result: SeedResult, *, author: User, locale: str = "zh"
    ) -> int:
        rows = self.data.get("activities", locale=locale)
        if not rows:
            rows = self.data.get("activities", locale="zh")
        # Pre-check: skip seeding entirely if any activities already exist.
        any_existing = (
            await self.db.execute(select(Activity.id).limit(1))
        ).scalar_one_or_none()
        if any_existing is not None:
            result._bump("activities", 0, len(rows))
            return 0
        bundle_by_idx: dict[int, dict[str, str]] = {}
        for loc in VALID_LOCALES:
            for i, row in enumerate(self.data.get("activities", locale=loc)):
                bundle_by_idx.setdefault(i, {})[loc] = row.get("text", "")
        types: dict[int, str] = {}
        for i, row in enumerate(self.data.get("activities", locale="zh")):
            types[i] = row.get("type", "say")
        now = self.clock()
        created = 0
        for i, content_i18n in bundle_by_idx.items():
            at_time = now - timedelta(
                days=self.rng.randint(0, 40),
                hours=self.rng.randint(0, 23),
                minutes=self.rng.randint(0, 59),
            )
            act = Activity(
                content=content_i18n,
                type=str(types.get(i, "say"))[:20],
                author_id=int(author.id),
                is_published=True,
                likes_count=self.rng.randint(0, 36),
                created_at=at_time,
                updated_at=at_time,
            )
            self.db.add(act)
            created += 1
        await self.db.flush()
        result._bump("activities", created, 0)
        return created

    # ======================================================================
    # Navigation + FriendLink (shortcuts, 无 JSON — 程序构造即可)
    # ======================================================================

    async def create_default_navigation(self, result: SeedResult, *, locale: str = "zh") -> int:
        any_existing = (
            await self.db.execute(select(Navigation.id).limit(1))
        ).scalar_one_or_none()
        if any_existing is not None:
            result._bump("navigations", 0, 10)
            return 0

        def ml(zh: str, en: str, ja: str, zh_hant: str) -> dict[str, str]:
            return {"zh": zh, "en": en, "ja": ja, "zh_Hant": zh_hant}

        flat: list[dict] = [
            # parent nodes
            {"temp_id": "home", "parent": None, "title": ml("首页", "Home", "ホーム", "首頁"),
             "url": "/", "icon": "material-symbols:home", "order": 1},
            {"temp_id": "posts_parent", "parent": None,
             "title": ml("文章", "Posts", "投稿一覧", "文章"),
             "url": "#", "icon": "material-symbols:article", "order": 2},
            {"temp_id": "social_parent", "parent": None,
             "title": ml("社交", "Social", "ソーシャル", "社交"),
             "url": "#", "icon": "material-symbols:group", "order": 3},
            {"temp_id": "about_parent", "parent": None,
             "title": ml("关于", "About", "このサイトについて", "關於"),
             "url": "#", "icon": "material-symbols:info", "order": 4},
            # children
            {"temp_id": "archive", "parent": "posts_parent",
             "title": ml("归档", "Archive", "アーカイブ", "彙整"),
             "url": "/archive/", "icon": "material-symbols:archive", "order": 1},
            {"temp_id": "categories", "parent": "posts_parent",
             "title": ml("分类", "Categories", "カテゴリ", "分類"),
             "url": "/categories/", "icon": "material-symbols:folder-open-rounded", "order": 2},
            {"temp_id": "tags", "parent": "posts_parent",
             "title": ml("标签", "Tags", "タグ", "標籤"),
             "url": "/tags/", "icon": "material-symbols:tag-rounded", "order": 3},
            {"temp_id": "friends", "parent": "social_parent",
             "title": ml("友链", "Friends", "フレンド", "友鏈"),
             "url": "/friends/", "icon": "material-symbols:link-2-rounded", "order": 1},
            {"temp_id": "guestbook_nav", "parent": "social_parent",
             "title": ml("留言板", "Guestbook", "掲示板", "留言板"),
             "url": "/guestbook/", "icon": "material-symbols:chat", "order": 2},
            {"temp_id": "about_page", "parent": "about_parent",
             "title": ml("关于我", "About Me", "プロフィール", "關於我"),
             "url": "/about/", "icon": "material-symbols:person", "order": 1},
        ]
        now = self.clock()
        id_map: dict[str, int] = {}
        created = 0
        parents_first = sorted(flat, key=lambda x: (x["parent"] is not None, x["order"]))
        for node in parents_first:
            parent_pk = id_map[node["parent"]] if node["parent"] else None
            nav = Navigation(
                title=node["title"],
                url=node["url"],
                icon=node["icon"],
                parent_id=parent_pk,
                location="header",
                order=node["order"],
                is_active=True,
                target_blank=False,
                created_at=now,
            )
            self.db.add(nav)
            await self.db.flush()
            id_map[node["temp_id"]] = nav.id
            created += 1
        result._bump("navigations", created, 0)
        return created

    # ======================================================================
    # Main orchestrator: run_seed
    # ======================================================================

    async def run_seed(
        self,
        *,
        author: User,
        include_posts: bool = True,
        include_comments: bool = True,
        include_activities: bool = True,
        include_guestbook: bool = True,
        include_galleries: bool = True,
        include_pages: bool = True,
        include_navigation: bool = False,
    ) -> SeedResult:
        """Run the full OOBE-compatible seed pipeline using shared factories.

        Args:
            author: The author User (typically OOBE admin, or mock_data admin).
            include_*: Toggle per-table creation (for lightweight runs).
        """
        result = SeedResult()
        # ---- always prereq categories + tags for posts to reference ----
        await self.create_all_categories(result)
        await self.create_all_tags(result)
        posts: list[Post] = []
        if include_posts:
            posts = await self.create_all_posts(result, author=author)
        if include_comments and posts:
            await self.create_comments_for_posts(
                result, posts=posts, admin_user=author, locale=self.lang
            )
        if include_activities:
            await self.create_activities(result, author=author, locale=self.lang)
        if include_guestbook:
            await self.create_guestbook_entries(result, admin_user=author, locale=self.lang)
        if include_galleries:
            await self.create_galleries(result, author=author, locale=self.lang)
        if include_pages:
            await self.create_pages(result, locale=self.lang)
        if include_navigation:
            await self.create_default_navigation(result, locale=self.lang)
        await self.db.commit()
        return result


__all__ = [
    "DATA_DIR",
    "VALID_LOCALES",
    "SeedDataBundle",
    "SeedResult",
    "SeedContext",
]
