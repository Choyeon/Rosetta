"""
Hero 轮播的 Bing 壁纸兜底必须复用全站唯一那份「已缓存」抓取实现。

历史上 backend/api/hero.py 自带一份 httpx 直连 Bing 的代码（另一域名、15s 超时、
模块级全局兜底、不进响应缓存）。后果：
  · /api/hero/slides 是公开端点，默认安装（DB 无轮播）下每个访客请求都触发一次站外 HTTP；
  · Bing 不可达时没有任何负缓存，重试没有上界；
  · 首页壁纸与 hero 各打各的上游，同一小时内对 Bing 重复取同一份数据。

本文件把这三条钉住：hero 侧不得再出现自有上游抓取；两次请求只打一次上游；
上游故障的空结果同样只打一次。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

HERO_SOURCE = Path(__file__).resolve().parent.parent / "backend" / "api" / "hero.py"


def _fake_bing_payload(count: int = 3) -> dict:
    return {
        "images": [
            {
                "url": f"/th-abcdef{i}-1920x1080.jpg",
                "urlbase": f"/th-abcdef{i}",
                "title": f"壁纸标题 {i}",
                "copyright": f"© 作者 {i}",
                "copyrightlink": "https://example.com",
                "startdate": "20260926",
                "enddate": "20260927",
            }
            for i in range(count)
        ]
    }


@pytest.mark.asyncio
async def test_hero_module_has_no_own_upstream_fetch() -> None:
    """hero.py 不得自带 Bing 上游抓取（防止重复实现再次长回来）。"""
    source = HERO_SOURCE.read_text(encoding="utf-8")
    for forbidden in ("AsyncClient", "HPImageArchive", "HTTP_PROXY", "import httpx"):
        assert forbidden not in source, f"hero.py 不应再出现自有抓取代码：{forbidden}"
    assert "get_bing_wallpapers" in source, "hero.py 必须委托 bing 侧共享端点"


@pytest.mark.asyncio
async def test_hero_slides_hit_bing_upstream_only_once(
    client: AsyncClient,
    monkeypatch,
) -> None:
    """DB 无轮播 → 兜底虚拟轮播；两次请求只应对 Bing 发起一次抓取。"""
    from backend.api import bing as bing_api

    calls: list[tuple] = []

    async def _fake_fetch(market: str = "zh-CN", n: int = 1) -> dict:
        calls.append((market, n))
        return _fake_bing_payload(n)

    monkeypatch.setattr(bing_api, "_fetch_bing_wallpaper", _fake_fetch)

    first = await client.get("/api/hero/slides")
    second = await client.get("/api/hero/slides")
    assert first.status_code == 200
    assert second.status_code == 200

    rows = first.json()
    assert isinstance(rows, list) and len(rows) == 8
    # 负 ID = 虚拟轮播标记，不得与 DB 主键撞
    assert all(row["id"] < 0 for row in rows)
    assert rows[0]["media_url"].startswith("https://cn.bing.com")
    assert rows[0]["title"] == "壁纸标题 0"
    assert rows[0]["subtitle"] == "© 作者 0"
    def _key(row: dict) -> tuple:
        return (row["id"], row["title"], row["media_url"], row["sort_order"])

    assert [_key(r) for r in second.json()] == [_key(r) for r in rows], (
        "兜底结果应命中共享缓存，返回同一份壁纸数据"
    )
    assert len(calls) == 1, f"上游应只被调用一次，实际 {len(calls)} 次"


@pytest.mark.asyncio
async def test_bing_unreachable_empty_result_is_cached(
    client: AsyncClient,
    monkeypatch,
) -> None:
    """上游不可达时返回空列表，且空结果被短缓存——不得每个请求都重试外呼。"""
    from backend.api import bing as bing_api

    calls: list[int] = []

    async def _fake_fetch(market: str = "zh-CN", n: int = 1) -> dict:
        calls.append(n)
        return {}

    monkeypatch.setattr(bing_api, "_fetch_bing_wallpaper", _fake_fetch)

    hero = await client.get("/api/hero/slides")
    assert hero.status_code == 200
    assert hero.json() == []

    listing = await client.get("/api/bing/wallpapers", params={"n": 8})
    assert listing.status_code == 200
    assert listing.json()["images"] == []

    assert len(calls) == 1, f"空结果应进缓存，实际每次请求都打了上游：{len(calls)} 次"


@pytest.mark.asyncio
async def test_db_slides_take_priority_over_bing_fallback(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """配了真实轮播就绝不该再碰 Bing —— 兜底只在「无生效轮播」时生效。"""
    from backend.api import bing as bing_api
    from backend.models.hero import HeroSlide

    async def _boom(market: str = "zh-CN", n: int = 1) -> dict:
        raise AssertionError("存在生效轮播时不得抓取 Bing")

    monkeypatch.setattr(bing_api, "_fetch_bing_wallpaper", _boom)

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

    resp = await client.get("/api/hero/slides")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["id"] > 0
    assert rows[0]["title"] == "真实轮播"
