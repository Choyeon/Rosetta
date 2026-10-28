"""投票绑定文章 + 结束投票（PUT /api/voting/polls/{id}）。

这一族此前的形状是**后端就绪、前端无从下手**：`Poll` 与 `Post` 没有关联列，所以
进行中的投票会挂在**每一篇**文章下方；`is_active` 只能在创建时定，管理员想停一个投票
只能把它连同票数一起删掉。本文件钉住补齐后的四条口径：

1. `GET /voting/polls?post_id=` 只返回「这篇文章的专属投票 + 全站投票」，别的文章的专属投票不出现；
2. `post_id=null` 是全站投票，非空是单篇投票，且创建/更新都会校验文章真的存在（否则
   PG 在 flush 时抛外键 IntegrityError → 500，而 SQLite 测试库不强制外键、CI 看不见）；
3. `PUT` 是**显式写值**且只写请求体里出现的键（`{"is_active": false}` 不会顺带清掉标题/说明）；
4. 结束后的投票拒绝新票（400），但记录与结果仍在。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Post
from backend.models.voting import Poll


async def _mk_post(db: AsyncSession, author_id: int, category_id: int, slug: str) -> Post:
    post = Post(
        title={"zh": f"另一篇 {slug}"},
        slug=slug,
        content={"zh": "内容"},
        excerpt={"zh": "摘要"},
        author_id=author_id,
        category_id=category_id,
        status="published",
        allow_comments=True,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def _mk_poll(client: AsyncClient, admin_headers: dict, title: str, **extra: object) -> dict:
    create = await client.post(
        "/api/voting/polls",
        json={"title": title, "choices": ["甲", "乙"], **extra},
        headers=admin_headers,
    )
    assert create.status_code == 201, create.text
    return create.json()


@pytest.mark.asyncio
async def test_list_by_post_only_returns_own_and_site_wide(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_post: Post,
    test_user,
    test_category,
):
    """绑定筛选的口径：本篇章 + 全站（post_id IS NULL），不含其它文章的专属投票。"""
    other = await _mk_post(db_session, test_user.id, test_category.id, "poll-bind-other")
    site = await _mk_poll(client, admin_headers, "全站投票")
    mine = await _mk_poll(client, admin_headers, "本篇投票", post_id=test_post.id)
    theirs = await _mk_poll(client, admin_headers, "别篇投票", post_id=other.id)

    resp = await client.get(f"/api/voting/polls?post_id={test_post.id}&is_active=true")
    assert resp.status_code == 200, resp.text
    got = {p["id"] for p in resp.json()["items"]}
    assert got == {site["id"], mine["id"]}
    assert theirs["id"] not in got

    # 不传 post_id 时行为不变（后台列表要看全部），且每条都带自己的绑定关系
    listing = await client.get("/api/voting/polls?page_size=100")
    assert listing.status_code == 200, listing.text
    by_id = {p["id"]: p for p in listing.json()["items"]}
    assert by_id[site["id"]]["post_id"] is None
    assert by_id[mine["id"]]["post_id"] == test_post.id
    assert by_id[theirs["id"]]["post_id"] == other.id

    # 详情口与列表同口径：绑定关系不能只在列表里出现
    detail = await client.get(f"/api/voting/polls/{mine['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["post_id"] == test_post.id


@pytest.mark.asyncio
async def test_create_poll_rejects_unknown_post_id(client: AsyncClient, admin_headers: dict):
    """绑一个不存在的文章 → 400，不是 500，也不是"写进去了但前台永远看不到"。"""
    resp = await client.post(
        "/api/voting/polls",
        json={"title": "幽灵绑定", "choices": ["甲", "乙"], "post_id": 999_999},
        headers=admin_headers,
    )
    assert resp.status_code == 400, resp.text
    # 失败走的是全仓统一信封（{success,message,...}），不是 FastAPI 的裸 detail
    assert "文章" in (resp.json().get("message") or resp.text)


@pytest.mark.asyncio
async def test_put_partial_body_keeps_other_fields_and_closes_voting(
    client: AsyncClient, admin_headers: dict
):
    """结束投票只写 is_active：标题/说明必须原样保留，且结束后新票被拒。"""
    poll = await _mk_poll(client, admin_headers, "要被结束的投票")
    poll_id = poll["id"]
    cid = poll["choices"][0]["id"]

    resp = await client.put(
        f"/api/voting/polls/{poll_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_active"] is False
    assert body["title"] == "要被结束的投票"
    assert body["description"] == poll["description"]
    assert body["allow_multiple"] == poll["allow_multiple"]
    # 选项与票数没有被 PUT 动过
    assert [c["id"] for c in body["choices"]] == [c["id"] for c in poll["choices"]]

    vote = await client.post(f"/api/voting/polls/{poll_id}/vote", json={"choice_ids": [cid]})
    assert vote.status_code == 400, vote.text

    # 重新开启后恢复可投
    reopen = await client.put(
        f"/api/voting/polls/{poll_id}", json={"is_active": True}, headers=admin_headers
    )
    assert reopen.status_code == 200, reopen.text
    assert reopen.json()["is_active"] is True
    again = await client.post(f"/api/voting/polls/{poll_id}/vote", json={"choice_ids": [cid]})
    assert again.status_code == 200, again.text


@pytest.mark.asyncio
async def test_put_rebinds_between_post_and_site_wide(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_post: Post,
    test_user,
    test_category,
):
    """改绑与解绑（post_id=null）都是显式写值，列表口径随之变化。"""
    other = await _mk_post(db_session, test_user.id, test_category.id, "poll-rebind-other")
    poll = await _mk_poll(client, admin_headers, "先绑 A", post_id=test_post.id)
    poll_id = poll["id"]

    moved = await client.put(
        f"/api/voting/polls/{poll_id}", json={"post_id": other.id}, headers=admin_headers
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["post_id"] == other.id

    released = await client.put(
        f"/api/voting/polls/{poll_id}", json={"post_id": None}, headers=admin_headers
    )
    assert released.status_code == 200, released.text
    assert released.json()["post_id"] is None

    # 解绑后回到"每篇都看得到"
    resp = await client.get(f"/api/voting/polls?post_id={test_post.id}")
    assert resp.status_code == 200, resp.text
    assert poll_id in {p["id"] for p in resp.json()["items"]}


@pytest.mark.asyncio
async def test_put_rejects_unknown_post_id(client: AsyncClient, admin_headers: dict):
    poll = await _mk_poll(client, admin_headers, "改绑到幽灵")
    resp = await client.put(
        f"/api/voting/polls/{poll['id']}", json={"post_id": 999_999}, headers=admin_headers
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_put_requires_staff(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    """后台口：普通登录用户不得改投票定义（那是"谁能编辑全站内容"的边界）。"""
    poll = await _mk_poll(client, admin_headers, "只有管理员能改")
    resp = await client.put(
        f"/api/voting/polls/{poll['id']}", json={"is_active": False}, headers=auth_headers
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_put_unknown_poll_is_404(client: AsyncClient, admin_headers: dict):
    resp = await client.put(
        "/api/voting/polls/999999", json={"is_active": False}, headers=admin_headers
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_title_must_stay_non_empty_on_put(client: AsyncClient, admin_headers: dict):
    """空标题会被 Pydantic 的 min_length 挡下（422），不会把标题写成空串。"""
    poll = await _mk_poll(client, admin_headers, "标题不能被清空")
    resp = await client.put(
        f"/api/voting/polls/{poll['id']}", json={"title": ""}, headers=admin_headers
    )
    assert resp.status_code == 422, resp.text
    after = await client.get(f"/api/voting/polls/{poll['id']}")
    assert after.json()["title"] == "标题不能被清空"


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"title": None}, {"is_active": None}])
async def test_explicit_null_on_not_null_column_is_422_not_500(
    client: AsyncClient, admin_headers: dict, body: dict
):
    """写回走 `apply_partial_update`：显式 null 落在 NOT NULL 列上拦成 422 信封。

    这是全仓那条统一守卫（backend/core/partial_update.py）在这个新端点上的落点检查——
    漏掉它就会 flush 出 IntegrityError，客户端收到一句"服务器内部错误"。
    """
    poll = await _mk_poll(client, admin_headers, "空值不该写进 NOT NULL 列")
    resp = await client.put(f"/api/voting/polls/{poll['id']}", json=body, headers=admin_headers)
    assert resp.status_code == 422, resp.text
    assert resp.json()["success"] is False
    after = await client.get(f"/api/voting/polls/{poll['id']}")
    assert after.json()["title"] == "空值不该写进 NOT NULL 列"
    assert after.json()["is_active"] is True


def test_poll_post_fk_is_cascade_not_set_null() -> None:
    """列的形状本身就是口径：SET NULL 会把"为已删文章写的投票"升级成全站可见。

    测试引擎（conftest 自建的 engine）没挂 `PRAGMA foreign_keys=ON`，所以删文章的行为在
    这里测不出来；把"必须是 CASCADE"钉在元数据上，改坏的人当场见红，而不是等到线上
    某条旧投票突然出现在每篇文章下方。
    """
    fk = next(iter(Poll.__table__.columns["post_id"].foreign_keys))
    assert fk.target_fullname == "posts.id"
    assert fk.ondelete == "CASCADE"
    assert Poll.__table__.columns["post_id"].nullable is True
