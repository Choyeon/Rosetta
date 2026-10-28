"""文章副标题（``Post.subtitle``）读写两端的回归测试。

这一族此前的形状是"半接通"：JSON 列在 ``Post`` 上、``PostBase``/``PostUpdate`` 都收这个键、
``PostResponse``/``PostEditResponse``/``PostLocalizedResponse``/列表项四个读口全都回显，
导入导出还会搬运它——但**后台编辑器表单从不发送、前台文章页从不渲染**。于是副标题只存在于
数据库与 API 文档里：作者写不了，读者看不见。本文件钉住接通之后的口径：

1. 写口（POST / PUT）落库的是完整 dict；响应体与公开详情/列表项按请求语言解析成字符串，
   两种形状各有归属，值必须同源。
2. ``/edit`` 必须回**完整 dict**：它是后台唯一的数据源。回成单语言字符串时
   ``normalizeI18nDict`` 会把字符串塞进 zh，PUT 再把其余三种语言整批抹掉。
3. 公开读口按请求语言解析成**字符串**（不是 dict），缺失语言回落 zh——与标题/摘要是同一口径。
4. PUT 显式 null 才清空（``exclude_unset`` 语义下省略键 = 不动它），这是后台"删掉副标题"
   唯一能成立的写法。
5. 历史脏值（裸字符串而不是 dict）不能把详情口打成 500——导入工具与直接写库都会留下这种行。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Post

SUBTITLE_ZH = "一句中文导语"
SUBTITLE_EN = "An English lede"


def _payload(body: dict) -> dict:
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


def _slug() -> str:
    return f"sub-{uuid.uuid4().hex[:10]}"


async def _create(
    client: AsyncClient, headers: dict, *, slug: str | None = None, **overrides
) -> dict:
    payload: dict = {
        "title": {"zh": "副标题测试文章", "en": "Subtitle test post"},
        "content": {"zh": "这是正文", "en": "body text"},
        "slug": slug or _slug(),
        "status": "published",
    }
    payload.update(overrides)
    response = await client.post("/api/blog/posts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return _payload(response.json())


class TestWritePath:
    @pytest.mark.asyncio
    async def test_create_persists_the_whole_dict(self, client, admin_headers, db_session):
        """创建口收四种语言并原样落库——后台一次提交就要写完整组，不能只留 zh。

        写口响应体是**单语言字符串**（``PostLocalizedResponse`` 一族），完整 dict 只从
        ``/edit`` 出：所以断言分两头，库里看 dict、响应看当前语言。
        """
        created = await _create(
            client,
            admin_headers,
            subtitle={"zh": SUBTITLE_ZH, "en": SUBTITLE_EN, "ja": "", "zh_Hant": "繁體導語"},
        )
        assert created["subtitle"] == SUBTITLE_ZH

        row = await db_session.get(Post, created["id"])
        assert row is not None
        assert row.subtitle == {
            "zh": SUBTITLE_ZH,
            "en": SUBTITLE_EN,
            "ja": "",
            "zh_Hant": "繁體導語",
        }

    @pytest.mark.asyncio
    async def test_create_without_subtitle_stays_null(self, client, admin_headers, db_session):
        created = await _create(client, admin_headers)
        assert created["subtitle"] is None
        row = await db_session.get(Post, created["id"])
        assert row is not None and row.subtitle is None

    @pytest.mark.asyncio
    async def test_put_updates_all_languages_at_once(self, client, admin_headers, db_session):
        created = await _create(client, admin_headers, subtitle={"zh": SUBTITLE_ZH})
        updated = _payload(
            (
                await client.put(
                    f"/api/blog/posts/{created['id']}",
                    json={"subtitle": {"zh": SUBTITLE_ZH, "en": SUBTITLE_EN}},
                    headers=admin_headers,
                )
            ).json()
        )
        assert updated["subtitle"] == SUBTITLE_ZH
        row = await db_session.get(Post, created["id"])
        assert row is not None and row.subtitle == {"zh": SUBTITLE_ZH, "en": SUBTITLE_EN}


class TestClearSemantics:
    @pytest.mark.asyncio
    async def test_explicit_null_clears(self, client, admin_headers, db_session):
        """后台删掉副标题发的是 null；不拦的话表单"删了又回来"。"""
        created = await _create(client, admin_headers, subtitle={"zh": SUBTITLE_ZH})

        cleared = await client.put(
            f"/api/blog/posts/{created['id']}", json={"subtitle": None}, headers=admin_headers
        )
        assert cleared.status_code == 200, cleared.text
        assert _payload(cleared.json())["subtitle"] is None

        row = await db_session.get(Post, created["id"])
        assert row is not None and row.subtitle is None

    @pytest.mark.asyncio
    async def test_omitting_the_key_leaves_it_untouched(self, client, admin_headers, db_session):
        """exclude_unset 的另一面：改标题不能顺手抹掉副标题。"""
        created = await _create(client, admin_headers, subtitle={"zh": SUBTITLE_ZH})

        await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"title": {"zh": "改过标题", "en": "renamed"}},
            headers=admin_headers,
        )
        row = await db_session.get(Post, created["id"])
        assert row is not None and row.subtitle == {"zh": SUBTITLE_ZH}


class TestReadSurfaces:
    @pytest.mark.asyncio
    async def test_edit_endpoint_returns_full_dict(self, client: AsyncClient, admin_headers: dict):
        """``/edit`` 是后台唯一数据源：必须是 dict，字符串会让 PUT 抹掉其余语言。

        顺带钉住 ``PostEditResponse.subtitle: dict | None`` 的形状契约——有人把它"优化"
        成按语言解析的字符串时，Pydantic 会在这一条上直接报错，而不是等到线上
        第一篇有副标题的文章打不开编辑器。
        """
        created = await _create(
            client, admin_headers, subtitle={"zh": SUBTITLE_ZH, "en": SUBTITLE_EN}
        )
        response = await client.get(f"/api/blog/posts/{created['id']}/edit", headers=admin_headers)
        assert response.status_code == 200, response.text
        data = _payload(response.json())
        assert data["subtitle"] == {"zh": SUBTITLE_ZH, "en": SUBTITLE_EN}

    @pytest.mark.asyncio
    async def test_public_detail_localizes_by_requested_language(
        self, client: AsyncClient, admin_headers: dict
    ):
        created = await _create(
            client, admin_headers, subtitle={"zh": SUBTITLE_ZH, "en": SUBTITLE_EN}
        )
        await cache.clear()

        en = _payload(
            (await client.get(f"/api/blog/posts/{created['slug']}", params={"lang": "en"})).json()
        )
        assert en["subtitle"] == SUBTITLE_EN

    @pytest.mark.asyncio
    async def test_missing_language_falls_back_to_default_language(
        self, client: AsyncClient, admin_headers: dict
    ):
        """只填了 zh 的副标题在英文页不能变成空白——与标题/摘要同一回落口径。"""
        created = await _create(client, admin_headers, subtitle={"zh": SUBTITLE_ZH})
        await cache.clear()
        en = _payload(
            (await client.get(f"/api/blog/posts/{created['slug']}", params={"lang": "en"})).json()
        )
        assert en["subtitle"] == SUBTITLE_ZH

    @pytest.mark.asyncio
    async def test_list_item_carries_localized_subtitle(
        self, client, admin_headers, db_session, test_category
    ):
        """列表项也要带：卡片/搜索结果以后要用副标题时不必再逐篇拉详情。

        范围收在专用分类 + 回拨发布时间里：匿名列表只收 ``published_at <= now()`` 的行，
        同一秒内创建的读数会因文本时间戳比较时隐时现，而全站列表的第 1 页也不保证
        收得下新文章——那是时序噪声，不是副标题的口径。
        """
        slug = _slug()
        created = await _create(
            client,
            admin_headers,
            slug=slug,
            category_id=test_category.id,
            subtitle={"zh": SUBTITLE_ZH},
        )
        row = await db_session.get(Post, created["id"])
        assert row is not None
        row.published_at = datetime(2020, 1, 1, tzinfo=UTC)
        await db_session.commit()
        await cache.clear()

        data = _payload(
            (
                await client.get(
                    "/api/blog/posts",
                    params={"category": test_category.slug, "page_size": 50, "lang": "zh"},
                )
            ).json()
        )
        item = next((i for i in data["items"] if i["slug"] == slug), None)
        assert item is not None, "新建文章没有出现在分类列表里"
        assert item["subtitle"] == SUBTITLE_ZH

    @pytest.mark.asyncio
    async def test_bare_string_subtitle_does_not_break_detail(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """JSON 多语言列的历史脏值：导入工具会直接落 ``subtitle="一句话"``。

        详情口汇聚在 ``get_i18n_value``，它认裸字符串；这条断言挡的是"以后有人改成
        ``post.subtitle[lang]``"——那会让一篇脏数据文章整口 500。
        """
        created = await _create(client, admin_headers)
        row = await db_session.get(Post, created["id"])
        assert row is not None
        row.subtitle = "导入工具留下的裸字符串"
        await db_session.commit()
        await cache.clear()

        detail = await client.get(f"/api/blog/posts/{created['slug']}", params={"lang": "zh"})
        assert detail.status_code == 200, detail.text
        assert _payload(detail.json())["subtitle"] == "导入工具留下的裸字符串"


class TestNonVacuity:
    """防止本文件在"字段根本没被读取"的情况下假绿。"""

    @pytest.mark.asyncio
    async def test_absent_subtitle_is_null_not_the_title(
        self, client: AsyncClient, admin_headers: dict
    ):
        """副标题不会自动等于标题：详情页靠"空则不渲染"，回落成标题就永远是两行重复。"""
        created = await _create(client, admin_headers)
        await cache.clear()
        data = _payload(
            (await client.get(f"/api/blog/posts/{created['slug']}", params={"lang": "zh"})).json()
        )
        assert data["subtitle"] is None
        assert data["title"]

    @pytest.mark.asyncio
    async def test_two_posts_do_not_share_a_subtitle(self, client: AsyncClient, admin_headers):
        """缓存串味守卫：详情缓存键必须区分有副标题/无副标题的两篇。"""
        a = await _create(client, admin_headers, subtitle={"zh": SUBTITLE_ZH})
        b = await _create(client, admin_headers)
        await cache.clear()

        da = _payload((await client.get(f"/api/blog/posts/{a['slug']}")).json())
        db_ = _payload((await client.get(f"/api/blog/posts/{b['slug']}")).json())
        assert da["subtitle"] == SUBTITLE_ZH
        assert db_["subtitle"] is None
