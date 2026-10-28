"""文章「来源 / 原文出处」（``Post.source`` / ``source_url``）读写两端的回归测试。

这一族此前的形状是"半接通"：列在 ``Post`` 上、``PostBase``/``PostUpdate`` 都收这两个键、
``PostResponse``/``PostEditResponse``/``PostLocalizedResponse`` 三个读口也都回显，导入导出
还会搬运它们——但**后台编辑器表单从不发送、前台文章页从不渲染**。于是"来源"这一列
只在数据库里存在，作者写不了，读者看不见。本文件钉住接通之后的口径：

1. 写口（POST 创建 / PUT 更新）与读口（创建响应、slug 公开详情）拿到的是同一条值。
2. 不填就是默认「原创」，且 ``source_url`` 为空；PUT 显式传 null 才清掉链接
   （exclude_unset 语义下"省略键"= 不动它，与分类/封面是同一套清空口径）。
3. 出处链接只收 http(s)：这个值会渲染成访客页面上的 ``<a href>``，
   ``javascript:`` / ``data:`` 进库就是每篇转载文章下方的可执行链接。
4. ``source`` 是 NOT NULL 列，显式 null 拦成 422，不是 flush 时的 IntegrityError 500。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Post


def _payload(body: dict) -> dict:
    """兼容统一响应封装：取出真正的业务负载。"""
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


def _slug() -> str:
    return f"src-{uuid.uuid4().hex[:10]}"


async def _create(
    client: AsyncClient, headers: dict, *, slug: str | None = None, **overrides
) -> dict:
    payload: dict = {
        "title": {"zh": "来源测试文章", "en": "Source test post"},
        "content": {"zh": "这是正文", "en": "body text"},
        "slug": slug or _slug(),
        "status": "published",
    }
    payload.update(overrides)
    response = await client.post("/api/blog/posts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return _payload(response.json())


class TestWriteAndReadAgree:
    @pytest.mark.asyncio
    async def test_create_carries_source_and_url_to_response_and_db(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        slug = _slug()
        created = await _create(
            client,
            admin_headers,
            slug=slug,
            source="少数派",
            source_url="https://sspai.com/post/10086",
        )
        assert created["source"] == "少数派"
        assert created["source_url"] == "https://sspai.com/post/10086"

        row = await db_session.get(Post, created["id"])
        assert row is not None
        assert row.source == "少数派"
        assert row.source_url == "https://sspai.com/post/10086"

    @pytest.mark.asyncio
    async def test_public_detail_exposes_the_same_pair(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        await cache.clear()
        slug = _slug()
        created = await _create(
            client,
            admin_headers,
            slug=slug,
            source="翻译自 OpenAI Blog",
            source_url="https://openai.com/index/demo",
        )
        await cache.clear()

        detail = await client.get(f"/api/blog/posts/{slug}", params={"lang": "zh"})
        assert detail.status_code == 200, detail.text
        data = _payload(detail.json())
        assert data["source"] == "翻译自 OpenAI Blog"
        assert data["source_url"] == "https://openai.com/index/demo"
        assert data["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_default_is_original_with_no_link(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        created = await _create(client, admin_headers)
        assert created["source"] == "原创"
        assert created["source_url"] is None

        row = await db_session.get(Post, created["id"])
        assert row is not None and row.source == "原创" and row.source_url is None


class TestSchemeGuard:
    """出处链接的写口拒绝：渲染侧还有一道，但脏值不该先进库。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_url",
        [
            "javascript:alert(document.cookie)",
            "data:text/html,<script>alert(1)</script>",
            # 缺 scheme 也不算合法：静默补 https 会造出一条猜错的出站链接
            "sspai.com/post/10086",
            "//sspai.com/post/10086",
        ],
    )
    async def test_create_rejects_non_http_source_url(
        self, client: AsyncClient, admin_headers: dict, bad_url: str
    ):
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": {"zh": "坏链接", "en": "bad"},
                "content": {"zh": "正文", "en": "body"},
                "slug": _slug(),
                "status": "published",
                "source_url": bad_url,
            },
            headers=admin_headers,
        )
        assert response.status_code == 422
        assert "http" in str(response.json())

    @pytest.mark.asyncio
    async def test_put_rejects_bad_scheme_and_leaves_row_untouched(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        created = await _create(
            client, admin_headers, source="转载", source_url="https://example.com/original"
        )

        bad = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"source_url": "javascript:alert(1)"},
            headers=admin_headers,
        )
        assert bad.status_code == 422

        row = await db_session.get(Post, created["id"])
        assert row is not None
        assert row.source_url == "https://example.com/original"
        assert row.source == "转载"


class TestPartialUpdateSemantics:
    @pytest.mark.asyncio
    async def test_explicit_null_clears_url_only(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        created = await _create(
            client, admin_headers, source="知乎专栏", source_url="https://zhuanlan.zhihu.com/p/1"
        )

        updated = await client.put(
            f"/api/blog/posts/{created['id']}", json={"source_url": None}, headers=admin_headers
        )
        assert updated.status_code == 200, updated.text
        data = _payload(updated.json())
        assert data["source_url"] is None
        # 没提的键必须原样留着：这是 exclude_unset 的全部意义
        assert data["source"] == "知乎专栏"

        row = await db_session.get(Post, created["id"])
        assert row is not None and row.source_url is None and row.source == "知乎专栏"

    @pytest.mark.asyncio
    async def test_omitting_the_keys_leaves_them_untouched(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        created = await _create(
            client, admin_headers, source="微信公众号", source_url="https://mp.weixin.qq.com/s/abc"
        )

        updated = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"title": {"zh": "改过标题", "en": "renamed"}},
            headers=admin_headers,
        )
        assert updated.status_code == 200, updated.text
        row = await db_session.get(Post, created["id"])
        assert row is not None
        assert row.source == "微信公众号"
        assert row.source_url == "https://mp.weixin.qq.com/s/abc"

    @pytest.mark.asyncio
    async def test_explicit_null_source_is_422_not_500(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """``source`` 是 NOT NULL 列：显式 null 要在写回前拦成 422。

        不拦的话 setattr 到 NULL 列、flush 抛 IntegrityError，兜底 except 转成一句
        "服务器内部错误"——作者只是清空了一个必填标记，却被当成服务端故障。
        """
        created = await _create(client, admin_headers, source="转载")

        response = await client.put(
            f"/api/blog/posts/{created['id']}", json={"source": None}, headers=admin_headers
        )
        assert response.status_code == 422, response.text
        assert response.json()["success"] is False

        row = await db_session.get(Post, created["id"])
        assert row is not None and row.source == "转载"
