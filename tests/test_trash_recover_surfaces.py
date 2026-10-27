"""回收站的三类可恢复资源（文章 / 独立页 / 评论）端到端契约。

背景：回收站页的筛选项与「保留 30 天，可随时恢复」的文案早就写了 `page` 与 `comment`
两类，而**全仓只有文章删除会写入回收站**——另两个筛选永远为空。更糟的是评论的恢复分支
（`POST /admin/trash/{id}/restore`）只重建 post_id/user_id/parent_id/content，而
`author_name`、`status` 都是 NOT NULL：即便当初真写入了快照，恢复一条评论也会当场撞
非空约束（500），已通过的评论还会退回 pending 悄悄消失。

本文件把三件事钉住：删除侧写快照 → 列表侧能筛出来 → 恢复侧按快照原样还原（含状态），
以及不可恢复时的 400（slug 冲突 / 原文章已删）。到期清理另有一条。
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.models.blog import Post
from backend.models.core import Page
from backend.models.log import TrashItem
from backend.services.trash import prune_expired_trash

PAGE_SLUG = "trash-recover-probe"


def _unwrap(body: dict) -> dict:
    return body.get("data", body) if isinstance(body, dict) else body


def _page_payload(**overrides) -> dict:
    body = {
        "title": {"zh": "回收站验证页", "en": "Trash probe page"},
        "slug": PAGE_SLUG,
        "content": {"zh": "第一版正文", "en": "first"},
        "status": "published",
    }
    body.update(overrides)
    return body


async def _make_page(client: AsyncClient, admin_headers: dict, **overrides) -> int:
    created = await client.post(
        "/api/pages", json=_page_payload(**overrides), headers=admin_headers
    )
    assert created.status_code in (200, 201), created.text
    return int(_unwrap(created.json())["id"])


async def _trash_entries(client: AsyncClient, headers: dict, resource_type: str) -> list[dict]:
    resp = await client.get(
        "/api/admin/trash",
        headers=headers,
        params={"resource_type": resource_type, "page_size": 100},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return [i for i in body.get("items", []) if i.get("resource_type") == resource_type]


@pytest.mark.asyncio
async def test_page_delete_lands_in_trash_and_restores(client: AsyncClient, admin_headers: dict):
    """独立页删除 → 回收站可筛 → 恢复后正文与 slug 都回来"""
    page_id = await _make_page(client, admin_headers)

    deleted = await client.delete(f"/api/pages/{page_id}", headers=admin_headers)
    assert deleted.status_code == 200, deleted.text
    # 提示语必须说清"可恢复"：写"页面已删除"会让管理员以为内容没了。
    assert "回收站" in _unwrap(deleted.json()).get("message", "")

    entries = await _trash_entries(client, admin_headers, "page")
    mine = [e for e in entries if e["resource_id"] == page_id]
    assert len(mine) == 1, f"独立页删除未写入回收站: {entries}"
    assert mine[0]["resource_data"]["slug"] == PAGE_SLUG
    # 快照本身存的是**渲染前**的原值，所以这里可以做逐字断言；
    # 恢复后的读口会再过一遍插件的内容过滤器（hello-rosetta / seo-toolkit 会往正文尾部追加），
    # 全量跑里插件已被其他用例注册进同一进程——那条只能断言"原文在里面"。
    assert mine[0]["resource_data"]["content"]["zh"] == "第一版正文"
    assert mine[0]["auto_delete_at"], "回收站记录没有到期时间，'保留 30 天'无从兑现"

    restored = await client.post(f"/api/admin/trash/{mine[0]['id']}/restore", headers=admin_headers)
    assert restored.status_code == 200, restored.text

    read = await client.get(f"/api/pages/{PAGE_SLUG}")
    assert read.status_code == 200, read.text
    body = _unwrap(read.json())
    assert body["content"]["zh"].startswith("第一版正文")

    # 恢复即消费：记录不该同时留在回收站里（否则第二次恢复会产出重复页）
    assert [
        e for e in await _trash_entries(client, admin_headers, "page") if e["id"] == mine[0]["id"]
    ] == []


@pytest.mark.asyncio
async def test_page_restore_conflicts_on_slug(client: AsyncClient, admin_headers: dict):
    """同 slug 已被占用时回 400，而不是撞唯一约束变成 500"""
    page_id = await _make_page(client, admin_headers)
    deleted = await client.delete(f"/api/pages/{page_id}", headers=admin_headers)
    assert deleted.status_code == 200
    entry = [
        e
        for e in await _trash_entries(client, admin_headers, "page")
        if e["resource_id"] == page_id
    ][0]

    # 同名页面重建（等价于"删除后新建了同 slug 页面"）
    await _make_page(client, admin_headers)

    conflict = await client.post(f"/api/admin/trash/{entry['id']}/restore", headers=admin_headers)
    assert conflict.status_code == 400, conflict.text
    assert "slug" in _unwrap(conflict.json()).get("message", "")


@pytest.mark.asyncio
async def test_comment_delete_restores_with_state(
    client: AsyncClient, admin_headers: dict, make_comments, test_post: Post
):
    """评论删除进回收站，且恢复后审核状态/作者名/点赞数按快照原样还原"""
    (comment,) = await make_comments(test_post, 1, status_cycle=["approved"])

    deleted = await client.delete(f"/api/admin/comments/{comment.id}", headers=admin_headers)
    assert deleted.status_code == 200, deleted.text
    assert "回收站" in _unwrap(deleted.json()).get("message", "")

    entries = [
        e
        for e in await _trash_entries(client, admin_headers, "comment")
        if e["resource_id"] == comment.id
    ]
    assert len(entries) == 1, f"评论删除未写入回收站: {entries}"
    snap = entries[0]["resource_data"]
    # 这一条是旧恢复分支的致命点：author_name NOT NULL，缺它则 INSERT 直接 500
    assert snap["author_name"] == comment.author_name
    assert snap["status"] == "approved"

    restored = await client.post(
        f"/api/admin/trash/{entries[0]['id']}/restore", headers=admin_headers
    )
    assert restored.status_code == 200, restored.text

    rows = (
        (await client.get("/api/admin/comments", headers=admin_headers, params={"page_size": 100}))
        .json()
        .get("items", [])
    )
    back = [r for r in rows if r.get("content") == comment.content]
    assert len(back) == 1, f"恢复的评论没有回到原文章: {back}"
    assert back[0]["status"] == "approved", "恢复后状态退回 pending = 评论在前台悄悄消失"
    assert back[0]["author_name"] == comment.author_name


@pytest.mark.asyncio
async def test_comment_restore_requires_existing_post(
    client: AsyncClient, admin_headers: dict, make_comments, test_post: Post
):
    """原文章被删除后评论无处可回：回 400，而不是撞外键变成 500"""
    (comment,) = await make_comments(test_post, 1)
    deleted = await client.delete(f"/api/admin/comments/{comment.id}", headers=admin_headers)
    assert deleted.status_code == 200
    entry = [
        e
        for e in await _trash_entries(client, admin_headers, "comment")
        if e["resource_id"] == comment.id
    ][0]

    # 连文章一起删掉（comments.post_id 是 ondelete=CASCADE，评论行已无处安放）
    post_deleted = await client.delete(f"/api/blog/posts/{test_post.id}", headers=admin_headers)
    assert post_deleted.status_code == 200, post_deleted.text

    resp = await client.post(f"/api/admin/trash/{entry['id']}/restore", headers=admin_headers)
    assert resp.status_code == 400, resp.text
    assert "文章" in _unwrap(resp.json()).get("message", "")


@pytest.mark.asyncio
async def test_batch_comment_delete_snapshots_every_row(
    client: AsyncClient, admin_headers: dict, make_comments, test_post: Post
):
    """批量删除与单删同构：每条都要落快照（AGENTS.md 的批量入口同口径红线）"""
    comments = await make_comments(test_post, 3, status_cycle=["approved"])

    resp = await client.post(
        "/api/admin/comments/batch",
        json={"ids": [c.id for c in comments], "action": "delete"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text

    ids = {c.id for c in comments}
    snapped = {e["resource_id"] for e in await _trash_entries(client, admin_headers, "comment")}
    assert ids <= snapped, f"批量删除漏写快照: 缺 {sorted(ids - snapped)}"


@pytest.mark.asyncio
async def test_prune_expired_trash_only_removes_due_rows(db_session):
    """到期清理真的会删：否则"保留 30 天"只是把删掉的文章正文永久留在库里"""
    now = datetime.now()
    due = TrashItem(
        resource_type="post",
        resource_id=1,
        resource_data="{}",
        auto_delete_at=now - timedelta(days=1),
    )
    keep = TrashItem(
        resource_type="post",
        resource_id=2,
        resource_data="{}",
        auto_delete_at=now + timedelta(days=29),
    )
    no_deadline = TrashItem(resource_type="post", resource_id=3, resource_data="{}")
    db_session.add_all([due, keep, no_deadline])
    await db_session.commit()

    removed = await prune_expired_trash(db_session, now=now)
    assert removed >= 1

    remaining = set((await db_session.execute(select(TrashItem.resource_id))).scalars().all())
    assert 1 not in remaining, "到期的回收站记录没被清除"
    assert 2 in remaining and 3 in remaining, "未到期的记录被误删"


@pytest.mark.asyncio
async def test_page_delete_still_removes_the_original_row(
    db_session, client: AsyncClient, admin_headers: dict
):
    """回收站里的只是副本：原行必须真的消失（否则前台 /slug 仍渲染已删页面）"""
    page_id = await _make_page(client, admin_headers, slug=f"{PAGE_SLUG}-orphan")
    await client.delete(f"/api/pages/{page_id}", headers=admin_headers)
    assert (
        await db_session.execute(select(Page).where(Page.id == page_id))
    ).scalar_one_or_none() is None
    assert (await client.get(f"/api/pages/{PAGE_SLUG}-orphan")).status_code == 404
