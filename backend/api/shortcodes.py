"""
短代码（Shortcode）渲染 API

提供内容短代码渲染、已注册短代码查询与预览能力。
公开渲染接口面向前端文章预览场景；管理接口用于后台列出所有
已注册短代码及其元数据。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import CurrentStaff
from backend.core.shortcodes import (
    ShortcodeInfo,
    do_shortcode,
    list_shortcodes,
    register_shortcode,
    unregister_shortcode,
)
from backend.schemas import BaseResponse

router = APIRouter(tags=["短代码"])


# ==================== 请求/响应模型 ====================


class ShortcodeRenderRequest(BaseModel):
    """短代码渲染请求"""

    content: str = Field(
        ...,
        min_length=0,
        max_length=1_000_000,
        description="包含短代码的原始内容文本",
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="可选的渲染上下文，将作为 attrs 兜底字段提供给回调",
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
    has_paired: bool = Field(..., description="是否支持成对语法 [tag]...[/tag]")
    description: str | None = Field(None, description="开发者提供的描述（可选）")


class ShortcodeListData(BaseModel):
    count: int
    items: list[ShortcodeDefinition]


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
    data: dict[str, str] = Field(default_factory=dict)


# ==================== 工具函数 ====================


def _info_to_def(info: ShortcodeInfo) -> ShortcodeDefinition:
    return ShortcodeDefinition(
        tag=info.tag,
        has_paired=info.has_paired,
        description=info.description,
    )


# ==================== 公开接口 ====================


@router.post(
    "/shortcodes/render",
    response_model=ShortcodeRenderResponse,
    summary="渲染内容中的短代码",
    description="输入任意文本，将 [tag]、[tag attr=val] 或 [tag]content[/tag] 等短代码展开为 HTML，并经过白名单安全清理后返回。",
)
async def render_shortcodes(
    payload: ShortcodeRenderRequest = Body(...),
) -> ShortcodeRenderResponse:
    """公开短代码渲染接口（用于前端编辑器预览等场景）"""

    context: dict[str, Any] = payload.context or {}
    try:
        rendered = do_shortcode(payload.content, context=context)
    except Exception as exc:  # pragma: no cover - 防御性兜底
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"短代码渲染失败: {exc}",
        ) from exc

    return ShortcodeRenderResponse(
        success=True,
        message="渲染完成",
        data=ShortcodeRenderData(
            rendered=rendered,
            original_length=len(payload.content),
            rendered_length=len(rendered),
        ),
    )


# ==================== 管理接口 ====================


@router.get(
    "/admin/shortcodes",
    response_model=ShortcodeListResponse,
    summary="列出所有已注册短代码（管理员）",
    description="返回当前运行中全局 ShortcodeManager 内已注册的所有短代码及元数据。",
)
async def list_registered_shortcodes(
    _staff: CurrentStaff,
) -> ShortcodeListResponse:
    infos = list_shortcodes()
    items = [_info_to_def(i) for i in infos]
    return ShortcodeListResponse(
        success=True,
        message="短代码列表获取成功",
        data=ShortcodeListData(count=len(items), items=items),
    )


@router.post(
    "/admin/shortcodes",
    response_model=ShortcodeRenderResponse,
    summary="预览短代码渲染结果（管理员）",
    description="与公开渲染接口一致，但可额外接受更复杂的上下文。",
)
async def preview_shortcodes(
    _staff: CurrentStaff,
    payload: ShortcodeRenderRequest = Body(...),
) -> ShortcodeRenderResponse:
    return await render_shortcodes(payload)


@router.post(
    "/admin/shortcodes/register",
    response_model=ShortcodeListResponse,
    summary="注册简单模板式短代码（管理员）",
    description=(
        "运行时注册一个基于 {replacement} 字符串模板的短代码。"
        "模板中可用 {content} 表示成对短代码的内部内容，"
        "或使用 {属性名} 引用调用时传入的属性。"
        "注册成功后返回更新后的短代码列表。"
    ),
)
async def register_template_shortcode(
    _staff: CurrentStaff,
    payload: ShortcodeRegisterRequest = Body(...),
) -> ShortcodeListResponse:
    def _handler(attrs: dict[str, Any], content: str | None) -> str:
        text = payload.replacement
        # 属性插值：{attr_name}
        for k, v in attrs.items():
            if isinstance(v, str):
                text = text.replace(f"{{{k}}}", v)
        # 内容插值：{content}
        if content is not None:
            text = text.replace("{content}", content)
        return text

    try:
        register_shortcode(
            tag=payload.tag,
            handler=_handler,
            has_paired=True,
            description=payload.description,
        )
    except Exception as exc:  # pragma: no cover - 防御性
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"注册短代码失败: {exc}",
        ) from exc

    infos = list_shortcodes()
    items = [_info_to_def(i) for i in infos]
    return ShortcodeListResponse(
        success=True,
        message=f"已注册短代码 {payload.tag}",
        data=ShortcodeListData(count=len(items), items=items),
    )


@router.delete(
    "/admin/shortcodes/{tag}",
    response_model=ShortcodeDeleteResponse,
    summary="注销运行时已注册的短代码（管理员）",
    description="根据 tag 名称移除一个已注册的短代码。若 tag 不存在仍视为成功（幂等）。",
)
async def remove_shortcode(
    _staff: CurrentStaff,
    tag: str,
) -> ShortcodeDeleteResponse:
    existed = unregister_shortcode(tag)
    msg = f"短代码 {tag} 已注销" if existed else f"短代码 {tag} 不存在"
    return ShortcodeDeleteResponse(
        success=True,
        message=msg,
        data={"tag": tag, "action": "unregister"},
    )
