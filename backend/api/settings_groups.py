"""
14 组系统设置 API（与前端 Tab 1:1 对应）

14 groups: basic, reading, comments, media, seo, email, security, features,
           appearance, navigation, hero, notice, footer, donate

- GET /api/settings → 返回 { group_key: {...} } 全部 14 组
- GET /api/settings/{group} → 返回单组 dict
- PATCH /api/settings/{group} → 保存单组（写入 site_configs：每 group 存一条 key=group, value=JSON 字符串）

历史上这里还有 cdn / cache / friendlinks / sidebar 四组，以及 security 的会话与主机白名单、
appearance 的代码高亮主题与字体族等键。它们没有任何执行点（既不进 read_group，也不进
/api/config 的分组覆写，前端也没有消费方），设置页却能勾选、保存并回显——
"改了没生效"的开关比没有开关更糟，所以整组删除：
CDN 前缀由 media.use_cdn + media.cdn_prefix 决定，缓存后端与 TTL 由环境变量决定，
友情链接由 friend_links 表 + /api/friend-links 决定，
侧边栏显示/位置由主题 Customizer 的 show_sidebar / sidebar_position（mods）决定，
代码高亮配色由 assets/css/main.css 的 --hljs-* 令牌决定，明暗首帧由 localStorage.theme 决定。
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
from backend.services.frontend_cache_purge import purge_frontend_page_cache
from backend.utils.compat import utc_now_naive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["系统设置"])


SETTING_GROUPS = [
    "basic",
    "reading",
    "comments",
    "media",
    "seo",
    "email",
    "security",
    "features",
    "appearance",
    "navigation",
    "hero",
    "notice",
    "footer",
    "donate",
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
    "navigation",
    "reading",
    "features",
    "donate",
    # comments 的 allow_guest / max_length / enable_nested / require_approval 需要下发给前台：
    # 匿名评论表单（昵称邮箱、字数上限、回复按钮、待审核提示）都按这份值决定渲染，
    # 缺它等于「后台改了开关，前台表单仍是写死的」。键集全是布尔与计数，无敏感项。
    "comments",
]

# 即便在公开分组内，这些键也一律脱敏（避免误配导致凭据外泄）
_SENSITIVE_KEY_RE = re.compile(r"(password|secret|token|api_?key|private_key|authorization)", re.I)


def _redact(data: dict) -> dict:
    """把 dict 中疑似敏感键的值替换为掩码字符串（仅在顶层做一次浅层脱敏即可，
    因为各分组存的值都是扁平标量 / 一维数组）。"""
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
        # 关于页完整 HTML：设置页会提交、/api/config 与前台 /about 会读取。
        # 缺这里 = _save_group 的 `if k in base` 把它静默丢弃，管理员改了永远不生效。
        "about_page_html": "",
    }


def _default_reading() -> dict:
    return {
        # 这个键唯一的消费点是前端 useSite.reading.posts_per_page（列表/分类/标签/作者/
        # 搜索五页的每页条数），那里的兜底写的是 9（三列网格 × 3 行，也是接这个设置之前
        # 各页写死的条数）。原先这里是 12，而 GET /api/settings/public 下发的是
        # "默认值 + 存值"合并后的**整组**——于是从未保存过 reading 分组的站点每次都能拿到
        # 12，前端那句"沿用 9 避免版式突变"的兜底只有在接口失败时才走得到：同一个设置
        # 两套版式，且后台显示的 12 永远不等于兜底那条路径的 9。
        # 统一成 9 的实际影响：未配置站点的每页从 12 篇变 9 篇（4 行 → 3 行，仍是整行），
        # 已保存过分组的站点读自己的存值，版式不变。
        "posts_per_page": 9,
        "show_reading_time": True,
        "show_word_count": True,
        "show_toc": True,
        "toc_depth": 3,
        "line_height": 1.7,
        "font_size": 16,
    }


def _default_comments() -> dict:
    # 默认值必须等于**装好系统后的既有行为**：_save_group 每次都是「默认值 + payload」整段
    # 落库，管理员改任意一个评论开关都会把这一整组写进库。若默认值与实际行为不一致
    # （旧版 allow_guest=False、max_length=1000），表现就是"我只是勾了个审核，
    # 访客评论全站被打死、长评论开始报 422"。
    return {
        # 评论功能的唯一开关：写口闸门（CommentService）与前台评论区渲染读的都是它。
        # features 组里曾有同义的 enable_comments，两个开关各管一半，已删除。
        "enable": True,
        "require_approval": False,
        "allow_guest": True,
        "max_length": 3000,
        "enable_antispam": True,
        # 嵌套回复只允许"根评论 + 一层回复"（comment_service.validate_parent_depth 硬钉
        # parent.parent_id 必须为空）。可配置层数从来没有人读，留着等于给管理员一个假开关。
        "enable_nested": True,
    }


def _default_media() -> dict:
    # 同 _default_comments：这两个类型清单会被整段落库，并与服务端安全白名单取交集，
    # 所以默认值必须**等于**内置清单。旧文案里的 ppt/pptx/zip/rar 从来没被真正放行过
    # （LIBRARY_ALLOWED_EXTENSIONS 里没有它们），而漏写的 mp4/webm/mov/mp3/wav/ogg
    # 会在一次无关保存后突然传不上去——那才是这份"看起来没生效"的清单真正会生效的时刻。
    return {
        "max_upload_size": 10485760,
        "allowed_image_types": "jpg,jpeg,png,gif,webp,svg",
        "allowed_file_types": "mp4,webm,mov,mp3,wav,ogg,pdf,doc,docx,xls,xlsx",
        # default_post_cover / default_avatar 已删除：封面回落 lib/post-cover.ts 的 picsum
        # 确定性 seed，头像回落 core/avatar_resolver 的 DiceBear，两者都没有这两个值的读取点。
        "use_cdn": False,
        "cdn_prefix": "",
        # 水印：api/media.py::_read_watermark_text 已在读这个键，缺这里等于永远写不进去。
        "watermark_text": "",
    }


def _default_seo() -> dict:
    return {
        "default_title": "",
        "default_description": "",
        "default_keywords": "",
        "og_image": "",
        "twitter_handle": "",
        # google_analytics_id / baidu_analytics_id 已删除：全仓没有任何统计脚本注入口，
        # 而补上它要往 CSP script-src 里加第三方域名（AGENTS §12.6 禁止放松 CSP）。
        # 管理员要挂统计码，唯一受支持通道是"页脚自定义 HTML"（走 sanitize 白名单）。
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
    }


def _default_security() -> dict:
    # 只保留有执行点的两项（api/users.py 登录失败计数）。
    # 会话超时由 JWT TTL（core/config.py）决定，频率限制由 core/rate_limit.py 的环境规则决定，
    # CORS / TrustedHost 只在启动时按 env 装配——把它们做成"后台可改"会诱导管理员
    # 改一个永远不会生效的开关，还可能让人误以为跨域已被收紧。
    return {
        "max_login_attempts": 5,
        "lockout_duration_sec": 1800,
    }


def _default_features() -> dict:
    # enable_comments 曾在这里：评论是否启用由 comments.enable 决定（执行点是
    # CommentService.create_comment 的 COMMENTS_DISABLED 闸门），这一项只有前台
    # 渲染读它，于是两个开关各管一半——关掉 features 那格，评论区消失但接口照常
    # 可写；关掉 comments 那格，接口拒绝但表单照样渲染，访客只拿到一条报错。
    # 现在评论只有 comments.enable 一个开关，/api/config 的扁平 enable_comments
    # 由它投影（core.py::_apply_settings_groups）。
    return {
        "enable_registration": True,
        "enable_rss": True,
        "enable_search": True,
        "enable_sitemap": True,
        "enable_guestbook": True,
        "enable_dark_mode": True,
        "enable_like_button": True,
        "enable_share_buttons": True,
        "enable_reading_progress": True,
        # 图形验证码闸门（评论 + 留言的匿名写口，见 services/captcha_service.py）。
        # 默认 False = 存量站点行为不变；打开后匿名提交必须带 captcha_key/captcha_code，
        # 登录用户始终免验。它同时管评论和留言，所以留在跨模块的 features 组。
        "enable_captcha": False,
    }


def _default_appearance() -> dict:
    # code_theme / code_theme_dark / default_theme / font_family 曾在这里：
    #   - 代码高亮配色由 assets/css/main.css 的 --hljs-* 令牌单源，明暗两套各一份；
    #   - 明/暗首帧由 useTheme.ts 读 localStorage.theme 决定，跟随的是浏览器偏好而非站点配置；
    #   - 字体族由 Tailwind preset 管理。
    # 四个键写进库、下发到 /api/config，却没有任何渲染点读它们——纯假开关，删除。
    return {
        "primary_color": "#0EA5A9",
        "page_width_px": 1200,
        "accent_color": "#8B5CF6",
        "show_copyright": True,
        "show_powered_by": True,
    }


def _default_navigation() -> dict:
    # custom_links 曾在这里：没有任何组件读它，顶栏链接实际来自导航表（/api/navigations）。
    return {
        "header_style": "sticky",
        "show_search": True,
        "show_language_switch": True,
        "show_theme_toggle": True,
    }


def _default_hero() -> dict:
    return {
        "enable": True,
        "title": {"zh": "欢迎来到 Rosetta", "en": "Welcome to Rosetta"},
        "subtitle": {"zh": "一个现代化的开源博客平台", "en": "A modern open-source blog platform"},
        "caption": "Powered by FastAPI + Nuxt 4",
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


def _default_donate() -> dict:
    # 捐助/打赏页（前台 /sponsor 的唯一内容源）。`methods` 每项形如
    # {name, image, note}：name 是收款方式名（支付宝/微信…），image 是收款码图片
    # （后台「媒体上传」产出的相对路径，前台按 <img :src> 渲染，不做 v-html），
    # note 是该通道的一句话说明（可选）。
    # 历史上这里还挂过 `/api/sponsors`（捐赠者名单）与 /api/config 的 sponsor_* 七个键，
    # 两边都没有写入方也没有读取方——本组是捐助功能的新唯一真源。
    return {
        "enable": True,
        "title": {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        "description": {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
        "methods": [],
    }


def _default_footer() -> dict:
    return {
        # text 是页脚"Powered by"那一行的自定义文案。默认留空：这一行有内置四语
        # 文案（i18n footer.poweredBy），写死英文默认值会让非英语站点在一次无关保存后
        # 被英文覆盖。slogan 与它各有独立渲染位（标语行 / Powered by 行），
        # 不再是同一位置的两个候选。
        "text": "",
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
    "security": _default_security,
    "features": _default_features,
    "appearance": _default_appearance,
    "navigation": _default_navigation,
    "hero": _default_hero,
    "notice": _default_notice,
    "footer": _default_footer,
    "donate": _default_donate,
}


def _default_for(group: str) -> dict:
    return _GROUP_DEFAULTS[group]()


def _only_known_keys(base: dict, data: dict) -> dict:
    """按该组**当前**默认键集过滤：读写两侧都要过这道，
    否则已从 _default_* 删掉的死键会一直留在库里的 JSON 中并被回显。"""
    return {k: v for k, v in data.items() if k in base}


async def _load_all_groups(db: DB) -> dict[str, dict]:
    rows = (await db.execute(select(SiteConfig))).scalars().all()
    db_map: dict[str, dict] = {}
    for r in rows:
        if r.key in SETTING_GROUPS:
            try:
                db_map[r.key] = json.loads(r.value) if r.value else {}
            except (json.JSONDecodeError, TypeError) as exc:
                # 单条 KV 损坏不能连带整组：这里退回默认值，但要点名是哪个 key——
                # 否则下一次 PUT 会用默认值静默覆盖整组配置。
                logger.warning(f"[settings] 配置项 {r.key} 的值不是合法 JSON，按默认值处理: {exc}")
                db_map[r.key] = {}

    out: dict[str, dict] = {}
    for g in SETTING_GROUPS:
        base = _default_for(g)
        stored = db_map.get(g)
        # 不过滤存量键 = 已删除的死配置继续回显，设置页再把它提交回来。
        if isinstance(stored, dict):
            out[g] = {**base, **_only_known_keys(base, stored)}
        else:
            out[g] = base
    return out


async def _save_group(db: DB, group: str, data: dict) -> dict:
    base = _default_for(group)
    row = (await db.execute(select(SiteConfig).where(SiteConfig.key == group))).scalar_one_or_none()
    # PATCH 是"部分更新"语义：没出现在请求体里的键，必须保留库里已有的值。
    # 旧实现只拿默认值当底（{**base, **incoming}），于是"只发一个键"的 PATCH 会把
    # 同组其余配置静默打回默认。Admin 界面每次提交整组，所以这条从没暴露过；
    # 插件或脚本走 API 做一次局部保存就会丢配置，而且丢在写入侧、读侧看不出来。
    stored: dict = {}
    if row is not None and row.value:
        try:
            parsed = json.loads(row.value)
            if isinstance(parsed, dict):
                stored = parsed
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning(f"[settings] {group} 存量值不是合法 JSON，本组按默认值重建: {exc}")
    merged = {**base, **_only_known_keys(base, stored), **_only_known_keys(base, data)}
    val_json = json.dumps(merged, ensure_ascii=False)
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

    group: str = Field(..., description="分组键（14 组之一）")
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
        description="全部 14 组配置，键为分组名、值为该组合并默认值后的完整 dict（含敏感明文值）",
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
        "需管理员（CurrentStaff）。返回全部 14 组分组的配置项（含敏感明文值，"
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
        "需管理员（CurrentStaff）。返回指定分组（14 组之一）合并默认值后的完整配置；"
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
    if group not in SETTING_GROUPS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"未知设置分组: {group}")
    all_g = await _load_all_groups(db)
    return SettingsGroupResponse(group=group, data=all_g[group])


@router.patch(
    "/{group}",
    summary="更新单个设置分组",
    description=(
        "需管理员（CurrentStaff）。payload 为该分组的部分键值对象；"
        "不在该组默认值键集内的键被静默丢弃。副作用：写入操作日志（含 before/after diff）、"
        "落库 site_configs 后立刻失效 /settings/public（300s）与 /api/config 的 site_config（3600s）缓存——"
        "分组 JSON 是 /api/config 的权威覆写来源，不失效则站点名等改动最长 1 小时不可见。"
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
    if group not in SETTING_GROUPS:
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
        logger.debug("cache delete for settings_public failed", exc_info=True)
    # 执行点（评论闸门、上传限制、robots 正文）读的是 backend/services/site_settings.py
    # 的分组缓存，不删它则"保存成功但要等 5 分钟才生效"——和上面两个键同一条口径。
    try:
        await cache.delete(make_cache_key("settings_group", group))
    except Exception:
        logger.debug("cache delete for settings_group failed", exc_info=True)
    # GET /api/robots.txt 把整份正文缓在 seo:robots_txt（1 小时）。它现在会读 seo 分组，
    # 不清这个键等于"改了 robots、爬虫 1 小时内继续看旧的"。
    if group == "seo":
        try:
            await cache.delete(make_cache_key("seo", "robots_txt"))
        except Exception:
            logger.debug("cache delete for seo:robots_txt failed", exc_info=True)
    # site_config 缓存（TTL 3600s）里叠了本分组的 JSON 覆写（见 core.py::_apply_settings_groups）：
    # 分组保存后不删它，站点名/简介/侧栏最长 1 小时不生效，RSS channel（同源读缓存）一起陈旧。
    try:
        await cache.delete(make_cache_key("site_config"))
    except Exception:
        logger.debug("cache delete for site_config failed", exc_info=True)
    # Nitro 对公开页做 swr 缓存，缓存的 HTML 字节里嵌着站点名等配置渲染结果；
    # API 缓存删了页面仍是旧口径，fire-and-forget 通知前端清页面级缓存。
    purge_frontend_page_cache(f"设置分组保存: {group}")
    return {"success": True, "group": group, "data": saved, "changed": list(diff.keys())}
