"""
Rosetta 留言板 API 测试（Task 6 要求的 2 条核心用例）

覆盖：
1. test_guestbook_pinned_sorted_first：2 条 A/B，B 置顶 → GET 列表首项为 B
2. test_guestbook_soft_delete_restore：1 条 → trash → 默认不见/trashed 见 → restore → 又见
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.guestbook import GuestbookEntry

BASE_DIR = Path(__file__).resolve().parent.parent
OOBE_LOCK_FILE = BASE_DIR / ".oobe_complete"
CONFIG_FILE = BASE_DIR / "rosetta.json"


@pytest.fixture(scope="module", autouse=True)
def _ensure_oobe_marked():
    """留言板端点要求 OOBE 完成。为了让本模块可以独立运行，临时写入标记文件。"""
    existed_lock = OOBE_LOCK_FILE.exists()
    existed_cfg = CONFIG_FILE.exists()
    if not existed_lock:
        OOBE_LOCK_FILE.write_text("1", encoding="utf-8")
    if not existed_cfg:
        sample = {
            "app_name": "Rosetta",
            "database_url": "sqlite+aiosqlite:///./rosetta.db",
            "admin_initialized": True,
        }
        CONFIG_FILE.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    yield
    if not existed_lock and OOBE_LOCK_FILE.exists():
        try:
            OOBE_LOCK_FILE.unlink()
        except Exception:
            pass
    if not existed_cfg and CONFIG_FILE.exists():
        try:
            CONFIG_FILE.unlink()
        except Exception:
            pass


@pytest.mark.asyncio(loop_scope="function")
async def test_guestbook_pinned_sorted_first(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """POST 2 条 A 和 B，通过 DB 把 B 设为置顶+已审核，GET 默认列表首项应为 B.id"""

    # A：IP 段 90
    a_payload = {
        "author_name": "留言人A",
        "author_email": "a@example.com",
        "content": "我是留言 A，应该在 B 之后（因为 B 置顶）。",
    }
    r_a = await client.post(
        "/api/guestbook",
        json=a_payload,
        headers={"X-Forwarded-For": "10.90.1.1"},
    )
    assert r_a.status_code == 201, f"A 创建失败: {r_a.status_code} {r_a.text}"
    a_body = r_a.json()
    a_id = int(a_body["id"])

    # B：IP 段 91（避开 30s 同 IP mask 后重复频控）
    b_payload = {
        "author_name": "留言人B",
        "author_email": "b@example.com",
        "content": "我是留言 B，会被设为置顶，应该排在第一个。",
    }
    r_b = await client.post(
        "/api/guestbook",
        json=b_payload,
        headers={"X-Forwarded-For": "10.91.2.1"},
    )
    assert r_b.status_code == 201, f"B 创建失败: {r_b.status_code} {r_b.text}"
    b_body = r_b.json()
    b_id = int(b_body["id"])

    # 通过 DB 直接把 A/B 状态设为 approved，并把 B 设 is_pinned=true
    stmt = select(GuestbookEntry).where(GuestbookEntry.id.in_([a_id, b_id]))
    rows = list((await db_session.execute(stmt)).scalars().all())
    assert len(rows) == 2
    for e in rows:
        e.status = "approved"
        if e.id == b_id:
            e.is_pinned = True
    await db_session.commit()

    # 调 GET /guestbook?status=approved
    list_r = await client.get("/api/guestbook?status=approved&page=1&page_size=20")
    assert list_r.status_code == 200, list_r.text
    data = list_r.json()
    items = data["items"]
    assert len(items) >= 2, f"至少应该有 2 条，实际 {len(items)}"
    assert items[0]["id"] == b_id, (
        f"置顶的留言 B(id={b_id}) 应该在列表首项，实际首项 id={items[0]['id']}, "
        f"首项 pinned={items[0].get('is_pinned')}, 整体顺序：{[(i['id'], i.get('is_pinned')) for i in items]}"
    )
    # A 应该在 B 之后（不一定是第二项，因为可能有其他残留数据，但必然 items 中 B 在 A 前）
    ordered_ids = [i["id"] for i in items]
    assert ordered_ids.index(b_id) < ordered_ids.index(a_id), "置顶留言 B 排序应在普通留言 A 之前"


@pytest.mark.asyncio(loop_scope="function")
async def test_guestbook_soft_delete_restore(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user,
    admin_headers: dict,
):
    """1 条留言 C：batch trash → 默认列表不显示；status=trashed 显示；restore → 又显示"""

    # C：创建 + DB 设 status=approved
    c_payload = {
        "author_name": "留言人C",
        "content": "我是留言 C，用于测试软删除与恢复流程。",
    }
    r_c = await client.post(
        "/api/guestbook",
        json=c_payload,
        headers={"X-Forwarded-For": "10.91.3.1"},
    )
    assert r_c.status_code == 201, r_c.text
    c_id = int(r_c.json()["id"])

    stmt = select(GuestbookEntry).where(GuestbookEntry.id == c_id)
    e = (await db_session.execute(stmt)).scalars().first()
    assert e is not None
    e.status = "approved"
    await db_session.commit()

    # 1) 默认列表 GET 应该包含
    r1 = await client.get("/api/guestbook?status=approved&page=1&page_size=50")
    assert r1.status_code == 200
    ids_1 = [i["id"] for i in r1.json()["items"]]
    assert c_id in ids_1

    # 2) batch trash
    trash_r = await client.post(
        "/api/admin/guestbook/batch",
        json={"ids": [c_id], "action": "trash"},
        headers=admin_headers,
    )
    assert trash_r.status_code == 200, trash_r.text

    # 3) 默认列表 GET 不包含
    r2 = await client.get("/api/guestbook?status=approved&page=1&page_size=50")
    assert r2.status_code == 200
    ids_2 = [i["id"] for i in r2.json()["items"]]
    assert c_id not in ids_2, "trash 后默认 approved 列表不应再包含"

    # 4) status=trashed GET 管理员可看到
    r3 = await client.get(
        "/api/admin/guestbook?status=trashed&page=1&page_size=50",
        headers=admin_headers,
    )
    assert r3.status_code == 200, r3.text
    ids_3 = [i["id"] for i in r3.json()["items"]]
    assert c_id in ids_3, "status=trashed 管理员列表应该包含"

    # 5) batch restore
    restore_r = await client.post(
        "/api/admin/guestbook/batch",
        json={"ids": [c_id], "action": "restore"},
        headers=admin_headers,
    )
    assert restore_r.status_code == 200, restore_r.text

    # 6) 默认 approved GET 再次包含
    r4 = await client.get("/api/guestbook?status=approved&page=1&page_size=50")
    assert r4.status_code == 200
    ids_4 = [i["id"] for i in r4.json()["items"]]
    assert c_id in ids_4, "restore 后 approved 列表应再次包含"
