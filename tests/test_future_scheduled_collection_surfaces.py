"""「定时未到」判据在其余匿名集合口的落点回归（批次 #32）。

`status == "published"` 是定时发布落库时的写法（`blog.py` 里 scheduled 分支就是
"status 先转 published + published_at 给未来时间"），所以**只圈 status 的集合口会在到点前
就把卡片发出去**，而详情端点判的是 404——用户看到的症状是"列表里有、点进去 404"，
sitemap 那条更糟：爬虫按 404 收一次 URL。

批次 #31 只把判据落到 `RecommendationService`（推荐 / 热榜 / 相似），这一轮把它推到
其余匿名集合口：sitemap、RSS、排行、系列章节、作者归档、年度/月度归档、预热口。
做法是把这些点原先手写的 `Post.status == "published", private_posts_excluded()` 这一对
统一换成单源谓词 `publicly_listable_posts()`（= status + 排私密 + 定时未到）。

三条守卫缺一不可：
- 行为守卫（下面的 surfaces 循环）证明换完真的挡住了，且 `due` 同批在场（防"整口变空"假绿）；
- 反向守卫证明后台仍能看到定时稿——收紧只针对匿名视角；
- 静态守卫证明这次清扫**没有留下手写的那一对**——漏一处的表现不是报错，而是某个周末
  定时稿悄悄出现在 sitemap 里，所以白名单里只允许几处**各有正当理由**的例外。

热榜/推荐/相似不在本文件的 surfaces 里：那一族缓存的是 **id 名单**，命中后靠回源过滤收敛，
`days` / `limit` 键位一换就可能拿到上一轮的旧名单，断言会退化成"赌缓存键位"。它的口径由
`test_recommendation_visibility_rebuild.py` 钉（那里直接操作名单，能证明过滤真的发生在回源那次 SELECT）。

响应缓存（`posts:*` / `archive:*` / `seo:sitemap`）在被 fixture 写行之前可能已被别的用例暖好，
所以每次打口前先清一遍——否则"due 不在场"会是一次假红，而"future 不在场"会是一次假绿。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import invalidate_cache
from backend.models.blog import Post
from backend.models.post_series import PostSeries
from backend.models.user import User
from backend.utils.compat import UTC

pytestmark = pytest.mark.asyncio

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

# 允许继续手写这一对的地方（唯一清单）：
# - post_access.py：谓词本体的定义；
# - blog.py 上下篇：它比的是 `published_key`（coalesce 后的排序键）而不是列本身，
#   换成单源谓词会多一条冗余条件、却拿不到更严的判据，所以保留原样；
# - favorite.py：这里用的是 Python 侧的 naive `now_naive`（生产 PG 与测试 SQLite 的
#   时区口径不同），刻意不走 `func.now()`。
HANDROLLED_ALLOWLIST = {
    "services/post_access.py": 2,
    "api/blog.py": 1,
    "api/favorite.py": 1,
}

PAIR_RE = re.compile(r"Post\.status\s*==\s*\"published\"[^\n]*private_posts_excluded\(\)")
PRIVATE_CALL_RE = re.compile(r"private_posts_excluded\(\)")
LISTER_RE = re.compile(r"publicly_listable_posts\(\)")


def _slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def _mk(
    db: AsyncSession,
    author_id: int,
    *,
    category_id: int,
    series_id: int,
    views: int,
    published_at: datetime,
    prefix: str,
) -> Post:
    name = _slug(prefix)
    post = Post(
        title={"zh": name, "en": name},
        slug=name,
        content={"zh": "定时未到集合口回归正文。", "en": "future scheduling gate body"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=author_id,
        category_id=category_id,
        series_id=series_id,
        status="published",
        visibility="public",
        views=views,
        published_at=published_at,
        allow_comments=True,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


def _collect_slugs(node: object, found: set[str]) -> None:
    """递归收集响应体里所有 `slug`——各口的字段形态不同，按形态写七份解析反而会漏。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "slug" and isinstance(value, str):
                found.add(value)
            else:
                _collect_slugs(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect_slugs(item, found)


async def _json_slugs(client: AsyncClient, path: str) -> tuple[int, set[str]]:
    response = await client.get(path)
    if response.status_code != 200:
        return response.status_code, set()
    found: set[str] = set()
    _collect_slugs(response.json(), found)
    return 200, found


async def _raw(client: AsyncClient, path: str) -> tuple[int, str]:
    response = await client.get(path)
    return response.status_code, response.text


@pytest.fixture
async def series(db_session: AsyncSession) -> PostSeries:
    row = PostSeries(
        title={"zh": "定时回归系列", "en": "scheduling gate series"},
        slug=_slug("sgseries"),
        is_active=True,
        sort_order=0,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest.fixture
async def pair(
    db_session: AsyncSession, test_user: User, test_category, series: PostSeries
) -> tuple[Post, Post]:
    """同一作者、同一分类、同一系列、同样高浏览量的一对：只差"到没到点"。

    其余维度全部相同，才让"某口里 future 在场 / due 不在场"无法被算法权重、分类开关
    之类的旁路解释掉。
    """
    now = datetime.now(UTC)
    future = await _mk(
        db_session,
        test_user.id,
        category_id=test_category.id,
        series_id=series.id,
        views=9_999,
        published_at=now + timedelta(days=2),
        prefix="sgfuture",
    )
    due = await _mk(
        db_session,
        test_user.id,
        category_id=test_category.id,
        series_id=series.id,
        views=9_998,
        published_at=now - timedelta(hours=1),
        prefix="sgdue",
    )
    # 这几族的缓存键只由语言/分页/周期构成，不带"本用例刚写了什么"，旧值会原样回放给断言。
    for pattern in ("posts", "archive", "seo"):
        await invalidate_cache(pattern)
    return future, due


class TestCollectionSurfaces:
    async def test_future_scheduled_post_absent_from_every_anonymous_surface(
        self, client: AsyncClient, pair: tuple[Post, Post], test_user: User, series: PostSeries
    ) -> None:
        """每个匿名集合口都必须"没有 future、有 due"——后半个断言是防整口变空的假绿。"""
        future, due = pair
        year = due.published_at.year

        surfaces = {
            "post-list": "/api/blog/posts?page=1&page_size=200&lang=zh",
            "ranking": "/api/ranking/posts?period=all&limit=50",
            "author-archive": f"/api/users/{test_user.id}/posts?page=1&page_size=100",
            "series-chapters": f"/api/series/{series.slug}",
            "archive": "/api/blog/archive?lang=zh",
            "archive-year": f"/api/blog/archive/{year}?lang=zh",
        }
        for name, path in surfaces.items():
            status, slugs = await _json_slugs(client, path)
            assert status == 200, f"{name} → HTTP {status}"
            assert due.slug in slugs, f"{name} 连已到点的文章都不在场，断言退化成空集合"
            assert future.slug not in slugs, f"{name} 在到点前就把定时稿发出去了"

    async def test_future_absent_from_sitemap_and_rss(
        self, client: AsyncClient, pair: tuple[Post, Post]
    ) -> None:
        """爬虫面：sitemap / RSS 里出现定时未到的 URL，等于让抓取器收一串 404。"""
        future, due = pair
        xml_paths = (
            "/api/seo/sitemap.xml",
            "/api/blog/sitemap-posts.xml",
            # RSS 默认只给 20 条且按发布时间倒序，测试库里若有更多文章会把 due 挤出窗口；
            # 上限 100 让"在场"这条断言不依赖库里恰好有多少别的文章。
            "/api/blog/rss?limit=100",
        )
        # /api/blog/sitemap.xml 是**索引**（只列子表 URL，不含文章 slug），不在这里断言；
        # 它按 publicly_listable_posts() 计数分页，由静态守卫覆盖。
        for path in xml_paths:
            status, text = await _raw(client, path)
            assert status == 200, f"{path} → HTTP {status}"
            assert due.slug in text, f"{path} 没有已到点的文章，在场断言是空转"
            assert future.slug not in text, f"{path} 把未到点的定时稿交给了爬虫"

    async def test_detail_keeps_the_same_stance_as_the_collections(
        self, client: AsyncClient, pair: tuple[Post, Post]
    ) -> None:
        """判据换了集合口，详情口这一侧的口径不能跟着漂：未到点匿名一律 404。"""
        future, due = pair
        assert (await client.get(f"/api/blog/posts/{future.slug}")).status_code == 404
        assert (await client.get(f"/api/blog/posts/{due.slug}")).status_code == 200

    async def test_future_visible_to_staff_listing(
        self, client: AsyncClient, pair: tuple[Post, Post], admin_headers: dict
    ) -> None:
        """反向闸门：收紧判据只针对匿名视角，后台列表与导出仍要能看到定时稿。"""
        future, _ = pair
        response = await client.get(
            "/api/blog/posts?status=all&page_size=200", headers=admin_headers
        )
        assert response.status_code == 200, response.text
        found: set[str] = set()
        _collect_slugs(response.json().get("data", response.json()), found)
        assert future.slug in found, "后台看不到自己的定时稿＝这批文章凭空失踪，作者会重复发帖"


class TestSingleSourceGuard:
    def test_no_handrolled_visibility_pair_left(self) -> None:
        """手写那一对的唯一清单就是上面的白名单——新增一处即红，防止"漏一条判据"回到代码里。"""
        counts: dict[str, int] = {}
        for path in BACKEND_DIR.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            hits = len(PRIVATE_CALL_RE.findall(text)) + len(PAIR_RE.findall(text))
            if hits:
                counts[str(path.relative_to(BACKEND_DIR)).replace("\\", "/")] = hits
        assert counts == HANDROLLED_ALLOWLIST, (
            f"匿名集合口请直接用 publicly_listable_posts()；实到 {counts}"
        )

    def test_shared_predicate_is_actually_wired_in(self) -> None:
        """单源谓词必须真的被这些文件用上（只删不接会把判据删没，而不是收紧）。"""
        users: set[str] = set()
        for path in BACKEND_DIR.rglob("*.py"):
            if LISTER_RE.search(path.read_text(encoding="utf-8")):
                users.add(str(path.relative_to(BACKEND_DIR)).replace("\\", "/"))
        expected = {
            "api/blog.py",
            "api/post_series.py",
            "api/ranking.py",
            "api/seo.py",
            "api/users.py",
            "core/cache_warmer.py",
            "repositories/post.py",
            "services/post_access.py",
            "services/recommendation.py",
        }
        assert expected <= users, f"这些文件没接上单源谓词：{sorted(expected - users)}"
