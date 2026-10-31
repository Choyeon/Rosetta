"""密码稿的「这篇要访问密码」一位在公开读面的往返契约（批次 #139）。

判据只有一处真源：详情口 ``bool(post.password)`` → ``is_password_protected``，
闸门据此出解锁界面。但**列表族以前不带这一位**，于是前台八个卡片渲染面
（列表 / 首页 / 热榜 / 归档三面 / 系列目录）一个信号都没有——读者的实际体验是
「卡片写着预计 4 分钟，点进去要密码」，而"要不要密码"恰恰是决定点不点进去的信息。

四件事必须同时成立，缺一条就是半只闸门：
1. 每个会显示分钟数的读面都带出 ``is_password_protected``，且取值与详情口同源；
2. **密码哈希绝不进任何公开载荷**——列表载荷被更多缓存键位复用，还会整份烘进
   SSR 的 ``__NUXT_DATA__``（探针用的哨兵串出现在响应文本里即失败）；
3. 文档模型一律给 ``False`` 默认值：这些响应进响应缓存，TTL 内的旧载荷没这个键，
   必填等于让整口 500（与 #120/#137/#138 同一口径）；
4. 详情页不得再对密码稿收起分钟数：元数据不是正文，日期与阅读量本来就在闸门
   上方给访客看——卡片显示 4 分钟、点进去什么都不显示，是同一族缺陷的另一半。
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Post
from backend.models.user import User

BACKEND = Path(__file__).resolve().parents[1] / "backend"
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

# 哨兵：一眼就能在响应文本里认出"哈希漏出去了"。真库里是 argon2id/bcrypt 摘要。
SENTINEL_HASH = "SENTINEL-PASSWORD-HASH-DO-NOT-LEAK"

PUBLISHED_AT = datetime(2001, 2, 3, 4, 5, tzinfo=timezone.utc)
YEAR, MONTH = 2001, 2


async def _mk_post(
    db_session: AsyncSession,
    test_user: User,
    *,
    slug: str,
    password: str | None = None,
    series_id: int | None = None,
) -> Post:
    post = Post(
        title={"zh": f"密码位测试 {slug}", "en": f"Lock Flag {slug}"},
        slug=slug,
        content={"zh": "正文内容" * 40, "en": "body text " * 40},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=test_user.id,
        status="published",
        visibility="public",
        published_at=PUBLISHED_AT,
        views=9,
        allow_comments=True,
        reading_time=6,
        password=password,
        series_id=series_id,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


def _unwrap(payload):
    if (
        isinstance(payload, dict)
        and "data" in payload
        and isinstance(payload["data"], (dict, list))
    ):
        return payload["data"]
    return payload


def _row_in_list(payload, slug: str) -> dict:
    body = _unwrap(payload)
    items = body.get("items") if isinstance(body, dict) else body
    found = [i for i in (items or []) if isinstance(i, dict) and i.get("slug") == slug]
    assert found, f"列表里没有 {slug}：{[i.get('slug') for i in (items or [])]}"
    return found[0]


def _row_in_groups(payload, slug: str) -> dict:
    body = _unwrap(payload)
    groups = body if isinstance(body, list) else []
    for group in groups:
        found = [p for p in (group.get("posts") or []) if p.get("slug") == slug]
        if found:
            return found[0]
    raise AssertionError(f"归档分组里没有 {slug}")


class TestFlagIsOnEveryReadingTimeSurface:
    """每一个会渲染分钟数 chip 的读口都必须带出这一位，否则那一面就是瞎的。"""

    @pytest.mark.asyncio
    async def test_post_list_distinguishes_locked_from_open(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        await _mk_post(db_session, test_user, slug="lock-list-on", password=SENTINEL_HASH)
        await _mk_post(db_session, test_user, slug="lock-list-off")
        await cache.clear()

        response = await client.get("/api/blog/posts", params={"page": 1, "page_size": 50})
        assert response.status_code == 200, response.text
        assert _row_in_list(response.json(), "lock-list-on")["is_password_protected"] is True
        assert _row_in_list(response.json(), "lock-list-off")["is_password_protected"] is False

    @pytest.mark.asyncio
    async def test_hot_and_ranking_outlets_carry_the_flag(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """综合榜（/blog/posts/hot）走列表模型、周期榜（/ranking/posts）自己搭 dict——两条路径各自一条断言。"""
        await _mk_post(db_session, test_user, slug="lock-hot", password=SENTINEL_HASH)
        await cache.clear()

        hot = await client.get("/api/blog/posts/hot", params={"limit": 50})
        assert hot.status_code == 200, hot.text
        assert _row_in_list(hot.json(), "lock-hot")["is_password_protected"] is True

        for period in ("all", "week"):
            await cache.clear()
            ranking = await client.get("/api/ranking/posts", params={"period": period, "limit": 50})
            assert ranking.status_code == 200, ranking.text
            row = _row_in_list(ranking.json(), "lock-hot")
            assert row["is_password_protected"] is True, f"{period} 榜没带出这一位"

    @pytest.mark.asyncio
    async def test_archive_three_surfaces_carry_the_flag(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """归档首页走**列级投影**（不实例化 Post，漏 select 列就拿不到值）；年页/月页各自手搭 dict。"""
        await _mk_post(db_session, test_user, slug="lock-archive", password=SENTINEL_HASH)

        await cache.clear()
        index = await client.get("/api/blog/archive")
        assert index.status_code == 200, index.text
        assert _row_in_groups(index.json(), "lock-archive")["is_password_protected"] is True

        for path in (f"/api/blog/archive/{YEAR}", f"/api/blog/archive/{YEAR}/{MONTH}"):
            await cache.clear()
            response = await client.get(path)
            assert response.status_code == 200, response.text
            body = _unwrap(response.json())
            if isinstance(body, dict) and "posts" in body:
                row = next(i for i in body["posts"] if i.get("slug") == "lock-archive")
            else:
                row = _row_in_groups(response.json(), "lock-archive")
            assert row["is_password_protected"] is True, f"{path} 没带出这一位"

    @pytest.mark.asyncio
    async def test_series_chapter_list_carries_the_flag(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        from backend.models.post_series import PostSeries

        series = PostSeries(
            title={"zh": "密码位系列", "en": "Lock Series"},
            slug="lock-series",
            is_active=True,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        await _mk_post(
            db_session,
            test_user,
            slug="lock-series-row",
            password=SENTINEL_HASH,
            series_id=series.id,
        )
        await cache.clear()

        response = await client.get("/api/series/lock-series")
        assert response.status_code == 200, response.text
        body = _unwrap(response.json())
        row = next(p for p in body["posts"] if p.get("slug") == "lock-series-row")
        assert row["is_password_protected"] is True

    @pytest.mark.asyncio
    async def test_detail_outlet_agrees_with_the_list(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """单源判据：卡片贴的锁徽标与详情页的密码闸门必须判同一批文章。"""
        await _mk_post(db_session, test_user, slug="lock-agrees", password=SENTINEL_HASH)
        await cache.clear()

        listing = await client.get("/api/blog/posts", params={"page": 1, "page_size": 50})
        row = _row_in_list(listing.json(), "lock-agrees")
        detail = await client.get("/api/blog/posts/lock-agrees")
        assert detail.status_code == 200, detail.text
        assert row["is_password_protected"] is True
        assert _unwrap(detail.json())["is_password_protected"] is True


class TestHashNeverLeaks:
    """存在性位就是存在性位：密码摘要不得以任何形态出现在公开载荷里。

    列表族只产出布尔；详情口的 `PostLocalizedResponse.password` 虽在模型里声明，
    两个构造点都不填它——这条断言钉住的是"哪天有人顺手 `password=post.password`"。
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/api/blog/posts?page=1&page_size=50",
            "/api/blog/posts/hot?limit=50",
            "/api/ranking/posts?period=all&limit=50",
            "/api/blog/archive",
            "/api/blog/posts/lock-leak",
        ],
    )
    async def test_sentinel_hash_absent_from_every_outlet(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, path: str
    ):
        await _mk_post(db_session, test_user, slug="lock-leak", password=SENTINEL_HASH)
        await cache.clear()

        response = await client.get(path)
        assert response.status_code == 200, response.text
        # 键真的在载荷里（否则"没有泄漏"只是因为这一口压根没跑到）
        assert "is_password_protected" in response.text, f"{path} 没带出这一位"
        assert SENTINEL_HASH not in response.text, f"{path} 把密码哈希带出去了"
        if path.startswith("/api/blog/posts/lock-leak"):
            assert _unwrap(response.json()).get("password") is None


