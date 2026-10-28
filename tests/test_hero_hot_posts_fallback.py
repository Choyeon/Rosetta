"""Hero 轮播兜底 = 高热度文章（不再抓 Bing）。

契约（2026-10 改动）：
1. `backend/api/hero.py` 不得出现任何站外抓取（Bing 壁纸只服务登录/注册页）。
2. DB 无生效轮播时，公开口用近 30 天热榜文章填充：负 ID、无封面回落按文章标识派生的
   picsum seed 展示面随机图（与 frontend/lib/post-cover.ts 同口径；og:image 侧仍是
   站内默认 OG 图，两者不同源互不影响）、
   CTA 指向文章详情的中性路径（语言前缀由前端负责）。
3. 存在生效轮播时，绝不查询热榜兜底——DB 记录优先。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

HERO_SOURCE = Path(__file__).resolve().parent.parent / "backend" / "api" / "hero.py"


class _FakePost:
    """热榜返回的 Post 形状替身（只用到映射里真实读取的字段）。"""

    def __init__(self, pid: int, slug: str, cover: str | None) -> None:
        self.id = pid
        self.slug = slug
        self.title = {"zh": f"热门文章 {pid}", "en": f"Hot post {pid}"}
        self.excerpt = {"zh": "  摘要正文  ", "en": "  excerpt text  "}
        self.cover_image = cover
        self.created_at = datetime(2026, 1, 1)


@pytest.mark.asyncio
async def test_hero_module_has_no_upstream_fetch() -> None:
    """hero 侧不得再出现自有或委托的 Bing 抓取。"""
    source = HERO_SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        "AsyncClient",
        "HTTP_PROXY",
        "import httpx",
        "HPImageArchive",
        "get_bing_wallpapers",
        "enable_bing_wallpaper",
    ):
        assert forbidden not in source, f"hero.py 不应再引用 Bing：{forbidden}"
    assert "get_hot_posts" in source, "hero.py 的兜底内容源必须是热榜文章"


@pytest.mark.asyncio
async def test_hero_slides_fall_back_to_hot_posts(
    client: AsyncClient,
    monkeypatch,
) -> None:
    """DB 无轮播 → 兜底轮播来自热榜文章。"""
    from backend.services.recommendation import RecommendationService

    posts = [_FakePost(11, "hot-eleven", None), _FakePost(12, "hot-twelve", "/media/12.jpg")]

    async def _fake_hot(self, limit: int = 10, days: int = 30) -> list:
        return posts[:limit]

    monkeypatch.setattr(RecommendationService, "get_hot_posts", _fake_hot)

    resp = await client.get("/api/hero/slides", params={"lang": "zh"})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    assert all(row["id"] < 0 for row in rows), "兜底项必须用负 ID，不与 DB 主键撞"
    assert rows[0]["title"] == "热门文章 11"
    assert rows[0]["subtitle"] == "摘要正文"
    # 没封面时回落 picsum seed 展示面随机图（seed=rosetta-post-<id>，与前端同口径），有封面用封面
    assert rows[0]["media_url"] == "https://picsum.photos/seed/rosetta-post-11/1200/800"
    assert rows[1]["media_url"] == "/media/12.jpg"
    assert rows[0]["cta_url"] == "/posts/hot-eleven"
    assert [row["sort_order"] for row in rows] == [0, 1]
    # 兜底行的底图是文章封面（深底亮底都有），色调必须显式给 light：前端拿到 undefined
    # 只能自己猜一个缺省，等于把这条路径的观感交给两处代码各写一遍。
    assert all(row["text_color"] == "light" for row in rows), "兜底项的文字色调缺声明"


@pytest.mark.asyncio
async def test_hero_slides_localize_by_lang(
    client: AsyncClient,
    monkeypatch,
) -> None:
    """同一篇文章在 en 请求下给出英文标题——兜底轮播不得硬锁中文。"""
    from backend.services.recommendation import RecommendationService

    async def _fake_hot(self, limit: int = 10, days: int = 30) -> list:
        return [_FakePost(21, "hot-twentyone", None)][:limit]

    monkeypatch.setattr(RecommendationService, "get_hot_posts", _fake_hot)

    rows = (await client.get("/api/hero/slides", params={"lang": "en"})).json()
    assert rows[0]["title"] == "Hot post 21"
    assert rows[0]["subtitle"] == "excerpt text"


@pytest.mark.asyncio
async def test_db_slides_take_priority_over_fallback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """配了真实轮播就绝不该再算热榜兜底。"""
    from backend.models.hero import HeroSlide
    from backend.services.recommendation import RecommendationService

    async def _boom(self, limit: int = 10, days: int = 30) -> list:
        raise AssertionError("存在生效轮播时不得走热榜兜底")

    monkeypatch.setattr(RecommendationService, "get_hot_posts", _boom)

    db_session.add(
        HeroSlide(
            title="真实轮播",
            media_type="image",
            media_url="/media/hero.jpg",
            is_active=True,
            sort_order=1,
        )
    )
    await db_session.flush()
    await db_session.commit()

    rows = (await client.get("/api/hero/slides")).json()
    assert len(rows) == 1
    assert rows[0]["id"] > 0
    assert rows[0]["title"] == "真实轮播"
