"""
短代码（Shortcode）API

三条互不相同的职责线：

* ``POST /api/shortcodes/render`` — 公开渲染（编辑器预览）。**忽略一切调用方传入的
  上下文**：``ctx`` 会原样作为关键字参数传给每个 handler，而插件 handler 可能用它做
  数据可见性判断；把 ``context`` 开放给未鉴权调用方等于让访客决定插件看到什么。
* ``POST /api/admin/shortcodes`` — 管理员预览，唯一接受 ``context`` 的入口。
* ``GET/POST/DELETE /api/admin/shortcodes*`` — 注册表管理。API 注册的模板式短代码
  持久化在 SiteConfig KV（``shortcode_templates``），启动与列表前重放进本进程注册表。

归属边界：插件在 ``register()`` 里自带的短代码（``plugin`` 非空）生命周期跟着插件启停，
运行时接口既不能覆盖它，也不能注销它——注销后唯一的恢复路径是重启进程。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import DB, CurrentStaff
from backend.core.exceptions import AppException
from backend.core.shortcodes import (
    ShortcodeInfo,
    do_shortcode,
    list_shortcodes,
    make_template_handler,
    register_shortcode,
    shortcode_owner,
    unregister_shortcode,
)
from backend.schemas import BaseResponse

logger = logging.getLogger(__name__)

SHORTCODE_PLUGIN_OWNED = "SHORTCODE_PLUGIN_OWNED"

# 公开渲染接口的正文上限。原 1,000,000 是给未鉴权接口的：正则扫描 + 逐层递归重扫
# 的代价随长度上升，单请求就能把 worker 的 CPU 吃掉一大块。200,000 字符仍远大于
# 任何真实单篇文章正文，配合引擎的嵌套深度闸门（_MAX_NESTING_DEPTH）才是完整防线。
RENDER_MAX_CHARS = 200_000

router = APIRouter(tags=["短代码"])


# ==================== 请求/响应模型 ====================


class ShortcodeRenderRequest(BaseModel):
    """公开渲染请求：只有正文，没有上下文。"""

    content: str = Field(
        ...,
        min_length=0,
        max_length=RENDER_MAX_CHARS,
        description="包含短代码的原始内容文本",
    )


class ShortcodePreviewRequest(ShortcodeRenderRequest):
    """管理员预览请求：可额外传入渲染上下文。"""

    context: dict[str, Any] | None = Field(
        default=None,
        description=(
            "渲染上下文，作为 ``ctx`` 关键字参数传给每个 handler。"
            "仅管理接口接受——公开渲染接口会忽略（且拒绝）该字段。"
        ),
    )


class ShortcodeRenderData(BaseModel):
    """渲染结果数据"""

    rendered: str = Field(..., description="经过短代码展开 + 安全清理后的 HTML")
    original_length: int = Field(..., description="原始内容长度")
    rendered_length: int = Field(..., description="渲染结果长度")


class ShortcodeRenderResponse(BaseResponse):
    """渲染响应"""

    data: ShortcodeRenderData


class ShortcodeDefinition(BaseModel):
    """短代码定义项"""

    tag: str = Field(..., description="短代码标签名，例如 [warning]")
    has_paired: bool = Field(
        ...,
        description=(
            "是否支持成对语法 [tag]...[/tag]。这是给编辑器 UI 的元数据："
            "渲染引擎不按它拒绝语法——未注册标签一律原样保留，"
            "has_paired=False 的标签写成成对时，开标签照常展开、多余的 [/tag] 原样留在正文。"
        ),
    )
    description: str | None = Field(None, description="开发者提供的描述（可选）")
    plugin: str | None = Field(
        None,
        description="归属插件 slug；None 表示由管理 API 注册的模板式短代码",
    )
    template: bool = Field(
        False,
        description="是否为 API 注册的字符串模板（True 才可经本接口注销）",
    )


class ShortcodeListData(BaseModel):
    count: int
    items: list[ShortcodeDefinition]
    persisted: int = Field(
        ...,
        description="SiteConfig KV 中登记的模板短代码条数（跨 worker/重启的事实来源）",
    )


class ShortcodeListResponse(BaseResponse):
    data: ShortcodeListData


class ShortcodeRegisterRequest(BaseModel):
    """通过 API 注册简单替换式短代码（仅管理员）"""

    tag: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-z_][A-Za-z0-9_\-]*$")
    replacement: str = Field(
        ...,
        min_length=0,
        max_length=50_000,
        description="用于替换 [tag] 或 [tag /] 的固定 HTML 文本。使用 {content} 表示内部内容，{key} 表示属性。",
    )
    description: str | None = Field(default=None, max_length=200)


class ShortcodeDeleteResponse(BaseResponse):
    data: dict[str, Any] = Field(default_factory=dict)


# ==================== 工具函数 ====================


def _info_to_def(info: ShortcodeInfo) -> ShortcodeDefinition:
    return ShortcodeDefinition(
        tag=info.tag,
        has_paired=info.has_paired,
        description=info.description,
        plugin=info.plugin,
        template=info.template,
    )


def _render(text: str, context: dict[str, Any] | None) -> ShortcodeRenderResponse:
    """渲染并包装成统一响应。

    异常不外泄细节：handler 之外的引擎故障（正则、递归）会把内部信息塞进
    ``detail``，而这个字段会经 toast 直接显示在编辑器界面上。原始异常进日志。
    """
    try:
        rendered = do_shortcode(text, context=context)
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.exception("短代码渲染失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="短代码渲染失败",
        ) from exc

    return ShortcodeRenderResponse(
        success=True,
        message="渲染完成",
        data=ShortcodeRenderData(
            rendered=rendered,
            original_length=len(text),
            rendered_length=len(rendered),
        ),
    )


async def _invalidate_rendered_content(*, reason: str) -> None:
    """短代码注册表变化后，抹掉一切嵌有渲染结果的缓存（与插件启停同口径）。

    注册/注销直接改变同一篇正文经 ``content_renderer`` 出来的 HTML；不清就等于
    管理员改完短代码，访客在 TTL（最长 10 分钟）内仍看到旧展开结果。
    """
    from backend.core.cache import invalidate_cache
    from backend.services.frontend_cache_purge import purge_frontend_page_cache

    await invalidate_cache("post:")  # 详情键不在 posts 前缀下，必须单独清
    await invalidate_cache("posts")  # 列表 + RSS
    await invalidate_cache("archive")
    purge_frontend_page_cache(f"shortcode:{reason}")


async def _reconcile_and_list(db: DB) -> tuple[list[ShortcodeDefinition], int]:
    """先把 DB 里的模板重放进本进程注册表，再列。

    多 worker 部署下写请求只落在处理它的那个进程；列表前不重放，管理员就会看到
    "刚注册的短代码刷新一次就消失"（下一次 GET 打到别的 worker）。
    """
    from backend.core.extensions import (
        get_shortcode_templates,
        reconcile_shortcode_templates,
    )

    await reconcile_shortcode_templates(db)
    templates = await get_shortcode_templates(db)
    return [_info_to_def(i) for i in list_shortcodes()], len(templates)


# ==================== 公开接口 ====================


@router.post(
    "/shortcodes/render",
    response_model=ShortcodeRenderResponse,
    summary="渲染内容中的短代码",
    description=(
        "输入任意文本，将 [tag]、[tag attr=val] 或 [tag]content[/tag] 等短代码展开为 HTML 后返回。"
        "清理口径：只注册过的短代码会被展开，未匹配的文本**原样返回**（不转义、不过滤），"
        "因此本接口不是 HTML 净化器；白名单 allowlist 只作用于 handler 的返回值。"
        "公开可访问但**不接受** ``context``（传了会被整体忽略，防止未鉴权调用方注入插件"
        " handler 读取的渲染上下文）；需要上下文请用 ``POST /api/admin/shortcodes``。"
        "正文上限 "
        f"{RENDER_MAX_CHARS} 字符，同名嵌套超过引擎深度闸门后内层原样保留。"
    ),
)
async def render_shortcodes(
    payload: ShortcodeRenderRequest = Body(...),
) -> ShortcodeRenderResponse:
    """公开短代码渲染接口（用于前端编辑器预览等场景）。"""
    return _render(payload.content, None)


# ==================== 管理接口 ====================


@router.get(
    "/admin/shortcodes",
    response_model=ShortcodeListResponse,
    summary="列出所有已注册短代码（管理员）",
    description=(
        "需 CurrentStaff。返回本进程注册表内的所有短代码及元数据"
        "（``plugin`` = 归属插件 slug，``template`` = 可经本接口管理的模板）。"
        "列表前会先把 SiteConfig KV 里的模板重放进本进程注册表，"
        "因此多 worker 下也能看到其他进程刚注册的那条。"
    ),
)
async def list_registered_shortcodes(
    db: DB,
    _staff: CurrentStaff,
) -> ShortcodeListResponse:
    items, persisted = await _reconcile_and_list(db)
    return ShortcodeListResponse(
        success=True,
        message="短代码列表获取成功",
        data=ShortcodeListData(count=len(items), items=items, persisted=persisted),
    )


@router.post(
    "/admin/shortcodes",
    response_model=ShortcodeRenderResponse,
    summary="预览短代码渲染结果（管理员）",
    description=(
        "与公开渲染接口的差异是**唯一**能带 ``context`` 的入口："
        "该字段会作为 ``ctx`` 传给每个 handler，供依赖文章/用户上下文的插件短代码在预览时取数。"
        "正文上限与公开接口一致（请求模型继承自公开请求，``context`` 为额外字段）。"
    ),
)
async def preview_shortcodes(
    _staff: CurrentStaff,
    payload: ShortcodePreviewRequest = Body(...),
) -> ShortcodeRenderResponse:
    return _render(payload.content, payload.context)


@router.post(
    "/admin/shortcodes/register",
    response_model=ShortcodeListResponse,
    summary="注册简单模板式短代码（管理员）",
    description=(
        "运行时注册一个基于 {replacement} 字符串模板的短代码，并写入 SiteConfig KV "
        "``shortcode_templates``（多 worker 与重启后仍然生效）。"
        "模板中可用 ``{content}`` 表示成对短代码的内部内容，或用 ``{属性名}`` 引用调用时传入的属性；"
        "属性值与正文都只经过引擎的 handler 输出清洗。"
        "同名标签若已由插件注册则返回 409（``SHORTCODE_PLUGIN_OWNED``），不覆盖插件实现。"
        "注册成功后返回重放后的短代码列表，并失效已渲染内容缓存。"
    ),
    responses={
        200: {"model": ShortcodeListResponse},
        409: {
            "description": "同名短代码由插件注册，运行时接口不得覆盖（error_code: SHORTCODE_PLUGIN_OWNED）"
        },
    },
)
async def register_template_shortcode(
    db: DB,
    _staff: CurrentStaff,
    payload: ShortcodeRegisterRequest = Body(...),
) -> ShortcodeListResponse:
    from backend.core.extensions import put_shortcode_template

    owner = shortcode_owner(payload.tag)
    if owner:
        raise AppException(
            status_code=409,
            message=f"短代码 {payload.tag} 由插件 {owner} 注册，运行时接口不能覆盖",
            error_code=SHORTCODE_PLUGIN_OWNED,
        )

    # 引擎以 fn(**attrs, content=…, _content=…, ctx=…) 调用 handler，
    # 所以模板 handler 必须由 core 的工厂构造（位置参数签名会打成错误注释）。
    register_shortcode(
        payload.tag,
        make_template_handler(payload.replacement),
        has_paired=True,
        description=payload.description,
        template=True,
    )
    await put_shortcode_template(
        db,
        payload.tag,
        replacement=payload.replacement,
        description=payload.description,
    )
    await db.commit()
    await _invalidate_rendered_content(reason=f"register:{payload.tag}")

    items, persisted = await _reconcile_and_list(db)
    return ShortcodeListResponse(
        success=True,
        message=f"已注册短代码 {payload.tag}",
        data=ShortcodeListData(count=len(items), items=items, persisted=persisted),
    )


@router.delete(
    "/admin/shortcodes/{tag}",
    response_model=ShortcodeDeleteResponse,
    summary="注销运行时已注册的短代码（管理员）",
    description=(
        "移除一个 API 注册的模板式短代码：同时摘除本进程注册表条目、SiteConfig KV 记录，"
        "并失效已渲染内容缓存。tag 不存在仍视为成功（幂等）。"
        "插件自带的同名短代码返回 409（``SHORTCODE_PLUGIN_OWNED``）——插件短代码跟着插件"
        "启停走，运行时注销后除了重启进程没有恢复路径。"
    ),
    responses={
        200: {"model": ShortcodeDeleteResponse},
        409: {
            "description": "该 tag 归属插件，须经插件停用移除（error_code: SHORTCODE_PLUGIN_OWNED）"
        },
    },
)
async def remove_shortcode(
    db: DB,
    _staff: CurrentStaff,
    tag: str,
) -> ShortcodeDeleteResponse:
    from backend.core.extensions import delete_shortcode_template

    owner = shortcode_owner(tag)
    if owner:
        raise AppException(
            status_code=409,
            message=f"短代码 {tag} 归属插件 {owner}，请通过停用插件移除",
            error_code=SHORTCODE_PLUGIN_OWNED,
        )

    existed = unregister_shortcode(tag)
    persisted = await delete_shortcode_template(db, tag)
    await db.commit()
    if existed or persisted:
        await _invalidate_rendered_content(reason=f"unregister:{tag}")
    return ShortcodeDeleteResponse(
        success=True,
        message=f"短代码 {tag} 已注销" if (existed or persisted) else f"短代码 {tag} 不存在",
        data={
            "tag": tag,
            "action": "unregister",
            "was_registered": existed,
            "was_persisted": persisted,
        },
    )
