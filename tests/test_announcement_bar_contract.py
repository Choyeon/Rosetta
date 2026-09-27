"""公告条跨端契约回归（后端 `notice` 分组 + `GET /announcements` ↔ 前台横幅）。

起因：前台公告条有两个"看不见的断点"——
① 设置页 `notice` 分组在 `PUBLIC_SETTING_GROUPS` 白名单里、后端注释还专门写"别让管理员配的
   公告前台不生效"，但前端 `useSite` 连 notice 访问器都没有，属于能存能读却无人渲染的死配置；
② 旧横幅代码按 `link` / `url` / `target` / i18n dict 分支写，而接口 `response_model` 是
   `list[AnnouncementResponse]`，这些键**永远不会出现**——死分支养出三处硬编码中文文案。
这里把"后端下发什么键、什么时候下发"钉住，防止同类漂移再次只在一侧被修好。
"""

from datetime import datetime, timedelta

import pytest

from backend.models.announcement import Announcement
from backend.utils.compat import UTC

PUBLIC_URL = "/api/settings/public"
PATCH_NOTICE_URL = "/api/settings/notice"
ANNOUNCEMENTS_URL = "/api/announcements"

# 前端公告条的消费面：useSite().notice 的兜底键 + useAnnouncementBar.noticeToRow 读取的键。
# 后端 _default_notice() 加/改键必须同步改这里——这条断言刻意用"精确相等"，
# 目的就是"新增一个没人消费的配置键"过不了 CI，而不是悄悄多一个死配置。
FRONTEND_NOTICE_KEYS = {"enable", "type", "title", "content_md", "dismissible", "sticky"}

# 读者拿到的每行键集 = AnnouncementResponse。前端不得按此处没有的键（link/target/dict）写分支。
ANNOUNCEMENT_ROW_KEYS = {
    "id",
    "title",
    "content",
    "type",
    "is_active",
    "is_dismissible",
    "start_time",
    "end_time",
    "sort_order",
    "created_at",
    "updated_at",
}


def _now():
    return datetime.now(UTC)


async def _notice_group(client):
    resp = await client.get(PUBLIC_URL)
    assert resp.status_code == 200, resp.text
    groups = resp.json()["groups"]
    assert "notice" in groups, f"notice 分组未下发，实际分组：{sorted(groups)}"
    return groups["notice"]


async def _announcement_rows(client):
    resp = await client.get(ANNOUNCEMENTS_URL)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _add_announcement(db_session, **kwargs) -> int:
    defaults = {
        "title": "公告标题",
        "content": "公告正文",
        "type": "info",
        "is_active": True,
        "is_dismissible": True,
        "sort_order": 0,
    }
    row = Announcement(**{**defaults, **kwargs})
    db_session.add(row)
    await db_session.commit()
    return row.id


# ==================== ① notice 分组：下发形状与写读闭环 ====================


@pytest.mark.asyncio
async def test_notice_group_shape_matches_frontend_consumer(client):
    """匿名可读（无 header），且键集与前端消费面精确一致。"""
    notice = await _notice_group(client)
    assert set(notice) == FRONTEND_NOTICE_KEYS
    # 默认关闭：横幅不得因为"装好系统就有一条没人写的占位公告"而出现
    assert notice["enable"] is False


@pytest.mark.asyncio
async def test_admin_enable_notice_reaches_public_reader(client, staff_headers):
    """PATCH 写 → 公开 GET 立刻读到（settings_public 缓存失效链路的实际收益）。

    本切片之前这条链走不到读者（前端不消费），缓存失效是否有效无从发现；
    现在公告条真会渲染它，缓存不失效就等于管理员改了公告前台最长 5 分钟不变。
    """
    payload = {"enable": True, "type": "warning", "title": "**维护**通知", "sticky": False}
    resp = await client.patch(PATCH_NOTICE_URL, json=payload, headers=staff_headers)
    assert resp.status_code == 200, resp.text

    notice = await _notice_group(client)
    assert notice["enable"] is True
    assert notice["title"] == "**维护**通知"
    assert notice["type"] == "warning"
    assert notice["sticky"] is False

    restore = await client.patch(
        PATCH_NOTICE_URL,
        json={"enable": False, "type": "info", "title": "", "sticky": True},
        headers=staff_headers,
    )
    assert restore.status_code == 200, restore.text
    assert (await _notice_group(client))["enable"] is False


# ==================== ② /announcements：服务端过滤口径 + 响应形状 ====================


@pytest.mark.asyncio
async def test_announcements_only_returns_active_rows_in_window(client, db_session):
    """is_active 与起止时间窗由服务端过滤——前端因此不得自己再判一遍（口径会漂）。"""
    now = _now()
    visible = await _add_announcement(db_session, title="在线公告", sort_order=20)
    first = await _add_announcement(db_session, title="排在最前", sort_order=10)
    future = await _add_announcement(db_session, title="预告", start_time=now + timedelta(days=1))
    expired = await _add_announcement(db_session, title="过期", end_time=now - timedelta(days=1))
    inactive = await _add_announcement(db_session, title="已停用", is_active=False)

    ids = [r["id"] for r in await _announcement_rows(client)]
    assert visible in ids
    assert first in ids
    assert future not in ids, "start_time 未到的公告不得下发"
    assert expired not in ids, "end_time 已过的公告不得下发"
    assert inactive not in ids, "is_active=False 的公告不得下发"
    # 排序由服务端负责（sort_order 升序），前端不再排
    assert ids.index(first) < ids.index(visible)


@pytest.mark.asyncio
async def test_announcement_row_contract_has_no_link_or_dict_keys(client, db_session):
    """钉死读者能拿到的键：没有 link/url/target，title/content 是明文字符串。

    反向意义：前端任何按链接 / i18n dict 分支的"防御代码"都是不可达死码（本次删了三处）；
    将来要加列，先改后端 schema 与本常量，再改 UI，别在消费侧凭想象加字段。
    """
    ann_id = await _add_announcement(db_session, title="唯一公告", content="**正文**")
    rows = [r for r in await _announcement_rows(client) if r["id"] == ann_id]
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == ANNOUNCEMENT_ROW_KEYS
    assert isinstance(row["title"], str)
    assert isinstance(row["content"], str)
    assert row["is_dismissible"] is True, "默认 True 才撑得住前端「缺省视为可关闭」的口径"


@pytest.mark.asyncio
async def test_announcements_is_public_and_returns_list_not_null(client):
    """匿名 200，且必须是数组而不是 null/对象——前端按数组消费、不做二次兜底。"""
    rows = await _announcement_rows(client)
    assert isinstance(rows, list)
