"""
Hero 轮播 API

提供公开接口获取当前活跃 Hero 幻灯片，以及管理员接口管理 CRUD。

路由设计：
- 公开接口: GET /api/hero/slides
- 管理接口: /api/admin/hero/slides (GET/POST/PUT/DELETE/toggle)
"""

from __future__ import annotations

import logging
import os as _os
import time as _time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.core.site_config import get_site_config_value
from backend.models.hero import HeroSlide
from backend.schemas import BaseResponse
from backend.schemas.hero import (
    HeroSlideCreate,
    HeroSlideResponse,
    HeroSlideUpdate,
)
from backend.utils.compat import UTC

logger = logging.getLogger("rosetta.api.hero")

router = APIRouter(tags=["Hero轮播"])

BING_API_URL = "https://www.bing.com/HPImageArchive.aspx"
_BING_FALLBACK_TTL = 3600 * 24
_bing_last_success: list[dict] | None = None
_bing_last_success_at: float = 0.0


def _get_proxy() -> str | None:
    http_proxy = _os.environ.get("HTTP_PROXY") or _os.environ.get("http_proxy")
    https_proxy = _os.environ.get("HTTPS_PROXY") or _os.environ.get("https_proxy")
    return https_proxy or http_proxy or None


def _build_full_url(url: str | None, urlbase: str | None) -> str:
    if url:
        if url.startswith("http"):
            return url
        return f"https://www.bing.com{url}"
    if urlbase:
        return f"https://www.bing.com{urlbase}_1920x1080.jpg"
    return ""


async def _fetch_bing_wallpapers(n: int = 8, mkt: str = "zh-CN") -> list[dict]:
    """拉取 Bing 壁纸，带 24h 最近一次成功 fallback。"""
    import httpx as _httpx

    global _bing_last_success, _bing_last_success_at

    proxy = _get_proxy()
    params = {"format": "js", "idx": 0, "n": max(1, min(15, int(n))), "mkt": mkt}
    images_out: list[dict] = []

    try:
        timeout = _httpx.Timeout(15.0, connect=8.0)
        async with _httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
            raw = await client.get(BING_API_URL, params=params)
            if raw.status_code != 200:
                raise RuntimeError(f"Bing HTTP {raw.status_code}")
            data = raw.json()
    except Exception as exc:
        logger.warning("Bing 壁纸拉取失败 n=%s mkt=%s: %s", n, mkt, exc)
        now = _time.time()
        if _bing_last_success and (now - _bing_last_success_at) < _BING_FALLBACK_TTL:
            return list(_bing_last_success)
        return []

    raw_images = data.get("images") or []
    for img in raw_images:
        url = img.get("url") or ""
        urlbase = img.get("urlbase") or ""
        full_url = _build_full_url(url, urlbase)
        if not full_url:
            continue
        images_out.append(
            {
                "title": img.get("title", ""),
                "copyright": img.get("copyright", ""),
                "copyrightlink": img.get("copyrightlink", ""),
                "startdate": img.get("startdate", ""),
                "enddate": img.get("enddate", ""),
                "full_url": full_url,
            }
        )
    if images_out:
        _bing_last_success = list(images_out)
        _bing_last_success_at = _time.time()
    return images_out


# ==================== 公开接口 ====================


