"""P1-8 回归：空值哨兵必须与「未命中」可区分。

旧 ``get()`` 把 NULL_MARKER 压成 None，``get_or_set`` 用 ``is not None`` 判命中，
导致 ``set_null()`` 写了等于没写：随机不存在的 user_id 会 N 次请求 N 次回源 DB。
"""

import pytest

from backend.core.cache_v2 import TwoLevelCache


@pytest.mark.asyncio
async def test_get_with_hit_distinguishes_null_from_miss():
    cache = TwoLevelCache()
    assert await cache.get_with_hit("review:absent") == (False, None)
    await cache.set_null("review:absent", ttl=60)
    assert await cache.get_with_hit("review:absent") == (True, None)


@pytest.mark.asyncio
async def test_get_or_set_fetches_missing_value_only_once():
    cache = TwoLevelCache()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return None

    for _ in range(3):
        assert await cache.get_or_set("review:missing-user", fetch, ttl=60, null_ttl=60) is None
    assert calls == 1
