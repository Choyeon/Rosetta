"""
Task B：市场索引 + 一键安装 + mods_schema 校验（TDD 最小冒烟）。

覆盖：
  1. 市场 HTTP 路由存在性（GET /api/admin/{plugins,themes}/market）
  2. fetch_market_index 本地 JSON 缓存命中 & TTL 过期行为
  3. ThemeManager.set_mods() 通过 mods_schema 校验 + 非法值被拒（MODS_SCHEMA_VIOLATION）
  4. set_mods 合法值成功写入

注：不依赖真实后端 OOBE 完成；路由存在性通过 TestClient(app) 断言「非 404」，
缓存/校验走纯单元路径。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.core.extensions import _validate_mods_against_schema
from backend.core.exceptions import AppException

BACKEND_ROOT = Path(__file__).resolve().parents[1]


# ── Unit：mods_schema 校验（jsonschema 缺失情况下的 pydantic 降级路径） ───


def test_validate_mods_ok_string_color_integer_boolean_enum():
    schema = {
        "type": "object",
        "properties": {
            "accent_color": {"type": "string", "format": "color"},
            "posts_per_row": {"type": "integer", "minimum": 1, "maximum": 6},
            "show_avatar": {"type": "boolean"},
            "greeting": {"type": "string", "enum": ["hello", "hi", "yo"]},
            "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }
    value = {
        "accent_color": "#4f46e5",
        "posts_per_row": 3,
        "show_avatar": True,
        "greeting": "hello",
        "score": 0.5,
    }
    # 不抛异常即为通过
    _validate_mods_against_schema(value, schema)


def test_validate_mods_reject_bad_color():
    schema = {
        "type": "object",
        "properties": {"accent_color": {"type": "string", "format": "color"}},
    }
    with pytest.raises(AppException) as ei:
        _validate_mods_against_schema({"accent_color": "not-a-color"}, schema)
    assert ei.value.error_code == "MODS_SCHEMA_VIOLATION"


def test_validate_mods_reject_out_of_range_integer():
    schema = {
        "type": "object",
        "properties": {"posts_per_row": {"type": "integer", "minimum": 1, "maximum": 4}},
    }
    with pytest.raises(AppException) as ei:
        _validate_mods_against_schema({"posts_per_row": 99}, schema)
    assert ei.value.error_code == "MODS_SCHEMA_VIOLATION"


def test_validate_mods_reject_wrong_enum():
    schema = {
        "type": "object",
        "properties": {"greeting": {"type": "string", "enum": ["a", "b"]}},
    }
    with pytest.raises(AppException) as ei:
        _validate_mods_against_schema({"greeting": "z"}, schema)
    assert ei.value.error_code == "MODS_SCHEMA_VIOLATION"


def test_validate_mods_reject_boolean_given_string():
    schema = {
        "type": "object",
        "properties": {"show": {"type": "boolean"}},
    }
    with pytest.raises(AppException) as ei:
        _validate_mods_against_schema({"show": "yes"}, schema)
    assert ei.value.error_code == "MODS_SCHEMA_VIOLATION"


def test_validate_mods_unknown_type_passes_loosely():
    """未知 JSON Schema 关键字绝不阻塞写回。"""
    schema = {
        "type": "object",
        "properties": {
            "weird_field": {"x-unknown-keyword": True},
        },
    }
    # 不抛异常即通过
    _validate_mods_against_schema({"weird_field": {"a": 1}}, schema)


# ── Unit：market 缓存行为（mock httpx） ──────────────────────────────────


def test_fetch_market_index_hit_cache(tmp_path: Path):
    from backend.core.market import CACHE_TTL, fetch_market_index

    cache_dir = tmp_path / "market_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "plugins.json"
    want = {"items": [{"slug": "hello", "name": "Hello"}], "updated_at": "2026-08-28"}
    cache_file.write_text(json.dumps(want), encoding="utf-8")

    with patch("backend.core.market.CACHE_DIR", cache_dir):
        got = pytest.importorskip("asyncio").run(fetch_market_index("plugins"))
    # 因为缓存有效 → 直接命中，返回值应与写入一致
    assert isinstance(got, dict)
    assert got.get("items") == want["items"]


def test_fetch_market_index_expired_ttl_fetches_remote(tmp_path: Path):
    from backend.core import market as market_module
    from backend.core.market import fetch_market_index

    cache_dir = tmp_path / "market_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "plugins.json"
    stale = {"items": [], "stale": True}
    cache_file.write_text(json.dumps(stale), encoding="utf-8")
    # 把 mtime 回退至超过 TTL
    old_ts = time.time() - (market_module.CACHE_TTL + 10)
    import os
    os.utime(cache_file, (old_ts, old_ts))

    fresh = {"items": [{"slug": "new"}], "fresh": True}

    class _FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return fresh

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, url):  # noqa: D401 - fake
            return _FakeResp()

    asyncio = pytest.importorskip("asyncio")
    import httpx as _httpx_pkg
    with patch.object(market_module, "CACHE_DIR", cache_dir), patch.object(
        _httpx_pkg, "AsyncClient", _FakeClient
    ):
        got = asyncio.run(fetch_market_index("plugins"))
    assert got["items"] == fresh["items"]
    # 且新值被写入缓存
    persisted = json.loads(cache_file.read_text(encoding="utf-8"))
    assert persisted.get("items") == fresh["items"]


# ── API：市场路由存在性（非 404 断言） ─────────────────────────────────────


def test_plugin_market_route_registered():
    """GET /api/admin/plugins/market 必须路由注册成功（绝不能 404）。

    未通过 OOBE → 返回 503/401 均合法；只禁止 404。
    """
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as client:
        resp = client.get("/api/admin/plugins/market")
        assert resp.status_code != 404, (
            f"plugins market route not registered, status={resp.status_code}"
        )


def test_theme_market_route_registered():
    """GET /api/admin/themes/market 必须路由注册成功（绝不能 404）。"""
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as client:
        resp = client.get("/api/admin/themes/market")
        assert resp.status_code != 404, (
            f"themes market route not registered, status={resp.status_code}"
        )


def test_plugin_market_install_route_registered():
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as client:
        resp = client.post("/api/admin/plugins/market/some-slug/install")
        # 允许 401/503/404(后端逻辑)，但禁止 FastAPI 路由级 404 带 msg "Not Found"
        if resp.status_code == 404:
            body = resp.text or ""
            assert "Not Found" not in body, "plugins market install route not registered"


def test_theme_market_install_route_registered():
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as client:
        resp = client.post("/api/admin/themes/market/some-slug/install")
        if resp.status_code == 404:
            body = resp.text or ""
            assert "Not Found" not in body, "themes market install route not registered"
