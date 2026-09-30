"""公告管理端回归：写入守卫、缓存失效、钩子与前台缓存清除。

起因（四条各自都有过"接口返回成功但结果不对"的历史）：
① 时间窗倒挂（end <= start）不报错，公告被存下来却永远不下发，管理员零反馈；
② 公开接口加缓存后如果不失效，改动在最坏 TTL 内对访客不可见；
③ 前台每个页面的 SSR HTML 都带公告条，而 Nitro 对这些页面做了 swr 300~3600s
   缓存——不清缓存的话，改公告要等一小时才生效（设置页 notice 分组早已清，公告侧漏了）；
④ 公告是内容实体，插件 / Webhook 要能监听其写路径（与文章同构的 do_action）。

另外钉住"排期字段在后端真的可写、可清空"——此前 UI 上完全不可达，只能改库。
"""

from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.api.announcement import _announcements_cache_key
from backend.core.cache import cache
from backend.core.plugin_bus import bus
from backend.models.announcement import Announcement
from backend.schemas.announcement import AnnouncementCreate
from backend.utils.compat import UTC

BASE = "/api/admin/announcements"
PUBLIC = "/api/announcements"
NOW = "2026-09-29T12:00:00Z"


def _future(days: int = 1) -> str:
    from datetime import datetime

    return (datetime.now(UTC) + timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _past(days: int = 1) -> str:
    from datetime import datetime

    return (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _payload(**over) -> dict:
    base = {
        "title": "回归公告",
        "content": "正文",
        "type": "info",
        "is_active": True,
        "is_dismissible": True,
        "sort_order": 0,
    }
    base.update(over)
    return base


async def _create(client, staff_headers, **over) -> int:
    resp = await client.post(BASE, json=_payload(**over), headers=staff_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ==================== ① 写入守卫 ====================


@pytest.mark.asyncio
async def test_create_rejects_inverted_time_window(client, staff_headers):
    """end <= start 必须 422：倒挂的窗口永远不成立，等于"存了但永不展示"。"""
    for start, end in [(_future(2), _future(1)), (NOW, NOW)]:
        resp = await client.post(
            BASE, json=_payload(start_time=start, end_time=end), headers=staff_headers
        )
        assert resp.status_code == 422, resp.text
        assert resp.json()["error_code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_rejects_oversized_content(client, staff_headers):
    """正文上限与前端提示同值（见 frontend/lib/announcement.ts）。"""
    resp = await client.post(BASE, json=_payload(content="x" * 2001), headers=staff_headers)
    assert resp.status_code == 422, resp.text
    ok = await client.post(BASE, json=_payload(content="x" * 2000), headers=staff_headers)
    assert ok.status_code == 201, ok.text


@pytest.mark.asyncio
async def test_partial_update_detects_window_becoming_inverted(client, staff_headers):
    """只传 end_time 时 schema 看不到库里的 start_time，必须由 API 层合并后判。"""
    ann_id = await _create(client, staff_headers, start_time=_future(3))
    resp = await client.put(
        f"{BASE}/{ann_id}", json={"end_time": _future(1)}, headers=staff_headers
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error_code"] == "VALIDATION_ERROR"

    # 顺序正确的更新照常通过
    ok = await client.put(
        f"{BASE}/{ann_id}", json={"end_time": _future(5)}, headers=staff_headers
    )
    assert ok.status_code == 200, ok.text


# ==================== 排期字段可写 / 可清空 ====================


@pytest.mark.asyncio
async def test_schedule_fields_persist_and_can_be_cleared(client, staff_headers, db_session):
    ann_id = await _create(client, staff_headers, start_time=_future(1), end_time=_future(2), sort_order=7)

    put = await client.put(f"{BASE}/{ann_id}", json={"sort_order": 3}, headers=staff_headers)
    assert put.status_code == 200, put.text
    assert put.json()["sort_order"] == 3
    assert put.json()["start_time"] and put.json()["end_time"], "未改动排期时不得被清掉"

    # 显式 null = 取消排期（前端清空输入框就是走这条路）
    cleared = await client.put(
        f"{BASE}/{ann_id}", json={"start_time": None, "end_time": None}, headers=staff_headers
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["start_time"] is None
    assert cleared.json()["end_time"] is None

    row = (
        await db_session.execute(select(Announcement).where(Announcement.id == ann_id))
    ).scalars().one()
    assert row.start_time is None and row.end_time is None


def test_schema_treats_naive_datetime_as_utc_not_local():
    """直接钉 schema：朴素入参补的是 **UTC**，不是运行机器的本地时区。

    刻意不经过 HTTP / 数据库——那两头在 SQLite 上都把朴素值原样存下，
    机器时区恰好是 UTC 时"按本地时区折算"的错法也一样能过，属于假阴性。
    这里断言的是 tzinfo 与钟点本身，与测试机时区无关。
    """
    parsed = AnnouncementCreate(
        title="t", content="c", start_time="2026-09-29T10:00:00"
    ).start_time
    assert parsed is not None
    assert parsed.tzinfo is not None, "朴素入参必须补上 tzinfo"
    assert parsed.utcoffset() == timedelta(0), "补的必须是 UTC，不是本地偏移"
    assert parsed.hour == 10, "钟点不得被时区搬动"

    # 带偏移的入参保持原瞬时，不被二次折算
    aware = AnnouncementCreate(
        title="t", content="c", end_time="2026-09-29T10:00:00+08:00"
    ).end_time
    assert aware is not None
    assert aware.utcoffset() == timedelta(hours=8)
    assert aware.hour == 10


@pytest.mark.asyncio
async def test_naive_datetime_is_treated_as_utc_not_local(client, staff_headers, db_session):
    """朴素入参按 UTC 解释（utils/compat 同口径），不得被当作运行机器的本地时区。

    断言的是"钟点没被搬动"：10:00 进来，回读还是 10:00。若按本地时区（如 UTC+8）
    折算成 UTC 再入库，这里会变成 02:00，排期就整体偏了 8 小时。
    （机器时区恰好是 UTC 时这条会假阴性，真正的守门是上面的 schema 直测。）
    """
    ann_id = await _create(client, staff_headers, start_time="2026-09-29T10:00:00")
    row = (
        await db_session.execute(select(Announcement).where(Announcement.id == ann_id))
    ).scalars().one()
    assert row.start_time is not None
    assert row.start_time.strftime("%Y-%m-%dT%H:%M") == "2026-09-29T10:00"

    # 朴素 / 带偏移混着传也不能 500：入参补齐 tz 后与库里的值比较必须有定义
    ok = await client.put(
        f"{BASE}/{ann_id}",
        json={"end_time": "2026-09-30T10:00:00"},
        headers=staff_headers,
    )
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
async def test_scheduled_announcement_stays_hidden_until_start(client, staff_headers):
    """start_time 未到不得下发——服务端过滤口径，前端不得自己再判一遍。"""
    ann_id = await _create(client, staff_headers, title="未来公告", start_time=_future(1))
    rows = (await client.get(PUBLIC)).json()
    assert all(r["id"] != ann_id for r in rows)

    # 已过期的同理
    expired = await _create(client, staff_headers, title="过期公告", end_time=_past(1))
    rows = (await client.get(PUBLIC)).json()
    assert all(r["id"] != expired for r in rows)


# ==================== ② 公开接口缓存必须随写操作失效 ====================


@pytest.mark.asyncio
async def test_public_list_reflects_write_despite_cache(client, staff_headers):
    """先读一次把结果写进缓存，再写一条，第二次读必须能看到——不失效就会漏。"""
    first = await client.get(PUBLIC)
    assert first.status_code == 200
    assert await cache.get(_announcements_cache_key()) is not None, "公开列表应当走缓存"

    ann_id = await _create(client, staff_headers, title="缓存失效验证")

    rows = (await client.get(PUBLIC)).json()
    assert any(r["id"] == ann_id for r in rows), "写操作未失效公开列表缓存"

    # 删除同理
    await client.delete(f"{BASE}/{ann_id}", headers=staff_headers)
    rows = (await client.get(PUBLIC)).json()
    assert all(r["id"] != ann_id for r in rows), "删除未失效公开列表缓存"


@pytest.mark.asyncio
async def test_toggle_also_invalidates_cache(client, staff_headers):
    ann_id = await _create(client, staff_headers, title="待停用", is_active=True)
    assert any(r["id"] == ann_id for r in (await client.get(PUBLIC)).json())

    resp = await client.put(f"{BASE}/{ann_id}/toggle", headers=staff_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert all(r["id"] != ann_id for r in (await client.get(PUBLIC)).json())


# ==================== ③ 写操作必须清前台 SSR 页面缓存 ====================


@pytest.fixture
def recorded_purges(monkeypatch):
    """拦下模块里的 purge_frontend_page_cache，记录调用原因。

    公告条渲染在 layouts/default.vue，前台**每一页**的 SSR HTML 都内嵌它，而
    Nitro 对这些页面做了 swr 缓存；不清的话管理员改完公告，访客最长一小时看不到变化。
    """
    import backend.api.announcement as ann_api

    calls: list[str] = []
    monkeypatch.setattr(ann_api, "purge_frontend_page_cache", lambda reason="": calls.append(reason))
    return calls


@pytest.mark.asyncio
async def test_every_write_purges_frontend_cache(client, staff_headers, recorded_purges):
    ann_id = await _create(client, staff_headers, title="清缓存验证", start_time=_past(1))
    assert len(recorded_purges) == 1, recorded_purges

    await client.put(f"{BASE}/{ann_id}", json={"title": "改过的标题"}, headers=staff_headers)
    await client.put(f"{BASE}/{ann_id}/toggle", headers=staff_headers)
    await client.delete(f"{BASE}/{ann_id}", headers=staff_headers)

    assert len(recorded_purges) == 4, f"四个写路径都要清缓存，实际：{recorded_purges}"
    assert all("公告变更" in c for c in recorded_purges)


# ==================== ④ 写路径钩子事件 ====================


@pytest.fixture
def recorded_announcement_events():
    events: list[tuple[str, int]] = []
    handlers = {}
    names = ("announcement.created", "announcement.updated", "announcement.deleted")

    def make(name):
        async def handler(*args, **kwargs):
            entity = args[0] if args else kwargs.get("announcement")
            events.append((name, getattr(entity, "id", None)))

        return handler

    for name in names:
        handlers[name] = make(name)
        bus.add_action(name, handlers[name])
    try:
        yield events
    finally:
        for name, handler in handlers.items():
            bus.remove_action(name, handler)


@pytest.mark.asyncio
async def test_write_paths_emit_bus_events(client, staff_headers, recorded_announcement_events):
    ann_id = await _create(client, staff_headers, title="钩子验证", start_time=_past(1))
    await client.put(f"{BASE}/{ann_id}", json={"content": "改过"}, headers=staff_headers)
    await client.delete(f"{BASE}/{ann_id}", headers=staff_headers)

    assert recorded_announcement_events == [
        ("announcement.created", ann_id),
        ("announcement.updated", ann_id),
        ("announcement.deleted", ann_id),
    ]


@pytest.mark.asyncio
async def test_toggle_emits_updated_not_created(client, staff_headers, recorded_announcement_events):
    ann_id = await _create(client, staff_headers, title="开关验证", start_time=_past(1))
    recorded_announcement_events.clear()

    await client.put(f"{BASE}/{ann_id}/toggle", headers=staff_headers)
    assert recorded_announcement_events == [("announcement.updated", ann_id)]


# ==================== 404 口径 ====================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,url",
    [
        ("put", f"{BASE}/999999"),
        ("delete", f"{BASE}/999999"),
        ("put", f"{BASE}/999999/toggle"),
    ],
)
async def test_missing_announcement_returns_enveloped_404(client, staff_headers, method, url):
    kwargs = {"headers": staff_headers}
    if method == "put":
        kwargs["json"] = {"is_active": True}
    resp = await getattr(client, method)(url, **kwargs)
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "NOT_FOUND", "裸 404 也要落到统一错误包络"
