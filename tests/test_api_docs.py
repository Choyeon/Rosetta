"""
开发文档 API 测试：`GET /api/docs/list` 与 `GET /api/docs/{slug}`

覆盖点：
1. 目录返回结构（items 排序 / available 标记 / 无 `docs_dir`）
2. 合法 slug 能读到 Markdown 正文
3. 未注册 slug 走 404（不是磁盘 404，避免成为文件存在性探针）
4. slug 路径参数受正则约束：`../` 之类的越权形态根本进不了处理函数
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.api.docs import DOCS_DIR


@pytest.mark.asyncio
async def test_docs_list_shape(client: AsyncClient):
    """目录接口返回白名单条目，且不回传服务器磁盘路径"""
    r = await client.get("/api/docs/list")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    items = data["items"]
    assert len(items) >= 4, f"内建文档应不少于 4 篇，实际={len(items)}"
    assert "docs_dir" not in data, (
        "未鉴权接口不得回传 DOCS_DIR 绝对路径（内部实现细节，可用于拼装后续攻击面）"
    )
    # order 升序 + index 恒为 available（后端可动态生成首页）
    orders = [it["order"] for it in items]
    assert orders == sorted(orders), f"items 必须按 order 升序，实际={orders}"
    index_row = next(it for it in items if it["slug"] == "index")
    assert index_row["available"] is True, "index 由后端兜底生成，永远可用"


@pytest.mark.asyncio
async def test_docs_get_registered_slug(client: AsyncClient):
    """已注册 slug 能取到 markdown 正文与标题"""
    r = await client.get("/api/docs/rest-api")
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["slug"] == "rest-api"
    assert body["title"], "标题不得为空"
    assert len(body["markdown"]) > 200, "正文应为完整 Markdown，而非占位串"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "slug,expected",
    [
        # 合法形态但未注册 → 处理函数白名单挡下
        ("not-a-real-doc", 404),
        # 非法形态 → 路径参数正则挡下；两种情形都必须对客户端泄露同样少的信息
        ("..%2F..%2F.env", (400, 404, 422)),
        ("%2E%2E%2Fetc%2Fpasswd", (400, 404, 422)),
    ],
)
async def test_docs_slug_cannot_escape_whitelist(client: AsyncClient, slug: str, expected):
    """slug 既受 `^[a-z][a-z0-9-]{1,63}$` 约束又受 _KNOWN_SLUGS 白名单约束"""
    r = await client.get(f"/api/docs/{slug}")
    codes = expected if isinstance(expected, tuple) else (expected,)
    assert r.status_code in codes, f"{slug!r} 应被拒绝，实际 {r.status_code}: {r.text}"
    assert str(DOCS_DIR.resolve()) not in r.text, (
        f"错误响应不得回显文档根目录绝对路径，实际={r.text}"
    )
