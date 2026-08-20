"""
核心功能 API

提供页面、导航、友链、站点配置等核心功能。

缓存策略：
- 站点配置：1 小时
- 导航列表：1 小时
- 友链列表：30 分钟

性能优化：
- 使用 asyncio.gather 并行查询
- 使用两级缓存（本地 + Redis）
- 使用后台任务处理缓存失效
"""

import math
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import func, select

from backend.core.auth import DB, CurrentStaff, CurrentUserOptional
from backend.core.cache import CACHE_TTL, cache, invalidate_cache, make_cache_key
from backend.models.core import FriendLink, Navigation, Page, SearchPlaceholder, SiteConfig

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OOBE_LOCK_FILE = BASE_DIR / ".oobe_complete"
CONFIG_FILE = BASE_DIR / "rosetta.json"


def is_oobe_complete() -> bool:
    return OOBE_LOCK_FILE.exists() and CONFIG_FILE.exists()


from backend.schemas import (
    BaseResponse,
    FriendLinkCreate,
    FriendLinkResponse,
    FriendLinkUpdate,
    NavigationCreate,
    NavigationResponse,
    NavigationUpdate,
    PageCreate,
    PageResponse,
    PageUpdate,
    PaginatedResponse,
    SiteConfigFullResponse,
    SiteConfigResponse,
    SiteConfigUpdate,
    SiteSettingGroup,
    SiteSettingItem,
)

router = APIRouter(tags=["核心"])


# ==================== 页面接口 ====================


@router.get(
    "/pages",
    response_model=PaginatedResponse,
    summary="页面列表",
    description="获取独立页面列表，普通用户只能看到已发布的页面。",
)
async def list_pages(
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: CurrentUserOptional = None,
):
    """获取页面列表"""
    query = select(Page)

    # 权限过滤：普通用户只能看已发布的
    if not current_user or not (current_user.is_staff or current_user.is_superuser):
        query = query.where(Page.status == "published")

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页查询
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Page.created_at.desc())
    result = await db.execute(query)
    pages = result.scalars().all()

    return PaginatedResponse(
        items=[PageResponse.model_validate(p) for p in pages],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/pages/{slug}",
    response_model=PageResponse,
    summary="页面详情",
    description="根据 slug 获取页面内容。",
)
async def get_page(slug: str, db: DB, current_user: CurrentUserOptional = None):
    """获取页面详情"""
    result = await db.execute(select(Page).where(Page.slug == slug))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )

    # 权限检查
    if page.status != "published":
        if not current_user or not (current_user.is_staff or current_user.is_superuser):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="页面不存在",
            )

    return PageResponse.model_validate(page)


@router.post(
    "/pages",
    response_model=PageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建页面",
    description="创建独立页面，需要管理员权限。",
)
async def create_page(data: PageCreate, current_user: CurrentStaff, db: DB):
    """创建页面"""
    # 检查 slug 是否重复
    existing = await db.execute(select(Page).where(Page.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="页面别名已存在",
        )

    page = Page(
        title=data.title,
        slug=data.slug,
        content=data.content,
        status=data.status,
    )
    db.add(page)
    await db.flush()

    return PageResponse.model_validate(page)


@router.put(
    "/pages/{page_id}",
    response_model=PageResponse,
    summary="更新页面",
    description="更新页面内容，需要管理员权限。",
)
async def update_page(page_id: int, data: PageUpdate, current_user: CurrentStaff, db: DB):
    """更新页面"""
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)

    await db.flush()
    return PageResponse.model_validate(page)


@router.delete(
    "/pages/{page_id}",
    response_model=BaseResponse,
    summary="删除页面",
    description="删除页面，需要管理员权限。",
)
async def delete_page(page_id: int, current_user: CurrentStaff, db: DB):
    """删除页面"""
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )

    await db.delete(page)
    return BaseResponse(message="页面已删除")


# ==================== 导航接口 ====================


@router.get(
    "/navigations",
    response_model=list[NavigationResponse],
    summary="导航列表",
    description="获取网站导航菜单，可按位置筛选。",
)
async def list_navigations(
    db: DB, location: str | None = Query(None, description="位置：header/footer/sidebar")
):
    """获取导航列表（带缓存）"""
    if not is_oobe_complete():
        # OOBE 默认导航：完全匹配前端 navBarConfig 的父子结构
        default_navs = [
            # ===== 父级导航（parent_id=None） =====
            {
                "id": 1,
                "parent_id": None,
                "icon": "material-symbols:home",
                "title": {"zh": "首页", "en": "Home", "ja": "ホーム", "zh_Hant": "首頁"},
                "url": "/",
                "location": "header",
                "order": 1,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 2,
                "parent_id": None,
                "icon": "material-symbols:article",
                "title": {"zh": "文章", "en": "Posts", "ja": "投稿一覧", "zh_Hant": "文章"},
                "url": "#",
                "location": "header",
                "order": 2,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 3,
                "parent_id": None,
                "icon": "material-symbols:group",
                "title": {"zh": "社交", "en": "Social", "ja": "ソーシャル", "zh_Hant": "社交"},
                "url": "#",
                "location": "header",
                "order": 3,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 4,
                "parent_id": None,
                "icon": "material-symbols:person",
                "title": {"zh": "我的", "en": "My", "ja": "マイページ", "zh_Hant": "我的"},
                "url": "#",
                "location": "header",
                "order": 4,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 5,
                "parent_id": None,
                "icon": "material-symbols:info",
                "title": {"zh": "关于", "en": "About", "ja": "このサイトについて", "zh_Hant": "關於"},
                "url": "#",
                "location": "header",
                "order": 5,
                "is_active": True,
                "target_blank": False,
            },
            # ===== 子级导航：文章（parent_id=2） =====
            {
                "id": 6,
                "parent_id": 2,
                "icon": "material-symbols:archive",
                "title": {"zh": "归档", "en": "Archive", "ja": "アーカイブ", "zh_Hant": "彙整"},
                "url": "/archive/",
                "location": "header",
                "order": 1,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 7,
                "parent_id": 2,
                "icon": "material-symbols:folder-open-rounded",
                "title": {"zh": "分类", "en": "Categories", "ja": "カテゴリ", "zh_Hant": "分類"},
                "url": "/categories/",
                "location": "header",
                "order": 2,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 8,
                "parent_id": 2,
                "icon": "material-symbols:tag-rounded",
                "title": {"zh": "标签", "en": "Tags", "ja": "タグ", "zh_Hant": "標籤"},
                "url": "/tags/",
                "location": "header",
                "order": 3,
                "is_active": True,
                "target_blank": False,
            },
            # ===== 子级导航：社交（parent_id=3） =====
            {
                "id": 9,
                "parent_id": 3,
                "icon": "material-symbols:link-2-rounded",
                "title": {"zh": "友链", "en": "Friends", "ja": "フレンド", "zh_Hant": "友鏈"},
                "url": "/friends/",
                "location": "header",
                "order": 1,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 10,
                "parent_id": 3,
                "icon": "material-symbols:chat",
                "title": {"zh": "留言板", "en": "Guestbook", "ja": "掲示板", "zh_Hant": "留言板"},
                "url": "/guestbook/",
                "location": "header",
                "order": 2,
                "is_active": True,
                "target_blank": False,
            },
            # ===== 子级导航：我的（parent_id=4） =====
            {
                "id": 11,
                "parent_id": 4,
                "icon": "material-symbols:forum-rounded",
                "title": {"zh": "动态", "en": "Dynamic", "ja": "ダイナミック", "zh_Hant": "動態"},
                "url": "/dynamic/",
                "location": "header",
                "order": 1,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 12,
                "parent_id": 4,
                "icon": "material-symbols:photo-library",
                "title": {"zh": "相册", "en": "Gallery", "ja": "ギャラリー", "zh_Hant": "相簿"},
                "url": "/gallery/",
                "location": "header",
                "order": 2,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 13,
                "parent_id": 4,
                "icon": "material-symbols:dashboard",
                "title": {"zh": "后台管理", "en": "Admin", "ja": "管理画面", "zh_Hant": "後台管理"},
                "url": "/admin/",
                "location": "header",
                "order": 3,
                "is_active": True,
                "target_blank": False,
            },
            # ===== 子级导航：关于（parent_id=5） =====
            {
                "id": 14,
                "parent_id": 5,
                "icon": "material-symbols:favorite",
                "title": {"zh": "打赏", "en": "Sponsor", "ja": "スポンサー", "zh_Hant": "打賞"},
                "url": "/sponsor/",
                "location": "header",
                "order": 1,
                "is_active": True,
                "target_blank": False,
            },
            {
                "id": 15,
                "parent_id": 5,
                "icon": "material-symbols:person",
                "title": {"zh": "关于我", "en": "About Me", "ja": "私について", "zh_Hant": "關於我"},
                "url": "/about/",
                "location": "header",
                "order": 2,
                "is_active": True,
                "target_blank": False,
            },
        ]
        if location:
            default_navs = [n for n in default_navs if n["location"] == location]
        return [NavigationResponse(**n) for n in default_navs]

    cache_key = make_cache_key("navigations", location or "all")
    cached = await cache.get(cache_key)
    if cached:
        return cached

    query = select(Navigation).where(Navigation.is_active.is_(True)).order_by(Navigation.order)

    if location:
        query = query.where(Navigation.location == location)

    result = await db.execute(query)
    navs = result.scalars().all()
    response = [NavigationResponse.model_validate(n) for n in navs]

    await cache.set(
        cache_key,
        [r.model_dump(mode="json") for r in response],
        CACHE_TTL["navigations"],
    )
    return response


@router.post(
    "/navigations",
    response_model=NavigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建导航",
    description="添加导航菜单项，需要管理员权限。",
)
async def create_navigation(data: NavigationCreate, current_user: CurrentStaff, db: DB):
    """创建导航"""
    nav = Navigation(
        title=data.title,
        url=data.url,
        icon=data.icon,
        parent_id=data.parent_id,
        location=data.location,
        order=data.order,
        is_active=data.is_active,
        target_blank=data.target_blank,
    )
    db.add(nav)
    await db.flush()

    await invalidate_cache("navigations")

    return NavigationResponse.model_validate(nav)


@router.put(
    "/navigations/{nav_id}",
    response_model=NavigationResponse,
    summary="更新导航",
    description="更新导航菜单项，需要管理员权限。",
)
async def update_navigation(
    nav_id: int, data: NavigationUpdate, current_user: CurrentStaff, db: DB
):
    """更新导航"""
    result = await db.execute(select(Navigation).where(Navigation.id == nav_id))
    nav = result.scalar_one_or_none()

    if not nav:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="导航不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(nav, field, value)

    await db.flush()
    await invalidate_cache("navigations")

    return NavigationResponse.model_validate(nav)


