"""Avatar privacy proxy.

对外：GET /media/avatar?src=<urlsafe_b64(original_url)>[&fallback=1]

策略：
- 默认 (fallback 缺省或 =0)：307 重定向到 original（省带宽，browser cache 友好）。
- fallback=1：流式代理上游，清空 Referer，伪造 Chrome UA；上游 4xx/5xx → 302 到 /favicon/rosetta-256.png 最终 fallback。
- 所有响应 Cache-Control: public, max-age=604800, immutable（7 天）。
"""
from __future__ import annotations

import base64
from typing import Literal, Union

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, StreamingResponse

router = APIRouter(tags=["媒体"])

# 允许的上游域名白名单（防止 SSRF 打内网）
_ALLOWED_HOST_SUFFIXES = (
    "github.com",
    "githubusercontent.com",
    "gravatar.com",
    "gravatar.cn",
    "qlogo.cn",
    "qpic.cn",
)

# 永久 fallback 图片（本地静态资源；走 CDN/browser 缓存）
_FINAL_FALLBACK = "/favicon/rosetta-256.png"

_HEADERS_PASS_THOUGH = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "referer": "",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}


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

    if not force_proxy and _is_allowed_host(url):
        resp = RedirectResponse(url, status_code=307)
        resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
        return resp

    if force_proxy:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0), follow_redirects=True) as client:
                r = await client.get(url, headers=_HEADERS_PASS_THOUGH)
                if r.status_code >= 400:
                    return RedirectResponse(_FINAL_FALLBACK, status_code=307)
                media_type = r.headers.get("content-type") or "image/png"
                cl = r.headers.get("content-length")
                headers = {"Cache-Control": "public, max-age=604800, immutable"}
                if cl:
                    headers["Content-Length"] = str(cl)
                return StreamingResponse(
                    r.aiter_bytes(),
                    media_type=media_type,
                    headers=headers,
                )
        except Exception:
            return RedirectResponse(_FINAL_FALLBACK, status_code=307)

    # 默认非白名单：直接 307 原图（让浏览器直接拿；后续如发现泄漏再收紧）
    resp = RedirectResponse(url, status_code=307)
    resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
    return resp
