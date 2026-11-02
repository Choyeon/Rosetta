"""整站恢复必须连带清掉公告列表缓存（`announcements:active`）。

动机：`GET /api/announcements` 是首页侧栏公告卡的数据源，服务端按 `is_active` + 起止时间窗
过滤后把结果整体缓存 60s。公告自己的四个写口都调了 `_invalidate_announcements_cache()`，
但 `POST /api/backup/restore` 是**绕过那些写口**直接重写 `announcements` 表的（第 11 步），
它原来只清 `site_config` / `navigations` / `friend_links` 那一族。

漏掉的表现代码里一个字都不会报：恢复完成后 60s 内，接口仍回备份前那一批公告，首页侧栏卡
也就仍是那一批——而备份恢复恰恰是"把站点整体换回另一个状态"的操作，公告条这类全站级内容
换血后仍播旧值，等于告诉运营者"恢复成功了"但访客看到的还是旧的。
"""

import io
import json
import zipfile

import pytest
from sqlalchemy import select

from backend.api.announcement import _announcements_cache_key
from backend.core.cache import cache
from backend.models.announcement import Announcement

ADMIN = "/api/admin"

OLD_TITLE = "备份前那条公告"
NEW_TITLE = "恢复回来的那条公告"


def _restore_zip(announcements: list[dict]) -> bytes:
    """构造只带 announcements.json 的备份包：恢复流程对缺分项按空集合跳过，
    所以不必为这条用例造齐全站十三张表。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps({"scope": "full"}))
        zf.writestr("announcements.json", json.dumps(announcements))
    return buffer.getvalue()


async def _seed(db_session, title: str) -> None:
    db_session.add(
        Announcement(title=title, content=f"{title} 的正文", type="info", is_active=True)
    )
    await db_session.commit()


async def _titles(client) -> list[str]:
    resp = await client.get("/api/announcements")
    assert resp.status_code == 200, resp.text
    return [row["title"] for row in resp.json()]


@pytest.mark.asyncio
async def test_backup_restore_refreshes_the_announcements_list_cache(
    client, db_session, staff_headers
):
    # 1) 先把 60s 列表缓存预热成"备份前"那一批
    await _seed(db_session, OLD_TITLE)
    assert await _titles(client) == [OLD_TITLE]

    # 恒真前置：缓存里必须真的有条目，否则第 3 步无论清没清都会绿。
    warmed = await cache.get(_announcements_cache_key())
    assert warmed is not None, "公开口没有把公告列表写进缓存，这条用例的前提不成立"
    assert [row["title"] for row in warmed] == [OLD_TITLE]

    # 2) 整站恢复：备份包里是完全不同的一条公告
    resp = await client.post(
        f"{ADMIN}/backup/restore",
        files={
            "file": (
                "rosetta_backup.zip",
                _restore_zip(
                    [
                        {
                            "title": NEW_TITLE,
                            "content": f"{NEW_TITLE} 的正文",
                            "type": "warning",
                            "is_active": True,
                        }
                    ]
                ),
                "application/zip",
            )
        },
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created_count"] == 1

    # 库里的真相已经是新那条（这一步与缓存无关，用来隔开"没写库"和"没清缓存"两种失败）
    rows = (await db_session.execute(select(Announcement.title))).scalars().all()
    assert NEW_TITLE in rows

    # 3) 立刻读公开口必须看到恢复进来的那条。
    #    恢复是 upsert（自然键 = title），不会删掉备份前那条，所以判据是"新条目在场"：
    #    没清缓存时这里拿到的是第 1 步那份逐字回放，NEW_TITLE 必然缺席。
    titles = await _titles(client)
    assert NEW_TITLE in titles, f"恢复后公开口仍是缓存里那一批：{titles}"


@pytest.mark.asyncio
async def test_stale_announcements_cache_would_have_been_served_without_the_fix(
    client, db_session, staff_headers
):
    """反向钉住"缓存键名对得上"：清的是 `announcements` 前缀，
    而读侧键位一旦改名（例如变成 `announcements:active:zh`），delete_pattern 照样回 0，
    这条断言就会指出「预热写进去的那个键现在还在缓存里」。"""
    await _seed(db_session, OLD_TITLE)
    assert await _titles(client) == [OLD_TITLE]

    # 直接改缓存载荷（模拟"缓存还活着"），确认恢复后这个键位确实被清掉而不是被覆写回旧值
    await cache.set(
        _announcements_cache_key(),
        [{"title": OLD_TITLE, "content": "缓存里的旧条目", "type": "info"}],
        ttl=60,
    )

    resp = await client.post(
        f"{ADMIN}/backup/restore",
        files={
            "file": (
                "rosetta_backup.zip",
                _restore_zip([{"title": NEW_TITLE, "content": "新正文", "is_active": True}]),
                "application/zip",
            )
        },
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text

    assert await cache.get(_announcements_cache_key()) is None, (
        "恢复后 `announcements:active` 仍在缓存里 —— 失效动作没命中这个键位"
    )
    assert NEW_TITLE in await _titles(client)
