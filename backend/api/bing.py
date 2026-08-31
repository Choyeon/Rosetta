"""
Bing 每日壁纸 API

提供获取 Bing 每日壁纸的功能，支持缓存以减少对 Bing API 的请求。
"""

import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.core.cache import cache, make_cache_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bing", tags=["Bing壁纸"])

BING_API_URL = "https://www.bing.com/HPImageArchive.aspx"
BING_CACHE_TTL = 3600  # 缓存 1 小时


class BingWallpaperResponse(BaseModel):
    """Bing 壁纸响应"""

    url: str = Field(..., description="壁纸图片 URL")
    full_url: str = Field(..., description="完整壁纸图片 URL")
    title: str = Field(..., description="壁纸标题")
    description: str = Field(default="", description="壁纸描述")
    copyright: str = Field(default="", description="版权信息")
    copyright_link: str = Field(default="", description="版权链接")
    date: str = Field(..., description="壁纸日期 YYYY-MM-DD")


class BingWallpaperItem(BaseModel):
    """Bing 多日壁纸列表项（对齐前端 useBingWallpaper 所需字段）"""

    url: str = Field(default="", description="相对图片路径")
    urlbase: str = Field(default="", description="图片基础路径（可拼缩略图/UHD）")
    full_url: str = Field(default="", description="完整图片 URL")
    uhd_url: str = Field(default="", description="UHD 高清图 URL")
    title: str = Field(default="", description="壁纸标题")
    copyright: str = Field(default="", description="版权信息")
    copyright_link: str = Field(default="", description="版权链接")
    startdate: str = Field(default="", description="开始日期 YYYYMMDD")
    enddate: str = Field(default="", description="结束日期 YYYYMMDD")


class BingWallpaperListResponse(BaseModel):
    """Bing 多日壁纸响应"""

    images: list[BingWallpaperItem] = Field(default_factory=list, description="壁纸列表")


async def _fetch_bing_wallpaper(market: str = "zh-CN", n: int = 1) -> dict[str, Any]:
    """从 Bing API 获取每日壁纸。若不可达返回 {} 由上层走兜底。

    保持默认 trust_env=True 让 httpx 自动读取 HTTP_PROXY / HTTPS_PROXY 环境变量：
    - 有代理（本地 clash/7897）时自动走代理
    - 无代理时直连
    不强制挂载 transport，避免本地代理未启动时直接报错。
    """
    import httpx

    params = {
        "format": "js",
        "idx": 0,
        "n": n,
        "mkt": market,
    }

    try:
        timeout_cfg = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True, trust_env=True) as client:
            response = await client.get(BING_API_URL, params=params)
            if response.status_code != 200:
                logger.warning(f"Bing API HTTP {response.status_code}, 将走兜底")
                return {}
            return response.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"获取 Bing 壁纸失败（网络或代理不可用）: {e}，将走兜底")
        return {}


@router.get(
    "/wallpaper",
    response_model=BingWallpaperResponse,
    summary="获取每日 Bing 壁纸",
    description="获取 Bing 每日壁纸信息，包含图片 URL、标题、描述和版权信息。结果会被缓存。",
)
async def get_bing_wallpaper(
    market: str = Query(
        default="zh-CN",
        description="地区市场，如 zh-CN、en-US、ja-JP",
    ),
) -> BingWallpaperResponse:
    """获取每日 Bing 壁纸"""
    cache_key = make_cache_key("bing_wallpaper", market)

    # 尝试从缓存获取
    cached = await cache.get(cache_key)
    if cached:
        return BingWallpaperResponse(**cached)

    # 从 Bing API 获取
    data = await _fetch_bing_wallpaper(market)

    images = data.get("images") or []
    if not images:
        # Bing 不可达时返回占位条目，保证前端不崩（前端会用 fullUrl 代理，失败再走 gradient fallback）
        return BingWallpaperResponse(
            url="",
            full_url="",
            title="Bing 壁纸暂不可用",
            description="",
            copyright="",
            copyright_link="",
            date=date.today().isoformat(),
        )

    image = images[0]

    url = image.get("url", "")
    full_url = f"https://www.bing.com{url}" if url and not url.startswith("http") else url

    end_date = image.get("enddate", "")
    if end_date and len(end_date) == 8:
        try:
            parsed_date = datetime.strptime(end_date, "%Y%m%d").date()
            wallpaper_date = parsed_date.isoformat()
        except ValueError:
            wallpaper_date = date.today().isoformat()
    else:
        wallpaper_date = date.today().isoformat()

    result = BingWallpaperResponse(
        url=url,
        full_url=full_url,
        title=image.get("title", ""),
        description=image.get("desc", ""),
        copyright=image.get("copyright", ""),
        copyright_link=image.get("copyrightlink", ""),
        date=wallpaper_date,
    )

    # 写入缓存
    await cache.set(cache_key, result.model_dump(mode="json"), BING_CACHE_TTL)

    return result


@router.get(
    "/wallpapers",
    response_model=BingWallpaperListResponse,
    summary="获取最近多天的 Bing 壁纸列表",
    description="代理 Bing HPImageArchive 接口，一次返回最近 n 天（1-8）的壁纸数据，供前端规避 CORS 直连限制。结果缓存 1 小时。",
)
async def get_bing_wallpapers(
    n: int = Query(default=8, ge=1, le=8, description="返回天数（1-8）"),
    market: str = Query(default="zh-CN", description="地区市场，如 zh-CN、en-US、ja-JP"),
) -> BingWallpaperListResponse:
    """获取最近多天的 Bing 壁纸列表（前端代理）"""
    cache_key = make_cache_key("bing_wallpapers", market, n)

    cached = await cache.get(cache_key)
    if cached:
        return BingWallpaperListResponse(**cached)

    data = await _fetch_bing_wallpaper(market, n=n)

    raw_images = data.get("images") or []
    if not raw_images:
        # Bing 不可达时返回空列表，不抛 502；前端 detect 空后自动走 gradient fallback，不打断页面
        return BingWallpaperListResponse(images=[])

    items: list[BingWallpaperItem] = []
    for image in raw_images:
        url = image.get("url", "")
        urlbase = image.get("urlbase", "")
        uhd_url = f"https://www.bing.com{urlbase}_UHD.jpg" if urlbase else ""
        full_url = f"https://www.bing.com{url}" if url and not url.startswith("http") else url
        items.append(
            BingWallpaperItem(
                url=url,
                urlbase=urlbase,
                full_url=full_url,
                uhd_url=uhd_url,
                title=image.get("title", ""),
                copyright=image.get("copyright", ""),
                copyright_link=image.get("copyrightlink", ""),
                startdate=str(image.get("startdate", "")),
                enddate=str(image.get("enddate", "")),
            )
        )

    result = BingWallpaperListResponse(images=items)
    await cache.set(cache_key, result.model_dump(mode="json"), BING_CACHE_TTL)
    return result