class TestDocModelsDegradeGracefully:
    """旧缓存载荷缺这个键时不能整口 500——四个模型一律给 False 默认值。"""

    def test_every_declared_model_defaults_to_false(self):
        from backend.api.post_series import SeriesPostItemDoc
        from backend.api.ranking import HotPostItemDoc
        from backend.schemas import PostListItemLocalized
        from backend.schemas.blog_reads import ArchivePostItem

        for model in (PostListItemLocalized, ArchivePostItem, SeriesPostItemDoc, HotPostItemDoc):
            field = model.model_fields["is_password_protected"]
            assert field.default is False, model.__name__
            assert field.is_required() is False, model.__name__

    def test_projection_single_source_is_used_at_every_site(self):
        """判据散写＝早晚分叉；`bool(post.password)` 只准出现在单源 helper 与 from_post 里。"""
        helpers = (BACKEND / "services" / "post_access.py").read_text(encoding="utf-8")
        assert "def access_flags(" in helpers
        assert "def post_access_flags(" in helpers
        assert '"is_password_protected": bool(password)' in helpers

        for rel in ("api/blog.py", "api/ranking.py"):
            src = (BACKEND / rel).read_text(encoding="utf-8")
            assert "post_access_flags(" in src, rel
        for rel in ("api/post_series.py", "repositories/post.py"):
            src = (BACKEND / rel).read_text(encoding="utf-8")
            assert "access_flags(password=" in src, rel

        # 列投影取的是 Post.password 这一列，行 dict 里绝不落它的值
        repos = (BACKEND / "repositories" / "post.py").read_text(encoding="utf-8")
        assert re.search(r"Post\.password,\n", repos)
        assert '"password":' not in repos


