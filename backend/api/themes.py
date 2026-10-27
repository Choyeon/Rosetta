"""
Rosetta 主题相关的公开读口。

职责只剩一条：``GET /api/themes/active`` —— 前台/访客读取站点激活主题
（slug / version / mods / screenshot_urls），以及后台「预览」按钮的
``?preview=<slug>`` 取数入口。

**调色板（palette）一族已于 2026-10-28 退役删除**：``GET /themes/palettes``、
``GET /themes/current.css``、``PUT /admin/themes/current`` 三条端点写入的
SiteConfig KV ``theme_palette`` 没有任何读取方，配套的 ``html.palette-*`` CSS 块
也没有任何代码给 ``<html>`` 挂过那个 class（挂 class 的 composable 在主题解耦那轮
已删除）。站点主色的唯一活路径是 ``settings.appearance.primary_color`` 与主题
mods 的 ``primary_color``（``frontend/composables/useFrontendTheme.ts`` 按
「theme mods > appearance 设置」优先级写进 ``:root --primary``）。保留三条只会让
后台与 API 文档多出一个"改了但什么都不发生"的开关。回归守卫见
``tests/test_retired_palette_family_is_gone.py``。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel
from pydantic import Field as PDField

from backend.core.auth import DB, CurrentUserOptional
from backend.schemas.extensions import ThemeOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["主题"])


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class ActiveThemeResponse(BaseModel):
    """当前激活主题端点的响应体（公开接口）。"""

    success: bool = PDField(True, description="固定为 true")
    data: ThemeOut | None = PDField(
        None,
        description=(
            "主题记录：mods 为清单默认值与 DB 存值的合并结果，"
            "mods 读取失败时该字段回退 null 而不阻断响应；站点尚未启用任何主题时为 null"
        ),
    )
    message: str | None = PDField(
        None, description="仅 data 为 null 时出现，取值为「未启用自定义主题」"
    )


# ── API 路由 ──


@router.get(
    "/themes/active",
    summary="获取当前激活主题（公开，支持 Customizer 前台渲染）",
    description=(
        "公开接口，访客无需登录即可读取（也可带 token，但权限一致），"
        "供前台页面渲染主题 Customizer 覆盖样式。data 是主题记录，"
        "mods 为清单默认值与已存值的合并；mods 读取失败只把 mods 置 null，不阻断响应。"
        "站点尚未启用任何主题时 data 为 null 并附 message 提示。"
        "preview 参数是后台预览入口：传主题 slug 时返回该主题自身的信息"
        "（不改变站点激活主题），slug 不存在或未安装时静默回落到激活主题。"
    ),
    responses={200: {"model": ActiveThemeResponse}},
)
async def public_get_active_theme(
    db: DB,
    _: CurrentUserOptional = None,
    preview: str | None = Query(
        None,
        max_length=80,
        description="预览模式：返回该 slug 主题自身的公开信息（version / mods / screenshot_urls），"
        "不改变站点激活主题，也不影响未安装/未知 slug（此时回落到激活主题）",
    ),
):
    """公开端点：供首页/公开页面读取当前激活主题的 slug / mods / screenshot_urls。

    - 不需要管理员权限（访客访问公开页面也要能渲染主题 Customizer 覆盖）；
    - 站点过滤统一走 ``ThemeManager.get_active``（避免各处手写 query 漏掉 site_id）；
    - 返回结构使用 ThemeOut schema（与后台列表一致）。
    - ``?preview=<slug>``：后台「预览」按钮的取数入口。必须返回**被预览主题自己**的
      version 与 mods，否则前台会拿激活主题的 ``?v=`` 与 ``layout_width`` 去渲染
      另一个主题（实测：预览极简主题时宽度是默认主题的 1200px，且 style.css 的
      缓存击穿键指向错误主题）。
    """
    from backend.core.extensions import theme_manager
    from backend.schemas.extensions import ThemeOut

    theme = None
    if preview:
        theme = await theme_manager.get(db, preview)
    if theme is None:
        theme = await theme_manager.get_active(db)
    if theme is None:
        return {"success": True, "data": None, "message": "未启用自定义主题"}
    # Commit boundary safe: refresh the ORM row from DB so datetime columns and JSON
    # fields are real Python values → Pydantic from_attributes won't need lazy
    # attribute access (causing MissingGreenlet errors).
    await db.refresh(theme)
    out = ThemeOut.model_validate(theme)
    try:
        out.mods = await theme_manager.get_mods(db, theme.slug)
    except Exception:
        # 公开路径容错：mods 读取失败不阻断页面渲染，但要留下日志痕迹
        # （静默吞掉是此前审计指出的问题，双端点各自吞、无从排查）。
        logger.exception("读取主题 %s mods 失败，已按空 mods 返回", theme.slug)
        out.mods = None
    return {"success": True, "data": out}
