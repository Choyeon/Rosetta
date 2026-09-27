"""站点设置写入编码守卫：显式 null 不得把字面量 "None" 存进 SiteConfig.value。

`update_site_settings` 的写回是 `SiteConfig.value = str(value)`（value 是各种 Python 类型）。
`str(None)` == "None"，前台把 author_bio / site_url 等读回时会原样渲染出字符串 "None"，
属于静默数据污染。修复后：None → "" 清空、bool → "true"/"false"、其余标量按 str。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.core import SiteConfig


async def _value(db: AsyncSession, key: str) -> str | None:
    return await db.scalar(select(SiteConfig.value).where(SiteConfig.key == key))


@pytest.mark.asyncio
async def test_text_setting_null_clears_not_literal_none(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """显式清空文本设置应落库为空串，而不是字符串 "None"。"""
    r = await client.post("/api/admin/settings", json={"site_url": None}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert await _value(db_session, "SITE_URL") == ""


@pytest.mark.asyncio
async def test_bool_settings_store_canonical_lowercase(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """bool 设置统一小写存储，与读取侧 `.lower() == "true"` 规范化口径一致。"""
    r = await client.post(
        "/api/admin/settings",
        json={"enable_comments": True, "enable_search": False},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    assert await _value(db_session, "ENABLE_COMMENTS") == "true"
    assert await _value(db_session, "ENABLE_SEARCH") == "false"
