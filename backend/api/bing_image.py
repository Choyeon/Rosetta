"""
Bing 每日一图代理 + 最近 N 天归档 + 图片流式代理。

说明：
- ``backend/api/bing.py`` 已有一条主路由（Bing 今日图重定向）；
- 这里的 ``bing_image`` 是另一条功能增强路由（JSON 详情 + 分辨率选择 + 最近 N 天归档 + 图片代理缓存）。
二者并存，互不冲突。
- 归档口的日期只认上游 ``startdate``，外发请求按上游保留窗口（``UPSTREAM_RETENTION_DAYS``）
  一次批量取回并进服务端缓存，不再逐日串行打上游。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from pydantic import Field as PDField

from backend.core.cache import cache, make_cache_key
from backend.core.config import settings
from backend.core.http_client import create_async_client
from backend.core.net_guard import is_image_mime, validated_get
from backend.schemas import raw_content_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bing壁纸"])

BING_WP_BASE = "https://cn.bing.com"

# 上游自己的保留窗口：一次请求最多回这么多条（2026-10-31 线上实测 n=14 也只回 8 条），
# 而 idx 越过窗口后重复返回最旧那一张（idx=9 与窗口末条同 urlbase）。
UPSTREAM_RETENTION_DAYS = 8
# 归档是"每天变一次"的外部数据，无缓存时每个访客每次 SSR 都会串行打 Bing。
ARCHIVE_CACHE_TTL = 3600


def _utc_today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _normalize_startdate(raw: object) -> str:
    """上游 ``startdate``（``YYYYMMDD``）归一成 ``YYYY-MM-DD``；不可解析就回空串。

    日期只认上游给的那一份：服务器本地时区与 Bing 的市场日界并不相同，
    按 ``date.today() - timedelta(idx)`` 反推会把同一张图标成另一天。
    """
    text = str(raw or "").strip()
    if len(text) != 8 or not text.isdigit():
        return ""
    year, month, day = int(text[:4]), int(text[4:6]), int(text[6:])
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def _entry_from_image(image: dict) -> dict | None:
    """上游一条 image → BingImageOut dict；缺 startdate 或缺 urlbase 的条目返回 None。"""
    day = _normalize_startdate(image.get("startdate"))
    base = str(image.get("urlbase") or "")
    if not day or not base:
        return None
    return BingImageOut(
        date=day,
        title=image.get("title") or image.get("copyright") or "",
        url=f"{BING_WP_BASE}{base}_1920x1080.jpg",
        url_uhd=f"{BING_WP_BASE}{base}_UHD.jpg",
        copyright=image.get("copyright"),
        copyright_url=image.get("copyrightlink"),
    ).model_dump()


# ========== Bing 图片代理（与前端 proxiedBingUrl 对应）==========
# Bing 官方域名白名单：CORS 正确、返回 image/*，可以 307 直跳省出口带宽
_BING_ALLOWED_HOST_SUFFIXES = (
    "bing.com",
    "bing.net",
    "windows.net",  # Bing 部分 CDN CNAME
    "microsoft.com",
)

_UPSTREAM_HEADERS = {
    "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
}
_FINAL_FALLBACK = "/images/bing-fallback.svg"


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
    # Bing 图片 URL 如 /th?id=xxx_1920x1080.jpg&rf=... 的扩展名在 query 中，需特殊处理
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if not ext:
        # 从 query string 中提取（如 id=OHR.xxx_1920x1080.jpg）
        m = re.search(r"\.(jpg|jpeg|png|webp|gif|avif|svg|bmp|ico)(?:&|$)", parsed.query, re.I)
        if m:
            ext = "." + m.group(1).lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg", ".bmp", ".ico"}:
        ext = ".bin"
    return _get_bing_cache_dir() / f"{h[:16]}{ext}"


async def _download_and_cache(url: str, target: Path) -> Path | None:
    """下载上游图片到 target；成功返回 target，失败返回 None。

    保持默认 trust_env=True：有 HTTP_PROXY/HTTPS_PROXY 环境变量时自动走代理，
    没有时直连；不强制挂载 transport，避免本地代理未启动时直接报错。

    SSRF 防护（net_guard）：请求前 DNS 解析校验 + 重定向逐跳校验。
    """
    try:
        timeout = httpx.Timeout(8.0, connect=3.0, pool=5.0, read=30.0)
        # follow_redirects 必须为 False：重定向由 validated_get 逐跳校验后手动跟随
        # http2 不强制开启：h2 包未安装时会直接抛异常导致下载失败
        async with create_async_client(
            timeout=timeout,
            follow_redirects=False,
            trust_env=True,
        ) as client:
            r = await validated_get(client, url, headers=_UPSTREAM_HEADERS)
            if r.status_code >= 400:
                return None
            media_type = r.headers.get("content-type") or ""
            if not is_image_mime(media_type):
                return None
            # 原子写入：先写 .tmp 再 rename，避免半写文件被读到
            tmp = target.with_suffix(target.suffix + ".tmp")
            with tmp.open("wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=256 * 1024):
                    await asyncio.to_thread(f.write, chunk)
            tmp.replace(target)
            return target
    except Exception as exc:
        logger.warning("[bing_image] 下载缓存失败 %s: %s", url, exc)
        try:
            target.with_suffix(target.suffix + ".tmp").unlink(missing_ok=True)
        except OSError as cleanup_error:
            # 临时文件残留不影响本次响应（已 return None），但会在缓存目录里堆积，
            # 所以按状态清理类要求回报而非吞掉。
            logger.warning(
                "[bing_image] 临时文件清理失败 %s: %s",
                target.with_suffix(target.suffix + ".tmp"),
                cleanup_error,
            )
        return None


@router.get(
    "/bing/image",
    summary="Bing 图片流式代理 + 本地缓存",
    description=(
        "图片代理端点：src 参数是原始图片地址的标准 base64（可含 URL 安全字符替换），"
        "解码失败、非 http(s) 协议或上游拉取失败时，一律 307 跳到站内兜底图，"
        "绝不 302 跳外部地址，以防被当作开放重定向使用。"
        "命中本地缓存或下载成功后以文件直出，Content-Type 取自落盘扩展名，"
        "带 Cache-Control: public, max-age=2592000, immutable（30 天强缓存）与 nosniff。"
        "上游只允许 Bing / Microsoft 白名单域名，且经 SSRF 校验（拒内网、逐跳校验重定向）；"
        "响应 Content-Type 必须是 image/*，否则不落盘直接走兜底。"
        "公开访问、无需鉴权。"
    ),
    responses=raw_content_response(
        "image/*",
        "壁纸二进制流；未命中缓存时可能 302 跳转到上游图片地址。",
        binary=True,
    ),
    response_class=Response,
)
async def bing_image_proxy(src: str = Query(..., description="base64(原始图片URL)")) -> Response:
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

    # 白名单闸门必须先过：`src` 是用户可控的 base64，未限定域名时本端点就是一个
    # 开放图片代理（可拿去探测内网门户、把任意站点资源<｜hy_place▁holder▁no▁813｜>联系方式 IP）。
    # net_guard 只挡私有网段，挡不住"任意公网 URL"，所以域名后缀白名单不可省。
    # （_cache_fp.is_file() 的缓存命中分支也在闸门之后，避免先落盘后被直接读取。）
    if not _is_bing_host(url):
        return RedirectResponse(_FINAL_FALLBACK, status_code=307)

    # 所有图片（包括 Bing 官方域名）统一走本地下载缓存：
    # - 避免 307 重定向导致浏览器每次重新解析上游缓存头
    # - 统一 max-age=2592000 immutable，浏览器重新打开直接命中磁盘缓存
    # - Nginx sendfile 零拷贝，性能优于流式代理
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
    """Bing 每日一图的元数据条目（对上游 URL 拼装后的结果，不含图片本体）。"""

    date: str = PDField(
        description="YYYY-MM-DD，取上游 ``startdate``（Bing 自己认定这张图属于哪一天）；"
        "归档口对没有 startdate 的条目直接丢弃，不拿服务器时钟猜"
    )
    title: str = PDField(description="标题；上游无标题时回退版权文字，再回退兜底文案")
    url: str = PDField(
        description="1920x1080 JPEG 直链；上游未给 urlbase 时是空字符串，"
        "今日图接口兜底分支则是一条 data: URI 占位图"
    )
    url_uhd: str | None = PDField(None, description="4K UHD 原图直链；无 urlbase 时为 null")
    copyright: str | None = PDField(None, description="上游版权署名文字；上游未提供时为 null")
    copyright_url: str | None = PDField(
        None, description="上游版权详情页链接（copyrightlink）；展示署名时可作为出处链接"
    )


class BingTodayResponse(BaseModel):
    """今日图元数据接口的响应体。"""

    success: bool = PDField(True, description="恒为 true：上游拉取失败也按兜底数据成功返回")
    fallback: bool | None = PDField(
        None, description="仅在上游拉取失败、走占位图兜底时出现并为 true；正常拉取时该键缺席"
    )
    data: BingImageOut = PDField(..., description="当日图片元数据")


class BingArchiveResponse(BaseModel):
    """最近 N 天归档接口的响应体。"""

    success: bool = PDField(True, description="恒为 true：整体异常被吞掉并返回已抓到的部分")
    data: list[BingImageOut] = PDField(
        default_factory=list,
        description="归档条目，按请求天数从新到旧排列；"
        "上游非 200 或当天无数据的天会被跳过，因此条数可能少于请求的 days，异常时可为空数组",
    )
    count: int = PDField(0, description="data 的实际长度，可能小于请求参数 days")


@router.get(
    "/bing/image/today",
    summary="获取 Bing 今日图元数据",
    description=(
        "从 Bing 首页图像元数据接口抓取今日信息，公开访问、无需鉴权。"
        "上游请求超时上限 8 秒；任何上游异常都不返回错误码，"
        "而是带 fallback 标记返回一条 data: URI 占位图，保证前端不崩。"
        "结果不做服务端缓存，每次请求都会打上游。"
        "``data.date`` 用上游 ``startdate``（Bing 认定的那一天），不是服务器时钟；"
        "只有兜底分支（上游根本没回）才按 UTC 日期填一条占位。"
    ),
    responses={200: {"model": BingTodayResponse}},
)
async def bing_today_image():
    """从 Bing HP 图像元数据 JSON 接口抓取今日信息，失败则回退到占位图。"""

    try:
        async with create_async_client(timeout=8) as client:
            r = await client.get(
                "https://cn.bing.com/HPImageArchive.aspx",
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
                date=_normalize_startdate(image.get("startdate")) or _utc_today_iso(),
                title=image.get("title") or image.get("copyright") or "Bing",
                url=url_1920,
                url_uhd=url_uhd,
                copyright=image.get("copyright"),
                copyright_url=image.get("copyrightlink"),
            ).model_dump(),
        }
    except Exception as exc:
        logger.warning(f"[bing_image] 拉取 Bing 今日图失败: {exc}")
        # 兜底：返回一张占位 1x1 图，保证前端不崩溃
        return {
            "success": True,
            "fallback": True,
            "data": BingImageOut(
                date=_utc_today_iso(),
                title="Bing 图片暂不可用",
                url="data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E",
            ).model_dump(),
        }


@router.get(
    "/bing/image/archive",
    summary="获取 Bing 最近 N 天图片归档",
    description=(
        "返回最近 days 天的图片元数据列表，公开访问、无需鉴权。"
        "上游一次批量请求即可拿到整段窗口（``n`` 直接传给 Bing），不再按天串行外发；"
        "但 Bing 自己只保留最近 "
        f"{UPSTREAM_RETENTION_DAYS} 天，越过窗口的 ``idx`` 会重复返回最旧那张图，"
        f"所以 ``count`` 最多 ``min(days, {UPSTREAM_RETENTION_DAYS})``，且按 ``urlbase`` 再去一次重。"
        "days 取值 1..14，越界由框架返回 422（保留原入参范围，多要的那几天上游确实没有）。"
        "每条的 ``date`` 取上游 ``startdate``；没有 ``startdate`` 或没有 ``urlbase`` 的条目丢弃，"
        "不按服务器时钟猜日期。"
        "上游不可用或某天缺数据时跳过该天，整体异常同样返回 200，只带已抓到的部分（可能为空数组）。"
        f"非空结果按 days 进服务端缓存 {ARCHIVE_CACHE_TTL} 秒；空结果不写缓存，"
        "一次上游故障不会把空归档钉住一小时。"
    ),
    responses={200: {"model": BingArchiveResponse}},
)
async def bing_archive(days: int = Query(7, ge=1, le=14, description="查询的天数 1..14")):
    """返回最近 days 天的图片元数据列表（上游批量一次请求 + 结果缓存）。"""

    cache_key = make_cache_key("bing", "archive", str(days))
    try:
        cached = await cache.get(cache_key)
    except Exception as exc:  # noqa: BLE001 - 缓存不可用只影响性能，不能让公开口 500
        logger.warning("[bing_image] 归档缓存读取失败: %s", exc)
        cached = None
    if isinstance(cached, list):
        return {"success": True, "data": cached, "count": len(cached)}

    out: list[dict] = []
    seen: set[str] = set()
    try:
        async with create_async_client(timeout=10) as client:
            r = await client.get(
                "https://cn.bing.com/HPImageArchive.aspx",
                params={
                    "format": "js",
                    "idx": 0,
                    # 上游最多回这么多条，多要的几天它并没有
                    "n": min(days, UPSTREAM_RETENTION_DAYS),
                    "mkt": "zh-CN",
                },
            )
            if r.status_code == 200:
                for image in r.json().get("images") or []:
                    if not isinstance(image, dict):
                        continue
                    base = str(image.get("urlbase") or "")
                    entry = _entry_from_image(image)
                    if entry is None or base in seen:
                        continue
                    seen.add(base)
                    out.append(entry)
    except Exception as exc:
        logger.warning(f"[bing_image] 归档查询失败: {exc}")

    if out:
        try:
            await cache.set(cache_key, out, ttl=ARCHIVE_CACHE_TTL)
        except Exception as exc:  # noqa: BLE001 - 缓存写失败不该影响本次响应
            logger.warning("[bing_image] 归档缓存写入失败: %s", exc)
    return {"success": True, "data": out, "count": len(out)}
