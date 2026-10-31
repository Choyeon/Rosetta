"""``GET /api/media/library/stats`` 的 type_stats 契约（批次 #152）。

统计载荷里 **体积（size）只有 type_stats 给得出**：四个分类型计数别名是从它派生的单维投影，
而后台此前只读别名，于是「哪种格式吃掉多少空间」在管理员界面无处可查（前端消费点见
``frontend/tests/unit/mediaStatsSurfaces.spec.ts``）。同批退役 ``total_size_formatted``——
后端自己格式化一遍、前台另有 ``lib/utils::formatBytes``，同一页两套口径即双真相。

钉住四件事：
① ``type_stats`` 每个键都带 count 与 size，size 是按 file_type 分组真实 SUM 出来的；
② 四个别名与 ``total_*`` 别名必须和 type_stats / 总数对得上（两份投影不许各改各的）；
③ ``file_type`` 落在四档之外（导入工具会写 ``other``）时**只在 type_stats 里出现**，
   证明别名是残缺投影、消费方不能只读别名；
④ 退役族（``total_size_formatted`` / ``format_file_size``）不回潮，且载荷键集与文档模型
   ``MediaStatsData`` 声明的字段集**相等**（文档不许宣称一个接口没有的键）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import media as media_module
from backend.api.media import MediaStatsData
from backend.models.core import Media

# image 两行 / video 一行 / document 一行 / other 一行；
# 数值互不相同且两两不成倍数，任何「其实一直按创建顺序算」的实现都骗不过 SUM。
ROWS = [
    ("img-a.png", "image", 300),
    ("img-b.png", "image", 100),
    ("clip.mp4", "video", 500),
    ("spec.pdf", "document", 40),
    ("mystery.bin", "other", 7),
]


@pytest_asyncio.fixture
async def media_rows(db_session: AsyncSession) -> None:
    for filename, file_type, file_size in ROWS:
        db_session.add(
            Media(
                file=f"/media/uploads/{file_type}/{filename}",
                filename=filename,
                file_type=file_type,
                file_size=file_size,
            )
        )
    await db_session.commit()


async def _stats(client: AsyncClient, staff_headers: dict) -> dict:
    resp = await client.get("/api/media/library/stats", headers=staff_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class TestTypeStatsVolume:
    async def test_each_type_carries_count_and_summed_size(
        self, client: AsyncClient, staff_headers: dict, media_rows
    ):
        data = await _stats(client, staff_headers)
        assert data["type_stats"] == {
            "image": {"count": 2, "size": 400},
            "video": {"count": 1, "size": 500},
            "document": {"count": 1, "size": 40},
            "other": {"count": 1, "size": 7},
        }
        # 全库总量与分组量同源于一次 SUM，两处口径不许分叉
        assert data["total_size"] == 947
        assert data["total_count"] == len(ROWS)

    async def test_alias_counts_match_type_stats(
        self, client: AsyncClient, staff_headers: dict, media_rows
    ):
        data = await _stats(client, staff_headers)
        type_stats = data["type_stats"]
        for alias, key in (
            ("images", "image"),
            ("videos", "video"),
            ("audios", "audio"),
            ("documents", "document"),
        ):
            expected = type_stats.get(key, {}).get("count", 0)
            assert data[alias] == expected, f"{alias} 与 type_stats.{key}.count 分叉"
        assert data["total_files"] == data["total_count"]
        assert data["total_size_bytes"] == data["total_size"]

    async def test_type_outside_the_four_aliases_only_appears_in_type_stats(
        self, client: AsyncClient, staff_headers: dict, media_rows
    ):
        """别名是残缺投影：库里出现第五种 file_type 时只有 type_stats 看得见。"""
        data = await _stats(client, staff_headers)
        assert "other" in data["type_stats"]
        assert data["images"] + data["videos"] + data["audios"] + data["documents"] < data[
            "total_files"
        ]


class TestRetiredFormattedSize:
    async def test_payload_has_no_formatted_size_key(
        self, client: AsyncClient, staff_headers: dict, media_rows
    ):
        data = await _stats(client, staff_headers)
        assert "total_size_formatted" not in data
        assert "total_size_formatted" not in MediaStatsData.model_fields

    async def test_payload_keys_equal_doc_model_fields(
        self, client: AsyncClient, staff_headers: dict, media_rows
    ):
        data = await _stats(client, staff_headers)
        assert set(data) == set(MediaStatsData.model_fields)

    def test_helper_is_gone_from_the_source(self):
        assert not hasattr(media_module, "format_file_size")
        source = Path(media_module.__file__).read_text(encoding="utf-8")
        assert "format_file_size" not in source
