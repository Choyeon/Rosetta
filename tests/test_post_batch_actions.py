"""文章批量操作（POST /api/admin/posts/batch）契约回归测试。

起因：`add_tag` / `remove_tag` 分支直接读写 `post.tags` 集合，而查询侧没有
`selectinload(Post.tags)`。async 会话里触碰未加载属性会抛
`MissingGreenlet: greenlet_spawn has not been called`，这两个 action 从写下起
就没成功过（前端只会拿到 500）。这里把八个 action 与全部校验分支钉住，防同类回归。
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.models.blog import Category, Post, Tag
from backend.models.log import TrashItem

URL = "/api/admin/posts/batch"


async def _batch(client, staff_headers, **payload):
    return await client.post(URL, json=payload, headers=staff_headers)


async def _post_row(db_session, post_id: int) -> Post:
    return (
        (
            await db_session.execute(
                select(Post).options(selectinload(Post.tags)).where(Post.id == post_id)
            )
        )
        .scalars()
        .one()
    )


async def _tag_slugs(db_session, post_id: int) -> list[str]:
    return sorted(t.slug for t in (await _post_row(db_session, post_id)).tags)


async def _set_tags(db_session, post_id: int, tags: list) -> None:
    """预置标签关系。

    刻意走"eager load 后整体赋值"而不是 test_post.tags.append()——后者正是被测
    代码刚修掉的那个 async 懒加载错误，测试自己不能踩。
    """
    row = await _post_row(db_session, post_id)
    row.tags = list(tags)
    await db_session.commit()


@pytest.mark.asyncio
async def test_add_tag_persists_relation(client, staff_headers, db_session, test_post, test_tag):
    """回归：修复前这里是 500（MissingGreenlet）。"""
    resp = await _batch(
        client, staff_headers, action="add_tag", post_ids=[test_post.id], tag_ids=[test_tag.id]
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["affected_count"] == 1
    assert "已处理 1 篇" in body["message"]

    assert await _tag_slugs(db_session, test_post.id) == [test_tag.slug]


@pytest.mark.asyncio
async def test_add_tag_is_idempotent(client, staff_headers, db_session, test_post, test_tag):
    await _set_tags(db_session, test_post.id, [test_tag])

    resp = await _batch(
        client, staff_headers, action="add_tag", post_ids=[test_post.id], tag_ids=[test_tag.id]
    )
    assert resp.status_code == 200, resp.text
    # 重复添加不得产生第二条关联行
    assert await _tag_slugs(db_session, test_post.id) == [test_tag.slug]


@pytest.mark.asyncio
async def test_remove_tag_keeps_other_tags(client, staff_headers, db_session, test_post, test_tag):
    """remove_tag 只摘指定标签，不能顺手清空其余标签。"""
    extra = Tag(name={"zh": "附加"}, slug="extra-tag", color="#111111", is_active=True)
    db_session.add(extra)
    await db_session.commit()
    await _set_tags(db_session, test_post.id, [test_tag, extra])

    resp = await _batch(
        client, staff_headers, action="remove_tag", post_ids=[test_post.id], tag_ids=[test_tag.id]
    )
    assert resp.status_code == 200, resp.text
    assert await _tag_slugs(db_session, test_post.id) == ["extra-tag"]


@pytest.mark.asyncio
async def test_publish_and_draft_toggle_status(client, staff_headers, db_session, test_post):
    """test_post 建出来就是 published，先落回 draft 才能验证 publish 分支。"""
    row = await _post_row(db_session, test_post.id)
    row.status = "draft"
    await db_session.commit()

    resp = await _batch(client, staff_headers, action="publish", post_ids=[test_post.id])
    assert resp.status_code == 200, resp.text
    published = await _post_row(db_session, test_post.id)
    assert published.status == "published"
    assert published.published_at is not None

    resp2 = await _batch(client, staff_headers, action="draft", post_ids=[test_post.id])
    assert resp2.status_code == 200, resp2.text
    assert (await _post_row(db_session, test_post.id)).status == "draft"


@pytest.mark.asyncio
async def test_publish_already_published_counts_nothing(client, staff_headers, test_post):
    resp = await _batch(client, staff_headers, action="publish", post_ids=[test_post.id])
    assert resp.status_code == 200, resp.text
    assert resp.json()["affected_count"] == 0


@pytest.mark.asyncio
async def test_pin_and_unpin(client, staff_headers, db_session, test_post):
    assert test_post.is_pinned is False

    await _batch(client, staff_headers, action="pin", post_ids=[test_post.id])
    assert (await _post_row(db_session, test_post.id)).is_pinned is True

    await _batch(client, staff_headers, action="unpin", post_ids=[test_post.id])
    assert (await _post_row(db_session, test_post.id)).is_pinned is False


@pytest.mark.asyncio
async def test_move_category(client, staff_headers, db_session, test_post, test_category):
    other = Category(name={"zh": "另一个分类"}, slug="another-cat")
    db_session.add(other)
    await db_session.commit()
    assert test_post.category_id == test_category.id

    resp = await _batch(
        client,
        staff_headers,
        action="move_category",
        post_ids=[test_post.id],
        category_id=other.id,
    )
    assert resp.status_code == 200, resp.text
    assert (await _post_row(db_session, test_post.id)).category_id == other.id


@pytest.mark.asyncio
async def test_move_category_unknown_id_returns_404(client, staff_headers, test_post):
    resp = await _batch(
        client, staff_headers, action="move_category", post_ids=[test_post.id], category_id=4242
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_moves_post_into_trash(client, staff_headers, db_session, test_post):
    post_id = test_post.id
    resp = await _batch(client, staff_headers, action="delete", post_ids=[post_id])
    assert resp.status_code == 200, resp.text

    trash = (
        (
            await db_session.execute(
                select(TrashItem).where(
                    TrashItem.resource_type == "post", TrashItem.resource_id == post_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(trash) == 1
    assert await db_session.get(Post, post_id) is None


# ==================== 参数校验分支 ====================


@pytest.mark.asyncio
async def test_empty_post_ids_rejected(client, staff_headers):
    resp = await _batch(client, staff_headers, action="publish", post_ids=[])
    assert resp.status_code == 400
    assert "选择" in resp.json()["message"]


@pytest.mark.asyncio
async def test_unknown_ids_return_404(client, staff_headers):
    resp = await _batch(client, staff_headers, action="publish", post_ids=[999999])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unknown_action_rejected(client, staff_headers, test_post):
    resp = await _batch(client, staff_headers, action="explode", post_ids=[test_post.id])
    assert resp.status_code == 400
    assert "explode" in resp.json()["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["add_tag", "remove_tag"])
async def test_tag_actions_require_tag_ids(client, staff_headers, test_post, action):
    resp = await _batch(client, staff_headers, action=action, post_ids=[test_post.id])
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_move_category_requires_category_id(client, staff_headers, test_post):
    resp = await _batch(client, staff_headers, action="move_category", post_ids=[test_post.id])
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_batch_requires_staff(client, auth_headers, test_post):
    resp = await client.post(
        URL, json={"action": "publish", "post_ids": [test_post.id]}, headers=auth_headers
    )
    assert resp.status_code in (401, 403)
