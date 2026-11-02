"""单篇 PUT 的状态分支必须把计划时间一起处理干净，且文章写口要连带清掉分类/标签列表缓存。

两件事同属「编辑器保存」这条链路的连带动作，此前都只差一处：

1. `PUT /blog/posts/{id}` 只在「提交的时间已过」那一支清了 `scheduled_at`，
   「库里回读到的旧值已过点」这一支和「转草稿」都没有清。残留值的直接后果是
   `GET /admin/posts/scheduled`（判据是 `scheduled_at` 非空，不看 status）继续把
   这篇已发布/已转草稿的文章摆在待发布队列里；草稿那条还会被 `GET /posts/{id}/edit`
   原样回读，作者下次只切状态不填时间就把它提交回去。
   批量口 `POST /blog/posts/batch-status` 早就两条都清（见
   `test_post_batch_schedule_cleared.py`），单篇口此前是唯一的不一致点。
2. `GET /blog/categories` 与 `GET /blog/tags` 把按 `publicly_listable_posts()`
   现算的 `post_count` 整列表写进 `categories:raw-i18n` / `tags:raw-i18n`（含 `-all`
   两份），而这两个前缀此前只有分类/标签自己的 CRUD 端点会清——发一篇新文章、
   改分类、转草稿都不会。于是整个 TTL 内前台分类/标签目录与后台标签下拉报旧章数。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from backend.core.cache import CACHE_KEY_CATEGORIES, CACHE_KEY_TAGS, cache
from backend.models.blog import Category, Post, Tag
from backend.models.user import User

I18N = {"zh": "标题", "en": "Title", "ja": "タイトル", "zh_Hant": "標題"}


async def _seed_post(
    db_session,
    author: User,
    category: Category,
    tag: Tag,
    slug: str,
    status_value: str = "published",
    scheduled_at: datetime | None = None,
) -> Post:
    post = Post(
        title={**I18N},
        content={**I18N, "zh": "正文内容 " * 30},
        excerpt=None,
        slug=slug,
        author_id=author.id,
        category_id=category.id,
        status=status_value,
        visibility="public",
        published_at=None,
        scheduled_at=scheduled_at,
        allow_comments=True,
        tags=[tag],
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _rows(client: AsyncClient, headers: dict, path: str) -> list[dict]:
    resp = await client.get(path, headers=headers)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def _count(rows: list[dict], resource_id: int) -> int:
    for row in rows:
        if row.get("id") == resource_id:
            return int(row.get("post_count") or 0)
    raise AssertionError(f"id={resource_id} 不在列表里：{[r.get('id') for r in rows]}")


@pytest.mark.asyncio
async def test_categories_cache_is_warm_after_first_read(
    client: AsyncClient, staff_headers, test_category, test_tag, staff_user, db_session
):
    """前置条件：列表口确实把结果写进了缓存。

    没有这一条，下面「计数会刷新」的用例在缓存从未生效时也会恒真通过。
    """
    await _seed_post(db_session, staff_user, test_category, test_tag, "warm-a")
    await _rows(client, staff_headers, "/api/blog/categories")
    assert await cache.get(CACHE_KEY_CATEGORIES) is not None, "分类列表口没有写缓存"
    await _rows(client, staff_headers, "/api/blog/tags")
    assert await cache.get(CACHE_KEY_TAGS) is not None, "标签列表口没有写缓存"


@pytest.mark.asyncio
async def test_create_post_refreshes_taxonomy_counts(
    client: AsyncClient, staff_headers, test_category, test_tag, staff_user, db_session
):
    await _seed_post(db_session, staff_user, test_category, test_tag, "count-a")

    rows = await _rows(client, staff_headers, "/api/blog/categories")
    assert _count(rows, test_category.id) == 1
    rows = await _rows(client, staff_headers, "/api/blog/tags")
    assert _count(rows, test_tag.id) == 1

    resp = await client.post(
        "/api/blog/posts",
        headers=staff_headers,
        json={
            "title": I18N,
            "content": {"zh": "新文章正文"},
            "slug": "count-b",
            "status": "published",
            "category_id": test_category.id,
            "tag_ids": [test_tag.id],
        },
    )
    assert resp.status_code == 201, resp.text

    rows = await _rows(client, staff_headers, "/api/blog/categories")
    assert _count(rows, test_category.id) == 2, "发文后分类计数仍是缓存里的旧值"
    rows = await _rows(client, staff_headers, "/api/blog/tags")
    assert _count(rows, test_tag.id) == 2, "发文后标签计数仍是缓存里的旧值"


@pytest.mark.asyncio
async def test_put_to_draft_refreshes_taxonomy_counts(
    client: AsyncClient, staff_headers, test_category, test_tag, staff_user, db_session
):
    keep = await _seed_post(db_session, staff_user, test_category, test_tag, "draft-keep")
    moved = await _seed_post(db_session, staff_user, test_category, test_tag, "draft-away")

    rows = await _rows(client, staff_headers, "/api/blog/categories")
    assert _count(rows, test_category.id) == 2

    resp = await client.put(
        f"/api/blog/posts/{moved.id}",
        headers=staff_headers,
        json={"status": "draft"},
    )
    assert resp.status_code == 200, resp.text

    rows = await _rows(client, staff_headers, "/api/blog/categories")
    assert _count(rows, test_category.id) == 1, "转草稿后分类计数没跟着回收"
    rows = await _rows(client, staff_headers, "/api/blog/tags")
    assert _count(rows, test_tag.id) == 1, "转草稿后标签计数没跟着回收"
    await db_session.refresh(keep)
    assert keep.status == "published", "只有被转草稿的那篇该退出计数"


@pytest.mark.asyncio
async def test_put_to_draft_clears_stale_schedule(
    client: AsyncClient, staff_headers, test_category, test_tag, staff_user, db_session
):
    future = datetime.now(UTC) + timedelta(days=3)
    post = await _seed_post(
        db_session,
        staff_user,
        test_category,
        test_tag,
        "stale-draft",
        status_value="scheduled",
        scheduled_at=future,
    )

    resp = await client.put(
        f"/api/blog/posts/{post.id}",
        headers=staff_headers,
        json={"status": "draft"},
    )
    assert resp.status_code == 200, resp.text

    await db_session.refresh(post)
    assert post.status == "draft"
    assert post.scheduled_at is None, "草稿仍带着计划时间，会挂在待发布队列里"

    edit = await client.get(f"/api/blog/posts/{post.id}/edit", headers=staff_headers)
    assert edit.status_code == 200, edit.text
    body = edit.json()
    assert (body["data"] if "data" in body else body)["scheduled_at"] is None


@pytest.mark.asyncio
async def test_put_scheduled_with_past_stored_time_clears_schedule(
    client: AsyncClient, staff_headers, test_category, test_tag, staff_user, db_session
):
    """状态仍是 scheduled 但库里回读的旧计划时间已过点：这次 PUT 判定立即发布，
    计划时间必须当场清掉，不能等 60s 扫描器替它收尾。"""
    past = datetime.now(UTC) - timedelta(minutes=5)
    post = await _seed_post(
        db_session,
        staff_user,
        test_category,
        test_tag,
        "due-publish",
        status_value="scheduled",
        scheduled_at=past,
    )

    # 带 status=scheduled 但不带 scheduled_at——走「库里旧值已过点」那一支
    resp = await client.put(
        f"/api/blog/posts/{post.id}",
        headers=staff_headers,
        json={"status": "scheduled", "title": {**I18N, "zh": "改过的标题"}},
    )
    assert resp.status_code == 200, resp.text

    await db_session.refresh(post)
    assert post.status == "published"
    assert post.scheduled_at is None, "已就地发布的文章仍挂在待发布队列里"
    assert post.published_at is not None
    assert resp.status_code == 200, resp.text

    await db_session.refresh(post)
    assert post.status == "published"
    assert post.scheduled_at is None, "已就地发布的文章仍挂在待发布队列里"
    assert post.published_at is not None
