"""定时发布端点（``PUT /api/admin/posts/{id}/schedule``）的行为守卫。

这个路由此前没有任何用例覆盖，于是两个"说了会发、其实不发"的死状态活了很久：

1. ``status`` 缺省为 None → 草稿仍是草稿；而 ``publish_due_posts`` 与 main.py 的
   定时循环只捞 ``scheduled`` / ``published``，草稿永远不会被发布，却一直躺在
   ``GET /admin/posts/scheduled`` 里（scheduled_at 早已过期）。
2. ``status="scheduled"`` 被 pydantic 的 ``^(draft|published)$`` pattern 直接 422，
   而 scheduled 恰恰是创建文章时真正表示"等待发布"的那个值。

下面按"缺省、显式、过去时间、非法值"四侧钉住。
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from backend.api.scheduled_posts import publish_due_posts
from backend.models.blog import Post
from backend.utils.compat import UTC


async def _make_draft(db_session, author) -> Post:
    post = Post(
        title={"zh": "待排期草稿"},
        slug="schedule-fixture-draft",
        status="draft",
        content="正文",
        author_id=author.id,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.mark.asyncio
async def test_default_status_schedules_instead_of_staying_draft(
    client, db_session, admin_user, admin_headers
):
    """不传 status 时，草稿必须变成真正会被扫描器发布的 scheduled 状态。"""
    post = await _make_draft(db_session, admin_user)
    fire_at = datetime.now(UTC) + timedelta(days=2)

    response = await client.put(
        f"/api/admin/posts/{post.id}/schedule",
        json={"scheduled_at": fire_at.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text

    await db_session.refresh(post)
    assert post.status == "scheduled", "缺省状态下文章仍是草稿，扫描器永远不会发布它"
    assert post.scheduled_at is not None
    assert post.published_at is None

    # 扫描器认的就是这个组合
    listed = await client.get("/api/admin/posts/scheduled", headers=admin_headers)
    assert listed.status_code == 200
    assert any(row["id"] == post.id for row in listed.json())


@pytest.mark.asyncio
async def test_scheduled_status_is_accepted(client, db_session, admin_user, admin_headers):
    """显式传 scheduled 必须被接受（旧 pattern 会直接 422）。"""
    post = await _make_draft(db_session, admin_user)
    fire_at = datetime.now(UTC) + timedelta(days=1)

    response = await client.put(
        f"/api/admin/posts/{post.id}/schedule",
        json={"scheduled_at": fire_at.isoformat(), "status": "scheduled"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    await db_session.refresh(post)
    assert post.status == "scheduled"


@pytest.mark.asyncio
async def test_draft_status_is_rejected_not_silently_stored(
    client, db_session, admin_user, admin_headers
):
    """draft + 定时发布是死状态，必须显式拒绝而不是回"已设置"。"""
    post = await _make_draft(db_session, admin_user)
    fire_at = datetime.now(UTC) + timedelta(days=1)

    response = await client.put(
        f"/api/admin/posts/{post.id}/schedule",
        json={"scheduled_at": fire_at.isoformat(), "status": "draft"},
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text

    await db_session.refresh(post)
    assert post.status == "draft"
    assert post.scheduled_at is None


@pytest.mark.asyncio
async def test_past_time_publishes_immediately(client, db_session, admin_user, admin_headers):
    """计划时间已过去：立即发布，而不是等下一个扫描周期。"""
    post = await _make_draft(db_session, admin_user)
    past = datetime.now(UTC) - timedelta(hours=2)

    response = await client.put(
        f"/api/admin/posts/{post.id}/schedule",
        json={"scheduled_at": past.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text

    await db_session.refresh(post)
    assert post.status == "published"
    assert post.scheduled_at is None
    assert post.published_at is not None


@pytest.mark.asyncio
async def test_publish_due_posts_handles_scheduled_rows(db_session, admin_user):
    """到期扫描必须把 scheduled 行推进成 published，并清空 scheduled_at。

    原先这条写成 `if published: assert …`——publish_due_posts 只捞 status=="published" 时
    返回 0，断言整块被跳过，用例永远绿却什么都没测。判据必须是无条件断言。
    """
    due = await _make_draft(db_session, admin_user)
    due.slug = "schedule-due-post"
    due.status = "scheduled"
    due.scheduled_at = datetime.now(UTC) - timedelta(minutes=5)
    await db_session.commit()

    published = await publish_due_posts(db_session)
    await db_session.commit()

    assert published == 1, "到期的 scheduled 行没被推进——GET 口承诺的'先到点先发布'是空话"
    refreshed = (await db_session.execute(select(Post).where(Post.id == due.id))).scalar_one()
    assert refreshed.status == "published"
    assert refreshed.scheduled_at is None
    assert refreshed.published_at is not None


@pytest.mark.asyncio
async def test_due_scheduled_post_leaves_the_queue(client, db_session, admin_user, admin_headers):
    """到点的文章不得继续躺在待发布队列里（列表口的承诺与扫描器必须同轨）。"""
    post = await _make_draft(db_session, admin_user)
    post.slug = "schedule-due-list"
    post.status = "scheduled"
    post.scheduled_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    listed = await client.get("/api/admin/posts/scheduled", headers=admin_headers)
    assert listed.status_code == 200
    assert not any(row["id"] == post.id for row in listed.json()), "已到点的定时文章仍在队列里"

    await db_session.refresh(post)
    assert post.status == "published"


@pytest.mark.asyncio
async def test_cancel_schedule_of_scheduled_post_does_not_create_limbo(
    client, db_session, admin_user, admin_headers
):
    """取消 scheduled 行的计划时间必须同时回到 draft。

    只清 scheduled_at 会留下"scheduled 状态 + 无计划时间"：扫描循环只捞 scheduled_at
    非空的行，于是这篇文章既不会被发布，也不再出现在待发布队列里——后台显示"等待发布"，
    前台永远等不到。
    """
    post = await _make_draft(db_session, admin_user)
    fire_at = datetime.now(UTC) + timedelta(days=3)
    await client.put(
        f"/api/admin/posts/{post.id}/schedule",
        json={"scheduled_at": fire_at.isoformat()},
        headers=admin_headers,
    )

    cancelled = await client.delete(f"/api/admin/posts/{post.id}/schedule", headers=admin_headers)
    assert cancelled.status_code == 200, cancelled.text
    assert "草稿" in cancelled.json()["message"], "提示语必须说清文章回到了草稿，否则作者以为还会发"

    await db_session.refresh(post)
    assert post.scheduled_at is None
    assert post.status == "draft", "scheduled 且无计划时间 = 谁也不会推进它的死状态"

    # 也不会继续占着待发布队列
    listed = await client.get("/api/admin/posts/scheduled", headers=admin_headers)
    assert not any(row["id"] == post.id for row in listed.json())


@pytest.mark.asyncio
async def test_cancel_schedule_of_published_post_clears_read_caches(
    client, db_session, admin_user, admin_headers, monkeypatch
):
    """published 行取消计划时间＝首次对匿名方可见，必须清读侧缓存（与立即发布同口径）。"""
    from backend.api import scheduled_posts as sp

    post = await _make_draft(db_session, admin_user)
    post.slug = "schedule-cancel-published"
    post.status = "published"
    post.scheduled_at = datetime.now(UTC) + timedelta(days=1)
    await db_session.commit()

    calls: list[str] = []
    monkeypatch.setattr(sp, "invalidate_cache", _spy(calls, "invalidate_cache"))
    monkeypatch.setattr(
        sp, "invalidate_post_detail_cache", _spy(calls, "invalidate_post_detail_cache")
    )
    monkeypatch.setattr(
        sp, "invalidate_post_aggregate_caches", _spy(calls, "invalidate_post_aggregate_caches")
    )

    cancelled = await client.delete(f"/api/admin/posts/{post.id}/schedule", headers=admin_headers)
    assert cancelled.status_code == 200, cancelled.text

    assert "invalidate_post_detail_cache" in calls, "详情缓存不清 = TTL 内匿名方仍拿不到正文"
    assert "invalidate_post_aggregate_caches" in calls, "聚合+前端页面缓存不清 = 首页迟迟不出现这篇"


def _spy(sink: list[str], name: str):
    """把三个失效函数换成记录调用的异步桩（不真去动缓存）。"""

    async def _inner(*_args, **_kwargs):
        sink.append(name)

    return _inner
