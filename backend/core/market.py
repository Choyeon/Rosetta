"""
Rosetta 官方市场索引客户端。

功能：
*   ``fetch_market_index(kind)`` — 拉取插件/主题市场的 index.json，
    带本地 JSON 文件缓存（默认 8 小时 TTL）。
*   缓存落盘到 ``backend/data/market_cache/{plugins,themes}.json``，
    进程内多协程访问同一 ``kind`` 时使用 ``asyncio.Lock`` 串行化，
    避免并发写穿导致的本地文件撕裂。
*   网络请求使用 ``httpx.AsyncClient``，支持 30x 重定向与超时。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from backend.core.config import settings

logger = logging.getLogger("rosetta.market")

# 缓存目录：与 seed_content 同属 backend/data，Git 忽略即可
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "market_cache"
CACHE_TTL = 8 * 3600  # 8 小时

_KIND_TO_SETTINGS = {
    "plugins": ("PLUGINS_MARKET_BASE_URL", lambda: settings.PLUGINS_MARKET_BASE_URL),
    "themes": ("THEMES_MARKET_BASE_URL", lambda: settings.THEMES_MARKET_BASE_URL),
}

# 进程内按 kind 串行化：避免多个请求同时击穿缓存
_fetch_locks: dict[str, asyncio.Lock] = {}


def _lock_for(kind: str) -> asyncio.Lock:
    if kind not in _fetch_locks:
        _fetch_locks[kind] = asyncio.Lock()
    return _fetch_locks[kind]


def _validate_kind(kind: str) -> None:
    if kind not in _KIND_TO_SETTINGS:
        raise ValueError(
            f"未知的市场 kind={kind!r}，合法值: {sorted(_KIND_TO_SETTINGS)}"
        )


def _base_url_for(kind: str) -> str:
    _, getter = _KIND_TO_SETTINGS[kind]
    base = getter()
    if not isinstance(base, str):  # pragma: no cover - 防御性
        raise TypeError(f"{_KIND_TO_SETTINGS[kind][0]} 必须是字符串 URL")
    return base.rstrip("/")


def _cache_path_for(kind: str) -> Path:
    return CACHE_DIR / f"{kind}.json"


def _read_cached(fp: Path) -> dict[str, Any] | None:
    """读取缓存，过期/损坏都返回 None（触发远端拉取）。"""
    try:
        if not fp.exists():
            return None
        age = time.time() - fp.stat().st_mtime
        if age >= CACHE_TTL:
            logger.debug("market cache %s 过期 (age=%.0fs)，准备刷新", fp.name, age)
            return None
        raw = fp.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            logger.warning("market cache %s 不是合法 JSON 对象，忽略", fp.name)
            return None
        return data
    except (OSError, json.JSONDecodeError) as e:  # pragma: no cover - IO edge
        logger.warning("market cache %s 读取失败: %s", fp.name, e)
        return None


def _write_cached(fp: Path, data: dict[str, Any]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = fp.with_suffix(fp.suffix + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(fp)
    except OSError as e:  # pragma: no cover - IO edge
        logger.warning("market cache %s 写入失败: %s", fp.name, e)


async def _fetch_remote(kind: str) -> dict[str, Any]:
    """从远端 market index URL 拉取 JSON。
    失败（DNS/HTTP 4xx/5xx/超时）回退：读本地最后一次成功缓存，不存在则返回空 items，
    由上游 UI 展示「离线模式/市场不可用」提示，绝不抛 500。
    """
    import httpx

    url = f"{_base_url_for(kind)}/index.json"
    fp = _cache_path_for(kind)
    timeout = httpx.Timeout(30.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        if not isinstance(data, dict):
            raise ValueError(f"market index {url} 返回值不是 JSON 对象")
        return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("拉取远端市场失败 kind=%s url=%s: %s", kind, url, exc)
        cached = _read_cached(fp)
        if cached is not None:
            cached["_offline"] = True
            return cached
        from datetime import datetime, timezone

        return {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": [],
            "_offline": True,
            "_error": f"{type(exc).__name__}: {exc}",
        }


async def fetch_market_index(
    kind: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """获取指定 kind 的市场索引。

    Parameters
    ----------
    kind:
        ``"plugins"`` 或 ``"themes"``。
    force:
        为 True 时跳过本地缓存（但仍写回缓存），用于后台管理员「刷新市场」按钮。

    Returns
    -------
    dict[str, Any]
        市场原始 JSON，结构约定（至少包含）::

            {
              "updated_at": "2026-08-28T00:00:00Z",
              "items": [ { "slug": "...", "name": "...", "zip_url": "...", ... } ]
            }
    """
    _validate_kind(kind)
    fp = _cache_path_for(kind)

    # Fast path：非强制 & 缓存有效直接命中
    if not force:
        cached = _read_cached(fp)
        if cached is not None:
            return cached

    # Slow path：串行化，双检后仍 miss 则拉远端
    lock = _lock_for(kind)
    async with lock:
        if not force:
            cached = _read_cached(fp)
            if cached is not None:
                return cached
        data = await _fetch_remote(kind)
        # 统一加上本地落盘时间戳（调试/排障用）
        enriched = dict(data)
        enriched.setdefault("_cached_at", int(time.time()))
        _write_cached(fp, enriched)
        return enriched
