"""Bing 归档口（``GET /api/bing/image/archive``）与今日口的批次判据守卫。

这批判据全部来自 2026-10-31 的线上实测：上游 ``n=14`` 只回 8 条，而 ``idx`` 越过保留窗口后
**重复返回最旧那一张**（同 ``urlbase``）。旧的逐日串行实现因此有三个可观测缺陷：
每次外发请求打 14 个串行请求、最旧那张图被复制成多张卡片、每张卡片各自按
``date.today() - timedelta(idx)`` 编一个和上游不一致的日期。

这里用打桩的上游客户端与打桩的缓存，把「一次批量请求 / 上游日期 / 去重 / 缓存判别位 /
空结果不缓存 / 异常不 5xx」逐个钉住——不打真实网络，也不依赖被测当天上游到底有几条。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _bing_setup(monkeypatch, tmp_path):
    """OOBE 锁 + 限流打桩：本族端点是公开无鉴权口，套上既有 catch-all 会误判成 429。"""
    from backend.core import config as _cfg
    from backend.core import deps as _deps
    from backend.core.rate_limit import (
        SENSITIVE_ENDPOINT_RULE,
        WRITE_ENDPOINT_RULE,
        rate_limiter,
    )

    lock_file = tmp_path / ".oobe_complete"
    cfg_file = tmp_path / "rosetta.json"
    lock_file.write_text("1", encoding="utf-8")
    cfg_file.write_text("{}", encoding="utf-8")

    real_base = Path(__file__).resolve().parent.parent
    real_lock = real_base / ".oobe_complete"
    real_cfg = real_base / "rosetta.json"
    prev_lock = real_lock.exists()
    prev_cfg = real_cfg.exists()
    prev_lock_text = real_lock.read_text(encoding="utf-8") if prev_lock else None
    prev_cfg_text = real_cfg.read_text(encoding="utf-8") if prev_cfg else None
    if not prev_lock:
        real_lock.write_text("1", encoding="utf-8")
    if not prev_cfg:
        real_cfg.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(SENSITIVE_ENDPOINT_RULE, "requests", 10_000)
    monkeypatch.setattr(WRITE_ENDPOINT_RULE, "requests", 10_000)
    monkeypatch.setattr(_cfg.settings, "rate_limit_sensitive_requests", 10_000)
    monkeypatch.setattr(_cfg.settings, "rate_limit_write_requests", 10_000)

    from backend.core.rate_limit import RateLimitResult

    async def _always_allowed(*args, **kwargs):
        import time

        return RateLimitResult(
            allowed=True,
            limit=999_999,
            remaining=999_999,
            reset_at=time.time() + 3600,
            retry_after=0,
        )

    monkeypatch.setattr(rate_limiter, "check_rate_limit", _always_allowed)
    monkeypatch.setattr(_deps, "OOBE_LOCK_FILE", lock_file)
    monkeypatch.setattr(_deps, "CONFIG_FILE", cfg_file)

    yield

    try:
        if not prev_lock:
            real_lock.unlink()
        elif prev_lock_text is not None:
            real_lock.write_text(prev_lock_text, encoding="utf-8")
        if not prev_cfg:
            real_cfg.unlink()
        elif prev_cfg_text is not None:
            real_cfg.write_text(prev_cfg_text, encoding="utf-8")
    except OSError:
        pass


# ==================== 上游与缓存打桩 ====================


def _image(startdate: object = "20261030", urlbase: object = "/th?id=OHR.a", **extra) -> dict:
    row = {
        "startdate": startdate,
        "urlbase": urlbase,
        "title": "示例标题",
        "copyright": "© 示例",
        "copyrightlink": "https://www.bing.com/example",
    }
    row.update(extra)
    return row


class _StubResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"upstream {self.status_code}")


class _StubClient:
    """记录每一次 ``client.get``，并可按调用序号抛错/回非 200。"""

    def __init__(
        self, recorder: dict, images: list | None, *, fail: bool = False, status: int = 200
    ) -> None:
        self._recorder = recorder
        self._images = images
        self._fail = fail
        self._status = status

    async def __aenter__(self) -> _StubClient:
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def get(self, url: str, params: dict | None = None, **kwargs) -> _StubResponse:
        self._recorder["calls"].append({"url": url, "params": dict(params or {})})
        if self._fail:
            raise RuntimeError("upstream unreachable")
        # 真实上游只按 ``n`` 给条数，桩也照此截断：这样 count 才能证明缓存键确实分开了 days。
        asked = int((params or {}).get("n") or 0)
        return _StubResponse({"images": (self._images or [])[:asked]}, status_code=self._status)


@pytest.fixture
def stub(monkeypatch):
    """把 ``bing_image`` 的上游客户端与缓存替换成可观测的桩。"""
    from backend.api import bing_image as mod

    recorder: dict = {"calls": []}
    store: dict = {}
    sets: list = []

    state = {"images": None, "fail": False, "status": 200}

    def _install(images: list | None, *, fail: bool = False, status: int = 200) -> dict:
        state["images"] = images
        state["fail"] = fail
        state["status"] = status
        return recorder

    class _FakeCache:
        async def get(self, key: str):
            recorder.setdefault("gets", []).append(key)
            return store.get(key)

        async def set(self, key: str, value, ttl: int | None = None) -> bool:
            sets.append({"key": key, "value": value, "ttl": ttl})
            store[key] = value
            return True

    monkeypatch.setattr(
        mod,
        "create_async_client",
        lambda *a, **kw: _StubClient(
            recorder, state["images"], fail=state["fail"], status=state["status"]
        ),
    )
    monkeypatch.setattr(mod, "cache", _FakeCache())
    return {"recorder": recorder, "store": store, "sets": sets, "install": _install}


# ==================== 归档口 ====================


@pytest.mark.asyncio
async def test_archive_makes_one_batched_upstream_request(client: AsyncClient, stub):
    """days=14 也只打一次上游，且 ``n`` 被钳到上游真实保留窗口。"""
    from backend.api.bing_image import UPSTREAM_RETENTION_DAYS

    images = [_image(startdate=f"202610{20 + i:02d}", urlbase=f"/th?id=OHR.{i}") for i in range(8)]
    stub["install"](images)

    response = await client.get("/api/bing/image/archive", params={"days": 14})
    assert response.status_code == 200
    calls = stub["recorder"]["calls"]
    assert len(calls) == 1, f"归档必须一次批量取回，实际外发 {len(calls)} 次"
    assert calls[0]["params"]["n"] == min(14, UPSTREAM_RETENTION_DAYS)
    assert calls[0]["params"]["idx"] == 0

    body = response.json()
    assert body["count"] == len(body["data"]) == 8


@pytest.mark.asyncio
async def test_archive_dates_come_from_upstream_startdate(client: AsyncClient, stub):
    """每条日期是上游 ``startdate`` 归一出来的，不是服务器时钟倒推。"""
    from datetime import date

    stub["install"]([_image(startdate="20260405", urlbase="/th?id=OHR.only")])
    body = (await client.get("/api/bing/image/archive", params={"days": 1})).json()
    entry = body["data"][0]
    assert entry["date"] == "2026-04-05"
    assert entry["date"] != date.today().isoformat()
    assert entry["url"] == "https://cn.bing.com/th?id=OHR.only_1920x1080.jpg"
    assert entry["url_uhd"] == "https://cn.bing.com/th?id=OHR.only_UHD.jpg"
    assert entry["copyright_url"] == "https://www.bing.com/example"


@pytest.mark.asyncio
async def test_archive_drops_entries_without_upstream_date_or_base(client: AsyncClient, stub):
    """缺 ``startdate`` 或缺 ``urlbase`` 的条目丢弃，而不是编个日期留成脏卡片。"""
    stub["install"](
        [
            _image(startdate="", urlbase="/th?id=OHR.nodate"),
            _image(startdate="2026102", urlbase="/th?id=OHR.badformat"),
            _image(startdate="20261340", urlbase="/th?id=OHR.badday"),
            _image(startdate="20261021", urlbase=""),
            _image(startdate="20261020", urlbase="/th?id=OHR.good"),
            "not-a-dict",
        ]
    )
    body = (await client.get("/api/bing/image/archive", params={"days": 5})).json()
    assert [e["date"] for e in body["data"]] == ["2026-10-20"]


@pytest.mark.asyncio
async def test_archive_dedupes_repeated_urlbase(client: AsyncClient, stub):
    """上游越过窗口时重复同一张图（实测 idx=9 与窗口末条同 urlbase）只留一张卡。"""
    stub["install"](
        [
            _image(startdate="20261024", urlbase="/th?id=OHR.oldest"),
            _image(startdate="20261023", urlbase="/th?id=OHR.oldest"),
            _image(startdate="20261022", urlbase="/th?id=OHR.oldest"),
        ]
    )
    body = (await client.get("/api/bing/image/archive", params={"days": 3})).json()
    assert body["count"] == 1
    assert body["data"][0]["date"] == "2026-10-24", "去重保留上游顺序里的第一条"


@pytest.mark.asyncio
async def test_archive_cache_hit_never_touches_upstream(client: AsyncClient, stub):
    """第二次同 days 的请求命中缓存：归档每天只变一次，不该每个访客都打 Bing。"""
    stub["install"]([_image(startdate="20261020", urlbase="/th?id=OHR.x")])
    first = (await client.get("/api/bing/image/archive", params={"days": 7})).json()
    second = (await client.get("/api/bing/image/archive", params={"days": 7})).json()
    assert len(stub["recorder"]["calls"]) == 1
    assert second == first
    assert stub["sets"][0]["ttl"] and stub["sets"][0]["ttl"] > 0


@pytest.mark.asyncio
async def test_archive_cache_key_carries_days(client: AsyncClient, stub):
    """判别位进了查询参数就必须进缓存键——否则 days=3 会回放 days=7 的整段窗口。"""
    images = [
        _image(startdate=f"202610{d:02d}", urlbase=f"/th?id=OHR.{d}") for d in range(28, 20, -1)
    ]
    stub["install"](images)
    three = (await client.get("/api/bing/image/archive", params={"days": 3})).json()
    seven = (await client.get("/api/bing/image/archive", params={"days": 7})).json()
    assert len(stub["recorder"]["calls"]) == 2, "不同 days 必须各自回源"
    keys = [entry["key"] for entry in stub["sets"]]
    assert len(set(keys)) == 2, f"缓存键必须区分 days：{keys}"
    assert three["count"] == 3, [e["date"] for e in three["data"]]
    assert seven["count"] == 7


@pytest.mark.asyncio
async def test_archive_empty_result_is_not_cached(client: AsyncClient, stub):
    """一次上游故障不能把空归档钉住一小时。"""
    stub["install"]([], fail=True)
    body = (await client.get("/api/bing/image/archive", params={"days": 7})).json()
    assert body == {"success": True, "data": [], "count": 0}
    assert stub["sets"] == []
    await client.get("/api/bing/image/archive", params={"days": 7})
    assert len(stub["recorder"]["calls"]) == 2


@pytest.mark.asyncio
async def test_archive_upstream_failure_still_returns_200(client: AsyncClient, stub):
    """不可达的上游是公开首屏数据源，只能降级成空列表，不能让页面 500/503。"""
    stub["install"](None, fail=True)
    response = await client.get("/api/bing/image/archive", params={"days": 5})
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_archive_non_200_upstream_returns_empty(client: AsyncClient, stub):
    """上游回 4xx/5xx 时不解析正文，仍然 200 + 空数组，且不写缓存。"""
    stub["install"]([_image()], status=503)
    response = await client.get("/api/bing/image/archive", params={"days": 4})
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert stub["sets"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("days", ["0", "15", "abc"])
async def test_archive_rejects_out_of_range_days(client: AsyncClient, stub, days):
    """入参范围仍由框架闸门守住：越界 422，而不是悄悄接受任意天数去放大外发。"""
    stub["install"]([_image()])
    response = await client.get("/api/bing/image/archive", params={"days": days})
    assert response.status_code == 422
    assert stub["recorder"]["calls"] == []


# ==================== 今日口 ====================


@pytest.mark.asyncio
async def test_today_entry_uses_upstream_startdate_and_copyright_link(client: AsyncClient, stub):
    """今日口与归档口同一日期口径：用上游 ``startdate``，兜底分支才用 UTC 日期。"""
    stub["install"]([_image(startdate="20260228", urlbase="/th?id=OHR.today")])
    body = (await client.get("/api/bing/image/today")).json()
    assert body["data"]["date"] == "2026-02-28"
    assert body["data"]["copyright_url"] == "https://www.bing.com/example"
    assert "fallback" not in body


@pytest.mark.asyncio
async def test_today_fallback_keeps_utc_date_and_200(client: AsyncClient, stub):
    """上游完全不可达时仍是 200 + 占位图，日期退回 UTC 今天（此时没有上游可采信）。"""
    from datetime import datetime, timezone

    stub["install"](None, fail=True)
    response = await client.get("/api/bing/image/today")
    assert response.status_code == 200
    body = response.json()
    assert body["fallback"] is True
    assert body["data"]["date"] == datetime.now(timezone.utc).date().isoformat()


# ==================== /wallpapers 的可索引性 ====================


def _loc_paths(text: str) -> list[str]:
    from re import findall
    from urllib.parse import urlsplit

    return [urlsplit(u).path for u in findall(r"<loc>(.*?)</loc>", text)]


@pytest.mark.asyncio
async def test_wallpapers_in_sitemap_follows_bing_switch(client: AsyncClient, db_session):
    """``/wallpapers`` 进不进 sitemap 由壁纸开关决定，且与 ``pages/wallpapers.vue`` 同口径。

    页面在开关关掉时输出 ``noindex, follow``（正文整批来自 Bing，关掉就是空态），页脚入口
    也一起收起；sitemap 若仍提交这条地址，等于向爬虫要一个自己声明"别收录"的 URL。
    反方向同样要断言：默认（从没写过这一项）必须收录，否则任何"索性摘掉整条"的实现都能过。
    """
    import backend.core.cache as _c
    from backend.models.core import SiteConfig

    await _c.cache.clear()
    r = await client.get("/api/blog/sitemap-pages.xml")
    assert r.status_code == 200, r.text
    paths = _loc_paths(r.text)
    for variant in ("/wallpapers", "/en/wallpapers", "/ja/wallpapers", "/zh_Hant/wallpapers"):
        assert paths.count(variant) == 1, f"壁纸页变体缺失或重复：{variant}"

    db_session.add(SiteConfig(key="ENABLE_BING_WALLPAPER", value="false"))
    await db_session.commit()
    await _c.cache.clear()
    r2 = await client.get("/api/blog/sitemap-pages.xml")
    assert "/wallpapers" not in _loc_paths(r2.text), "关掉开关后仍提交壁纸页"
    # 其余固定路由不受影响（别把整段条件分支写成"少输出"）
    assert "/" in _loc_paths(r2.text)


@pytest.mark.asyncio
async def test_bing_switch_merged_the_same_way_as_api_config(client: AsyncClient, db_session):
    """``bing_wallpaper_enabled`` 与 ``/api/config`` 的 ``enable_bing_wallpaper`` 不得分叉。

    开关有两层写手：OOBE 写 SiteConfig 扁平键，``features`` 分组（若运营者手写过这一项）
    在后。``/api/config`` 先把扁平键投影成 ``enable_bing_wallpaper``，再让分组里**是 bool**
    的同名键覆盖；sitemap 的收录判据必须是同一份合并结果，只读一层就会一处判成开、另一处
    判成关。这里逐形态对账，两种读法各自漏掉哪半边都会被钉住。
    """
    import json

    import backend.core.cache as _c
    from backend.models.core import SiteConfig
    from backend.services.site_settings import bing_wallpaper_enabled

    async def _both_states() -> tuple[bool, bool]:
        """返回 (``/api/config`` 的值, 判据函数的值)。"""
        await _c.cache.clear()
        cfg = await client.get("/api/config")
        assert cfg.status_code == 200, cfg.text
        body = cfg.json()
        payload = body.get("data") if isinstance(body.get("data"), dict) else body
        from_api = payload["enable_bing_wallpaper"]
        from_helper = await bing_wallpaper_enabled(db_session)
        return from_api, from_helper

    # ① 什么都没写过 ⇒ 默认开（老站点没这一项，不等于关）
    assert await _both_states() == (True, True)

    # ② 只有 OOBE 的扁平行 ⇒ 两层都跟着它
    db_session.add(SiteConfig(key="ENABLE_BING_WALLPAPER", value="false"))
    await db_session.commit()
    assert await _both_states() == (False, False)

    # ③ 扁平行是大小写混用的历史写法 ⇒ 仍按"整串 true 才算开"
    await db_session.execute(SiteConfig.__table__.delete())
    db_session.add(SiteConfig(key="enable_bing_wallpaper", value="True"))
    await db_session.commit()
    assert await _both_states() == (True, True)

    # ④ 扁平行写 "1"（不是 true）⇒ 判成关，两侧同判据
    await db_session.execute(SiteConfig.__table__.delete())
    db_session.add(SiteConfig(key="ENABLE_BING_WALLPAPER", value="1"))
    await db_session.commit()
    assert await _both_states() == (False, False)

    # ⑤ features 分组里的 bool 覆盖扁平键
    db_session.add(
        SiteConfig(
            key="features",
            value=json.dumps({"enable_bing_wallpaper": True}),
            description=None,
        )
    )
    await db_session.commit()
    assert await _both_states() == (True, True)

    # ⑥ 分组里的值是**字符串** ⇒ 两边都忽略它，扁平键继续算
    await db_session.execute(SiteConfig.__table__.delete())
    db_session.add_all(
        [
            SiteConfig(key="ENABLE_BING_WALLPAPER", value="false"),
            SiteConfig(key="features", value=json.dumps({"enable_bing_wallpaper": "true"})),
        ]
    )
    await db_session.commit()
    assert await _both_states() == (False, False)
