"""搜索占位符：写口 → 存储 → 响应模型 → 消费方，四段必须齐。

缺陷类（与 `PostViewHistory` 同形）：模型 `SearchPlaceholder` 与公开读口
`GET /api/search-placeholders` 一直存在，前台 `/posts` 搜索框也真的在轮播这些文案，
但全仓没有任何写口——运营者既看不到也管不了，表里永远只有"空"这一种状态。

读口那一段还叠了一只隐性 500：它声明 `response_model=list[str]`，却把 JSON 列的 dict
原样吐出去。没有行时看不出问题，**一旦真的写进一行**，Pydantic 的 dict→str 校验失败
就是整口 500——所以"能写入"这件事本身必须与"读口按语言解析"同批落地。
"""

import pytest
from httpx import AsyncClient

from backend.models.core import SearchPlaceholder

pytestmark = pytest.mark.asyncio


async def _seed(db_session, text, *, is_active: bool = True, order: int = 0):
    row = SearchPlaceholder(text=text, is_active=is_active, order=order)
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


class TestPublicReader:
    async def test_returns_strings_not_raw_dicts(self, client: AsyncClient, db_session):
        """dict 直出 `list[str]` 是 500 面：写入后读口仍 200，且元素是字符串。"""
        await _seed(db_session, {"zh": "搜索你想看的文章", "en": "Search posts"})

        resp = await client.get("/api/search-placeholders")

        assert resp.status_code == 200, resp.text
        assert resp.json() == ["搜索你想看的文章"]

    async def test_lang_param_resolves_language(self, client: AsyncClient, db_session):
        await _seed(db_session, {"zh": "中文占位", "en": "English hint"})

        resp = await client.get("/api/search-placeholders", params={"lang": "en"})

        assert resp.status_code == 200
        assert resp.json() == ["English hint"]

    async def test_missing_language_falls_back_to_default(self, client: AsyncClient, db_session):
        """该语言没填时回退默认语言，与前台其余多语言读取面同口径。"""
        await _seed(db_session, {"zh": "只有中文"})

        resp = await client.get("/api/search-placeholders", params={"lang": "ja"})

        assert resp.json() == ["只有中文"]

    async def test_inactive_excluded_and_order_respected(self, client: AsyncClient, db_session):
        await _seed(db_session, {"zh": "停用项"}, is_active=False)
        await _seed(db_session, {"zh": "第二顺位"}, order=2)
        await _seed(db_session, {"zh": "同序靠 id"})
        await _seed(db_session, {"zh": "同序后 id"})

        resp = await client.get("/api/search-placeholders", params={"lang": "zh"})

        assert resp.json() == ["同序靠 id", "同序后 id", "第二顺位"]


class TestAdminCrud:
    async def test_anonymous_cannot_write(self, client: AsyncClient):
        resp = await client.post("/api/search-placeholders", json={"text": {"zh": "x"}})
        assert resp.status_code == 401
        assert (await client.get("/api/search-placeholders/all")).status_code == 401

    async def test_non_staff_cannot_write(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/search-placeholders",
            json={"text": {"zh": "x"}},
            headers=auth_headers,
        )
        assert resp.status_code in (401, 403)

    async def test_create_list_update_delete(self, client: AsyncClient, staff_headers: dict):
        created = await client.post(
            "/api/search-placeholders",
            json={"text": {"zh": "搜索文章", "en": "Search"}, "order": 3},
            headers=staff_headers,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["text"]["en"] == "Search"
        assert body["is_active"] is True
        assert body["order"] == 3

        listed = await client.get("/api/search-placeholders/all", headers=staff_headers)
        assert listed.status_code == 200
        rows = listed.json()
        # 后台口给完整 dict（不做语言解析），否则编辑器一次保存就抹掉其余语言
        assert rows[0]["id"] == body["id"]
        assert rows[0]["text"] == {"zh": "搜索文章", "en": "Search"}

        updated = await client.put(
            f"/api/search-placeholders/{body['id']}",
            json={"is_active": False},
            headers=staff_headers,
        )
        assert updated.status_code == 200
        # 省略的键保持原值（exclude_unset 增量语义）
        assert updated.json()["is_active"] is False
        assert updated.json()["text"]["zh"] == "搜索文章"

        # 停用后公开口不再返回这一条
        public = await client.get("/api/search-placeholders", params={"lang": "zh"})
        assert public.json() == []

        deleted = await client.delete(
            f"/api/search-placeholders/{body['id']}", headers=staff_headers
        )
        assert deleted.status_code == 200
        remaining = await client.get("/api/search-placeholders/all", headers=staff_headers)
        assert remaining.json() == []

    async def test_empty_text_rejected(self, client: AsyncClient, staff_headers: dict):
        """四语全空等价于"没有这一行"，写入侧直接拒，不让它进库后静默消失。"""
        resp = await client.post(
            "/api/search-placeholders",
            json={"text": {"zh": "   ", "en": ""}},
            headers=staff_headers,
        )
        assert resp.status_code == 422

    async def test_null_text_rejected_not_500(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        row = await _seed(db_session, {"zh": "原值"})

        resp = await client.put(
            f"/api/search-placeholders/{row.id}",
            json={"text": None},
            headers=staff_headers,
        )

        # NOT NULL 列的显式 null 必须被 apply_partial_update 拦成 422，不能落成 500
        assert resp.status_code == 422

    async def test_missing_row_is_404(self, client: AsyncClient, staff_headers: dict):
        put = await client.put(
            "/api/search-placeholders/999999", json={"order": 1}, headers=staff_headers
        )
        delete = await client.delete("/api/search-placeholders/999999", headers=staff_headers)
        assert put.status_code == 404
        assert delete.status_code == 404
