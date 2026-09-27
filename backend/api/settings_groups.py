"""
17 组系统设置 API（与前端 Tab 1:1 对应）

17 groups: basic, reading, comments, media, seo, email, cdn, cache,
           security, features, appearance, navigation, friendlinks,
           hero, notice, sidebar, footer

- GET /api/settings → 返回 { group_key: {...} } 全部 17 组
- GET /api/settings/{group} → 返回单组 dict
- PATCH /api/settings/{group} → 保存单组（写入 site_configs：每 group 存一条 key=group, value=JSON 字符串）
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Path, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.logging_middleware import log_operation
from backend.models.core import SiteConfig
from backend.utils.compat import utc_now_naive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["系统设置"])


SETTING_GROUPS_17 = [
    "basic",
    "reading",
    "comments",
    "media",
    "seo",
    "email",
    "cdn",
    "cache",
    "security",
    "features",
    "appearance",
    "navigation",
    "friendlinks",
    "hero",
    "notice",
    "sidebar",
    "footer",
]

# ===== 公开可读分组（GET /api/settings/public，无需登录）=====
# 背景：站点前台（首页 / 文章 / 关于 …）需要读取 hero / footer / appearance 等分组来渲染，
# 而这些内容本质上就是要展示给所有访客看的公开素材。若强制要求 admin 身份，
# 未登录访客必然收到 401 —— 既污染浏览器控制台，也让管理员配置的 hero/公告在前台永远不生效。
# 因此这里显式声明「可以安全下发给所有人」的分组名单。
PUBLIC_SETTING_GROUPS = [
    "basic",
    "appearance",
    "hero",
    "footer",
    "seo",
    "notice",
    "sidebar",
    "navigation",
    "friendlinks",
    "reading",
    "features",
]

# 即便在公开分组内，这些键也一律脱敏（避免误配导致凭据外泄）
_SENSITIVE_KEY_RE = re.compile(r"(password|secret|token|api_?key|private_key|authorization)", re.I)


def _redact(data: dict) -> dict:
    """把 dict 中疑似敏感键的值替换为掩码字符串（仅在顶层做一次浅层脱敏即可，
    因为 17 组配置的值都是扁平标量 / 一维数组）。"""
    out: dict[str, Any] = {}
    for k, v in data.items():
        if _SENSITIVE_KEY_RE.search(str(k)) and v not in (None, "", [], {}):
            out[k] = "******"
        else:
            out[k] = v
    return out


def _default_basic() -> dict:
    return {
        "site_name": "Rosetta Blog",
        "subtitle": "Share knowledge, inspire creativity",
        "logo": "",
        "description": "Rosetta 开源博客系统",
        "keywords": "Rosetta, FastAPI, Astro",
        "site_url": "https://example.com",
        "icp_number": "",
        "about_content": "",
    }


def _default_reading() -> dict:
    return {
        "posts_per_page": 12,
        "show_reading_time": True,
        "show_word_count": True,
        "show_toc": True,
        "toc_depth": 3,
        "line_height": 1.7,
        "font_size": 16,
    }


def _default_comments() -> dict:
    return {
        "enable": True,
        "require_approval": False,
        "allow_guest": False,
        "max_length": 1000,
        "enable_antispam": True,
        "enable_nested": True,
        "max_nested_depth": 3,
    }


def _default_media() -> dict:
    return {
        "max_upload_size": 10485760,
        "allowed_image_types": "jpg,jpeg,png,gif,webp,svg",
        "allowed_file_types": "pdf,doc,docx,xls,xlsx,ppt,pptx,zip,rar",
        "default_post_cover": "",
        "default_avatar": "",
        "use_cdn": False,
        "cdn_prefix": "",
    }


def _default_seo() -> dict:
    return {
        "default_title": "",
        "default_description": "",
        "default_keywords": "",
        "og_image": "",
        "twitter_handle": "",
        "google_analytics_id": "",
        "baidu_analytics_id": "",
        "google_verification": "",
        "baidu_verification": "",
        "robots_txt": "User-agent: *\nAllow: /",
    }


def _default_email() -> dict:
    return {
        "smtp_host": "",
        "smtp_port": 465,
        "smtp_user": "",
        "smtp_password": "",
        "use_tls": True,
        "from_address": "",
        "from_name": "Rosetta",
        "enable_notifications": False,
        "admin_email": "",
    }


def _default_cdn() -> dict:
    return {
        "enable": False,
        "provider": "",
        "cdn_url": "",
        "image_cdn_url": "",
        "static_cdn_url": "",
        "purge_token": "",
    }


def _default_cache() -> dict:
    return {
        "enable": True,
        "backend": "memory",
        "default_ttl": 3600,
        "site_config_ttl": 3600,
        "post_list_ttl": 600,
        "flush_on_post_update": True,
    }


def _default_security() -> dict:
    return {
        "require_email_verification": False,
        "allow_password_reset": True,
        "session_timeout_sec": 3600,
        "max_login_attempts": 5,
        "lockout_duration_sec": 1800,
        "enable_rate_limit": True,
        "allowed_hosts": "*",
        "cors_origins": "*",
    }


def _default_features() -> dict:
    return {
        "enable_comments": True,
        "enable_registration": True,
        "enable_rss": True,
        "enable_search": True,
        "enable_sitemap": True,
        "enable_guestbook": True,
        "enable_dark_mode": True,
        "enable_like_button": True,
        "enable_share_buttons": True,
        "enable_reading_progress": True,
    }


def _default_appearance() -> dict:
    return {
        "code_theme": "github",
        "code_theme_dark": "github-dark",
        "default_theme": "system",
        "primary_color": "#0EA5A9",
        "font_family": "",
        "page_width_px": 1200,
        "accent_color": "#8B5CF6",
        "show_copyright": True,
        "show_powered_by": True,
    }


def _default_navigation() -> dict:
    return {
        "header_style": "sticky",
        "show_search": True,
        "show_language_switch": True,
        "show_theme_toggle": True,
        "custom_links": [],
    }


def _default_friendlinks() -> dict:
    return {
        "enable": True,
        "links": [
            {
                "name": "Rosetta",
                "url": "https://github.com/rosetta-blog",
                "desc": "Rosetta 官方仓库",
                "avatar": "",
            }
        ],
        "auto_approve": False,
    }


def _default_hero() -> dict:
    return {
        "enable": True,
        "title": {"zh": "欢迎来到 Rosetta", "en": "Welcome to Rosetta"},
        "subtitle": {"zh": "一个现代化的开源博客平台", "en": "A modern open-source blog platform"},
        "caption": "Powered by FastAPI + Astro + Svelte",
        "cta_text": {"zh": "开始阅读", "en": "Start Reading"},
        "cta_url": "/posts",
        "bg_image": "",
        "bg_gradient": "linear-gradient(135deg, #0EA5A9 0%, #06B6D4 100%)",
    }


def _default_notice() -> dict:
    return {
        "enable": False,
        "type": "info",
        "title": "",
        "content_md": "**提示**：此处可编辑公告正文，支持 Markdown。",
        "dismissible": True,
        "sticky": True,
    }


def _default_sidebar() -> dict:
    return {
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


def _default_footer() -> dict:
    return {
        "text": "Powered by Rosetta",
        "slogan": "Share knowledge, inspire creativity",
        "copyright": "© 2026 Rosetta",
        "icp_number": "",
        "police_icp_number": "",
        "show_social_links": True,
        "show_back_to_top": True,
    }


_GROUP_DEFAULTS = {
    "basic": _default_basic,
    "reading": _default_reading,
    "comments": _default_comments,
    "media": _default_media,
    "seo": _default_seo,
    "email": _default_email,
    "cdn": _default_cdn,
    "cache": _default_cache,
    "security": _default_security,
    "features": _default_features,
    "appearance": _default_appearance,
    "navigation": _default_navigation,
    "friendlinks": _default_friendlinks,
    "hero": _default_hero,
    "notice": _default_notice,
    "sidebar": _default_sidebar,
    "footer": _default_footer,
}


def _default_for(group: str) -> dict:
    return _GROUP_DEFAULTS[group]()


async def _load_all_groups(db: DB) -> dict[str, dict]:
    rows = (await db.execute(select(SiteConfig))).scalars().all()
    db_map: dict[str, dict] = {}
    for r in rows:
        if r.key in SETTING_GROUPS_17:
            try:
                db_map[r.key] = json.loads(r.value) if r.value else {}
            except (json.JSONDecodeError, TypeError) as exc:
                # 单条 KV 损坏不能连带整组：这里退回默认值，但要点名是哪个 key——
                # 否则下一次 PUT 会用默认值静默覆盖整组配置。
                logger.warning(f"[settings] 配置项 {r.key} 的值不是合法 JSON，按默认值处理: {exc}")
                db_map[r.key] = {}

    out: dict[str, dict] = {}
    for g in SETTING_GROUPS_17:
        base = _default_for(g)
        if g in db_map and isinstance(db_map[g], dict):
            merged = {**base, **db_map[g]}
            out[g] = merged
        else:
            out[g] = base
    return out


async def _save_group(db: DB, group: str, data: dict) -> dict:
    base = _default_for(group)
    merged = {**base, **{k: v for k, v in data.items() if k in base}}
    val_json = json.dumps(merged, ensure_ascii=False)
    row = (await db.execute(select(SiteConfig).where(SiteConfig.key == group))).scalar_one_or_none()
    if row is None:
        row = SiteConfig(key=group, value=val_json, description=f"系统设置 - {group}")
        db.add(row)
    else:
        row.value = val_json
        row.updated_at = utc_now_naive()
    await db.flush()
    return merged


class SettingsGroupResponse(BaseModel):
    """``GET /api/settings/{group}`` 直接返回的裸对象（无 success 信封）。"""

    group: str = Field(..., description="分组键（17 组之一）")
    data: dict[str, Any] = Field(..., description="该分组的完整配置（默认值与 DB 存值的合并结果）")


class SettingsPublicResponse(BaseModel):
    """``GET /api/settings/public`` 的响应体（匿名可读）。"""

    groups: dict[str, Any] = Field(
        ...,
        description=(
            "仅 PUBLIC_SETTING_GROUPS 白名单内的分组；"
            '疑似敏感键（password/secret/token/api_key 等）值统一脱敏为 "******"'
        ),
    )


class SettingsAllResponse(BaseModel):
    """``GET /api/settings`` 的响应体（需管理员）。"""

    groups: dict[str, Any] = Field(
        ...,
        description="全部 17 组配置，键为分组名、值为该组合并默认值后的完整 dict（含敏感明文值）",
    )


class SettingsPatchResponse(BaseModel):
    """``PATCH /api/settings/{group}`` 的响应体。"""

    success: bool = Field(..., description="固定为 true；已写操作日志并失效公开设置缓存")
    group: str = Field(..., description="被更新的分组键")
    data: dict[str, Any] = Field(
        ..., description="保存后的最终配置（payload 中不在该组默认值键集内的键已被丢弃）"
    )
    changed: list[str] = Field(default_factory=list, description="与更新前相比发生变化的键名列表")


@router.get(
    "/public",
    summary="公开站设置（无需登录）",
    description=(
        "匿名可读的站点配置子集：只对 PUBLIC_SETTING_GROUPS 白名单分组下发，"
        '白名单内疑似敏感键（password/secret/token/api_key/...）统一脱敏为 "******"。'
        "结果服务端缓存 300s（PATCH 任一分组后立即失效）。只读、幂等。"
    ),
    responses={200: {"model": SettingsPublicResponse}},
)
async def get_public_settings(db: DB):
    """
    匿名可读的站点配置子集。

    - 只对 PUBLIC_SETTING_GROUPS 白名单内的分组下发
    - 白名单内疑似敏感键（password/secret/token/api_key/...）统一脱敏为 "******"
    - 结果缓存 300s（前台每个页面都会读一次，避免每次 SSR 都打 DB）
    """
    cache_key = make_cache_key("settings_public")
    cached = await cache.get(cache_key)
    if cached and isinstance(cached, dict):
        return {"groups": cached}

    all_groups = await _load_all_groups(db)
    public = {g: _redact(all_groups[g]) for g in PUBLIC_SETTING_GROUPS if g in all_groups}
    try:
        await cache.set(cache_key, public, 300)
    except Exception:  # 缓存不可用不影响正常响应
        logger.debug("cache set for public settings failed", exc_info=True)
    return {"groups": public}


@router.get(
    "",
    summary="获取所有设置分组",
    description=(
        "需管理员（CurrentStaff）。返回全部 17 组分组的配置项（含敏感明文值，"
        "如 SMTP 密码）；前台/SSR 一律改用 GET /settings/public，不得调用本接口。只读、幂等。"
    ),
    responses={200: {"model": SettingsAllResponse}},
)
async def get_all_settings(db: DB, current_user: CurrentStaff):
    data = await _load_all_groups(db)
    return {"groups": data}


@router.get(
    "/{group}",
    summary="获取单个设置分组",
    description=(
        "需管理员（CurrentStaff）。返回指定分组（17 组之一）合并默认值后的完整配置；"
        "未知分组 404。直接返回 {group, data} 裸对象（无 success 信封）。只读、幂等。"
    ),
    responses={
        200: {"model": SettingsGroupResponse},
        404: {"description": "未知设置分组"},
    },
)
async def get_one_setting(
    db: DB,
    current_user: CurrentStaff,
    group: str = Path(..., description="设置分组"),
):
    if group not in SETTING_GROUPS_17:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"未知设置分组: {group}")
    all_g = await _load_all_groups(db)
    return SettingsGroupResponse(group=group, data=all_g[group])


@router.patch(
    "/{group}",
    summary="更新单个设置分组",
    description=(
        "需管理员（CurrentStaff）。payload 为该分组的部分键值对象；"
        "不在该组默认值键集内的键被静默丢弃。副作用：写入操作日志（含 before/after diff）、"
        "落库 site_configs 后立刻失效 /settings/public 的 300s 缓存。"
        "未知分组 404；payload 非对象 400。"
    ),
    responses={
        200: {"model": SettingsPatchResponse},
        400: {"description": "payload 必须为 JSON 对象"},
        404: {"description": "未知设置分组"},
    },
)
async def patch_one_setting(
    request: Request,
    db: DB,
    current_user: CurrentStaff,
    group: str = Path(..., description="设置分组"),
    payload: dict[str, Any] = Body(...),
):
    if group not in SETTING_GROUPS_17:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"未知设置分组: {group}")
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "payload 必须为对象")
    all_before = await _load_all_groups(db)
    before = all_before[group]
    saved = await _save_group(db, group, payload)
    diff: dict = {}
    for k in set(list(before.keys()) + list(saved.keys())):
        if before.get(k) != saved.get(k):
            diff[k] = {"before": before.get(k), "after": saved.get(k)}
    await log_operation(
        db,
        request,
        user_id=current_user.id,
        action="settings",
        target_type="settings",
        target_id=None,
        details={"group": group, "diff": diff},
        status="success",
    )
    await db.commit()
    # 前台 ANY 页面都在读 /settings/public（含 300s 缓存），保存后必须立刻失效，
    # 否则管理员保存 hero/footer/公告后前台最长 5 分钟看不到更新。
    try:
        await cache.delete(make_cache_key("settings_public"))
    except Exception:
        logger.debug("cache delete for public settings failed", exc_info=True)
    return {"success": True, "group": group, "data": saved, "changed": list(diff.keys())}
