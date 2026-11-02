"""批量发布 / 转草稿必须清空 ``scheduled_at``。

起因：待发布队列 `GET /api/admin/posts/scheduled` 的判据是
`Post.scheduled_at.is_not(None)`——它不看 status；扫描器 `publish_due_posts` 又按
`status in ("scheduled", "published") AND scheduled_at <= now` 捞行。而批量口
`POST /api/admin/posts/batch` 原先只改 status，留下的计划时间意味着：

  ① 一篇已被批量转成草稿的文章仍挂在管理端"待发布"列表里（草稿不参与定时发布，
     `PUT /posts/{id}/schedule` 对 draft 直接 400）；
  ② 一篇已被批量发布的文章会被 60s 扫描器反复当成"到期定时稿"重进发布流程。

单篇路径与同族的 `POST /blog/posts/batch-status` 一直在清空这一列，只有批量口漏，
属于"同一动作两条路径、一条少一步"的分叉。故这里把两条动作都钉住，并额外证明
待发布列表真的不再包含它（判据的消费面，不只是列值）。
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from backend.models.blog import Category, Post

BATCH_URL = "/api/admin/posts/batch"
SCHEDULED_URL = "/api/admin/posts/scheduled"


async def _seed_post(
    db_session,
    author,
    category: Category,
    slug: str,
    status_value: str,
    scheduled_at: datetime | None,
    published_at: datetime | None = None,
) -> Post:
    post = Post(
        title={"zh": "批量口径文章", "en": "Batch fixture post"},
        slug=slug,
        content={"zh": "正文", "en": "Body"},
        excerpt={"zh": "摘要", "en": "Excerpt"},
        author_id=author.id,
        category_id=category.id,
        status=status_value,
        allow_comments=True,
        scheduled_at=scheduled_at,
        published_at=published_at,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _reload(db_session, post_id: int) -> Post:
    db_session.expire_all()
    return (await db_session.execute(select(Post).where(Post.id == post_id))).scalars().one()


async def _queued_ids(client, headers) -> list[int]:
    resp = await client.get(SCHEDULED_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    return [row["id"] for row in resp.json()]


async def test_batch_draft_clears_stale_schedule(
    client, staff_headers, staff_user, test_category, db_session
):
    """批量转草稿后不得留在待发布队列里。"""
    past = datetime.now(UTC) - timedelta(hours=1)
    post = await _seed_post(
        db_session,
        staff_user,
        test_category,
        "batch-draft-stale",
        "published",
        scheduled_at=past,
        published_at=past,
    )

    resp = await client.post(
        BATCH_URL,
        json={"action": "draft", "post_ids": [post.id]},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text

    row = await _reload(db_session, post.id)
    assert row.status == "draft"
    assert row.scheduled_at is None
    assert post.id not in await _queued_ids(client, staff_headers)


async def test_batch_publish_clears_schedule_and_sets_published_at(
    client, staff_headers, staff_user, test_category, db_session
):
    """批量发布（含未到点的定时稿）必须落 published_at 并退出待发布队列。"""
    future = datetime.now(UTC) + timedelta(days=2)
    post = await _seed_post(
        db_session,
        staff_user,
        test_category,
        "batch-publish-scheduled",
        "scheduled",
        scheduled_at=future,
    )
    assert post.id in await _queued_ids(client, staff_headers)

    resp = await client.post(
        BATCH_URL,
        json={"action": "publish", "post_ids": [post.id]},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text

    row = await _reload(db_session, post.id)
    assert row.status == "published"
    assert row.scheduled_at is None
    assert row.published_at is not None
    assert post.id not in await _queued_ids(client, staff_headers)
