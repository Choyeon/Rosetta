"""`/api/config` 读侧的形状闸门（批次 #111）。

症状是线上实测的：批次 #108 把 OOBE 幽灵开关从 `SiteConfigResponse` 删掉之后，生产机
`GET /api/config` 稳定 500（`{"error_code":"INTERNAL_SERVER_ERROR"}`，88 字节），而首页与
文章页仍是 200——SSR 把配置口吞进了兜底分支，所以只有配置驱动的那部分功能静默退化。

原因不在数据库，在缓存：

* `site_config` 的载荷存在 Redis 里，TTL 3600 且**跨进程、跨重启**存活，它比代码旧是常态；
* `backend/schemas/strict_config.py::apply_strict_extra_forbid` 给包内**所有**模型补了
  `extra="forbid"`（本意是拦"请求体多带字段被接受"），于是旧载荷里那个已退役的键
  让 `SiteConfigResponse(**cached)` 抛 ValidationError；
* `cache_warmer._warmup_site_config` 委托的就是这同一个端点函数，所以冷启动预热同样撞进去，
  **重启也救不回来**，只能等 TTL 自然到期。

口径是把"缓存命中"定义成"还能按当前模型解出来"：形状不符就重算一次并在返回前覆写缓存，
漂移只发生一次请求。注意这不是把模型放宽——`extra="forbid"` 留在原地（写口那半边门禁照旧），
收的是"存量载荷"与"当前声明"之间的边界。
"""

import pytest
from pydantic import ValidationError

from backend.core.cache import CACHE_TTL, cache, make_cache_key
from backend.schemas import SiteConfigResponse

_CACHE_KEY = make_cache_key("site_config")


@pytest.fixture(autouse=True)
async def _isolate_site_config_cache():
    """每条用例前后都清掉这份缓存：本文件的用例要往载荷里塞脏值，漏清会把脏站名留给其它文件。"""
    await cache.delete(_CACHE_KEY)
    yield
    await cache.delete(_CACHE_KEY)


async def _warm_payload(client) -> dict:
    """先跑一次正常请求把缓存焐热，并确认焐热真的发生了。

    没有这一步，后面每条"陈旧载荷不会 500"的断言都会在 `cached` 为空时恒真。
    """
    response = await client.get("/api/config")
    assert response.status_code == 200, response.text
    payload = await cache.get(_CACHE_KEY)
    assert isinstance(payload, dict) and payload, "缓存里没有 site_config 载荷，后续断言不可信"
    return payload


class TestRetiredKeysInCachedPayload:
    """退役字段的反向漂移：旧载荷**多带**键（批次 #108 的实际形态）。"""

    @pytest.mark.asyncio
    async def test_public_config_survives_a_retired_key(self, client):
        stale = await _warm_payload(client)
        stale.update({"enable_pagefind_search": True, "enable_music_player": False})
        await cache.set(_CACHE_KEY, stale, CACHE_TTL["site_config"])

        response = await client.get("/api/config")
        assert response.status_code == 200, (
            f"已退役的键把整个配置口打挂了（Extra inputs are not permitted → 500）：{response.text[:200]}"
        )
        body = response.json()
        assert "enable_pagefind_search" not in body
        assert "enable_music_player" not in body
        assert body["site_name"], "重算路径没产出配置，200 只是空壳"
        assert body["pagination_page_size"] > 0

    @pytest.mark.asyncio
    async def test_drifted_entry_is_overwritten_not_recomputed_every_time(self, client):
        """自愈一次即收口：覆写后的载荷必须已是当前形状。

        只断言 200 挡不住"每个请求都绕开缓存重算"——那等于把配置口做成永远不打缓存的口子。
        """
        stale = await _warm_payload(client)
        stale["enable_pio"] = "false"
        await cache.set(_CACHE_KEY, stale, CACHE_TTL["site_config"])

        assert (await client.get("/api/config")).status_code == 200

        healed = await cache.get(_CACHE_KEY)
        assert isinstance(healed, dict) and healed
        assert "enable_pio" not in healed, "陈旧载荷没被覆写：命中路径每请求重算，缓存形同不存在"
        assert set(healed) <= set(SiteConfigResponse.model_fields)

    @pytest.mark.asyncio
    async def test_matching_shape_still_serves_from_cache(self, client):
        """闸门不得把命中路径改成死代码：形状相符时仍然要用缓存里那份值。"""
        warm = await _warm_payload(client)
        warm["site_name"] = "来自缓存的站名"
        await cache.set(_CACHE_KEY, warm, CACHE_TTL["site_config"])

        body = (await client.get("/api/config")).json()
        assert body["site_name"] == "来自缓存的站名"


class TestMissingKeysInCachedPayload:
    """新增字段的正向漂移：旧载荷**少带**必填键，同一条路（重算而不是 500）。"""

    @pytest.mark.asyncio
    async def test_public_config_survives_a_missing_required_key(self, client):
        stale = await _warm_payload(client)
        required = [
            name for name, field in SiteConfigResponse.model_fields.items() if field.is_required()
        ]
        assert required, "模型没有必填字段，这条用例失去意义"
        stale.pop(required[0])
        await cache.set(_CACHE_KEY, stale, CACHE_TTL["site_config"])

        response = await client.get("/api/config")
        assert response.status_code == 200, response.text
        assert response.json().get(required[0]) is not None


class TestStrictGateIsNotLoosened:
    """放宽的是边界投影，不是模型本身。"""

    @pytest.mark.asyncio
    async def test_response_model_still_forbids_extra_inputs(self, client):
        assert SiteConfigResponse.model_config.get("extra") == "forbid"

    @pytest.mark.asyncio
    async def test_constructing_with_a_retired_key_still_raises(self, client):
        payload = await _warm_payload(client)
        payload["enable_pagefind_search"] = True
        with pytest.raises(ValidationError):
            SiteConfigResponse(**payload)
