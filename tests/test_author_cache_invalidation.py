"""作者资料变更 → 文章缓存失效守卫。

背景：文章详情缓存 `post:{slug}:{lang}` 的响应体嵌了 author 段
（username/nickname/avatar/bio/website/github/cover_image，见 blog._build_author_data）。
作者改昵称/头像后，若不失效自己的文章缓存，前台每篇文章的作者卡片
在 TTL 内仍显示旧昵称/头像。

本用例直接打 update_profile 这个统一入口（self /me、/me/avatar、/me/cover、admin 编辑都走它），
验证：
1. 命中展示字段 → 清详情 + 列表缓存；
2. 只改隐私字段（email / password）→ 不动文章缓存（避免无谓的全量失效）。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache, make_cache_key
from backend.models.blog import Post
from backend.services.user_service import UserService


async def _seed(slug: str) -> tuple[str, str]:
    detail_key = make_cache_key("post", slug, "zh")
    list_key = make_cache_key("posts", "list", "zh")
    await cache.set(detail_key, {"stale": True}, ttl=600)
    await cache.set(list_key, {"stale": True}, ttl=600)
    assert await cache.get(detail_key) is not None
    assert await cache.get(list_key) is not None
    return detail_key, list_key


@pytest.mark.asyncio
async def test_visible_author_field_clears_post_caches(db_session: AsyncSession, test_post: Post):
    detail_key, list_key = await _seed(test_post.slug)

    service = UserService(db_session)
    await service.update_profile(test_post.author_id, {"nickname": "换掉的昵称"})
    await db_session.commit()

    assert await cache.get(detail_key) is None, "改昵称后作者的文章详情缓存未清"
    assert await cache.get(list_key) is None, "改昵称后列表/RSS 缓存未清"


@pytest.mark.asyncio
async def test_avatar_update_clears_post_caches(db_session: AsyncSession, test_post: Post):
    detail_key, _ = await _seed(test_post.slug)

    service = UserService(db_session)
    await service.update_profile(test_post.author_id, {"avatar": "https://cdn/new.png"})
    await db_session.commit()

    assert await cache.get(detail_key) is None, "改头像后详情缓存未清"


@pytest.mark.asyncio
async def test_private_field_change_keeps_post_caches(db_session: AsyncSession, test_post: Post):
    # email / password 不进 author 展示段，改它们不应触发文章缓存全量失效。
    detail_key, list_key = await _seed(test_post.slug)

    service = UserService(db_session)
    await service.update_profile(
        test_post.author_id,
        {"email": "changed@example.com", "password": "NewStrongPass123!"},
    )
    await db_session.commit()

    assert await cache.get(detail_key) is not None, "隐私字段变更不应清详情缓存"
    assert await cache.get(list_key) is not None, "隐私字段变更不应清列表缓存"
