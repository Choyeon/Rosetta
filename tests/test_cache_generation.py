"""列表缓存世代键回归。

验证：
- namespaced_key 为 versioned 命名空间嵌入世代段；非 versioned 退化为普通拼接。
- invalidate_cache("posts") 撞世代（bump）而非删除版本化键，避免列表缓存惊群；
  明文旧式 posts* 键仍被清理（兼容历史/测试路径）。
- 世代自增后，读侧转向新世代键 → 旧键自然过期（命中失效）。
"""

import pytest

from backend.core.cache import cache, invalidate_cache, namespaced_key


@pytest.fixture(autouse=True)
async def _reset_cache():
    cache._generations.clear()
    await cache.clear()
    yield
    cache._generations.clear()
    await cache.clear()


@pytest.mark.asyncio
async def test_namespaced_key_embeds_generation():
    assert await namespaced_key("posts", "ranking", "week", "10") == "posts:g0:ranking:week:10"
    # 非 versioned 命名空间退化为普通拼接
    assert await namespaced_key("site_config") == "site_config"
    assert await namespaced_key("site_config", "x") == "site_config:x"


@pytest.mark.asyncio
async def test_generation_bump_changes_key():
    before = await namespaced_key("posts", "x")
    await cache.bump_generation("posts")
    after = await namespaced_key("posts", "x")
    assert before == "posts:g0:x"
    assert after == "posts:g1:x"


@pytest.mark.asyncio
async def test_invalidate_posts_bumps_generation_not_versioned_delete():
    vkey = await namespaced_key("posts", "ranking", "week", "10")
    await cache.set(vkey, {"old": True}, 60)
    # 明文旧式 posts* 键（无 :g 段）——历史/测试路径
    legacy = "posts:list:zh:1:10"
    await cache.set(legacy, {"old": True}, 60)

    await invalidate_cache("posts")

    # 世代自增
    assert await cache.get_generation("posts") == "1"
    # 版本化旧键仍在（未被删除，靠 TTL 自然过期，无惊群）
    assert await cache.get(vkey) is not None
    # 明文旧式键被清理
    assert await cache.get(legacy) is None


@pytest.mark.asyncio
async def test_read_after_bump_misses():
    await cache.set(await namespaced_key("posts", "ranking", "week", "10"), {"items": [1]}, 60)
    # 同一世代命中
    assert await cache.get(await namespaced_key("posts", "ranking", "week", "10")) is not None
    await cache.bump_generation("posts")
    # 新世代读 miss（旧键自然过期）
    assert await cache.get(await namespaced_key("posts", "ranking", "week", "10")) is None


@pytest.mark.asyncio
async def test_non_versioned_invalidate_still_deletes():
    await cache.set("categories:raw-i18n", {"x": 1}, 60)
    await invalidate_cache("categories")
    assert await cache.get("categories:raw-i18n") is None
