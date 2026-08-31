"""
Rosetta 调色板（Palette）主题系统。

职责：
1. 维护后端的调色板清单 ``AVAILABLE_PALETTES``，与前端
   ``frontend/composables/useThemePalette.ts`` 中的 PALETTES 定义一一对应；
2. 提供 ``_build_palette_css(palette_id)`` → CSS 字符串，将调色板色相/饱和度/亮度
   编译成 HSL 自定义属性（CSS Variables），供 ``main.css`` 中 ``html.palette-*`` 覆盖；
3. 提供 REST 路由：
   - ``GET /api/themes/palettes`` —— 返回所有调色板（便于后端主题管理页渲染）
   - ``GET /api/themes/current.css`` —— 返回当前用户/站点启用调色板的 CSS 片段
   - ``PUT /api/admin/themes/current`` —— 管理员设置默认调色板（写入 SiteConfig）。
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field as PDField

from backend.core.auth import CurrentStaff, CurrentUserOptional, DB
from backend.models.core import SiteConfig

logger = logging.getLogger(__name__)

router = APIRouter(tags=["主题"])

CONFIG_KEY = "theme_palette"


# ── 调色板定义（与 frontend/composables/useThemePalette.ts 同步） ──────────


@dataclass(frozen=True)
class Palette:
    id: str
    name: str
    label: str
    # 浅色 / 深色两套 HSL 配置：以 primary 色相为核心差异点，其它颜色派生
    light: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    dark: dict[str, tuple[float, float, float]] = field(default_factory=dict)


_DEFAULT_HUES: dict[str, float] = {
    # palette_id -> 浅色 primary 色相（h 度）；深色模式使用同一色相 + 调整饱和度/亮度
    "sky": 201,
    "indigo": 262,
    "emerald": 158,
    "amber": 42,
    "rose": 346,
    "violet": 271,
    "warm-stone": 32,
    "minimal": 220,
}

# 派生：基于 primary hue 生成一套基础的 light/dark 色板变量
# keys 对齐 main.css 中 --primary / --accent / --info / --ring / --muted 等
# 我们用 (h, s%, l%) 三元组表示，在 CSS 中渲染成 hsl(var(--X) / <alpha-value>) 兼容模式。
_LIGHT_DEFAULTS = {
    "background": (0, 0, 100),  # 白
    "foreground": (222, 47, 11),
    "card": (0, 0, 100),
    "card-foreground": (222, 47, 11),
    "muted": (210, 40, 96),
    "muted-foreground": (215, 16, 47),
    "border": (214, 32, 91),
    "input": (214, 32, 91),
    "ring": (222, 47, 11),
    "secondary": (210, 40, 96),
    "secondary-foreground": (222, 47, 11),
    "accent": (210, 40, 96),
    "accent-foreground": (222, 47, 11),
    "destructive": (0, 84, 60),
    "destructive-foreground": (210, 40, 98),
    "info": (201, 96, 52),
    "success": (158, 64, 46),
    "warning": (42, 96, 55),
    "error": (0, 84, 60),
}

_DARK_DEFAULTS = {
    "background": (222, 47, 6),
    "foreground": (210, 40, 98),
    "card": (222, 47, 8),
    "card-foreground": (210, 40, 98),
    "muted": (217, 33, 17),
    "muted-foreground": (215, 20, 65),
    "border": (217, 33, 17),
    "input": (217, 33, 17),
    "ring": (212, 27, 84),
    "secondary": (217, 33, 17),
    "secondary-foreground": (210, 40, 98),
    "accent": (217, 33, 17),
    "accent-foreground": (210, 40, 98),
    "destructive": (0, 75, 42),
    "destructive-foreground": (210, 40, 98),
    "info": (201, 96, 60),
    "success": (158, 64, 52),
    "warning": (42, 96, 62),
    "error": (0, 75, 42),
}


def _build_palette(id: str, name: str, label: str, hue: float) -> Palette:
    light = dict(_LIGHT_DEFAULTS)
    dark = dict(_DARK_DEFAULTS)
    # 替换 primary / primary-foreground：hue 是每个调色板唯一的核心变量
    light["primary"] = (hue, 96 if id != "minimal" else 9, 52 if id != "minimal" else 46)
    light["primary-foreground"] = (210, 40, 98)
    dark["primary"] = (hue, 91 if id != "minimal" else 9, 65 if id != "minimal" else 65)
    dark["primary-foreground"] = (222, 47, 6)
    # ring/info 跟随 primary hue
    light["ring"] = (hue, 90, 50)
    dark["ring"] = (hue, 85, 70)
    light["info"] = (hue, 96, 55)
    dark["info"] = (hue, 90, 65)
    return Palette(id=id, name=name, label=label, light=light, dark=dark)


AVAILABLE_PALETTES: tuple[Palette, ...] = (
    _build_palette("sky", "Sky", "天青", _DEFAULT_HUES["sky"]),
    _build_palette("indigo", "Indigo", "靛蓝", _DEFAULT_HUES["indigo"]),
    _build_palette("emerald", "Emerald", "翠绿", _DEFAULT_HUES["emerald"]),
    _build_palette("amber", "Amber", "琥珀", _DEFAULT_HUES["amber"]),
    _build_palette("rose", "Rose", "玫瑰", _DEFAULT_HUES["rose"]),
    _build_palette("violet", "Violet", "紫罗兰", _DEFAULT_HUES["violet"]),
    _build_palette("warm-stone", "Warm Stone", "赭石", _DEFAULT_HUES["warm-stone"]),
    _build_palette("minimal", "Minimal", "极简", _DEFAULT_HUES["minimal"]),
)

DEFAULT_PALETTE_ID: str = "sky"

_PALETTE_BY_ID: dict[str, Palette] = {p.id: p for p in AVAILABLE_PALETTES}


@functools.lru_cache(maxsize=None)
def _build_palette_css(key: str) -> str:
    """为指定调色板生成 CSS 自定义属性块。

    返回的字符串形如::

        html.palette-violet {
            --primary: 271 91% 65%;
            ...
        }
        html.dark.palette-violet {
            --primary: 271 88% 70%;
            ...
        }

    非法 key 抛 KeyError（单测依赖此行为）。
    ``lru_cache`` 保证二次调用返回同一对象（单测依赖 identity 断言）。
    """
    palette = _PALETTE_BY_ID[key]  # 非法 key 抛 KeyError（由测试断言）
    lines: list[str] = []

    def _render_block(selector: str, colors: dict[str, tuple[float, float, float]]) -> None:
        lines.append(f"{selector} {{")
        for k, (h, s, l) in colors.items():
            lines.append(f"  --{k}: {h:.0f} {s:.0f}% {l:.0f}%;")
        lines.append("}")

    _render_block(f"html.palette-{palette.id}", palette.light)
    _render_block(f"html.dark.palette-{palette.id}", palette.dark)
    return "\n".join(lines) + "\n"


# ── API 路由 ────────────────────────────────────────────────────────────────


class PaletteOut(BaseModel):
    id: str
    name: str
    label: str
    swatch_light: str = PDField(description="浅色模式 primary HSL 字符串，例：201 96% 52%")
    swatch_dark: str = PDField(description="深色模式 primary HSL 字符串")


@router.get("/themes/palettes", summary="获取所有可用调色板")
async def list_palettes(_: CurrentUserOptional = None) -> dict:
    out = []
    for p in AVAILABLE_PALETTES:
        hl, sl, ll = p.light["primary"]
        hd, sd, ld = p.dark["primary"]
        out.append(
            PaletteOut(
                id=p.id,
                name=p.name,
                label=p.label,
                swatch_light=f"{hl:.0f} {sl:.0f}% {ll:.0f}%",
                swatch_dark=f"{hd:.0f} {sd:.0f}% {ld:.0f}%",
            ).model_dump()
        )
    return {"success": True, "data": out, "default": DEFAULT_PALETTE_ID}


@router.get("/themes/current.css", summary="获取当前启用调色板的 CSS")
async def get_current_palette_css(
    db: DB,
    palette: Optional[str] = Query(None, description="强制指定调色板 id（调试用）"),
):
    """返回 text/css 响应，可通过 <link rel=stylesheet> 直链。"""
    from fastapi.responses import Response

    pid = palette
    if not pid:
        from sqlalchemy import select as _s
        r = await db.execute(_s(SiteConfig).where(SiteConfig.key == CONFIG_KEY))
        row = r.scalar_one_or_none()
        pid = row.value if row and row.value else DEFAULT_PALETTE_ID
    if pid not in _PALETTE_BY_ID:
        raise HTTPException(status_code=400, detail=f"非法调色板 id: {pid}")
    css = _build_palette_css(pid)
    return Response(content=css, media_type="text/css; charset=utf-8")


@router.put("/admin/themes/current", summary="管理员设置默认调色板")
async def put_current_palette(
    db: DB,
    _: CurrentStaff,
    payload: dict = Body(...),
):
    from sqlalchemy import select as _s

    pid = (payload or {}).get("palette_id") or (payload or {}).get("id")
    if not isinstance(pid, str) or pid not in _PALETTE_BY_ID:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"palette_id 非法，可选值：{list(_PALETTE_BY_ID)}",
        )
    r = await db.execute(_s(SiteConfig).where(SiteConfig.key == CONFIG_KEY))
    row = r.scalar_one_or_none()
    if row is None:
        row = SiteConfig(key=CONFIG_KEY, value=pid, description="当前默认调色板 id")
        db.add(row)
    else:
        row.value = pid
    await db.flush()
    # 调色板切换后需要让 lru_cache 保持命中即可（不清除缓存），不刷新浏览器也生效
    return {"success": True, "palette_id": pid}


@router.get("/themes/active", summary="获取当前激活主题（公开，支持 Customizer 前台渲染）")
async def public_get_active_theme(
    db: DB,
    _: CurrentUserOptional = None,
):
    """公开端点：供首页/公开页面读取当前激活主题的 slug / mods / screenshot_urls。

    与 :router:`themes_ext.router` 中 ``GET /admin/themes/active`` 不同，此处：
    - 不需要管理员权限（访客访问公开页面也要能渲染主题 Customizer 覆盖）；
    - 返回结构使用 ThemeOut schema（与后台返回一致）。
    """
    from sqlalchemy import select as _s

    from backend.models.extensions import Theme
    from backend.schemas.extensions import ThemeOut

    result = await db.execute(_s(Theme).where(Theme.is_active == True))  # noqa: E712
    theme = result.scalar_one_or_none()
    if theme is None:
        return {"success": True, "data": None, "message": "未启用自定义主题"}
    # Commit boundary safe: refresh the ORM row from DB so datetime columns and JSON
    # fields are real Python values → Pydantic from_attributes won't need lazy
    # attribute access (causing MissingGreenlet errors).
    await db.refresh(theme)
    out = ThemeOut.model_validate(theme)
    # 填充 mods：读取 JSON 字段（theme.mods 通常已经是 dict；如果为字符串兜底做一次 json.loads）
    try:
        from backend.core.extensions import theme_manager
        out.mods = await theme_manager.get_mods(db, theme.slug)
    except Exception:
        out.mods = None
    return {"success": True, "data": out}
