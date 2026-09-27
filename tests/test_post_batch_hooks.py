"""批量写路径必须与单篇路径同构地发钩子（Webhook 外发与插件监听的唯一触发源）。

起因：`blog.py` 的 create / update / delete 一直在 `do_action`，而两个批量入口
（`POST /blog/posts/batch-status`、`POST /admin/posts/batch`）从写下起零钩子——
用户把「逐篇操作」换成「多选批量」的那一刻，外部 Webhook 与插件监听就静默失聪。
钉住三件事：该发的发（updated/published/deleted 与单篇同名同传法）、
不该发的别发（状态没真变的篇、以及只改置顶/分类/标签时不发 published）。
"""

import pytest
from sqlalchemy import select

from backend.core.plugin_bus import bus
from backend.models.blog import Post

BATCH_URL = "/api/admin/posts/batch"
STATUS_URL = "/api/blog/posts/batch-status"
EVENT_NAMES = ("post.updated", "post.published", "post.deleted")


@pytest.fixture
def recorded_events():
    """在总线三个文章事件上挂临时监听，返回按触发顺序记录的 (事件名, 文章 ID) 列表。

    刻意复用生产总线而不是 mock `do_action`：传法（位置参数 vs `post=` 关键字）
    与 `webhook.py` 监听侧的解析口径必须一起被验，mock 就把它俩解耦了。
    """
    events = []
    handlers = {}

    def make(name):
        async def handler(*args, **kwargs):
            entity = kwargs.get("post") if "post" in kwargs else (args[0] if args else None)
            post_id = getattr(entity, "id", entity)
            events.append((name, post_id))

        return handler

    for name in EVENT_NAMES:
        handlers[name] = make(name)
        bus.add_action(name, handlers[name])
    try:
        yield events
    finally:
        for name, handler in handlers.items():
            bus.remove_action(name, handler)


async def _set_status(db_session, post_id: int, status: str) -> None:
    row = (await db_session.execute(select(Post).where(Post.id == post_id))).scalars().one()
    row.status = status
    await db_session.commit()


async def _reauthor(db_session, post_id: int, author_id: int) -> None:
    row = (await db_session.execute(select(Post).where(Post.id == post_id))).scalars().one()
    row.author_id = author_id
    await db_session.commit()


@pytest.mark.asyncio
async def test_batch_publish_emits_updated_and_published(
    client, staff_headers, db_session, test_post, recorded_events
):
    await _set_status(db_session, test_post.id, "draft")

    resp = await client.post(
        BATCH_URL, json={"action": "publish", "post_ids": [test_post.id]}, headers=staff_headers
    )
    assert resp.status_code == 200, resp.text
    assert recorded_events == [
        ("post.updated", test_post.id),
        ("post.published", test_post.id),
    ]


@pytest.mark.asyncio
async def test_batch_publish_skips_posts_that_did_not_change(
    client, staff_headers, test_post, recorded_events
):
    # test_post 建出来就是 published：状态没真变，一篇都不该发（防 webhook 噪声）
    resp = await client.post(
        BATCH_URL, json={"action": "publish", "post_ids": [test_post.id]}, headers=staff_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["affected_count"] == 0
    assert recorded_events == []


@pytest.mark.asyncio
async def test_batch_delete_emits_post_deleted(client, staff_headers, test_post, recorded_events):
    resp = await client.post(
        BATCH_URL, json={"action": "delete", "post_ids": [test_post.id]}, headers=staff_headers
    )
    assert resp.status_code == 200, resp.text
    assert recorded_events == [("post.deleted", test_post.id)]


@pytest.mark.asyncio
async def test_batch_pin_emits_updated_only(client, staff_headers, test_post, recorded_events):
    resp = await client.post(
        BATCH_URL, json={"action": "pin", "post_ids": [test_post.id]}, headers=staff_headers
    )
    assert resp.status_code == 200, resp.text
    assert recorded_events == [("post.updated", test_post.id)]


@pytest.mark.asyncio
async def test_batch_status_publish_emits_both_events(
    client, staff_headers, staff_user, db_session, test_post, recorded_events
):
    # batch-status 只处理「本人文章或 superuser」，staff_user 非 superuser，
    # 不先把作者改成他就会被过滤成 0 篇，测不到钩子分支。
    await _reauthor(db_session, test_post.id, staff_user.id)
    await _set_status(db_session, test_post.id, "draft")

    resp = await client.post(
        STATUS_URL,
        json={"post_ids": [test_post.id], "status": "published"},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["updated_count"] == 1
    assert recorded_events == [
        ("post.updated", test_post.id),
        ("post.published", test_post.id),
    ]


@pytest.mark.asyncio
async def test_batch_status_draft_emits_updated_only(
    client, staff_headers, staff_user, db_session, test_post, recorded_events
):
    await _reauthor(db_session, test_post.id, staff_user.id)

    resp = await client.post(
        STATUS_URL,
        json={"post_ids": [test_post.id], "status": "draft"},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["updated_count"] == 1
    assert recorded_events == [("post.updated", test_post.id)]