@router.get(
    "/hero/slides",
    response_model=list[HeroSlideResponse],
    summary="获取当前活跃 Hero 幻灯片",
    description="获取当前时间范围内处于激活状态的 Hero 幻灯片列表，按 sort_order 升序排列。若尚未配置任何轮播且开启 Bing 壁纸，则自动用 Bing 最近几日壁纸作为虚拟轮播填充。",
)
async def list_active_hero_slides(db: DB):
    """获取当前生效的 Hero 幻灯片（公开接口）"""
    now = datetime.now(UTC)

    query = (
        select(HeroSlide)
        .where(HeroSlide.is_active.is_(True))
        .where((HeroSlide.start_time.is_(None)) | (HeroSlide.start_time <= now))
        .where((HeroSlide.end_time.is_(None)) | (HeroSlide.end_time >= now))
        .order_by(HeroSlide.sort_order.asc(), HeroSlide.created_at.desc())
    )

    result = await db.execute(query)
    slides = list(result.scalars().all())

    if slides:
        return slides

    # ========== DB 无轮播时：Bing 壁纸作为虚拟轮播 fallback ==========
    # 读取 Bing 壁纸开关（site_configs 大小写不敏感；默认 True）
    bing_enabled_raw = await get_site_config_value("enable_bing_wallpaper")
    if bing_enabled_raw is None:
        bing_enabled_raw = await get_site_config_value("ENABLE_BING_WALLPAPER")
    bing_enabled = True
    if isinstance(bing_enabled_raw, str):
        bing_enabled = bing_enabled_raw.strip().lower() not in ("0", "false", "no", "off", "")
    elif bing_enabled_raw is None:
        bing_enabled = True
    else:
        bing_enabled = bool(bing_enabled_raw)

    if not bing_enabled:
        return []

    wallpapers = await _fetch_bing_wallpapers(n=8)
    now_ts = datetime.now(UTC)
    virtual: list[HeroSlideResponse] = []
    for i, wp in enumerate(wallpapers):
        full_url = wp.get("full_url") or ""
        if not full_url:
            continue
        title = wp.get("title") or ""
        copyright_text = wp.get("copyright") or ""
        # 主标题使用 Bing 标题；副标题使用版权说明作为信息
        virtual.append(
            HeroSlideResponse(
                id=-(i + 1),  # 负 ID 表示「Bing 虚拟轮播」，避免与 DB 冲突
                created_at=now_ts,
                updated_at=now_ts,
                title=title or copyright_text or "Bing 每日壁纸",
                subtitle=copyright_text if title else None,
                media_type="image",
                media_url=full_url,
                overlay_opacity=35,
                overlay_color="#000000",
                sort_order=i,
                is_active=True,
                text_align="center",
                text_color="light",
            )
        )
    return virtual


# ==================== 管理接口 ====================


@router.get(
    "/admin/hero/slides",
    response_model=list[HeroSlideResponse],
    summary="管理员获取所有 Hero 幻灯片",
    description="管理员获取所有 Hero 幻灯片列表，支持按激活状态过滤。",
)
async def admin_list_hero_slides(
    db: DB,
    current_user: CurrentStaff,
    is_active: bool | None = Query(None, description="按激活状态过滤"),
):
    """管理员获取所有 Hero 幻灯片"""
    query = select(HeroSlide).order_by(HeroSlide.sort_order.asc(), HeroSlide.created_at.desc())

    if is_active is not None:
        query = query.where(HeroSlide.is_active == is_active)

    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/admin/hero/slides",
    response_model=HeroSlideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 Hero 幻灯片",
    description="管理员创建新 Hero 幻灯片。",
)
async def create_hero_slide(
    data: HeroSlideCreate,
    db: DB,
    current_user: CurrentStaff,
):
    """创建 Hero 幻灯片"""
    slide = HeroSlide(
        title=data.title,
        subtitle=data.subtitle,
        media_type=data.media_type,
        media_url=data.media_url,
        poster_url=data.poster_url,
        overlay_opacity=data.overlay_opacity,
        overlay_color=data.overlay_color,
        cta_text=data.cta_text,
        cta_url=data.cta_url,
        cta_secondary_text=data.cta_secondary_text,
        cta_secondary_url=data.cta_secondary_url,
        text_align=data.text_align,
        text_color=data.text_color,
        is_active=data.is_active,
        sort_order=data.sort_order,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(slide)
    await db.flush()
    await db.refresh(slide)

    return HeroSlideResponse.model_validate(slide)


@router.put(
    "/admin/hero/slides/{slide_id}",
    response_model=HeroSlideResponse,
    summary="更新 Hero 幻灯片",
    description="管理员更新指定 Hero 幻灯片。",
)
async def update_hero_slide(
    slide_id: int,
    data: HeroSlideUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """更新 Hero 幻灯片"""
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()

    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hero 幻灯片不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slide, field, value)

    await db.flush()
    await db.refresh(slide)
    return HeroSlideResponse.model_validate(slide)


@router.delete(
    "/admin/hero/slides/{slide_id}",
    response_model=BaseResponse,
    summary="删除 Hero 幻灯片",
    description="管理员删除指定 Hero 幻灯片。",
)
async def delete_hero_slide(
    slide_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除 Hero 幻灯片"""
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()

    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hero 幻灯片不存在",
        )

    await db.delete(slide)
    return BaseResponse(message="Hero 幻灯片已删除")


@router.put(
    "/admin/hero/slides/{slide_id}/toggle",
    response_model=HeroSlideResponse,
    summary="切换 Hero 幻灯片激活状态",
    description="管理员切换 Hero 幻灯片的激活状态。",
)
async def toggle_hero_slide(
    slide_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """切换 Hero 幻灯片激活状态"""
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()

    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hero 幻灯片不存在",
        )

    slide.is_active = not slide.is_active
    await db.flush()
    await db.refresh(slide)
    return HeroSlideResponse.model_validate(slide)