@router.delete(
    "/navigations/{nav_id}",
    response_model=BaseResponse,
    summary="删除导航",
    description="删除导航菜单项，需要管理员权限。",
)
async def delete_navigation(nav_id: int, current_user: CurrentStaff, db: DB):
    """删除导航"""
    result = await db.execute(select(Navigation).where(Navigation.id == nav_id))
    nav = result.scalar_one_or_none()

    if not nav:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="导航不存在",
        )

    await db.delete(nav)
    await invalidate_cache("navigations")

    return BaseResponse(message="导航已删除")


@router.get(
    "/admin/navigations",
    response_model=list[NavigationResponse],
    summary="管理员获取所有导航",
    description="管理员获取所有导航菜单（包括未激活），需要管理员权限。",
)
async def admin_list_navigations(
    db: DB,
    current_user: CurrentStaff,
    location: str | None = Query(None, description="位置：header/footer/sidebar"),
):
    """管理员获取所有导航"""
    query = select(Navigation).order_by(Navigation.order)

    if location:
        query = query.where(Navigation.location == location)

    result = await db.execute(query)
    return result.scalars().all()


# ==================== 友链接口 ====================


@router.get(
    "/friend-links",
    response_model=list[FriendLinkResponse],
    summary="友链列表",
    description="获取友情链接列表。",
)
async def list_friend_links(
    db: DB, all: bool = Query(False, description="是否获取所有友链（包括未激活）")
):
    """获取友链列表（带缓存）"""
    if not is_oobe_complete():
        return []

    cache_key = make_cache_key("friend_links", "all" if all else "active")
    cached = await cache.get(cache_key)
    if cached:
        # 直接返回缓存的列表，不需要再验证
        return cached

    query = select(FriendLink).order_by(FriendLink.order)
    if not all:
        query = query.where(FriendLink.is_active.is_(True))
    result = await db.execute(query)
    links = result.scalars().all()
    response = [FriendLinkResponse.model_validate(f) for f in links]

    # 缓存序列化后的数据
    await cache.set(
        cache_key,
        [r.model_dump(mode="json") for r in response],
        CACHE_TTL["friend_links"],
    )
    return response


@router.post(
    "/friend-links",
    response_model=FriendLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建友链",
    description="添加友情链接，需要管理员权限。",
)
async def create_friend_link(data: FriendLinkCreate, current_user: CurrentStaff, db: DB):
    """创建友链"""
    link = FriendLink(
        name=data.name,
        url=data.url,
        description=data.description,
        logo=data.logo,
        order=data.order,
        is_active=data.is_active,
        target_blank=data.target_blank,
    )
    db.add(link)
    await db.flush()

    await invalidate_cache("friend_links")

    return FriendLinkResponse.model_validate(link)


@router.delete(
    "/friend-links/{link_id}",
    response_model=BaseResponse,
    summary="删除友链",
    description="删除友情链接，需要管理员权限。",
)
async def delete_friend_link(link_id: int, current_user: CurrentStaff, db: DB):
    """删除友链"""
    result = await db.execute(select(FriendLink).where(FriendLink.id == link_id))
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="友情链接不存在",
        )

    await db.delete(link)
    await invalidate_cache("friend_links")

    return BaseResponse(message="友情链接已删除")


@router.put(
    "/friend-links/{link_id}",
    response_model=FriendLinkResponse,
    summary="更新友链",
    description="更新友情链接，需要管理员权限。",
)
async def update_friend_link(
    link_id: int,
    data: FriendLinkUpdate,
    current_user: CurrentStaff,
    db: DB,
):
    """更新友链"""
    result = await db.execute(select(FriendLink).where(FriendLink.id == link_id))
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="友情链接不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(link, field, value)

    await db.flush()
    await invalidate_cache("friend_links")

    return FriendLinkResponse.model_validate(link)


# ==================== 其他接口 ====================


@router.get(
    "/sponsors",
    response_model=list[dict],
    summary="打赏者列表",
    description="获取公开的打赏者列表。优先从站点配置 SPONSORS 读取，未配置时返回空列表。",
)
async def list_sponsors(db: DB):
    """
    获取打赏者列表（带缓存）

    数据来源：site_configs 表中 key='SPONSORS' 的 JSON 字符串，
    格式为 `[{"name": "用户名", "avatar": "...", "amount": "¥50", "date": "2025-10-01"}, ...]`。
    未配置时返回空列表，前端应回退到本地 sponsorConfig。
    """
    cache_key = make_cache_key("sponsors")
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(SiteConfig).where(SiteConfig.key == "SPONSORS")
    )
    config = result.scalar_one_or_none()

    sponsors: list[dict] = []
    if config and config.value:
        import json as _json

        try:
            parsed = _json.loads(config.value)
            if isinstance(parsed, list):
                sponsors = [
                    {
                        "name": str(item.get("name", "")),
                        "avatar": item.get("avatar") or "",
                        "amount": item.get("amount") or "",
                        "date": item.get("date") or "",
                    }
                    for item in parsed
                    if isinstance(item, dict) and item.get("name")
                ]
        except (ValueError, TypeError):
            pass

    await cache.set(cache_key, sponsors, CACHE_TTL["friend_links"])
    return sponsors


@router.get(
    "/search-placeholders",
    response_model=list[str],
    summary="搜索占位符",
    description="获取搜索框的随机占位符文本列表。",
)
async def list_search_placeholders(db: DB):
    """获取搜索占位符"""
    result = await db.execute(
        select(SearchPlaceholder.text)
        .where(SearchPlaceholder.is_active.is_(True))
        .order_by(SearchPlaceholder.order)
    )
    return [r[0] for r in result.all()]


