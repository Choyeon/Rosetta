"""
Bing 每日一图代理 + 历史归档（骨架路由）+ 图片流式代理。

说明：
- ``backend/api/bing.py`` 已有一条主路由（Bing 今日图重定向）；
- 这里的 ``bing_image`` 是另一条功能增强路由（JSON 详情 + 分辨率选择 + 最近 N 天归档 + 图片代理缓存）。
二者并存，互不冲突。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field as PDField

from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bing壁纸"])

BING_WP_BASE = "https://www.bing.com"

# ========== Bing 图片代理（与前端 proxiedBingUrl 对应）==========
# Bing 官方域名白名单：CORS 正确、返回 image/*，可以 307 直跳省出口带宽
_BING_ALLOWED_HOST_SUFFIXES = (
    "bing.com",
    "bing.net",
    "windows.net",   # Bing 部分 CDN CNAME
    "microsoft.com",
)

_IMAGE_MIME_RE = re.compile(
    r"^(image/(png|jpeg|jpg|gif|webp|avif|svg\+xml|bmp|x-icon|vnd\.microsoft\.icon|ico))(?:;.*)?$",
    re.I,
)
_UPSTREAM_HEADERS = {
    "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
}
_FINAL_FALLBACK = "/favicon/rosetta-256.png"


def _is_image_mime(ct: str | None) -> bool:
    if not ct:
        return False
    return bool(_IMAGE_MIME_RE.match(ct.strip()))


def _is_bing_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    import ipaddress as _ip
    try:
        ip = _ip.ip_address(host)
        # 禁止 SSRF 打内网
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass  # hostname
    for suf in _BING_ALLOWED_HOST_SUFFIXES:
        if host == suf or host.endswith("." + suf):
            return True
    return False


def _std_b64decode(src: str) -> str:
    """前端用 btoa(unescape(encodeURIComponent(s))) 编码的标准 base64 解码。"""
    # btoa 输出不含 padding 时浏览器也能 atob，Python 需要补 "="
    src = src.replace("-", "+").replace("_", "/")
    padding = "=" * (-len(src) % 4)
    raw = base64.b64decode(src + padding)
    return raw.decode("utf-8")


def _get_bing_cache_dir() -> Path:
    d = Path(settings.media_dir) / "bing"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cached_filepath(url: str) -> Path:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    # 保留 URL 末尾扩展名（若存在）作为本地文件扩展名，帮助静态服务识别 Content-Type
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower() or ".bin"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg", ".bmp", ".ico"}:
        ext = ".bin"
    return _get_bing_cache_dir() / f"{h[:16]}{ext}"


async def _download_and_cache(url: str, target: Path) -> Path | None:
    """下载上游图片到 target；成功返回 target，失败返回 None。

    保持默认 trust_env=True：有 HTTP_PROXY/HTTPS_PROXY 环境变量时自动走代理，
    没有时直连；不强制挂载 transport，避免本地代理未启动时直接报错。
    """
    try:
        timeout = httpx.Timeout(8.0, connect=3.0, pool=5.0, read=30.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            http2=True,
            trust_env=True,
        ) as client:
            r = await client.get(url, headers=_UPSTREAM_HEADERS)
            if r.status_code >= 400:
                return None
            media_type = r.headers.get("content-type") or ""
            if not _is_image_mime(media_type):
                return None
            # 原子写入：先写 .tmp 再 rename，避免半写文件被读到
            tmp = target.with_suffix(target.suffix + ".tmp")
            async with tmp.open("wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=256 * 1024):
                    await asyncio.to_thread(f.write, chunk)
            tmp.replace(target)
            return target
    except Exception as exc:
        logger.warning("[bing_image] 下载缓存失败 %s: %s", url, exc)
        try:
            target.with_suffix(target.suffix + ".tmp").unlink(missing_ok=True)
        except Exception:
            pass
        return None


@router.get("/bing/image", summary="Bing 图片流式代理 + 本地缓存")
async def bing_image_proxy(src: str = Query(..., description="base64(原始图片URL)")):
    """
    前端 ``proxiedBingUrl`` 生成的 /api/bing/image?src=<base64(url)> 代理端点。

    策略：
    - Bing 官方域名 → 307 直跳（省出口带宽，浏览器缓存友好）
    - 其他域名 / 要求本地缓存 → 服务端流式代理 + 本地落盘缓存
      - 先检查 media/bing/<sha256 prefix>.<ext>，命中直接 FileResponse
      - 未命中则下载并校验 Content-Type 为 image/*，成功后落盘再返回
      - 上游失败 / 非图片 MIME → 307 跳 /favicon/rosetta-256.png 兜底
    """
    try:
        url = _std_b64decode(src)
    except Exception:
        return RedirectResponse(_FINAL_FALLBACK, status_code=307)

    if not url.startswith(("http://", "https://")):
        return RedirectResponse(_FINAL_FALLBACK, status_code=307)

    # Bing 官方域名：CORS 正确、返回 image/*，直接 307 让浏览器取 CDN
    if _is_bing_host(url):
        resp = RedirectResponse(url, status_code=307)
        resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
        return resp

    # 本地缓存命中 → 直接用 FileResponse（Nginx 可 sendfile，不走 Python streaming）
    cache_fp = _cached_filepath(url)
    if cache_fp.is_file():
        return FileResponse(
            cache_fp,
            headers={
                "Cache-Control": "public, max-age=2592000, immutable",
                "X-Content-Type-Options": "nosniff",
            },
        )

    # 下载并落盘；成功后再读本地文件（保证后续请求命中缓存）
    saved = await _download_and_cache(url, cache_fp)
    if saved is not None and saved.is_file():
        return FileResponse(
            saved,
            headers={
                "Cache-Control": "public, max-age=2592000, immutable",
                "X-Content-Type-Options": "nosniff",
            },
        )

    # 所有失败路径：安全跳本地兜底图（保证是 image/* 不触发 ORB）
    return RedirectResponse(_FINAL_FALLBACK, status_code=307)


class BingImageOut(BaseModel):
    date: str = PDField(description="YYYY-MM-DD，发布日期")
    title: str = PDField(description="标题 / 版权文字（中文）")
    url: str = PDField(description="1920x1080 JPEG 直链")
    url_uhd: str | None = PDField(None, description="4K UHD 原图直链")
    copyright: str | None = None


@router.get("/bing/image/today", summary="获取 Bing 今日图元数据")
async def bing_today_image():
    """从 Bing HP 图像元数据 JSON 接口抓取今日信息，失败则回退到占位图。"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                "https://www.bing.com/HPImageArchive.aspx",
                params={"format": "js", "idx": 0, "n": 1, "mkt": "zh-CN"},
            )
            r.raise_for_status()
            data = r.json()
        image = (data.get("images") or [])[0]
        base = image.get("urlbase", "")
        url_1920 = f"{BING_WP_BASE}{base}_1920x1080.jpg" if base else ""
        url_uhd = f"{BING_WP_BASE}{base}_UHD.jpg" if base else None
        return {
            "success": True,
            "data": BingImageOut(
                date=str(date.today()),
                title=image.get("title") or image.get("copyright") or "Bing",
                url=url_1920,
                url_uhd=url_uhd,
                copyright=image.get("copyright"),
            ).model_dump(),
        }
    except Exception as exc:
        logger.warning(f"[bing_image] 拉取 Bing 今日图失败: {exc}")
        # 兜底：返回一张占位 1x1 图，保证前端不崩溃
        return {
            "success": True,
            "fallback": True,
            "data": BingImageOut(
                date=str(date.today()),
                title="Bing 图片暂不可用",
                url="data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E",
            ).model_dump(),
        }


@router.get("/bing/image/archive", summary="获取 Bing 最近 N 天图片归档（骨架）")
async def bing_archive(days: int = Query(7, ge=1, le=14, description="查询的天数 1..14")):
    """返回最近 days 天的图片元数据列表。实现方式：串行请求 idx=0..days-1 的归档。"""
    import httpx

    out: list[dict] = []
    today = date.today()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for idx in range(days):
                r = await client.get(
                    "https://www.bing.com/HPImageArchive.aspx",
                    params={"format": "js", "idx": idx, "n": 1, "mkt": "zh-CN"},
                )
                if r.status_code != 200:
                    continue
                image = (r.json().get("images") or [])[0] if r.json().get("images") else None
                if not image:
                    continue
                base = image.get("urlbase", "")
                d = today - timedelta(days=idx)
                out.append(
                    BingImageOut(
                        date=str(d),
                        title=image.get("title") or image.get("copyright") or "",
                        url=f"{BING_WP_BASE}{base}_1920x1080.jpg" if base else "",
                        url_uhd=f"{BING_WP_BASE}{base}_UHD.jpg" if base else None,
                        copyright=image.get("copyright"),
                    ).model_dump()
                )
                await asyncio.sleep(0.05)
    except Exception as exc:
        logger.warning(f"[bing_image] 归档查询失败: {exc}")
    return {"success": True, "data": out, "count": len(out)}