class TestFrontendContract:
    """徽标必须挂在每一个会显示分钟数的渲染面，且详情页不再对密码稿收起分钟数。"""

    SURFACES = (
        "components/PostCard.vue",
        "pages/archive/index.vue",
        "pages/archive/[year]/index.vue",
        "pages/archive/[year]/[month].vue",
        "pages/series/[slug].vue",
    )

    @pytest.mark.parametrize("rel", SURFACES)
    def test_surface_renders_the_badge_and_allows_the_key(self, rel: str):
        src = (FRONTEND / rel).read_text(encoding="utf-8")
        # 分钟数 chip 有几处，锁徽标就得有几处（同一行元数据，缺一处就是那一列没有标记）
        assert src.count("<PostReadingTime :post=") == src.count("<PostLockBadge :post=") > 0, rel
        assert "import PostLockBadge from '~~/components/PostLockBadge.vue'" in src, rel
        assert "is_password_protected?: boolean | null" in src, rel

    def test_badge_only_uses_the_existence_bit(self):
        src = (FRONTEND / "components" / "PostLockBadge.vue").read_text(encoding="utf-8")
        assert "props.post.is_password_protected === true" in src
        # 不读密码、不读正文：这一位的全部职责是"要不要密码"
        assert "post.password" not in src

    def test_detail_page_no_longer_hides_minutes_for_locked_posts(self):
        src = (FRONTEND / "pages" / "posts" / "[slug].vue").read_text(encoding="utf-8")
        block = src.split("const readingTime = computed")[1].split("})")[0]
        assert "needPassword" not in block, "详情页又对密码稿收起了分钟数（与卡片不同口径）"
        assert "post.value?.reading_time" in block

    def test_hot_page_forwards_the_flag_to_the_card(self):
        src = (FRONTEND / "pages" / "posts" / "hot.vue").read_text(encoding="utf-8")
        assert "is_password_protected: row.is_password_protected ?? null" in src