@router.get(
    "/config",
    response_model=SiteConfigResponse,
    summary="站点配置",
    description="获取网站全局配置信息。",
)
async def get_site_config(db: DB):
    """
    获取站点配置（带缓存和并发优化）
    """
    # 侧边栏默认配置
    default_sidebar: dict[str, Any] = {
        "show_profile": True,
        "show_categories": True,
        "show_tags": True,
        "show_recent_posts": True,
        "show_recent_comments": True,
        "show_tag_cloud": True,
        "show_site_info": True,
        "show_music": True,
        "show_statistics": True,
        "show_dynamics": True,
        "widget_order": [
            "profile",
            "site_info",
            "statistics",
            "dynamics",
            "music",
            "categories",
            "tags",
            "recent_posts",
            "recent_comments",
        ],
    }

    def _sidebar_dict_to_flat(sb: dict[str, Any]) -> dict[str, Any]:
        """把 sidebar 分组字典打平成 SiteConfigResponse 的 sidebar_* 字段"""
        out: dict[str, Any] = {}
        for k, v in sb.items():
            if k == "widget_order":
                out["sidebar_widget_order"] = v
            else:
                out[f"sidebar_{k}"] = v
        return out

    if not is_oobe_complete():
        oobe_kwargs = dict(
            site_name="Rosetta",
            site_description="Rosetta开源博客系统",
            site_keywords="Rosetta, Blog",
            site_author="Choyeon",
            site_email="",
            footer_text="Powered by Rosetta",
            enable_comments=True,
            enable_registration=True,
            enable_rss_feed=True,
            pagination_page_size=12,
            code_theme="github",
            # 音乐播放器默认设置（不内置歌单，请到管理后台填写）
            music_enabled=True,
            music_show_in_navbar=True,
            music_show_in_sidebar=True,
            music_mode="meting",
            music_volume=0.7,
            music_play_mode="list",
            music_show_lyrics=True,
            music_meting_api="",
            music_meting_server="netease",
            music_meting_type="playlist",
            music_meting_id="",
            # 壁纸默认设置（默认开启 Bing 每日壁纸）
            wallpaper_mode="banner",
            wallpaper_player_enable=True,
            wallpaper_use_bing=True,
            wallpaper_bing_days=30,
            wallpaper_dim_opacity=0.2,
            wallpaper_home_title="Welcome",
            # 关于页面内容
            about_content="",
            # 友链申请区域自定义 HTML 内容
            friends_apply_html="",
            # 作者/侧边栏资料设置（与一键 OOBE 默认管理员昵称/bio 对齐，避免显示 ROSETTA 示例文案）
            author_name="Choyeon",
            author_bio="Full-Stack Development",
            author_avatar="",
            author_links_json="[]",
            # ===== 新增字段 =====
            site_url="",
            site_start_date="2025-01-01",
            footer_custom_html="",
            friends_page_title="",
            friends_page_description="",
            friends_page_show_comment=True,
            friends_page_show_custom_content=True,
            dynamic_page_title="",
            dynamic_page_description="",
            dynamic_page_items_per_page=10,
            dynamic_page_show_comment=True,
            sponsor_page_title="",
            sponsor_page_description="",
            sponsor_page_usage="",
            sponsor_methods_json="[]",
            sponsor_show_sponsors_list=True,
            sponsor_page_show_comment=True,
            # ========== 页面开关配置 ==========
            page_friends_enabled=True,
            page_sponsor_enabled=True,
            page_guestbook_enabled=True,
            page_bangumi_enabled=True,
            page_gallery_enabled=True,
            page_anime_enabled=True,
            page_dynamic_enabled=True,
            # ========== 导航栏显示配置 ==========
            category_bar_enabled=True,
            # ========== 归档页配置 ==========
            archive_fold_old_articles=True,
            # ========== 文章列表布局配置 ==========
            post_list_default_mode="list",
            post_list_mobile_mode="grid",
            post_list_description_lines=2,
            post_list_show_stats_icons=True,
            post_list_tags_position="bottom",
            # ========== 文章详情页配置 ==========
            post_show_last_modified=True,
            post_outdated_threshold_days=30,
            post_enable_share_poster=True,
            post_generate_og_images=False,
            # ========== 封面图配置 ==========
            cover_enable_in_post=True,
            cover_enable_overlay=True,
            cover_show_loading=False,
            cover_random_enable=False,
            cover_random_apis_json="[]",
            # ========== 许可证配置 ==========
            license_enable=True,
            license_name="CC BY-NC-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
            license_icon="",
            # ========== 评论系统配置 ==========
            comment_system_type="none",
            comment_twikoo_env_id="",
            comment_twikoo_lang="zh-CN",
            comment_twikoo_visitor_count=True,
            comment_twikoo_js_url="https://cdn.jsdelivr.net/npm/twikoo@1.7.14/dist/twikoo.min.js",
            comment_twikoo_css_url="",
            comment_waline_server_url="",
            comment_waline_lang="zh-CN",
            comment_waline_emoji_json='["https://unpkg.com/@waline/emojis@1.4.0/weibo","https://unpkg.com/@waline/emojis@1.4.0/bilibili"]',
            comment_waline_login_mode="enable",
            comment_waline_visitor_count=True,
            comment_artalk_server="",
            comment_artalk_locale="zh-CN",
            comment_artalk_visitor_count=True,
            comment_giscus_repo="",
            comment_giscus_repo_id="",
            comment_giscus_category="General",
            comment_giscus_category_id="",
            comment_giscus_mapping="title",
            comment_giscus_strict="0",
            comment_giscus_reactions_enabled="1",
            comment_giscus_emit_metadata="1",
            comment_giscus_input_position="top",
            comment_giscus_lang="zh-CN",
            comment_giscus_loading="lazy",
            comment_disqus_shortname="",
            # ========== Bangumi配置 ==========
            bangumi_user_id="",
            bangumi_mode="dynamic",
            bangumi_api_url="https://bgmapi.anibt.net",
            bangumi_subject_base_url="https://bgmmi.anibt.net/subject/",
            bangumi_category_order_json='["anime","book","music","game"]',
            # ========== 追番配置 ==========
            anime_bilibili_uid="",
            anime_tmdb_api_key="",
            anime_tmdb_list_id="",
            # ========== 分页配置 ==========
            pagination_posts_per_page=10,
            # ========== 图像优化配置 ==========
            image_opt_formats="webp",
            image_opt_quality=85,
            image_opt_no_referrer_json='["*.hdslb.com","*.bilibili.com"]',
            # ========== 樱花特效配置 ==========
            sakura_enable=False,
            sakura_count=21,
            sakura_min_scale=0.5,
            sakura_max_scale=1.1,
            sakura_min_opacity=0.3,
            sakura_max_opacity=0.9,
            sakura_z_index=100,
            # ========== 看板娘/Spine模型配置 ==========
            pio_spine_enable=False,
            pio_spine_model_path="",
            pio_spine_scale=1.0,
            pio_spine_position_corner="bottom-left",
            pio_spine_width=135,
            pio_spine_height=165,
            pio_spine_z_index=1000,
            # ========== Mermaid图表配置 ==========
            mermaid_theme="default",
            mermaid_security_level="strict",
            # ========== PlantUML配置 ==========
            plantuml_server_url="https://www.plantuml.com/plantuml",
        )
        oobe_kwargs.update(_sidebar_dict_to_flat(default_sidebar))
        return SiteConfigResponse(**oobe_kwargs)


    # 合并 settings_groups 表中 17 组 JSON（admin 编辑保存的）进入 /api/config 返回值。
    # 优先级：site_configs 扁平 key → settings_groups JSON（覆盖/补充） → 环境 fallback
    def _apply_settings_groups(cfg_base: dict[str, Any]) -> dict[str, Any]:
        import json as _json_
        try:
            # basic
            raw_basic = configs.get("basic")
            if raw_basic:
                parsed = _json_.loads(raw_basic)
                if isinstance(parsed, dict):
                    if parsed.get("site_name"):
                        cfg_base["site_name"] = str(parsed["site_name"])
                    if parsed.get("subtitle") is not None:
                        cfg_base["site_subtitle"] = str(parsed["subtitle"])
                    if parsed.get("description"):
                        cfg_base["site_description"] = str(parsed["description"])
                    if parsed.get("keywords") is not None:
                        cfg_base["site_keywords"] = str(parsed["keywords"])
                    if parsed.get("site_url"):
                        cfg_base["site_url"] = str(parsed["site_url"])
                    if parsed.get("logo"):
                        cfg_base["site_logo"] = str(parsed["logo"])
                    if parsed.get("icp_number") is not None:
                        cfg_base["icp_number"] = str(parsed["icp_number"]) or None
                    if parsed.get("about_content") is not None:
                        cfg_base["about_content"] = str(parsed["about_content"])
            # seo
            raw_seo = configs.get("seo")
            if raw_seo:
                parsed = _json_.loads(raw_seo)
                if isinstance(parsed, dict):
                    if parsed.get("default_description"):
                        cfg_base["site_description"] = str(parsed["default_description"])
                    if parsed.get("default_keywords"):
                        cfg_base["site_keywords"] = str(parsed["default_keywords"])
                    if parsed.get("og_image"):
                        cfg_base["default_og_image"] = str(parsed["og_image"])
            # appearance
            raw_appearance = configs.get("appearance")
            if raw_appearance:
                parsed = _json_.loads(raw_appearance)
                if isinstance(parsed, dict):
                    if parsed.get("primary_color"):
                        cfg_base["primary_color"] = str(parsed["primary_color"])
                        cfg_base["theme_primary"] = str(parsed["primary_color"])
                    if parsed.get("accent_color"):
                        cfg_base["theme_accent"] = str(parsed["accent_color"])
                        cfg_base["accent_color"] = str(parsed["accent_color"])
                    if parsed.get("default_theme"):
                        cfg_base["default_theme"] = str(parsed["default_theme"])
                    if parsed.get("code_theme"):
                        cfg_base["code_theme"] = str(parsed["code_theme"])
                    if parsed.get("code_theme_dark"):
                        cfg_base["code_theme_dark"] = str(parsed["code_theme_dark"])
                    if parsed.get("font_family"):
                        cfg_base["font_family"] = str(parsed["font_family"])
            # footer
            raw_footer = configs.get("footer")
            if raw_footer:
                parsed = _json_.loads(raw_footer)
                if isinstance(parsed, dict):
                    if parsed.get("text") is not None:
                        cfg_base["footer_text"] = str(parsed["text"])
                    if parsed.get("slogan") is not None:
                        cfg_base["footer_slogan"] = str(parsed["slogan"])
                    if parsed.get("copyright") is not None:
                        cfg_base["copyright_text"] = str(parsed["copyright"])
                    if parsed.get("icp_number") is not None:
                        cfg_base["icp_number"] = str(parsed["icp_number"]) or None
                    if parsed.get("police_icp_number") is not None:
                        cfg_base["police_icp_number"] = str(parsed["police_icp_number"]) or None
            # sidebar（已经由后续 _sidebar_dict_to_flat 读取默认，这里覆盖）
            raw_sb = configs.get("sidebar")
            if raw_sb:
                parsed_sb = _json_.loads(raw_sb)
                if isinstance(parsed_sb, dict):
                    for k, v in parsed_sb.items():
                        if k == "widget_order" and isinstance(v, list):
                            cfg_base["sidebar_widget_order"] = v
                        else:
                            cfg_base[f"sidebar_{k}"] = bool(v) if isinstance(v, bool) else v
        except Exception as exc:  # 任何合并异常不影响核心配置返回
            logger.warning("merge settings_groups into /config failed: %s", exc)
        return cfg_base
    cache_key = make_cache_key("site_config")
    cached = await cache.get(cache_key)
    if cached:
        return SiteConfigResponse(**cached)

    # 单次查询获取所有配置
    result = await db.execute(select(SiteConfig))
    rows = result.scalars().all()
    configs: dict[str, str] = {c.key: c.value for c in rows}

    # 尝试读取 settings_groups 中保存的 sidebar 分组（JSON 格式）
    sidebar = dict(default_sidebar)
    raw_sidebar_json = configs.get("sidebar")
    if raw_sidebar_json:
        try:
            import json as _json

            parsed_sb = _json.loads(raw_sidebar_json)
            if isinstance(parsed_sb, dict):
                for k, v in parsed_sb.items():
                    if k in default_sidebar:
                        sidebar[k] = v
        except Exception:
            pass

    # 从 basic 分组 JSON 中读取 about_content
    about_content = configs.get("ABOUT_CONTENT", "")
    if not about_content:
        raw_basic_json = configs.get("basic")
        if raw_basic_json:
            try:
                import json as _json

                parsed_basic = _json.loads(raw_basic_json)
                if isinstance(parsed_basic, dict):
                    about_content = parsed_basic.get("about_content", "")
            except Exception:
                pass

    def get_bool(key: str, default: str = "true") -> bool:
        return configs.get(key, default).lower() == "true"

    def get_int(key: str, default: str = "0") -> int:
        return int(configs.get(key, default))

    def get_str(key: str, default: str = "") -> str | None:
        return configs.get(key, default) or None

    response_dict: dict[str, Any] = dict(
        # 基础信息
        site_name=get_str("SITE_NAME", "Rosetta Blog") or "Rosetta Blog",
        site_description=get_str(
            "SITE_DESCRIPTION",
            "Rosetta开源博客系统",
        )
        or "Rosetta开源博客系统",
        site_keywords=get_str("SITE_KEYWORDS", "Rosetta, FastAPI, Astro, Svelte, Blog") or "",
        site_author=get_str("SITE_AUTHOR", "Rosetta Team") or "Rosetta Team",
        site_email=get_str("SITE_EMAIL", "contact@rosetta.dev") or "",
        site_logo=get_str("SITE_LOGO"),
        site_favicon=get_str("SITE_FAVICON"),
        site_icon=get_str("SITE_ICON"),
        # 页脚设置
        footer_text=get_str("FOOTER_TEXT", "Powered by Rosetta"),
        footer_slogan=get_str("FOOTER_SLOGAN", "Share knowledge, inspire creativity"),
        copyright_text=get_str("COPYRIGHT_TEXT"),
        icp_number=get_str("ICP_NUMBER"),
        police_icp_number=get_str("POLICE_ICP_NUMBER"),
        # 社交媒体链接
        github_url=get_str("GITHUB_URL"),
        x_url=get_str("X_URL"),
        bilibili_url=get_str("BILIBILI_URL"),
        weibo_url=get_str("WEIBO_URL"),
        zhihu_url=get_str("ZHIHU_URL"),
        youtube_url=get_str("YOUTUBE_URL"),
        linkedin_url=get_str("LINKEDIN_URL"),
        telegram_url=get_str("TELEGRAM_URL"),
        # 联系方式
        contact_email=get_str("CONTACT_EMAIL"),
        contact_qq=get_str("CONTACT_QQ"),
        contact_wechat=get_str("CONTACT_WECHAT"),
        # 功能开关
        enable_comments=get_bool("ENABLE_COMMENTS", "true"),
        enable_registration=get_bool("ENABLE_REGISTRATION", "true"),
        enable_rss_feed=get_bool("ENABLE_RSS_FEED", "true"),
        enable_search=get_bool("ENABLE_SEARCH", "true"),
        enable_sitemap=get_bool("ENABLE_SITEMAP", "true"),
        enable_guestbook=get_bool("ENABLE_GUESTBOOK", "true"),
        enable_dark_mode=get_bool("ENABLE_DARK_MODE", "true"),
        enable_reading_time=get_bool("ENABLE_READING_TIME", "true"),
        enable_word_count=get_bool("ENABLE_WORD_COUNT", "true"),
        enable_like_button=get_bool("ENABLE_LIKE_BUTTON", "true"),
        enable_share_buttons=get_bool("ENABLE_SHARE_BUTTONS", "true"),
        enable_toc=get_bool("ENABLE_TOC", "true"),
        # 分页设置
        pagination_page_size=get_int("PAGINATION_PAGE_SIZE", "12"),
        pagination_max_page_size=get_int("PAGINATION_MAX_PAGE_SIZE", "100"),
        # 外观设置
        code_theme=get_str("CODE_THEME", "github") or "github",
        code_theme_dark=get_str("CODE_THEME_DARK", "github-dark") or "github-dark",
        default_theme=get_str("DEFAULT_THEME", "system") or "system",
        primary_color=get_str("PRIMARY_COLOR", "#3B82F6") or "#3B82F6",
        accent_color=get_str("ACCENT_COLOR", "#0284C7") or "#0284C7",
        theme_primary=get_str("THEME_PRIMARY", "#0EA5A9") or "#0EA5A9",
        theme_accent=get_str("THEME_ACCENT", "#0284C7") or "#0284C7",
        font_family=get_str("FONT_FAMILY"),
        default_og_image=get_str("DEFAULT_OG_IMAGE"),
        site_subtitle=get_str("SITE_SUBTITLE", "") or "",
        # 维护模式
        maintenance_mode=get_bool("MAINTENANCE_MODE", "false"),
        maintenance_message=get_str("MAINTENANCE_MESSAGE", "Site is under maintenance"),
        maintenance_end_time=get_str("MAINTENANCE_END_TIME"),
        # 默认图片
        default_post_cover=get_str("DEFAULT_POST_COVER"),
        default_avatar=get_str("DEFAULT_AVATAR"),
        default_category_cover=get_str("DEFAULT_CATEGORY_COVER"),
        # SEO 设置
        google_analytics_id=get_str("GOOGLE_ANALYTICS_ID"),
        baidu_analytics_id=get_str("BAIDU_ANALYTICS_ID"),
        google_site_verification=get_str("GOOGLE_SITE_VERIFICATION"),
        baidu_site_verification=get_str("BAIDU_SITE_VERIFICATION"),
        robots_txt=get_str("ROBOTS_TXT"),
        # 安全设置
        require_email_verification=get_bool("REQUIRE_EMAIL_VERIFICATION", "false"),
        allow_password_reset=get_bool("ALLOW_PASSWORD_RESET", "true"),
        session_timeout=get_int("SESSION_TIMEOUT", "3600"),
        max_login_attempts=get_int("MAX_LOGIN_ATTEMPTS", "5"),
        login_lockout_duration=get_int("LOGIN_LOCKOUT_DURATION", "1800"),
        # 邮件设置
        email_configured=get_bool("EMAIL_CONFIGURED", "false"),
        email_from=get_str("EMAIL_FROM"),
        email_from_name=get_str("EMAIL_FROM_NAME"),
        # 文件上传设置
        max_upload_size=get_int("MAX_UPLOAD_SIZE", "10485760"),
        allowed_image_types=get_str("ALLOWED_IMAGE_TYPES", "jpg,jpeg,png,gif,webp,svg")
        or "jpg,jpeg,png,gif,webp,svg",
        allowed_file_types=get_str("ALLOWED_FILE_TYPES", "pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar")
        or "pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar",
        # 评论设置
        comment_require_approval=get_bool("COMMENT_REQUIRE_APPROVAL", "false"),
        comment_allow_guest=get_bool("COMMENT_ALLOW_GUEST", "false"),
        comment_max_length=get_int("COMMENT_MAX_LENGTH", "1000"),
        comment_antispam=get_bool("COMMENT_ANTISPAM", "true"),
        # 自定义代码
        custom_header_code=get_str("CUSTOM_HEADER_CODE"),
        custom_footer_code=get_str("CUSTOM_FOOTER_CODE"),
        custom_css=get_str("CUSTOM_CSS"),
        custom_js=get_str("CUSTOM_JS"),
        # 音乐播放器设置
        music_enabled=get_bool("MUSIC_ENABLED", "true"),
        music_show_in_navbar=get_bool("MUSIC_SHOW_IN_NAVBAR", "true"),
        music_show_in_sidebar=get_bool("MUSIC_SHOW_IN_SIDEBAR", "true"),
        music_mode=get_str("MUSIC_MODE", "meting") or "meting",
        music_volume=float(configs.get("MUSIC_VOLUME", "0.7")),
        music_play_mode=get_str("MUSIC_PLAY_MODE", "list") or "list",
        music_show_lyrics=get_bool("MUSIC_SHOW_LYRICS", "true"),
        music_meting_api=get_str(
            "MUSIC_METING_API",
            "",
        )
        or "",
        music_meting_server=get_str("MUSIC_METING_SERVER", "netease") or "netease",
        music_meting_type=get_str("MUSIC_METING_TYPE", "playlist") or "playlist",
        music_meting_id=get_str("MUSIC_METING_ID", "") or "",
        # 壁纸/Banner设置
        wallpaper_mode=get_str("WALLPAPER_MODE", "banner") or "banner",
        wallpaper_player_enable=get_bool("WALLPAPER_PLAYER_ENABLE", "true"),
        wallpaper_desktop=get_str("WALLPAPER_DESKTOP", "") or "",
        wallpaper_mobile=get_str("WALLPAPER_MOBILE", "") or "",
        wallpaper_video=get_str("WALLPAPER_VIDEO", "") or "",
        wallpaper_use_bing=get_bool("WALLPAPER_USE_BING", "true"),
        wallpaper_bing_days=get_int("WALLPAPER_BING_DAYS", "30"),
        wallpaper_dim_opacity=float(configs.get("WALLPAPER_DIM_OPACITY", "0.2")),
        wallpaper_home_title=get_str("WALLPAPER_HOME_TITLE", "Welcome") or "Welcome",
        wallpaper_home_subtitle=get_str("WALLPAPER_HOME_SUBTITLE", "") or "",
        # 关于页面内容
        about_content=about_content or "",
        # 友链申请区域自定义 HTML 内容
        friends_apply_html=get_str("FRIENDS_APPLY_HTML", "") or "",
        # 作者/侧边栏资料设置
        author_name=get_str("AUTHOR_NAME", "") or "",
        author_bio=get_str("AUTHOR_BIO", "") or "",
        author_avatar=get_str("AUTHOR_AVATAR", "") or "",
        author_links_json=get_str("AUTHOR_LINKS_JSON", "[]") or "[]",
        # ===== 新增字段 =====
        site_url=get_str("SITE_URL", "") or "",
        site_start_date=get_str("SITE_START_DATE", "2025-01-01") or "2025-01-01",
        footer_custom_html=get_str("FOOTER_CUSTOM_HTML", "") or "",
        friends_page_title=get_str("FRIENDS_PAGE_TITLE", "") or "",
        friends_page_description=get_str("FRIENDS_PAGE_DESCRIPTION", "") or "",
        friends_page_show_comment=get_bool("FRIENDS_PAGE_SHOW_COMMENT", "true"),
        friends_page_show_custom_content=get_bool("FRIENDS_PAGE_SHOW_CUSTOM_CONTENT", "true"),
        dynamic_page_title=get_str("DYNAMIC_PAGE_TITLE", "") or "",
        dynamic_page_description=get_str("DYNAMIC_PAGE_DESCRIPTION", "") or "",
        dynamic_page_items_per_page=get_int("DYNAMIC_PAGE_ITEMS_PER_PAGE", "10"),
        dynamic_page_show_comment=get_bool("DYNAMIC_PAGE_SHOW_COMMENT", "true"),
        sponsor_page_title=get_str("SPONSOR_PAGE_TITLE", "") or "",
        sponsor_page_description=get_str("SPONSOR_PAGE_DESCRIPTION", "") or "",
        sponsor_page_usage=get_str("SPONSOR_PAGE_USAGE", "") or "",
        sponsor_methods_json=get_str("SPONSOR_METHODS_JSON", "[]") or "[]",
        sponsor_show_sponsors_list=get_bool("SPONSOR_SHOW_SPONSORS_LIST", "true"),
        sponsor_page_show_comment=get_bool("SPONSOR_PAGE_SHOW_COMMENT", "true"),
        # ========== 页面开关配置 ==========
        page_friends_enabled=get_bool("PAGE_FRIENDS_ENABLED", "true"),
        page_sponsor_enabled=get_bool("PAGE_SPONSOR_ENABLED", "true"),
        page_guestbook_enabled=get_bool("PAGE_GUESTBOOK_ENABLED", "true"),
        page_bangumi_enabled=get_bool("PAGE_BANGUMI_ENABLED", "true"),
        page_gallery_enabled=get_bool("PAGE_GALLERY_ENABLED", "true"),
        page_anime_enabled=get_bool("PAGE_ANIME_ENABLED", "true"),
        page_dynamic_enabled=get_bool("PAGE_DYNAMIC_ENABLED", "true"),
        # ========== 导航栏显示配置 ==========
        category_bar_enabled=get_bool("CATEGORY_BAR_ENABLED", "true"),
        # ========== 归档页配置 ==========
        archive_fold_old_articles=get_bool("ARCHIVE_FOLD_OLD_ARTICLES", "true"),
        # ========== 文章列表布局配置 ==========
        post_list_default_mode=get_str("POST_LIST_DEFAULT_MODE", "list") or "list",
        post_list_mobile_mode=get_str("POST_LIST_MOBILE_MODE", "grid") or "grid",
        post_list_description_lines=get_int("POST_LIST_DESCRIPTION_LINES", "2"),
        post_list_show_stats_icons=get_bool("POST_LIST_SHOW_STATS_ICONS", "true"),
        post_list_tags_position=get_str("POST_LIST_TAGS_POSITION", "bottom") or "bottom",
        # ========== 文章详情页配置 ==========
        post_show_last_modified=get_bool("POST_SHOW_LAST_MODIFIED", "true"),
        post_outdated_threshold_days=get_int("POST_OUTDATED_THRESHOLD_DAYS", "30"),
        post_enable_share_poster=get_bool("POST_ENABLE_SHARE_POSTER", "true"),
        post_generate_og_images=get_bool("POST_GENERATE_OG_IMAGES", "false"),
        # ========== 封面图配置 ==========
        cover_enable_in_post=get_bool("COVER_ENABLE_IN_POST", "true"),
        cover_enable_overlay=get_bool("COVER_ENABLE_OVERLAY", "true"),
        cover_show_loading=get_bool("COVER_SHOW_LOADING", "false"),
        cover_random_enable=get_bool("COVER_RANDOM_ENABLE", "false"),
        cover_random_apis_json=get_str("COVER_RANDOM_APIS_JSON", "[]") or "[]",
        # ========== 许可证配置 ==========
        license_enable=get_bool("LICENSE_ENABLE", "true"),
        license_name=get_str("LICENSE_NAME", "CC BY-NC-SA 4.0") or "CC BY-NC-SA 4.0",
        license_url=get_str("LICENSE_URL", "https://creativecommons.org/licenses/by-nc-sa/4.0/") or "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        license_icon=get_str("LICENSE_ICON", "") or "",
        # ========== 评论系统配置 ==========
        comment_system_type=get_str("COMMENT_SYSTEM_TYPE", "none") or "none",
        comment_twikoo_env_id=get_str("COMMENT_TWIKOO_ENV_ID", "") or "",
        comment_twikoo_lang=get_str("COMMENT_TWIKOO_LANG", "zh-CN") or "zh-CN",
        comment_twikoo_visitor_count=get_bool("COMMENT_TWIKOO_VISITOR_COUNT", "true"),
        comment_twikoo_js_url=get_str("COMMENT_TWIKOO_JS_URL", "https://cdn.jsdelivr.net/npm/twikoo@1.7.14/dist/twikoo.min.js") or "https://cdn.jsdelivr.net/npm/twikoo@1.7.14/dist/twikoo.min.js",
        comment_twikoo_css_url=get_str("COMMENT_TWIKOO_CSS_URL", "") or "",
        comment_waline_server_url=get_str("COMMENT_WALINE_SERVER_URL", "") or "",
        comment_waline_lang=get_str("COMMENT_WALINE_LANG", "zh-CN") or "zh-CN",
        comment_waline_emoji_json=get_str("COMMENT_WALINE_EMOJI_JSON", '["https://unpkg.com/@waline/emojis@1.4.0/weibo","https://unpkg.com/@waline/emojis@1.4.0/bilibili"]') or '["https://unpkg.com/@waline/emojis@1.4.0/weibo","https://unpkg.com/@waline/emojis@1.4.0/bilibili"]',
        comment_waline_login_mode=get_str("COMMENT_WALINE_LOGIN_MODE", "enable") or "enable",
        comment_waline_visitor_count=get_bool("COMMENT_WALINE_VISITOR_COUNT", "true"),
        comment_artalk_server=get_str("COMMENT_ARTALK_SERVER", "") or "",
        comment_artalk_locale=get_str("COMMENT_ARTALK_LOCALE", "zh-CN") or "zh-CN",
        comment_artalk_visitor_count=get_bool("COMMENT_ARTALK_VISITOR_COUNT", "true"),
        comment_giscus_repo=get_str("COMMENT_GISCUS_REPO", "") or "",
        comment_giscus_repo_id=get_str("COMMENT_GISCUS_REPO_ID", "") or "",
        comment_giscus_category=get_str("COMMENT_GISCUS_CATEGORY", "General") or "General",
        comment_giscus_category_id=get_str("COMMENT_GISCUS_CATEGORY_ID", "") or "",
        comment_giscus_mapping=get_str("COMMENT_GISCUS_MAPPING", "title") or "title",
        comment_giscus_strict=get_str("COMMENT_GISCUS_STRICT", "0") or "0",
        comment_giscus_reactions_enabled=get_str("COMMENT_GISCUS_REACTIONS_ENABLED", "1") or "1",
        comment_giscus_emit_metadata=get_str("COMMENT_GISCUS_EMIT_METADATA", "1") or "1",
        comment_giscus_input_position=get_str("COMMENT_GISCUS_INPUT_POSITION", "top") or "top",
        comment_giscus_lang=get_str("COMMENT_GISCUS_LANG", "zh-CN") or "zh-CN",
        comment_giscus_loading=get_str("COMMENT_GISCUS_LOADING", "lazy") or "lazy",
        comment_disqus_shortname=get_str("COMMENT_DISQUS_SHORTNAME", "") or "",
        # ========== Bangumi配置 ==========
        bangumi_user_id=get_str("BANGUMI_USER_ID", "") or "",
        bangumi_mode=get_str("BANGUMI_MODE", "dynamic") or "dynamic",
        bangumi_api_url=get_str("BANGUMI_API_URL", "https://bgmapi.anibt.net") or "https://bgmapi.anibt.net",
        bangumi_subject_base_url=get_str("BANGUMI_SUBJECT_BASE_URL", "https://bgmmi.anibt.net/subject/") or "https://bgmmi.anibt.net/subject/",
        bangumi_category_order_json=get_str("BANGUMI_CATEGORY_ORDER_JSON", '["anime","book","music","game"]') or '["anime","book","music","game"]',
        # ========== 追番配置 ==========
        anime_bilibili_uid=get_str("ANIME_BILIBILI_UID", "") or "",
        anime_tmdb_api_key=get_str("ANIME_TMDB_API_KEY", "") or "",
        anime_tmdb_list_id=get_str("ANIME_TMDB_LIST_ID", "") or "",
        # ========== 分页配置 ==========
        pagination_posts_per_page=get_int("PAGINATION_POSTS_PER_PAGE", "10"),
        # ========== 图像优化配置 ==========
        image_opt_formats=get_str("IMAGE_OPT_FORMATS", "webp") or "webp",
        image_opt_quality=get_int("IMAGE_OPT_QUALITY", "85"),
        image_opt_no_referrer_json=get_str("IMAGE_OPT_NO_REFERRER_JSON", '["*.hdslb.com","*.bilibili.com"]') or '["*.hdslb.com","*.bilibili.com"]',
        # ========== 樱花特效配置 ==========
        sakura_enable=get_bool("SAKURA_ENABLE", "false"),
        sakura_count=get_int("SAKURA_COUNT", "21"),
        sakura_min_scale=float(configs.get("SAKURA_MIN_SCALE", "0.5")),
        sakura_max_scale=float(configs.get("SAKURA_MAX_SCALE", "1.1")),
        sakura_min_opacity=float(configs.get("SAKURA_MIN_OPACITY", "0.3")),
        sakura_max_opacity=float(configs.get("SAKURA_MAX_OPACITY", "0.9")),
        sakura_z_index=get_int("SAKURA_Z_INDEX", "100"),
        # ========== 看板娘/Spine模型配置 ==========
        pio_spine_enable=get_bool("PIO_SPINE_ENABLE", "false"),
        pio_spine_model_path=get_str("PIO_SPINE_MODEL_PATH", "") or "",
        pio_spine_scale=float(configs.get("PIO_SPINE_SCALE", "1.0")),
        pio_spine_position_corner=get_str("PIO_SPINE_POSITION_CORNER", "bottom-left") or "bottom-left",
        pio_spine_width=get_int("PIO_SPINE_WIDTH", "135"),
        pio_spine_height=get_int("PIO_SPINE_HEIGHT", "165"),
        pio_spine_z_index=get_int("PIO_SPINE_Z_INDEX", "1000"),
        # ========== Mermaid图表配置 ==========
        mermaid_theme=get_str("MERMAID_THEME", "default") or "default",
        mermaid_security_level=get_str("MERMAID_SECURITY_LEVEL", "strict") or "strict",
        # ========== PlantUML配置 ==========
        plantuml_server_url=get_str("PLANTUML_SERVER_URL", "https://www.plantuml.com/plantuml") or "https://www.plantuml.com/plantuml",
    )
    response_dict.update(_sidebar_dict_to_flat(sidebar))
    # 把后台 17 组 settings 合并进 /api/config 公开返回
    response_dict = _apply_settings_groups(response_dict)
    response = SiteConfigResponse(**response_dict)

    # 异步设置缓存（不阻塞响应）
    await cache.set(cache_key, response.model_dump(mode="json"), CACHE_TTL["site_config"])
    return response


