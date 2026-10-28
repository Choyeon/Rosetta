"""摘要与 SEO meta 三字段"显式 null 才清空"的往返回归（批次 #33）。

`excerpt` / `meta_title` / `meta_description` / `meta_keywords` 与副标题（#30）是同一个 bug 类：
后端 PUT 走 `model_dump(exclude_unset=True)`，**键没出现 = 不动它**，而编辑器此前发的是
`toI18nPayload(form.x)`——全空 dict 返回 `undefined`，键整个不在请求体里。表现是作者删掉摘要
或 SEO 标题、后台提示保存成功、再打开还是旧值，前台 RSS / og:description 继续用旧摘要，
且这个"删不掉"在接口层没有任何报错。

所以后台唯一能成立的写法是发显式 `null`（前端 `toI18nPayload(...) ?? null`，
类型必须允许 `| null`）。本文件钉住两端：清空真的落库、省略键真的不动它——
后一条是前一条存在的理由，不能被当成冗余断言删掉。

读侧口径一并钉住：摘要清空后不得继续把旧摘要端给 RSS / 详情口（该回落正文截取），
四列都允许 NULL，所以 `apply_partial_update` 的守卫（`core/partial_update.py`）不会拦。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.models.blog import Post

CLEARABLE_FIELDS = ["excerpt", "meta_title", "meta_description", "meta_keywords"]

CONTENT_ZH = "这是探针正文，摘要被清掉之后 RSS 与详情都必须回落到它。"


def _payload(body: dict) -> dict:
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


def _values(field: str) -> dict[str, str]:
    return {
        "zh": f"{field} 中文值",
        "en": f"{field} english value",
        "ja": "",
        "zh_Hant": f"{field} 繁體值",
    }


async def _create(client: AsyncClient, headers: dict) -> dict:
    slug = f"clr-{uuid.uuid4().hex[:10]}"
    body: dict = {
        "title": {"zh": "清空回归文章", "en": "Clear regression post"},
        "content": {"zh": CONTENT_ZH, "en": "clear regression body"},
        "slug": slug,
        "status": "published",
    }
    for field in CLEARABLE_FIELDS:
        body[field] = _values(field)
    response = await client.post("/api/blog/posts", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return _payload(response.json())


class TestWritePath:
    @pytest.mark.asyncio
    async def test_create_persists_every_language(self, client, admin_headers, db_session):
        """四个字段创建时都按完整 dict 落库——否则"清空"这条断言是在赌列本来就是空的。"""
        created = await _create(client, admin_headers)
        row = await db_session.get(Post, created["id"])
        assert row is not None
        await db_session.refresh(row)
        for field in CLEARABLE_FIELDS:
            assert getattr(row, field) == _values(field), field

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field", CLEARABLE_FIELDS)
    async def test_explicit_null_clears(self, field, client, admin_headers, db_session):
        created = await _create(client, admin_headers)
        response = await client.put(
            f"/api/blog/posts/{created['id']}", json={field: None}, headers=admin_headers
        )
        assert response.status_code == 200, response.text

        row = await db_session.get(Post, created["id"])
        assert row is not None
        await db_session.refresh(row)
        assert getattr(row, field) is None, f"{field} 发 null 后库里必须真的没有值"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field", CLEARABLE_FIELDS)
    async def test_omitting_the_key_leaves_it_untouched(
        self, field, client, admin_headers, db_session
    ):
        """省略键 = 不动它（exclude_unset 增量语义）。

        这条不是冗余：编辑器正是踩在这条语义上才把"删掉摘要"变成静默失败的。
        改 PUT 语义（比如换成全量覆盖）会让前端那套 `?? null` 变成多余，但也会连带
        把"只改状态"这类局部请求写成抹数据，所以两端都要钉住。
        """
        created = await _create(client, admin_headers)
        expected = _values(field)
        response = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"title": {"zh": "只改标题", "en": "title only"}},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text

        row = await db_session.get(Post, created["id"])
        assert row is not None
        await db_session.refresh(row)
        assert getattr(row, field) == expected, f"{field} 没出现在请求体里，不该被动"

    @pytest.mark.asyncio
    async def test_clearing_all_four_at_once(self, client, admin_headers, db_session):
        """后台一次保存要能把四个字段一起清掉——分四次发是前端做不到的（表单只有一个状态）。"""
        created = await _create(client, admin_headers)
        body = {field: None for field in CLEARABLE_FIELDS}
        response = await client.put(
            f"/api/blog/posts/{created['id']}", json=body, headers=admin_headers
        )
        assert response.status_code == 200, response.text

        row = await db_session.get(Post, created["id"])
        assert row is not None
        await db_session.refresh(row)
        assert all(getattr(row, field) is None for field in CLEARABLE_FIELDS)


class TestReadSurfacesAfterClear:
    @pytest.mark.asyncio
    async def test_edit_endpoint_returns_none(self, client, admin_headers):
        """``/edit`` 是后台唯一数据源：清空后它必须回 null，不能回旧 dict，
        否则表单重新打开又把旧值填回去，作者看到的是"删了又回来了"。"""
        created = await _create(client, admin_headers)
        for field in CLEARABLE_FIELDS:
            assert (
                await client.put(
                    f"/api/blog/posts/{created['id']}", json={field: None}, headers=admin_headers
                )
            ).status_code == 200

        edit = await client.get(f"/api/blog/posts/{created['id']}/edit", headers=admin_headers)
        assert edit.status_code == 200, edit.text
        body = _payload(edit.json())
        for field in CLEARABLE_FIELDS:
            assert body.get(field, "<<missing>>") is None, field

    @pytest.mark.asyncio
    async def test_detail_does_not_leak_cleared_excerpt(self, client, admin_headers):
        created = await _create(client, admin_headers)
        assert (
            await client.put(
                f"/api/blog/posts/{created['id']}", json={"excerpt": None}, headers=admin_headers
            )
        ).status_code == 200

        detail = await client.get(f"/api/blog/posts/{created['slug']}")
        assert detail.status_code == 200, detail.text
        excerpt = _payload(detail.json()).get("excerpt") or ""
        assert "excerpt 中文值" not in excerpt
        assert CONTENT_ZH[:12] in excerpt or excerpt == ""

    @pytest.mark.asyncio
    async def test_rss_falls_back_to_content_after_clear(self, client, admin_headers):
        """RSS 的 description 是摘要的第二个消费点：清掉后必须回落正文，不能继续播出旧摘要。"""
        created = await _create(client, admin_headers)
        slug = created["slug"]
        assert (
            await client.put(
                f"/api/blog/posts/{created['id']}", json={"excerpt": None}, headers=admin_headers
            )
        ).status_code == 200

        rss = await client.get("/api/blog/rss")
        assert rss.status_code == 200, rss.text
        text = rss.text
        assert slug in text, "文章本身仍应在 RSS 里"
        assert "excerpt 中文值" not in text
        assert CONTENT_ZH[:12] in text

    @pytest.mark.asyncio
    async def test_list_item_survives_cleared_fields(self, client, admin_headers):
        created = await _create(client, admin_headers)
        body = {field: None for field in CLEARABLE_FIELDS}
        assert (
            await client.put(f"/api/blog/posts/{created['id']}", json=body, headers=admin_headers)
        ).status_code == 200

        listing = await client.get("/api/blog/posts", params={"page_size": 200, "lang": "zh"})
        assert listing.status_code == 200, listing.text
        items = _payload(listing.json()).get("items") or []
        row = next((it for it in items if it.get("slug") == created["slug"]), None)
        assert row is not None, "清掉元数据不能让文章从列表里消失"
        assert "excerpt 中文值" not in (row.get("excerpt") or "")
