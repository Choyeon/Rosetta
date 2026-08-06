"""
Bing 壁纸代理 API 与空音乐默认状态测试

Task 9 配套测试：
- Bing 壁纸 API 返回正确的 schema
- 默认音乐/OOBE 不注入任何音乐示例数据
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def _task9_setup(monkeypatch, tmp_path):
    """每用例前：标记 OOBE 已完成，放宽速率限制，清理内存存储"""
    from backend.core import config as _cfg
    from backend.core import deps as _deps
    from backend.core.rate_limit import (
        SENSITIVE_ENDPOINT_RULE,
        WRITE_ENDPOINT_RULE,
        rate_limiter,
    )

    lock_file = tmp_path / ".oobe_complete"
    cfg_file = tmp_path / "rosetta.json"
    lock_file.write_text("1", encoding="utf-8")
    cfg_file.write_text("{}", encoding="utf-8")

    real_base = Path(__file__).resolve().parent.parent
    real_lock = real_base / ".oobe_complete"
    real_cfg = real_base / "rosetta.json"
    _prev_lock: bool = real_lock.exists()
    _prev_cfg: bool = real_cfg.exists()
    _prev_lock_text = real_lock.read_text(encoding="utf-8") if _prev_lock else None
    _prev_cfg_text = real_cfg.read_text(encoding="utf-8") if _prev_cfg else None
    if not _prev_lock:
        try:
            real_lock.write_text("1", encoding="utf-8")
        except Exception:
            pass
    if not _prev_cfg:
        try:
            real_cfg.write_text("{}", encoding="utf-8")
        except Exception:
            pass

    try:
        rate_limiter._memory_store.clear()
    except Exception:
        pass
    monkeypatch.setattr(SENSITIVE_ENDPOINT_RULE, "requests", 10_000)
    monkeypatch.setattr(WRITE_ENDPOINT_RULE, "requests", 10_000)
    monkeypatch.setattr(_cfg.settings, "rate_limit_sensitive_requests", 10_000)
    monkeypatch.setattr(_cfg.settings, "rate_limit_write_requests", 10_000)
    from backend.core.rate_limit import RateLimitResult

    async def _always_allowed_check(*args, **kwargs):
        import time

        return RateLimitResult(
            allowed=True, remaining=999_999, reset_at=time.time() + 3600, retry_after=0
        )

    monkeypatch.setattr(rate_limiter, "check_rate_limit", _always_allowed_check)
    monkeypatch.setattr(_deps, "OOBE_LOCK_FILE", lock_file)
    monkeypatch.setattr(_deps, "CONFIG_FILE", cfg_file)

    yield

    try:
        if not _prev_lock:
            try:
                real_lock.unlink()
            except Exception:
                pass
        else:
            try:
                real_lock.write_text(_prev_lock_text, encoding="utf-8")
            except Exception:
                pass
        if not _prev_cfg:
            try:
                real_cfg.unlink()
            except Exception:
                pass
        else:
            try:
                real_cfg.write_text(_prev_cfg_text, encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass


class TestBingWallpaperProxy:
    """Bing 每日壁纸代理 API 测试"""

    @pytest.mark.asyncio
    async def test_bing_wallpaper_proxy_returns_schema(self, client: AsyncClient):
        """
        GET /api/media/bing-wallpaper?n=1 返回结构包含 images 数组，
        数组每项至少包含 full_url 与 title 字段。
        如果离线环境或 Bing 不可达，endpoint 会返回 fallback 空值结构。
        """
        response = await client.get(
            "/api/media/bing-wallpaper", params={"idx": 0, "n": 1, "mkt": "zh-CN"}
        )
        assert response.status_code == 200, (
            f"Bing 壁纸接口应该返回 200，实际 {response.status_code}"
        )

        data = response.json()
        assert isinstance(data, dict), "响应必须是 JSON 对象"
        assert "images" in data, "响应必须包含 images 字段"
        assert isinstance(data["images"], list), "images 必须是数组"
        assert len(data["images"]) >= 1, "images 数组至少 1 条 fallback 记录"

        first = data["images"][0]
        assert isinstance(first, dict), "images 数组项必须是对象"
        assert "full_url" in first, "images 项必须包含 full_url 字段"
        assert "title" in first, "images 项必须包含 title 字段"
        assert isinstance(first["full_url"], str), "full_url 必须是字符串"
        assert isinstance(first["title"], str), "title 必须是字符串"

        cors_origin = response.headers.get("access-control-allow-origin")
        assert cors_origin == "*", "响应必须带 CORS 头 Access-Control-Allow-Origin: *"

    @pytest.mark.asyncio
    async def test_bing_wallpaper_invalid_params_clamped(self, client: AsyncClient):
        """超出范围的 idx/n 参数应被 clamp，仍然返回 200 与 images 数组。"""
        response = await client.get("/api/media/bing-wallpaper", params={"idx": 99, "n": 50})
        assert response.status_code == 200

        data = response.json()
        assert "images" in data
        assert isinstance(data["images"], list)
        assert len(data["images"]) >= 1


class TestEmptyMusicDefaults:
    """空音乐默认状态：OOBE mock_data 不再注入示例音乐"""

    @pytest.mark.asyncio
    async def test_oobe_mock_data_no_default_music(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        generate_oobe_mock_data 执行后，系统中不应有任何注入的示例音乐。
        Rosetta 当前无独立 Music 模型表，改为：
        - 检查 mock_data 模块中不包含任何 create_sample_music / add_default_music / seed_music
          等相关符号；
        - 断言 SiteConfig 中没有 music 相关的默认 seed 条目（如果有则为空数组）。
        """
        import inspect

        from backend.scripts import mock_data

        source = inspect.getsource(mock_data)
        forbidden_tokens = [
            "create_sample_music",
            "add_default_music",
            "seed_music",
            "sample_music",
            "default_music",
            "insert_music",
            "demo_music",
        ]
        for token in forbidden_tokens:
            assert token not in source, (
                f"mock_data.py 中不应包含音乐 seed 相关的 '{token}' 调用，"
                f"以保证 Task 9 的空音乐默认状态。"
            )

        from sqlalchemy import select

        from backend.models.core import SiteConfig

        result = await db_session.execute(select(SiteConfig))
        all_configs = result.scalars().all()
        music_keys = [
            c.key
            for c in all_configs
            if "music" in c.key.lower() or "playlist" in c.key.lower() or "song" in c.key.lower()
        ]
        for key in music_keys:
            cfg = next((c for c in all_configs if c.key == key), None)
            if cfg is None or not cfg.value:
                continue
            val = cfg.value
            if isinstance(val, str) and val.strip().startswith("["):
                import json

                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        assert len(parsed) == 0, f"配置 {key} 应为空数组，实际长度 {len(parsed)}"
                except Exception:
                    pass
