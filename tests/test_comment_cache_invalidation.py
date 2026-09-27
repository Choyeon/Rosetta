"""评论写操作 → 文章展示缓存失效守卫。

背景：列表缓存（``posts*`` 前缀）里的列表项嵌了 ``comments_count``，而读侧
**不会**当场重算它（只有详情读侧会重算计数）。评论的审核/删除改的正是
"可见评论集合"——旧实现里 comments.py 与 admin.py 的六个评论写端点一次缓存都没清：
管理员批准一条评论，列表页/首页的"N 评论"在 TTL(600s) 内纹丝不动，
看起来就像"审核没生效"。详情键一并失效是为了两层快照口径一致。

反方向同样要守住：评论点赞改的是 ``comment.likes_count``，它在文章的
详情与列表响应体里都不存在，清文章缓存属于无谓的缓存雪崩。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache, make_cache_key
from backend.models.blog import Comment, Post


async def _seed_stale(slug: str) -> tuple[str, str]:
    detail_key = make_cache_key("post", slug, "zh")
    list_key = make_cache_key("posts", "list", "zh")
    await cache.set(detail_key, {"stale": True}, ttl=600)
    await cache.set(list_key, {"stale": True}, ttl=600)
    assert await cache.get(detail_key) is not None
    assert await cache.get(list_key) is not None
    return detail_key, list_key


async def _make_pending_comment(db_session: AsyncSession, post: Post, content: str) -> Comment:
    """直接落一条"待审核（不可见）"的评论，避免依赖站点的自动审核开关。"""
    comment = Comment(
        post_id=post.id,
        user_id=None,
        parent_id=None,
        author_name="访客",
        author_email=None,
        author_website=None,
        author_ip=None,
        author_user_agent=None,
        content=content,
        status="pending",
        active=False,
        likes_count=0,
        is_pinned=False,
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


@pytest.mark.asyncio
async def test_approve_comment_clears_post_caches(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_post: Post,
):
    comment = await _make_pending_comment(db_session, test_post, "等待放行的评论")
    detail_key, list_key = await _seed_stale(test_post.slug)

    r = await client.post(f"/api/admin/comments/{comment.id}/approve", headers=staff_headers)
    assert r.status_code == 200, r.text

    assert await cache.get(detail_key) is None, "批准评论后文章详情缓存的评论数仍是旧值"
    assert await cache.get(list_key) is None, "批准评论后列表缓存的评论数仍是旧值"


@pytest.mark.asyncio
async def test_spam_comment_clears_post_caches(
    client: AsyncClient,
    staff_headers: dict,
    test_comment: Comment,
    test_post: Post,
):
    # 已展示的评论被判垃圾 → 可见数减少，同样必须失效。
    detail_key, list_key = await _seed_stale(test_post.slug)

    r = await client.post(f"/api/admin/comments/{test_comment.id}/spam", headers=staff_headers)
    assert r.status_code == 200, r.text

    assert await cache.get(detail_key) is None
    assert await cache.get(list_key) is None


@pytest.mark.asyncio
async def test_batch_action_clears_post_caches(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_post: Post,
):
    c1 = await _make_pending_comment(db_session, test_post, "批量批准 1")
    c2 = await _make_pending_comment(db_session, test_post, "批量批准 2")
    detail_key, list_key = await _seed_stale(test_post.slug)

    r = await client.post(
        "/api/admin/comments/batch",
        json={"ids": [c1.id, c2.id], "action": "approve"},
        headers=staff_headers,
    )
    assert r.status_code == 200, r.text

    assert await cache.get(detail_key) is None, "批量审核后文章缓存评论数未更新"
    assert await cache.get(list_key) is None


@pytest.mark.asyncio
async def test_admin_patch_comment_clears_post_caches(
    client: AsyncClient,
    staff_headers: dict,
    test_comment: Comment,
    test_post: Post,
):
    detail_key, list_key = await _seed_stale(test_post.slug)

    r = await client.patch(
        f"/api/admin/comments/{test_comment.id}",
        json={"status": "rejected"},
        headers=staff_headers,
    )
    assert r.status_code == 200, r.text

    assert await cache.get(detail_key) is None, "下架评论后详情缓存仍是旧评论数"
    assert await cache.get(list_key) is None


@pytest.mark.asyncio
async def test_admin_delete_comment_clears_post_caches(
    client: AsyncClient,
    staff_headers: dict,
    test_comment: Comment,
    test_post: Post,
):
    detail_key, list_key = await _seed_stale(test_post.slug)

    r = await client.delete(f"/api/admin/comments/{test_comment.id}", headers=staff_headers)
    assert r.status_code == 200, r.text

    assert await cache.get(detail_key) is None, "删除评论后详情缓存仍是旧评论数"
    assert await cache.get(list_key) is None


@pytest.mark.asyncio
async def test_comment_like_keeps_post_caches(
    client: AsyncClient,
    test_comment: Comment,
    test_post: Post,
):
    """点赞数不属于文章响应体，不该顺手清掉整篇文章的展示缓存。"""
    detail_key, list_key = await _seed_stale(test_post.slug)

    r = await client.post(f"/api/comments/{test_comment.id}/like")
    assert r.status_code == 200, r.text

    assert await cache.get(detail_key) is not None, "无关写操作不应清详情缓存"
    assert await cache.get(list_key) is not None, "无关写操作不应清列表缓存"