@router.get(
    "/config/full",
    response_model=SiteConfigFullResponse,
    summary="完整站点配置（管理员）",
    description="获取完整的站点配置，包含分组信息，需要管理员权限。",
)
async def get_site_config_full(current_user: CurrentStaff, db: DB):
    """获取完整站点配置（带分组）"""
    result = await db.execute(select(SiteConfig))
    configs = {c.key: c.value for c in result.scalars().all()}

    def get_val(key: str, default: str = "") -> str:
        return configs.get(key, default)

    def get_bool_val(key: str, default: str = "false") -> bool:
        return get_val(key, default).lower() == "true"

    def get_int_val(key: str, default: str = "0") -> int:
        return int(get_val(key, default))

    groups = [
        SiteSettingGroup(
            name="basic",
            label="基础设置",
            description="网站基本信息配置",
            icon="settings",
            settings=[
                SiteSettingItem(
                    key="SITE_NAME",
                    label="网站名称",
                    description="显示在浏览器标题栏和页面顶部",
                    type="text",
                    value=get_val("SITE_NAME", "Rosetta Blog"),
                    default="Rosetta Blog",
                    required=True,
                    placeholder="请输入网站名称",
                ),
                SiteSettingItem(
                    key="SITE_DESCRIPTION",
                    label="网站描述",
                    description="用于 SEO 和社交媒体分享",
                    type="textarea",
                    value=get_val("SITE_DESCRIPTION"),
                    default="Rosetta开源博客系统",
                    placeholder="请输入网站描述",
                ),
                SiteSettingItem(
                    key="SITE_KEYWORDS",
                    label="网站关键词",
                    description="用于 SEO，用逗号分隔",
                    type="text",
                    value=get_val("SITE_KEYWORDS"),
                    default="Rosetta, FastAPI, Astro, Svelte, Blog",
                    placeholder="关键词1, 关键词2, 关键词3",
                ),
                SiteSettingItem(
                    key="SITE_AUTHOR",
                    label="网站作者",
                    type="text",
                    value=get_val("SITE_AUTHOR"),
                    default="Rosetta Team",
                ),
                SiteSettingItem(
                    key="SITE_EMAIL",
                    label="网站邮箱",
                    type="email",
                    value=get_val("SITE_EMAIL"),
                    default="contact@rosetta.dev",
                ),
                SiteSettingItem(
                    key="SITE_LOGO",
                    label="网站 Logo",
                    description="网站 Logo 图片 URL",
                    type="image",
                    value=get_val("SITE_LOGO"),
                ),
                SiteSettingItem(
                    key="SITE_FAVICON",
                    label="网站图标",
                    description="浏览器标签页图标",
                    type="image",
                    value=get_val("SITE_FAVICON"),
                ),
                SiteSettingItem(
                    key="AUTHOR_AVATAR",
                    label="作者头像",
                    description="侧边栏资料卡片显示的头像。可上传图片或填写 URL，留空显示占位图。",
                    type="image",
                    value=get_val("AUTHOR_AVATAR"),
                    default="",
                ),
                SiteSettingItem(
                    key="AUTHOR_NAME",
                    label="作者名称",
                    description="侧边栏资料卡片显示的名字，留空使用一键 OOBE 的管理员昵称。",
                    type="text",
                    value=get_val("AUTHOR_NAME", "Choyeon"),
                    default="Choyeon",
                    placeholder="Choyeon",
                ),
                SiteSettingItem(
                    key="AUTHOR_BIO",
                    label="作者简介 / 签名",
                    description="侧边栏资料卡片上显示的一句个性签名或简介。",
                    type="textarea",
                    value=get_val("AUTHOR_BIO", "Full-Stack Development"),
                    default="Full-Stack Development",
                    rows=2,
                ),
                SiteSettingItem(
                    key="AUTHOR_LINKS_JSON",
                    label="作者社交链接（JSON）",
                    description="JSON 数组格式，每项包含 name / icon / url / showName 字段。留空使用 profileConfig 默认。",
                    type="json",
                    value=get_val("AUTHOR_LINKS_JSON", "[]"),
                    default="[]",
                    rows=5,
                    placeholder='[{"name":"GitHub","icon":"fa7-brands:github","url":"https://github.com/","showName":false}]',
                ),
            ],
        ),
        SiteSettingGroup(
            name="footer",
            label="页脚设置",
            icon="layout",
            settings=[
                SiteSettingItem(
                    key="FOOTER_TEXT",
                    label="页脚文字",
                    type="text",
                    value=get_val("FOOTER_TEXT"),
                    default="Powered by Rosetta",
                ),
                SiteSettingItem(
                    key="FOOTER_SLOGAN",
                    label="页脚标语",
                    type="text",
                    value=get_val("FOOTER_SLOGAN"),
                ),
                SiteSettingItem(
                    key="COPYRIGHT_TEXT",
                    label="版权信息",
                    type="text",
                    value=get_val("COPYRIGHT_TEXT"),
                    placeholder="© 2024 Your Name. All rights reserved.",
                ),
                SiteSettingItem(
                    key="ICP_NUMBER",
                    label="ICP 备案号",
                    description="网站 ICP 备案号",
                    type="text",
                    value=get_val("ICP_NUMBER"),
                    placeholder="京ICP备XXXXXXXX号",
                ),
                SiteSettingItem(
                    key="POLICE_ICP_NUMBER",
                    label="公安备案号",
                    type="text",
                    value=get_val("POLICE_ICP_NUMBER"),
                    placeholder="京公网安备 XXXXXXXXXXX号",
                ),
            ],
        ),
        SiteSettingGroup(
            name="social",
            label="社交媒体",
            icon="share-2",
            settings=[
                SiteSettingItem(
                    key="GITHUB_URL",
                    label="GitHub",
                    type="url",
                    value=get_val("GITHUB_URL"),
                    placeholder="https://github.com/yourusername",
                ),
                SiteSettingItem(
                    key="X_URL",
                    label="X (Twitter)",
                    type="url",
                    value=get_val("X_URL"),
                    placeholder="https://x.com/yourusername",
                ),
                SiteSettingItem(
                    key="BILIBILI_URL",
                    label="哔哩哔哩",
                    type="url",
                    value=get_val("BILIBILI_URL"),
                    placeholder="https://space.bilibili.com/xxxxx",
                ),
                SiteSettingItem(
                    key="WEIBO_URL",
                    label="微博",
                    type="url",
                    value=get_val("WEIBO_URL"),
                ),
                SiteSettingItem(
                    key="ZHIHU_URL",
                    label="知乎",
                    type="url",
                    value=get_val("ZHIHU_URL"),
                ),
                SiteSettingItem(
                    key="YOUTUBE_URL",
                    label="YouTube",
                    type="url",
                    value=get_val("YOUTUBE_URL"),
                ),
                SiteSettingItem(
                    key="LINKEDIN_URL",
                    label="LinkedIn",
                    type="url",
                    value=get_val("LINKEDIN_URL"),
                ),
                SiteSettingItem(
                    key="TELEGRAM_URL",
                    label="Telegram",
                    type="url",
                    value=get_val("TELEGRAM_URL"),
                ),
            ],
        ),
        SiteSettingGroup(
            name="features",
            label="功能开关",
            icon="toggle-left",
            settings=[
                SiteSettingItem(
                    key="ENABLE_COMMENTS",
                    label="启用评论",
                    type="switch",
                    value=get_bool_val("ENABLE_COMMENTS", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_REGISTRATION",
                    label="启用注册",
                    type="switch",
                    value=get_bool_val("ENABLE_REGISTRATION", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_RSS_FEED",
                    label="启用 RSS 订阅",
                    type="switch",
                    value=get_bool_val("ENABLE_RSS_FEED", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_SEARCH",
                    label="启用搜索",
                    type="switch",
                    value=get_bool_val("ENABLE_SEARCH", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_SITEMAP",
                    label="启用站点地图",
                    type="switch",
                    value=get_bool_val("ENABLE_SITEMAP", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_GUESTBOOK",
                    label="启用留言板",
                    type="switch",
                    value=get_bool_val("ENABLE_GUESTBOOK", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_DARK_MODE",
                    label="启用暗黑模式",
                    type="switch",
                    value=get_bool_val("ENABLE_DARK_MODE", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_READING_TIME",
                    label="显示阅读时间",
                    type="switch",
                    value=get_bool_val("ENABLE_READING_TIME", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_WORD_COUNT",
                    label="显示字数统计",
                    type="switch",
                    value=get_bool_val("ENABLE_WORD_COUNT", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_LIKE_BUTTON",
                    label="启用点赞按钮",
                    type="switch",
                    value=get_bool_val("ENABLE_LIKE_BUTTON", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_SHARE_BUTTONS",
                    label="启用分享按钮",
                    type="switch",
                    value=get_bool_val("ENABLE_SHARE_BUTTONS", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="ENABLE_TOC",
                    label="启用文章目录",
                    type="switch",
                    value=get_bool_val("ENABLE_TOC", "true"),
                    default=True,
                ),
            ],
        ),
        SiteSettingGroup(
            name="appearance",
            label="外观设置",
            icon="palette",
            settings=[
                SiteSettingItem(
                    key="CODE_THEME",
                    label="代码高亮主题（亮色）",
                    type="select",
                    value=get_val("CODE_THEME", "github"),
                    default="github",
                    options=[
                        {"value": "github", "label": "GitHub"},
                        {"value": "monokai", "label": "Monokai"},
                        {"value": "one-dark", "label": "One Dark"},
                        {"value": "dracula", "label": "Dracula"},
                        {"value": "nord", "label": "Nord"},
                    ],
                ),
                SiteSettingItem(
                    key="CODE_THEME_DARK",
                    label="代码高亮主题（暗色）",
                    type="select",
                    value=get_val("CODE_THEME_DARK", "github-dark"),
                    default="github-dark",
                    options=[
                        {"value": "github-dark", "label": "GitHub Dark"},
                        {"value": "monokai", "label": "Monokai"},
                        {"value": "one-dark", "label": "One Dark"},
                        {"value": "dracula", "label": "Dracula"},
                        {"value": "nord", "label": "Nord"},
                    ],
                ),
                SiteSettingItem(
                    key="DEFAULT_THEME",
                    label="默认主题",
                    type="select",
                    value=get_val("DEFAULT_THEME", "system"),
                    default="system",
                    options=[
                        {"value": "system", "label": "跟随系统"},
                        {"value": "light", "label": "亮色"},
                        {"value": "dark", "label": "暗色"},
                    ],
                ),
                SiteSettingItem(
                    key="PRIMARY_COLOR",
                    label="主题色",
                    type="color",
                    value=get_val("PRIMARY_COLOR", "#3B82F6"),
                    default="#3B82F6",
                ),
                SiteSettingItem(
                    key="FONT_FAMILY",
                    label="字体",
                    type="text",
                    value=get_val("FONT_FAMILY"),
                    placeholder="如: 'Noto Sans SC', sans-serif",
                ),
            ],
        ),
        SiteSettingGroup(
            name="seo",
            label="SEO 设置",
            icon="search",
            settings=[
                SiteSettingItem(
                    key="GOOGLE_ANALYTICS_ID",
                    label="Google Analytics ID",
                    type="text",
                    value=get_val("GOOGLE_ANALYTICS_ID"),
                    placeholder="G-XXXXXXXXXX",
                ),
                SiteSettingItem(
                    key="BAIDU_ANALYTICS_ID",
                    label="百度统计 ID",
                    type="text",
                    value=get_val("BAIDU_ANALYTICS_ID"),
                ),
                SiteSettingItem(
                    key="GOOGLE_SITE_VERIFICATION",
                    label="Google 站点验证",
                    type="text",
                    value=get_val("GOOGLE_SITE_VERIFICATION"),
                ),
                SiteSettingItem(
                    key="BAIDU_SITE_VERIFICATION",
                    label="百度站点验证",
                    type="text",
                    value=get_val("BAIDU_SITE_VERIFICATION"),
                ),
                SiteSettingItem(
                    key="ROBOTS_TXT",
                    label="robots.txt 内容",
                    type="textarea",
                    value=get_val("ROBOTS_TXT"),
                    placeholder="User-agent: *\nAllow: /",
                ),
            ],
        ),
        SiteSettingGroup(
            name="security",
            label="安全设置",
            icon="shield",
            settings=[
                SiteSettingItem(
                    key="REQUIRE_EMAIL_VERIFICATION",
                    label="要求邮箱验证",
                    type="switch",
                    value=get_bool_val("REQUIRE_EMAIL_VERIFICATION", "false"),
                    default=False,
                ),
                SiteSettingItem(
                    key="ALLOW_PASSWORD_RESET",
                    label="允许密码重置",
                    type="switch",
                    value=get_bool_val("ALLOW_PASSWORD_RESET", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="SESSION_TIMEOUT",
                    label="会话超时时间（秒）",
                    type="number",
                    value=get_int_val("SESSION_TIMEOUT", "3600"),
                    default=3600,
                    min_value=300,
                    max_value=86400,
                ),
                SiteSettingItem(
                    key="MAX_LOGIN_ATTEMPTS",
                    label="最大登录尝试次数",
                    type="number",
                    value=get_int_val("MAX_LOGIN_ATTEMPTS", "5"),
                    default=5,
                    min_value=1,
                    max_value=20,
                ),
                SiteSettingItem(
                    key="LOGIN_LOCKOUT_DURATION",
                    label="登录锁定时长（秒）",
                    type="number",
                    value=get_int_val("LOGIN_LOCKOUT_DURATION", "1800"),
                    default=1800,
                    min_value=60,
                    max_value=86400,
                ),
            ],
        ),
        SiteSettingGroup(
            name="upload",
            label="上传设置",
            icon="upload",
            settings=[
                SiteSettingItem(
                    key="MAX_UPLOAD_SIZE",
                    label="最大上传大小（字节）",
                    type="number",
                    value=get_int_val("MAX_UPLOAD_SIZE", "10485760"),
                    default=10485760,
                    min_value=1024,
                    max_value=104857600,
                ),
                SiteSettingItem(
                    key="ALLOWED_IMAGE_TYPES",
                    label="允许的图片类型",
                    type="text",
                    value=get_val("ALLOWED_IMAGE_TYPES", "jpg,jpeg,png,gif,webp,svg"),
                    default="jpg,jpeg,png,gif,webp,svg",
                ),
                SiteSettingItem(
                    key="ALLOWED_FILE_TYPES",
                    label="允许的文件类型",
                    type="text",
                    value=get_val("ALLOWED_FILE_TYPES", "pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar"),
                    default="pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar",
                ),
                SiteSettingItem(
                    key="DEFAULT_POST_COVER",
                    label="默认文章封面",
                    type="image",
                    value=get_val("DEFAULT_POST_COVER"),
                ),
                SiteSettingItem(
                    key="DEFAULT_AVATAR",
                    label="默认用户头像",
                    type="image",
                    value=get_val("DEFAULT_AVATAR"),
                ),
            ],
        ),
        SiteSettingGroup(
            name="comment",
            label="评论设置",
            icon="message-square",
            settings=[
                SiteSettingItem(
                    key="COMMENT_REQUIRE_APPROVAL",
                    label="评论需要审核",
                    type="switch",
                    value=get_bool_val("COMMENT_REQUIRE_APPROVAL", "false"),
                    default=False,
                ),
                SiteSettingItem(
                    key="COMMENT_ALLOW_GUEST",
                    label="允许游客评论",
                    type="switch",
                    value=get_bool_val("COMMENT_ALLOW_GUEST", "false"),
                    default=False,
                ),
                SiteSettingItem(
                    key="COMMENT_MAX_LENGTH",
                    label="评论最大长度",
                    type="number",
                    value=get_int_val("COMMENT_MAX_LENGTH", "1000"),
                    default=1000,
                    min_value=100,
                    max_value=10000,
                ),
                SiteSettingItem(
                    key="COMMENT_ANTISPAM",
                    label="启用反垃圾",
                    type="switch",
                    value=get_bool_val("COMMENT_ANTISPAM", "true"),
                    default=True,
                ),
            ],
        ),
        SiteSettingGroup(
            name="maintenance",
            label="维护模式",
            icon="tool",
            settings=[
                SiteSettingItem(
                    key="MAINTENANCE_MODE",
                    label="启用维护模式",
                    type="switch",
                    value=get_bool_val("MAINTENANCE_MODE", "false"),
                    default=False,
                ),
                SiteSettingItem(
                    key="MAINTENANCE_MESSAGE",
                    label="维护提示信息",
                    type="textarea",
                    value=get_val("MAINTENANCE_MESSAGE", "Site is under maintenance"),
                    default="Site is under maintenance",
                ),
                SiteSettingItem(
                    key="MAINTENANCE_END_TIME",
                    label="预计结束时间",
                    type="datetime",
                    value=get_val("MAINTENANCE_END_TIME"),
                ),
            ],
        ),
        SiteSettingGroup(
            name="custom_code",
            label="自定义代码",
            icon="code",
            settings=[
                SiteSettingItem(
                    key="CUSTOM_HEADER_CODE",
                    label="头部代码",
                    description="插入到 <head> 标签内的代码",
                    type="textarea",
                    value=get_val("CUSTOM_HEADER_CODE"),
                ),
                SiteSettingItem(
                    key="CUSTOM_FOOTER_CODE",
                    label="底部代码",
                    description="插入到 </body> 标签前的代码",
                    type="textarea",
                    value=get_val("CUSTOM_FOOTER_CODE"),
                ),
                SiteSettingItem(
                    key="CUSTOM_CSS",
                    label="自定义 CSS",
                    type="textarea",
                    value=get_val("CUSTOM_CSS"),
                ),
                SiteSettingItem(
                    key="CUSTOM_JS",
                    label="自定义 JavaScript",
                    type="textarea",
                    value=get_val("CUSTOM_JS"),
                ),
            ],
        ),
        SiteSettingGroup(
            name="music",
            label="音乐播放器",
            icon="music",
            settings=[
                SiteSettingItem(
                    key="MUSIC_ENABLED",
                    label="启用音乐播放器",
                    type="switch",
                    value=get_bool_val("MUSIC_ENABLED", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="MUSIC_SHOW_IN_NAVBAR",
                    label="在导航栏显示",
                    type="switch",
                    value=get_bool_val("MUSIC_SHOW_IN_NAVBAR", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="MUSIC_SHOW_IN_SIDEBAR",
                    label="在侧边栏显示",
                    type="switch",
                    value=get_bool_val("MUSIC_SHOW_IN_SIDEBAR", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="MUSIC_MODE",
                    label="音乐模式",
                    type="select",
                    value=get_val("MUSIC_MODE", "meting"),
                    default="meting",
                    options=[
                        {"value": "meting", "label": "Meting API"},
                        {"value": "local", "label": "本地音乐"},
                    ],
                ),
                SiteSettingItem(
                    key="MUSIC_VOLUME",
                    label="默认音量",
                    type="number",
                    value=float(get_val("MUSIC_VOLUME", "0.7")),
                    default=0.7,
                    min_value=0,
                    max_value=1,
                ),
                SiteSettingItem(
                    key="MUSIC_PLAY_MODE",
                    label="播放模式",
                    type="select",
                    value=get_val("MUSIC_PLAY_MODE", "list"),
                    default="list",
                    options=[
                        {"value": "list", "label": "列表循环"},
                        {"value": "one", "label": "单曲循环"},
                        {"value": "random", "label": "随机播放"},
                    ],
                ),
                SiteSettingItem(
                    key="MUSIC_SHOW_LYRICS",
                    label="显示歌词",
                    type="switch",
                    value=get_bool_val("MUSIC_SHOW_LYRICS", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="MUSIC_METING_API",
                    label="Meting API 地址",
                    type="text",
                    value=get_val(
                        "MUSIC_METING_API",
                        "https://api.i-meto.com/meting/api?server=:server&type=:type&id=:id&r=:r",
                    ),
                    default="https://api.i-meto.com/meting/api?server=:server&type=:type&id=:id&r=:r",
                ),
                SiteSettingItem(
                    key="MUSIC_METING_SERVER",
                    label="音乐平台",
                    type="select",
                    value=get_val("MUSIC_METING_SERVER", "netease"),
                    default="netease",
                    options=[
                        {"value": "netease", "label": "网易云音乐"},
                        {"value": "tencent", "label": "QQ音乐"},
                        {"value": "kugou", "label": "酷狗音乐"},
                        {"value": "xiami", "label": "虾米音乐"},
                        {"value": "baidu", "label": "百度音乐"},
                    ],
                ),
                SiteSettingItem(
                    key="MUSIC_METING_TYPE",
                    label="类型",
                    type="select",
                    value=get_val("MUSIC_METING_TYPE", "playlist"),
                    default="playlist",
                    options=[
                        {"value": "song", "label": "单曲"},
                        {"value": "playlist", "label": "歌单"},
                        {"value": "album", "label": "专辑"},
                        {"value": "search", "label": "搜索"},
                        {"value": "artist", "label": "艺术家"},
                    ],
                ),
                SiteSettingItem(
                    key="MUSIC_METING_ID",
                    label="歌单/专辑 ID",
                    type="text",
                    value=get_val("MUSIC_METING_ID", ""),
                    default="",
                    placeholder="例如网易云歌单 ID（在后台设置后生效）",
                ),
            ],
        ),
        SiteSettingGroup(
            name="wallpaper",
            label="壁纸/Banner",
            icon="image",
            settings=[
                SiteSettingItem(
                    key="WALLPAPER_MODE",
                    label="壁纸模式",
                    type="select",
                    value=get_val("WALLPAPER_MODE", "banner"),
                    default="banner",
                    options=[
                        {"value": "banner", "label": "横幅壁纸"},
                        {"value": "fullscreen", "label": "全屏壁纸"},
                        {"value": "overlay", "label": "全屏透明"},
                        {"value": "none", "label": "纯色背景"},
                    ],
                ),
                SiteSettingItem(
                    key="WALLPAPER_PLAYER_ENABLE",
                    label="启用背景视频播放",
                    type="switch",
                    value=get_bool_val("WALLPAPER_PLAYER_ENABLE", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="WALLPAPER_USE_BING",
                    label="使用 Bing 每日壁纸",
                    description="开启后当自定义桌面壁纸为空时，默认加载 Bing 每日壁纸",
                    type="switch",
                    value=get_bool_val("WALLPAPER_USE_BING", "true"),
                    default=True,
                ),
                SiteSettingItem(
                    key="WALLPAPER_BING_DAYS",
                    label="Bing 壁纸天数范围",
                    description="从最近多少天内随机选择 Bing 壁纸",
                    type="number",
                    value=get_int_val("WALLPAPER_BING_DAYS", "30"),
                    default=30,
                    min_value=1,
                    max_value=30,
                ),
                SiteSettingItem(
                    key="WALLPAPER_DESKTOP",
                    label="桌面壁纸地址",
                    description="支持单张图片、多张图片（JSON数组）或单张图片 URL。留空并开启 Bing 每日壁纸即可加载必应背景图。",
                    type="textarea",
                    value=get_val("WALLPAPER_DESKTOP", ""),
                    default="",
                    placeholder='["/images/bg1.jpg", "/images/bg2.jpg"]',
                ),
                SiteSettingItem(
                    key="WALLPAPER_MOBILE",
                    label="移动端壁纸地址",
                    description="支持单张图片或多张图片（JSON数组），留空则使用桌面壁纸或 Bing 每日壁纸",
                    type="textarea",
                    value=get_val("WALLPAPER_MOBILE", ""),
                    default="",
                    placeholder='["/images/m_bg1.jpg", "/images/m_bg2.jpg"]',
                ),
                SiteSettingItem(
                    key="WALLPAPER_VIDEO",
                    label="背景视频地址",
                    description="支持单个视频或多个视频（JSON数组）",
                    type="textarea",
                    value=get_val("WALLPAPER_VIDEO", ""),
                    default="",
                    placeholder='["/videos/bg1.mp4", "/videos/bg2.mp4"]',
                ),
                SiteSettingItem(
                    key="WALLPAPER_DIM_OPACITY",
                    label="壁纸遮罩暗度",
                    description="值越大越暗，有助于文字显示，范围 0-1",
                    type="number",
                    value=float(get_val("WALLPAPER_DIM_OPACITY", "0.2")),
                    default=0.2,
                    min_value=0,
                    max_value=1,
                ),
                SiteSettingItem(
                    key="WALLPAPER_HOME_TITLE",
                    label="主页横幅主标题",
                    type="text",
                    value=get_val("WALLPAPER_HOME_TITLE", "Welcome"),
                    default="Welcome",
                ),
                SiteSettingItem(
                    key="WALLPAPER_HOME_SUBTITLE",
                    label="主页横幅副标题",
                    description="多个副标题请用 | 分隔",
                    type="text",
                    value=get_val("WALLPAPER_HOME_SUBTITLE", ""),
                    default="",
                    placeholder="副标题1 | 副标题2 | 副标题3",
                ),
            ],
        ),
    ]

    return SiteConfigFullResponse(groups=groups)


@router.post(
    "/admin/settings",
    response_model=BaseResponse,
    summary="更新站点设置",
    description="更新站点配置，需要管理员权限。",
)
async def update_site_settings(
    data: SiteConfigUpdate,
    current_user: CurrentStaff,
    db: DB,
    background_tasks: BackgroundTasks,
):
    """
    更新站点设置

    性能优化：
    - 批量查询现有配置
    - 使用后台任务处理缓存失效
    - 减少 N+1 查询问题
    """
    config_map = {
        # 基础信息
        "site_name": "SITE_NAME",
        "site_description": "SITE_DESCRIPTION",
        "site_keywords": "SITE_KEYWORDS",
        "site_author": "SITE_AUTHOR",
        "site_email": "SITE_EMAIL",
        "site_logo": "SITE_LOGO",
        "site_favicon": "SITE_FAVICON",
        "site_icon": "SITE_ICON",
        # 页脚设置
        "footer_text": "FOOTER_TEXT",
        "footer_slogan": "FOOTER_SLOGAN",
        "copyright_text": "COPYRIGHT_TEXT",
        "icp_number": "ICP_NUMBER",
        "police_icp_number": "POLICE_ICP_NUMBER",
        # 社交媒体链接
        "github_url": "GITHUB_URL",
        "x_url": "X_URL",
        "bilibili_url": "BILIBILI_URL",
        "weibo_url": "WEIBO_URL",
        "zhihu_url": "ZHIHU_URL",
        "youtube_url": "YOUTUBE_URL",
        "linkedin_url": "LINKEDIN_URL",
        "telegram_url": "TELEGRAM_URL",
        # 联系方式
        "contact_email": "CONTACT_EMAIL",
        "contact_qq": "CONTACT_QQ",
        "contact_wechat": "CONTACT_WECHAT",
        # 功能开关
        "enable_comments": "ENABLE_COMMENTS",
        "enable_registration": "ENABLE_REGISTRATION",
        "enable_rss_feed": "ENABLE_RSS_FEED",
        "enable_search": "ENABLE_SEARCH",
        "enable_sitemap": "ENABLE_SITEMAP",
        "enable_guestbook": "ENABLE_GUESTBOOK",
        "enable_dark_mode": "ENABLE_DARK_MODE",
        "enable_reading_time": "ENABLE_READING_TIME",
        "enable_word_count": "ENABLE_WORD_COUNT",
        "enable_like_button": "ENABLE_LIKE_BUTTON",
        "enable_share_buttons": "ENABLE_SHARE_BUTTONS",
        "enable_toc": "ENABLE_TOC",
        # 分页设置
        "pagination_page_size": "PAGINATION_PAGE_SIZE",
        "pagination_max_page_size": "PAGINATION_MAX_PAGE_SIZE",
        # 外观设置
        "code_theme": "CODE_THEME",
        "code_theme_dark": "CODE_THEME_DARK",
        "default_theme": "DEFAULT_THEME",
        "primary_color": "PRIMARY_COLOR",
        "font_family": "FONT_FAMILY",
        # 维护模式
        "maintenance_mode": "MAINTENANCE_MODE",
        "maintenance_message": "MAINTENANCE_MESSAGE",
        "maintenance_end_time": "MAINTENANCE_END_TIME",
        # 默认图片
        "default_post_cover": "DEFAULT_POST_COVER",
        "default_avatar": "DEFAULT_AVATAR",
        "default_category_cover": "DEFAULT_CATEGORY_COVER",
        # SEO 设置
        "google_analytics_id": "GOOGLE_ANALYTICS_ID",
        "baidu_analytics_id": "BAIDU_ANALYTICS_ID",
        "google_site_verification": "GOOGLE_SITE_VERIFICATION",
        "baidu_site_verification": "BAIDU_SITE_VERIFICATION",
        "robots_txt": "ROBOTS_TXT",
        # 安全设置
        "require_email_verification": "REQUIRE_EMAIL_VERIFICATION",
        "allow_password_reset": "ALLOW_PASSWORD_RESET",
        "session_timeout": "SESSION_TIMEOUT",
        "max_login_attempts": "MAX_LOGIN_ATTEMPTS",
        "login_lockout_duration": "LOGIN_LOCKOUT_DURATION",
        # 文件上传设置
        "max_upload_size": "MAX_UPLOAD_SIZE",
        "allowed_image_types": "ALLOWED_IMAGE_TYPES",
        "allowed_file_types": "ALLOWED_FILE_TYPES",
        # 评论设置
        "comment_require_approval": "COMMENT_REQUIRE_APPROVAL",
        "comment_allow_guest": "COMMENT_ALLOW_GUEST",
        "comment_max_length": "COMMENT_MAX_LENGTH",
        "comment_antispam": "COMMENT_ANTISPAM",
        # 自定义代码
        "custom_header_code": "CUSTOM_HEADER_CODE",
        "custom_footer_code": "CUSTOM_FOOTER_CODE",
        "custom_css": "CUSTOM_CSS",
        "custom_js": "CUSTOM_JS",
        # 音乐播放器设置
        "music_enabled": "MUSIC_ENABLED",
        "music_show_in_navbar": "MUSIC_SHOW_IN_NAVBAR",
        "music_show_in_sidebar": "MUSIC_SHOW_IN_SIDEBAR",
        "music_mode": "MUSIC_MODE",
        "music_volume": "MUSIC_VOLUME",
        "music_play_mode": "MUSIC_PLAY_MODE",
        "music_show_lyrics": "MUSIC_SHOW_LYRICS",
        "music_meting_api": "MUSIC_METING_API",
        "music_meting_server": "MUSIC_METING_SERVER",
        "music_meting_type": "MUSIC_METING_TYPE",
        "music_meting_id": "MUSIC_METING_ID",
        # 壁纸/Banner设置
        "wallpaper_mode": "WALLPAPER_MODE",
        "wallpaper_player_enable": "WALLPAPER_PLAYER_ENABLE",
        "wallpaper_desktop": "WALLPAPER_DESKTOP",
        "wallpaper_mobile": "WALLPAPER_MOBILE",
        "wallpaper_video": "WALLPAPER_VIDEO",
        "wallpaper_use_bing": "WALLPAPER_USE_BING",
        "wallpaper_bing_days": "WALLPAPER_BING_DAYS",
        "wallpaper_dim_opacity": "WALLPAPER_DIM_OPACITY",
        "wallpaper_home_title": "WALLPAPER_HOME_TITLE",
        "wallpaper_home_subtitle": "WALLPAPER_HOME_SUBTITLE",
        # 作者/侧边栏资料设置
        "author_name": "AUTHOR_NAME",
        "author_bio": "AUTHOR_BIO",
        "author_avatar": "AUTHOR_AVATAR",
        "author_links_json": "AUTHOR_LINKS_JSON",
        # 关于页面内容
        "about_content": "ABOUT_CONTENT",
        # 友链申请区域自定义 HTML 内容
        "friends_apply_html": "FRIENDS_APPLY_HTML",
        # ===== 新增字段映射 =====
        "site_url": "SITE_URL",
        "site_start_date": "SITE_START_DATE",
        "footer_custom_html": "FOOTER_CUSTOM_HTML",
        "friends_page_title": "FRIENDS_PAGE_TITLE",
        "friends_page_description": "FRIENDS_PAGE_DESCRIPTION",
        "friends_page_show_comment": "FRIENDS_PAGE_SHOW_COMMENT",
        "friends_page_show_custom_content": "FRIENDS_PAGE_SHOW_CUSTOM_CONTENT",
        "dynamic_page_title": "DYNAMIC_PAGE_TITLE",
        "dynamic_page_description": "DYNAMIC_PAGE_DESCRIPTION",
        "dynamic_page_items_per_page": "DYNAMIC_PAGE_ITEMS_PER_PAGE",
        "dynamic_page_show_comment": "DYNAMIC_PAGE_SHOW_COMMENT",
        "sponsor_page_title": "SPONSOR_PAGE_TITLE",
        "sponsor_page_description": "SPONSOR_PAGE_DESCRIPTION",
        "sponsor_page_usage": "SPONSOR_PAGE_USAGE",
        "sponsor_methods_json": "SPONSOR_METHODS_JSON",
        "sponsor_show_sponsors_list": "SPONSOR_SHOW_SPONSORS_LIST",
        "sponsor_page_show_comment": "SPONSOR_PAGE_SHOW_COMMENT",
    }

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        return BaseResponse(success=True, message="没有需要更新的设置")

    # 获取需要更新的配置键
    config_keys = [config_map.get(field) for field in update_data.keys() if config_map.get(field)]

    if not config_keys:
        return BaseResponse(success=True, message="没有需要更新的设置")

    # 批量查询现有配置（避免 N+1 查询）
    result = await db.execute(select(SiteConfig).where(SiteConfig.key.in_(config_keys)))
    existing_configs = {c.key: c for c in result.scalars().all()}

    # 批量更新或创建配置
    for field, value in update_data.items():
        key = config_map.get(field)
        if not key:
            continue

        str_value = str(value) if not isinstance(value, str) else value

        if key in existing_configs:
            existing_configs[key].value = str_value
        else:
            config = SiteConfig(key=key, value=str_value)
            db.add(config)

    await db.flush()
    await db.commit()

    # 同步删除缓存，确保下次读取时使用新值（测试也能看到变更）
    await cache.delete(make_cache_key("site_config"))

    # 使用后台任务处理缓存预热（不阻塞响应）
    async def warmup_cache_async():
        try:
            from backend.core.cache_warmer import cache_warmer

            await cache_warmer.warmup_task("site_config")
        except Exception:
            pass

    background_tasks.add_task(warmup_cache_async)

    return BaseResponse(success=True, message="设置已保存")
