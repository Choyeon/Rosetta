"""Avatar privacy proxy.

对外：GET /media/avatar?src=<urlsafe_b64(original_url)>[&fallback=1]

策略：
- 白名单域名（github/gravatar/qq/dicebear 等）→ 307 直跳（省带宽、浏览器缓存友好）
- fallback=1 或非白名单域名 → 服务端流式代理：
    - 上游 4xx/5xx → 307 到最终兜底（本地静态图）
    - 上游 Content-Type 非 image/* → 307 兜底（防止 example.com 的 HTML/CORS/ORB 污染，Chromium 会以 ERR_BLOCKED_BY_ORB 杀掉这类响应）
    - 上游请求异常 → 307 兜底
- 所有响应 Cache-Control: public, max-age=604800, immutable（7 天）。
"""
from __future__ import annotations

import base64
import re
from typing import Literal, Union

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, StreamingResponse

router = APIRouter(tags=["媒体"])

# 允许的上游域名白名单（可以 307 直跳，不需要代理流式；同时防止 SSRF 打内网）
_ALLOWED_HOST_SUFFIXES = (
    "github.com",
    "githubusercontent.com",
    "gravatar.com",
    "gravatar.cn",
    "wp.com",  # Gravatar 0.gravatar.com 等别名 CNAME 最终走 wp.com
    "qlogo.cn",
    "qpic.cn",
    "dicebear.com",  # v7/v8/v9 默认头像 API（identicon/avataaars 等矢量 SVG）
    "dicebear.me",  # DiceBear 短链
)

# 永久 fallback 图片（本地静态资源；走 CDN/browser 缓存，保证必返回 image/*）
_FINAL_FALLBACK = "/favicon/rosetta-256.png"

_HEADERS_PASS_THOUGH = {
    "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
}

# 允许的图片 MIME（严格匹配，杜绝代理到 HTML/JSON 触发 ORB）
_IMAGE_MIME_RE = re.compile(r"^(image/(png|jpeg|jpg|gif|webp|avif|svg\+xml|bmp|x-icon|vnd\.microsoft\.icon|ico))(?:;.*)?$", re.I)


def _is_image_mime(ct: str | None) -> bool:
    if not ct:
        return False
    return bool(_IMAGE_MIME_RE.match(ct.strip()))


def _b64url_decode(src: str) -> str:
    padding = "=" * (-len(src) % 4)
    raw = base64.urlsafe_b64decode(src + padding)
    return raw.decode("utf-8")


def _is_allowed_host(url: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    import ipaddress as _ip
    try:
        ip = _ip.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass  # hostname
    for suf in _ALLOWED_HOST_SUFFIXES:
        if host == suf or host.endswith("." + suf):
            return True
    return False


_FB = Union[str, int, bool, None]


async def _proxy_and_validate(url: str) -> StreamingResponse | RedirectResponse:
    """流式代理上游图片；若状态码/Content-Type 不是图片，安全跳转最终兜底。"""
    try:
        timeout = httpx.Timeout(8.0, connect=3.0, pool=5.0, read=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, http2=True) as client:
            r = await client.get(url, headers=_HEADERS_PASS_THOUGH)
            if r.status_code >= 400:
                return RedirectResponse(_FINAL_FALLBACK, status_code=307)
            media_type = r.headers.get("content-type") or ""
            if not _is_image_mime(media_type):
                # 上游返回了 HTML / JSON / 其它文本（例如 example.com 的 404）
                # → Chromium ORB 会拦截 cross-origin text/* 响应当作图片
                return RedirectResponse(_FINAL_FALLBACK, status_code=307)
            # 清理 media_type 中的 charset / boundary，防止 image/png; charset=utf-8 出错
            clean_media = _IMAGE_MIME_RE.match(media_type.strip())
            mt = clean_media.group(1) if clean_media else "image/png"
            cl = r.headers.get("content-length")
            headers = {
                "Cache-Control": "public, max-age=604800, immutable",
                "X-Content-Type-Options": "nosniff",
            }
            if cl:
                headers["Content-Length"] = str(cl)
            return StreamingResponse(
                r.aiter_bytes(chunk_size=64 * 1024),
                media_type=mt,
                headers=headers,
            )
    except Exception:
        return RedirectResponse(_FINAL_FALLBACK, status_code=307)


@router.get("/media/avatar")
async def avatar_proxy(
    request: Request,
    src: str,
    fallback: Literal["0", "1", "true", "false"] | bool = "0",
):
    try:
        url = _b64url_decode(src)
    except Exception:
        return RedirectResponse(_FINAL_FALLBACK, status_code=307)

    if not url.startswith(("http://", "https://")):
        return RedirectResponse(_FINAL_FALLBACK, status_code=307)

    force_proxy = str(fallback).lower() in ("1", "true")
    allowed = _is_allowed_host(url)

    if not force_proxy and allowed:
        # 白名单直跳（省后端出口带宽；这些域名通常 CORS 正确、且不可能返回 HTML 作为 avatar）
        resp = RedirectResponse(url, status_code=307)
        resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
        return resp

    # fallback=1 或 非白名单：统一走「代理 + Content-Type 强校验」，避免 ORB / 意外 HTML 泄漏
    return await _proxy_and_validate(url)
