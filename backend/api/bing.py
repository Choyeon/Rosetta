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
    """从 Bing API 获取每日壁纸"""
    import httpx

    params = {
        "format": "js",
        "idx": 0,
        "n": n,
        "mkt": market,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(BING_API_URL, params=params)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Bing API 返回错误: {response.status_code}",
                )
            return response.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Bing 壁纸失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="获取 Bing 壁纸失败，请稍后重试",
        )


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

    if not data.get("images") or len(data["images"]) == 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bing API 未返回壁纸数据",
        )

    image = data["images"][0]

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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bing API 未返回壁纸数据",
        )

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
