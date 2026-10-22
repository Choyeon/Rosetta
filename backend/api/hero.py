"""
Hero 轮播 API

提供公开接口获取当前活跃 Hero 幻灯片，以及管理员接口管理 CRUD。

路由设计：
- 公开接口: GET /api/hero/slides
- 管理接口: /api/admin/hero/slides (GET/POST/PUT/DELETE/toggle)

硬契约：DB 无生效轮播时的兜底内容源是**高热度文章**（`RecommendationService.get_hot_posts`，
与前台热榜同一个算法与缓存），不再回退到 Bing 每日壁纸。首页横幅的职责是"推荐内容"，
不是"装饰图片"；把壁纸当轮播会让首页首屏依赖站外图片。历史上这里确实直连过 Bing，
结果是公开端点每次请求都对站外发一次最长 15s 的 HTTP。
Bing 壁纸现在只服务登录/注册页（`composables/useBingWallpaper.ts`）。
兜底项用负 ID 标记，不与 DB 记录冲突。
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.core.i18n import get_i18n_value, get_language_from_request
from backend.core.partial_update import apply_partial_update
from backend.models.hero import HeroSlide
from backend.schemas import BaseResponse
from backend.schemas.hero import (
    HeroSlideCreate,
    HeroSlideResponse,
    HeroSlideUpdate,
)
from backend.services.content_renderer import render_title
from backend.services.frontend_cache_purge import purge_frontend_page_cache
from backend.services.recommendation import RecommendationService
from backend.utils.compat import UTC

logger = logging.getLogger("rosetta.api.hero")

router = APIRouter(tags=["Hero轮播"])

# 兜底轮播封面缺省尺寸：与前端 lib/post-cover.ts 的 picsum 兜底同一 seed 口径，
# 同一篇文章在卡片与横幅上拿到同一张占位图。
_FALLBACK_COVER_SIZE = "1600/900"


# ==================== 公开接口 ====================


@router.get(
    "/hero/slides",
    response_model=list[HeroSlideResponse],
    summary="获取当前活跃 Hero 幻灯片",
    description=(
        "公开接口、无需鉴权。获取当前时间范围内处于激活状态的 Hero 幻灯片列表，按 sort_order 升序排列。"
        "若尚未配置任何轮播，则用近 30 天高热度文章自动填充（标题 / 摘要 / 封面 / 文章链接），"
        "这些兜底项带负 ID、不落库、不可在后台编辑。"
        "lang 支持 zh|en|ja|zh_Hant，缺省按 Accept-Language 请求头推断（语言真相只有 URL 前缀，不读 cookie）。"
    ),
)
async def list_active_hero_slides(
    db: DB,
    request: Request,
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
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

    # ========== DB 无轮播时：高热度文章作为虚拟轮播 fallback ==========
    language = get_language_from_request(request, lang)
    hot_posts = await RecommendationService(db).get_hot_posts(limit=5, days=30)
    now_ts = datetime.now(UTC)
    virtual: list[HeroSlideResponse] = []
    for i, post in enumerate(hot_posts):
        title = await render_title(
            get_i18n_value(post.title, language), post=post, language=language
        )
        excerpt = get_i18n_value(post.excerpt, language) if post.excerpt else ""
        # 主标题走 the_title 钩子链（与列表 / RSS / 详情页同口径），
        # 副标题用摘要截断；CTA 指向文章详情的中性路径，语言前缀由前端 localeHref 负责。
        virtual.append(
            HeroSlideResponse(
                id=-(i + 1),  # 负 ID 表示「热榜虚拟轮播」，避免与 DB 冲突
                created_at=now_ts,
                updated_at=now_ts,
                title=title or post.slug,
                subtitle=(excerpt.strip()[:140] or None),
                media_type="image",
                media_url=post.cover_image
                or f"https://picsum.photos/seed/rosetta-post-{post.id}/{_FALLBACK_COVER_SIZE}",
                overlay_opacity=45,
                overlay_color="#000000",
                cta_url=f"/posts/{post.slug}",
                sort_order=i,
                is_active=True,
                text_align="left",
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
    purge_frontend_page_cache("hero slide create")

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
    apply_partial_update(slide, update_data)

    await db.flush()
    await db.refresh(slide)
    purge_frontend_page_cache("hero slide update")
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
    purge_frontend_page_cache("hero slide delete")
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
    purge_frontend_page_cache("hero slide toggle")
    return HeroSlideResponse.model_validate(slide)
