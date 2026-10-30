"""公开动态列表 ``?type=`` 筛选的回归测试（批次 #222）。

``type`` 是进 SQL ``WHERE`` 的判别位，按 AGENTS.md §9.1「响应缓存的键必须带齐查询侧
真正使用的判别位」的口径，它一旦不进缓存键，第一个用 `?type=say` 的访客就会把
「只有说说」写进 `/activity` 首屏共用的那条键位，TTL 内全站列表被单一类型污染。

同时钉住四件容易各自漂移的事：
1. 未知类型按「不筛选」处理（不是 422、也不是空列表）——旧分享链接与手打的错参数
   要看到完整列表，且归一后的值才进缓存键，垃圾参数不能各自占一条键位；
2. 计数与列表必须过同一组条件，否则筛选后的 ``total_pages`` 会宣称还有下一页；
3. 可筛选类型集合 = ``schemas.activity.ActivityType`` 这个 Literal，不再抄第二份清单；
4. 前台 ``pages/activity.vue`` 的 ``ACTIVITY_TYPES`` 与后端同集合（跨语言对账，
   漏一个的表现是筛出来的动态全部落回「说说」图标）。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

import pytest
from httpx import AsyncClient

from backend.api.activity import ACTIVITY_TYPE_FILTERS, _get_activities_cache_key
from backend.main import app
from backend.schemas.activity import ActivityType

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "frontend" / "pages" / "activity.vue"
LOCALES_DIR = REPO / "frontend" / "i18n" / "locales"
LOCALE_CODES = ("zh", "en", "ja", "zh_Hant")

CONTENT_TEMPLATE = {
    "zh": "{tag}内容",
    "en": "{tag} content",
    "ja": "{tag}コンテンツ",
    "zh_Hant": "{tag}內容",
}


async def _publish(client: AsyncClient, auth_headers: dict, activity_type: str, tag: str) -> int:
    body = {
        "content": {k: v.format(tag=tag) for k, v in CONTENT_TEMPLATE.items()},
        "type": activity_type,
        "is_published": True,
    }
    response = await client.post("/api/activities", headers=auth_headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _page_text() -> str:
    # 仓库混用 CRLF 与 LF：跨行 needle 必须先归一，否则永远匹配不到
    return PAGE.read_text(encoding="utf-8").replace("\r\n", "\n")


class TestTypeFilterSetIsSingleSource:
    """筛选白名单不得是第二份手抄清单"""

    def test_filters_come_from_the_pydantic_literal(self):
        assert ACTIVITY_TYPE_FILTERS == frozenset(get_args(ActivityType))

    def test_openapi_documents_the_type_parameter_with_the_same_values(self):
        spec = app.openapi()
        param = next(
            p for p in spec["paths"]["/api/activities"]["get"]["parameters"] if p["name"] == "type"
        )
        assert param["in"] == "query"
        # 文档里的可选值必须跟白名单同源，否则调用方照着过期清单接线
        for activity_type in sorted(ACTIVITY_TYPE_FILTERS):
            assert activity_type in param["description"], param["description"]

    def test_frontend_enum_matches_the_backend_filter_set(self):
        """跨语言对账：前端 ACTIVITY_TYPES ⇔ 后端 ACTIVITY_TYPE_FILTERS 集合相等。"""
        match = re.search(
            r"const ACTIVITY_TYPES = \[([^\]]*)\] as const",
            _page_text(),
        )
        assert match, "pages/activity.vue 里找不到 ACTIVITY_TYPES 清单"
        frontend_types = {
            item.strip().strip("'\"") for item in match.group(1).split(",") if item.strip()
        }
        assert frontend_types == set(ACTIVITY_TYPE_FILTERS), (
            f"前后端类型集合漂移：前端多 {frontend_types - set(ACTIVITY_TYPE_FILTERS)}，"
            f"后端多 {set(ACTIVITY_TYPE_FILTERS) - frontend_types}"
        )


class TestPublicTypeFiltering:
    @pytest.mark.asyncio
    async def test_type_returns_only_matching_rows(self, client: AsyncClient, auth_headers: dict):
        await _publish(client, auth_headers, "say", "说说一")
        await _publish(client, auth_headers, "say", "说说二")
        await _publish(client, auth_headers, "notice", "公告一")

        r = await client.get("/api/activities", params={"type": "say", "page_size": 50})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["items"]) == 2, body
        assert {i["type"] for i in body["items"]} == {"say"}
        assert "公告一" not in "".join(i["content"] for i in body["items"])

    @pytest.mark.asyncio
    async def test_count_and_pages_use_the_same_condition_as_the_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        """筛选后的 total / total_pages 必须是筛选后的数。

        计数不带 type 时：3 条说说 + 5 条公告，`?type=say&page_size=2` 会回
        total=8 / total_pages=4，而第 2 页之后就再也翻不出内容。
        """
        for i in range(3):
            await _publish(client, auth_headers, "say", f"说说{i}")
        for i in range(5):
            await _publish(client, auth_headers, "update", f"更新{i}")

        r = await client.get("/api/activities", params={"type": "say", "page": 1, "page_size": 2})
        body = r.json()
        assert body["total"] == 3, body
        assert body["total_pages"] == 2, body

        # 越界页拿空列表，而不是"还有下一页"的谎
        r2 = await client.get("/api/activities", params={"type": "say", "page": 3, "page_size": 2})
        assert r2.json()["items"] == []

    @pytest.mark.asyncio
    async def test_unknown_type_falls_back_to_the_whole_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _publish(client, auth_headers, "say", "说说")
        await _publish(client, auth_headers, "article", "文章")

        r = await client.get("/api/activities", params={"type": "does-not-exist", "page_size": 50})
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) == 2, "垃圾参数被筛成空列表"

        plain = await client.get("/api/activities", params={"page_size": 50})
        assert [i["id"] for i in plain.json()["items"]] == [i["id"] for i in r.json()["items"]]

    @pytest.mark.asyncio
    async def test_blank_type_is_treated_as_no_filter(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _publish(client, auth_headers, "notice", "公告")

        r = await client.get("/api/activities", params={"type": "   ", "page_size": 50})
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) == 1

    @pytest.mark.asyncio
    async def test_link_type_is_filterable(self, client: AsyncClient, auth_headers: dict):
        """``link`` 曾只在后台白名单里，前台筛不到、图标也没有（批次 #222 一并补齐）。"""
        await _publish(client, auth_headers, "link", "友链")
        await _publish(client, auth_headers, "say", "说说")

        r = await client.get("/api/activities", params={"type": "link", "page_size": 50})
        body = r.json()
        assert [i["type"] for i in body["items"]] == ["link"], body


