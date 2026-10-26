"""独立页（`/pages` 写路径）必须失效前端页面缓存。

背景：独立页的 HTML 由 Nitro 的页面缓存消费（兼容口 `/page/<slug>` 走 600s swr），
而 `create_page` / `update_page` / `delete_page` 此前是**全仓唯一**三条既不清后端缓存、
也不调 `purge_frontend_page_cache` 的内容写路径。表现：

* 管理员改了「关于」页正文，访客最长 10 分钟仍看到旧内容；
* 新建页面在缓存窗口内先拿到 404；
* 删除页面后已删内容继续对外可见。

同族写路径（文章 / 分类 / 标签 / 公告 / 导航）全都调它，所以这里按"三次写操作各自
触发一次、读操作一次都不触发"两侧钉住——反过来（GET 也 purge）等于每次浏览都把
整站 HTML 缓存清空，比不缓存更糟。
"""

import pytest
from httpx import AsyncClient

from backend.api import core as core_api

SLUG = "cache-purge-probe"


def _payload(**overrides):
    body = {
        "title": {"zh": "缓存验证页", "en": "Cache probe"},
        "slug": SLUG,
        "content": {"zh": "第一版正文", "en": "first"},
        "status": "published",
    }
    body.update(overrides)
    return body


def _unwrap(body: dict) -> dict:
    return body.get("data", body) if isinstance(body, dict) else body


@pytest.mark.asyncio
async def test_page_writes_purge_frontend_cache(
    client: AsyncClient, admin_headers: dict, monkeypatch
):
    reasons: list[str] = []
    monkeypatch.setattr(
        core_api, "purge_frontend_page_cache", lambda reason="": reasons.append(reason)
    )

    created = await client.post("/api/pages", json=_payload(), headers=admin_headers)
    assert created.status_code in (200, 201), created.text
    page_id = _unwrap(created.json())["id"]
    assert len(reasons) == 1, f"创建页面未清前台缓存: {reasons}"
    assert SLUG in reasons[0]

    updated = await client.put(
        f"/api/pages/{page_id}",
        json={"content": {"zh": "第二版正文", "en": "second"}},
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text
    assert len(reasons) == 2, f"更新页面未清前台缓存: {reasons}"

    # 读路径绝不允许清缓存：GET 每个访客都会打，清了等于整站 HTML 缓存形同虚设。
    read = await client.get(f"/api/pages/{SLUG}")
    assert read.status_code == 200
    assert len(reasons) == 2, f"读接口不该触发缓存清除: {reasons}"

    deleted = await client.delete(f"/api/pages/{page_id}", headers=admin_headers)
    assert deleted.status_code == 200, deleted.text
    assert len(reasons) == 3, f"删除页面未清前台缓存: {reasons}"
    assert all(SLUG in reason for reason in reasons)
