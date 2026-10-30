"""``GET /api/media/library`` 的排序契约（批次 #223）。

后端 ``sort_by`` / ``sort_order`` 支持了很久，但后台媒体库页面从来没有排序入口：
列表只有「按上传时间倒序」一条路，要找「占空间最大的文件」或按文件名核对只能翻页。
UI 接上之后两侧都不能再各改各的，这里钉住四件事：
① 四个白名单字段在两个方向上**真的换了 SQL 顺序**（不是发出去被静默丢弃）；
② 分页偏移排在排序**之后**（换序后第 2 页的内容跟着换，否则排序只是当页的外观）；
③ 非法 ``sort_by`` / 非法 ``sort_order`` 静默回落，不 422 也不 500；
④ 排序与 ``search`` / ``file_type`` 叠加时 ``total`` 不变（计数不该被 ORDER BY 带跑）。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.core import Media

# filename / file_size / created_at / updated_at 四个维度互相打乱，
# 任何「其实一直在按 created_at 排」的实现都骗不过这组期望值。
ROWS = [
    {
        "filename": "alpha.png",
        "file_size": 300,
        "created": datetime(2026, 1, 1, tzinfo=UTC),
        "updated": datetime(2026, 6, 1, tzinfo=UTC),
    },
    {
        "filename": "beta.png",
        "file_size": 100,
        "created": datetime(2026, 2, 1, tzinfo=UTC),
        "updated": datetime(2026, 5, 1, tzinfo=UTC),
    },
    {
        "filename": "gamma.png",
        "file_size": 200,
        "created": datetime(2026, 3, 1, tzinfo=UTC),
        "updated": datetime(2026, 4, 1, tzinfo=UTC),
    },
    {
        "filename": "delta.png",
        "file_size": 400,
        "created": datetime(2026, 4, 1, tzinfo=UTC),
        "updated": datetime(2026, 3, 1, tzinfo=UTC),
    },
]


@pytest_asyncio.fixture
async def media_rows(db_session: AsyncSession) -> dict[str, int]:
    """落四行媒体记录，返回 ``filename -> id``（顺序与 ROWS 一致，id 递增）。"""
    created: dict[str, int] = {}
    for spec in ROWS:
        media = Media(
            file=f"/media/uploads/image/{spec['filename']}",
            filename=spec["filename"],
            file_type="image",
            file_size=spec["file_size"],
            created_at=spec["created"],
            updated_at=spec["updated"],
        )
        db_session.add(media)
        await db_session.flush()
        created[spec["filename"]] = media.id
    await db_session.commit()
    return created


def _ids(body: dict) -> list[str]:
    """响应里的文件名序列（按位置比对，不依赖 id 自增方向）。"""
    return [item["filename"] for item in body["items"]]


async def _order(client: AsyncClient, staff_headers: dict, **params: str) -> list[str]:
    resp = await client.get(
        "/api/media/library", headers=staff_headers, params={"page_size": "50", **params}
    )
    assert resp.status_code == 200
    return _ids(resp.json())


class TestSortableFields:
    """四个白名单字段 × 两个方向都要真的换顺序。"""

    @pytest.mark.parametrize(
        ("sort_by", "sort_order", "expected"),
        [
            ("created_at", "desc", ["delta.png", "gamma.png", "beta.png", "alpha.png"]),
            ("created_at", "asc", ["alpha.png", "beta.png", "gamma.png", "delta.png"]),
            ("filename", "asc", ["alpha.png", "beta.png", "delta.png", "gamma.png"]),
            ("filename", "desc", ["gamma.png", "delta.png", "beta.png", "alpha.png"]),
            ("file_size", "desc", ["delta.png", "alpha.png", "gamma.png", "beta.png"]),
            ("file_size", "asc", ["beta.png", "gamma.png", "alpha.png", "delta.png"]),
            ("updated_at", "asc", ["delta.png", "gamma.png", "beta.png", "alpha.png"]),
            ("updated_at", "desc", ["alpha.png", "beta.png", "gamma.png", "delta.png"]),
        ],
    )
    async def test_each_column_orders_the_whole_set(
        self,
        client: AsyncClient,
        staff_headers: dict,
        media_rows: dict,
        sort_by: str,
        sort_order: str,
        expected: list[str],
    ):
        assert (
            await _order(client, staff_headers, sort_by=sort_by, sort_order=sort_order) == expected
        )

    async def test_default_is_newest_first(
        self, client: AsyncClient, staff_headers: dict, media_rows: dict
    ):
        """不带参数 = created_at desc：UI 的初始态必须与服务端默认同一条，否则首屏换序。"""
        assert await _order(client, staff_headers) == await _order(
            client, staff_headers, sort_by="created_at", sort_order="desc"
        )


class TestSortIsAppliedBeforePaging:
    """排序必须作用于整张表，而不是只重排当页。"""

    async def test_second_page_follows_the_order(
        self, client: AsyncClient, staff_headers: dict, media_rows: dict
    ):
        by_name = await client.get(
            "/api/media/library",
            headers=staff_headers,
            params={"sort_by": "filename", "sort_order": "asc", "page": "2", "page_size": "2"},
        )
        assert _ids(by_name.json()) == ["delta.png", "gamma.png"]

    async def test_total_is_untouched_by_ordering(
        self, client: AsyncClient, staff_headers: dict, media_rows: dict
    ):
        counts = set()
        for order in ("asc", "desc"):
            resp = await client.get(
                "/api/media/library",
                headers=staff_headers,
                params={"sort_by": "file_size", "sort_order": order},
            )
            counts.add(resp.json()["total"])
        assert counts == {4}


class TestIllegalSortValuesFallBack:
    """后台选项与手改地址栏都不能把列表打成 422/500。"""

    @pytest.mark.parametrize("junk", ["password", "id", "", "no_such_column", "FILENAME"])
    async def test_junk_sort_by_falls_back_to_created_at(
        self, client, staff_headers, media_rows, junk
    ):
        assert await _order(client, staff_headers, sort_by=junk) == await _order(
            client, staff_headers, sort_by="created_at"
        )

    @pytest.mark.parametrize("junk", ["up", "", "DESC"])
    async def test_junk_sort_order_falls_back_to_desc(
        self, client, staff_headers, media_rows, junk
    ):
        assert await _order(
            client, staff_headers, sort_by="file_size", sort_order=junk
        ) == await _order(client, staff_headers, sort_by="file_size", sort_order="desc")


class TestSortWithFilters:
    async def test_search_and_type_narrow_the_ordered_set(
        self, client: AsyncClient, staff_headers: dict, media_rows: dict
    ):
        resp = await client.get(
            "/api/media/library",
            headers=staff_headers,
            params={
                "search": "a",
                "file_type": "image",
                "sort_by": "filename",
                "sort_order": "asc",
            },
        )
        body = resp.json()
        assert body["total"] == 4  # alpha/beta/gamma/delta 的文件名都含 a
        assert _ids(body) == ["alpha.png", "beta.png", "delta.png", "gamma.png"]

    async def test_non_matching_type_returns_empty_not_error(
        self, client: AsyncClient, staff_headers: dict, media_rows: dict
    ):
        resp = await client.get(
            "/api/media/library",
            headers=staff_headers,
            params={"file_type": "video", "sort_by": "file_size"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestEndpointDocumentedWhitelist:
    """文档里写的可排序字段必须就是代码里那几个——少列一个，后台选项就成了没声明的能力。"""

    async def test_openapi_lists_every_sortable_column(self, client: AsyncClient):
        spec = await client.get("/openapi.json")
        params = spec.json()["paths"]["/api/media/library"]["get"]["parameters"]
        sort_param = next(item for item in params if item["name"] == "sort_by")
        for column in ("created_at", "file_size", "filename", "updated_at"):
            assert column in sort_param["description"], f"sort_by 文档漏了 {column}"