class TestCacheKeyCarriesTheDiscriminator:
    @pytest.mark.asyncio
    async def test_filtered_response_does_not_poison_the_all_key(
        self, client: AsyncClient, auth_headers: dict
    ):
        """先打 `?type=say`，再打不带 type 的请求，必须仍是完整列表。"""
        await _publish(client, auth_headers, "say", "说说")
        await _publish(client, auth_headers, "notice", "公告")

        first = await client.get("/api/activities", params={"type": "say", "page_size": 50})
        assert len(first.json()["items"]) == 1, first.text

        second = await client.get("/api/activities", params={"page_size": 50})
        assert len(second.json()["items"]) == 2, "筛选响应写进了「全部」的缓存键位"

    @pytest.mark.asyncio
    async def test_reverse_order_also_stays_separate(self, client: AsyncClient, auth_headers: dict):
        await _publish(client, auth_headers, "say", "说说")
        await _publish(client, auth_headers, "notice", "公告")

        full = await client.get("/api/activities", params={"page_size": 50})
        assert len(full.json()["items"]) == 2, full.text

        filtered = await client.get("/api/activities", params={"type": "notice", "page_size": 50})
        assert [i["type"] for i in filtered.json()["items"]] == ["notice"], filtered.text

    @pytest.mark.asyncio
    async def test_junk_type_does_not_take_its_own_cache_key(
        self, client: AsyncClient, auth_headers: dict
    ):
        """归一必须发生在算键之前：否则每个垃圾值都能各占一条键位（缓存撑大面）。"""
        from backend.core.cache import cache

        await _publish(client, auth_headers, "say", "说说")
        junk = "not-a-type"
        r = await client.get(
            "/api/activities", params={"type": junk, "page_size": 50, "lang": "zh"}
        )
        assert len(r.json()["items"]) == 1, r.text

        junk_key = await _get_activities_cache_key("zh", 1, 50, junk)
        assert not await cache.exists(junk_key), "垃圾类型名进了缓存键，归一发生在算键之后"

        all_key = await _get_activities_cache_key("zh", 1, 50, None)
        assert await cache.exists(all_key), "归一后的请求没落到「全部」键位"


def test_frontend_sends_the_type_in_the_request_query():
    """筛选状态必须真的进请求 query，否则 chip 只是装饰。"""
    text = _page_text()
    assert "if (type) q.type = type" in text
    # 请求侧：有筛选才发这个键（不筛选时不发空串，与地址栏形态同口径）
    assert "...(currentType.value ? { type: currentType.value } : {})" in text
