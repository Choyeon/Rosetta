"""插件钩子变化的缓存失效回归。

插件的 the_content / the_excerpt filter 结果嵌在详情（post:{slug}:{lang}）、
列表与 RSS（posts*）响应缓存里。启停/改设置若不抹这些键，访客在 TTL 内
仍看到旧钩子集的渲染——后台开关拨了没效果。_invalidate_rendered_content
是这条协同链路的收口，本文件钉住它的删除范围（该删的删、不该删的不误伤）。
"""

import pytest

from backend.api.plugins import _invalidate_rendered_content
from backend.core.cache import cache


@pytest.mark.asyncio
async def test_invalidate_rendered_content_clears_detail_list_rss_only():
    await cache.set("post:hello-world:zh", {"id": 1}, 60)
    await cache.set("posts:list:zh:1:10", {"items": []}, 60)
    await cache.set("posts:rss:zh:20", "<rss/>", 60)
    # 与文章渲染无关的键必须存活：误清会在下次插件操作后引发对应面板集体回源
    await cache.set("categories:raw-i18n", {"items": []}, 60)
    await cache.set("site_stats:summary", {"views": 1}, 60)

    await _invalidate_rendered_content(reason="unit-test")

    assert await cache.get("post:hello-world:zh") is None
    assert await cache.get("posts:list:zh:1:10") is None
    assert await cache.get("posts:rss:zh:20") is None
    assert await cache.get("categories:raw-i18n") is not None
    assert await cache.get("site_stats:summary") is not None
