"""
文章目录（TOC）生成 API

从 Markdown 内容中提取标题生成目录。
"""

import re
from html import escape
from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

router = APIRouter(tags=["TOC"])


class TOCItem(BaseModel):
    """目录项"""

    id: str
    text: str
    level: int
    children: list["TOCItem"] = []


class TOCRequest(BaseModel):
    """TOC 请求"""

    content: str
    max_depth: int = 3


class TOCResponse(BaseModel):
    """TOC 响应"""

    items: list[TOCItem]
    html: str


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class TOCHeadingItem(BaseModel):
    """从 Markdown 里提取出的单个标题（扁平结构，不含 children）。"""

    id: str = Field(
        ...,
        description=(
            "由标题文本推导的锚点 id：转小写后把非 [字母数字下划线/中文/连字符] 的字符换成 -"
            "并压缩连续连字符；纯符号标题可能是空字符串"
        ),
    )
    text: str = Field(..., description="标题纯文本：已剥掉粗体、斜体、行内代码与链接语法")
    level: int = Field(..., description="标题层级 1–6，等于行首 # 的个数")


class TOCExtractResponse(BaseModel):
    """标题提取端点的响应体。"""

    headings: list[TOCHeadingItem] = Field(
        default_factory=list, description="按文中出现顺序排列的扁平标题列表，无命中时是空数组"
    )
    count: int = Field(0, description="标题条数，等于 headings 长度")


class TOCAddIdsResponse(BaseModel):
    """标题加锚点端点的响应体。"""

    content: str = Field(
        ...,
        description=(
            "改写后的整篇内容：行首的 Markdown 标题被替换成带 id 属性的原生 h1–h6 HTML 标签"
            "（文本与 id 均已 HTML 转义），其余行原样保留；没有标题时与入参完全相同"
        ),
    )


def extract_headings(content: str, max_depth: int = 3) -> list[dict[str, Any]]:
    """
    从 Markdown 内容中提取标题

    Args:
        content: Markdown 内容
        max_depth: 最大标题深度（1-6）

    Returns:
        标题列表
    """
    headings = []

    # 匹配 Markdown 标题
    pattern = r"^(#{1,6})\s+(.+)$"
    matches = re.finditer(pattern, content, re.MULTILINE)

    for match in matches:
        level = len(match.group(1))
        if level > max_depth:
            continue

        text = match.group(2).strip()

        # 移除 Markdown 格式
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # 粗体
        text = re.sub(r"\*(.+?)\*", r"\1", text)  # 斜体
        text = re.sub(r"`(.+?)`", r"\1", text)  # 代码
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # 链接

        # 生成 ID
        heading_id = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower())
        heading_id = re.sub(r"-+", "-", heading_id).strip("-")

        headings.append(
            {
                "id": heading_id,
                "text": text,
                "level": level,
            }
        )

    return headings


def build_toc_tree(headings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    构建目录树

    将扁平的标题列表转换为嵌套的树结构。

    Args:
        headings: 标题列表

    Returns:
        目录树
    """
    if not headings:
        return []

    root: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []

    for heading in headings:
        node = {
            "id": heading["id"],
            "text": heading["text"],
            "level": heading["level"],
            "children": [],
        }

        # 找到合适的父节点
        while stack and stack[-1]["level"] >= node["level"]:
            stack.pop()

        if stack:
            stack[-1]["children"].append(node)
        else:
            root.append(node)

        stack.append(node)

    return root


def generate_toc_html(items: list[dict[str, Any]], indent: int = 0) -> str:
    """
    生成目录 HTML

    Args:
        items: 目录项列表
        indent: 缩进级别

    Returns:
        HTML 字符串
    """
    if not items:
        return ""

    html_parts = []
    prefix = "  " * indent

    html_parts.append(f'{prefix}<ul class="toc-list">')

    for item in items:
        # XSS 防护：标题文本来自用户 Markdown，必须转义后再入 HTML
        # （id 由 extract_headings 归一化为 [\w\u4e00-\u9fff-]，本身安全，但仍统一转义）
        item_id = escape(str(item["id"]), quote=True)
        item_text = escape(str(item["text"]), quote=True)
        html_parts.append(f'{prefix}  <li class="toc-item toc-level-{item["level"]}">')
        html_parts.append(f'{prefix}    <a href="#{item_id}" class="toc-link">{item_text}</a>')

        if item.get("children"):
            html_parts.append(generate_toc_html(item["children"], indent + 2))

        html_parts.append(f"{prefix}  </li>")

    html_parts.append(f"{prefix}</ul>")

    return "\n".join(html_parts)


@router.post(
    "/generate",
    response_model=TOCResponse,
    summary="生成目录",
    description=(
        "从 Markdown 内容中生成文章目录。公开接口、无需鉴权。"
        "提取 ATX 标题（max_depth 控制保留层级）后按层级嵌套成树，"
        "并渲染成 toc-list 结构的无序列表 HTML；标题文本与锚点 id 均已 HTML 转义。"
        "无命中标题时 items 为空数组、html 为空字符串。"
    ),
)
async def generate_toc(
    request: TOCRequest = Body(...),
):
    """
    生成文章目录

    从 Markdown 内容中提取标题，生成目录树和 HTML。
    """
    # 提取标题
    headings = extract_headings(request.content, request.max_depth)

    # 构建目录树
    toc_tree = build_toc_tree(headings)

    # 生成 HTML
    html = generate_toc_html(toc_tree)

    return TOCResponse(
        items=[TOCItem(**item) for item in toc_tree],
        html=html,
    )


@router.post(
    "/extract",
    summary="提取标题",
    description=(
        "从 Markdown 内容中提取所有标题。公开接口、无需鉴权，纯文本解析不落库。"
        "只认 ATX 形式（行首 1–6 个 # 加空格），max_depth 指定保留的最大层级（更深的标题整条丢弃）。"
        "返回的是按文中顺序排列的扁平列表，不构建树结构（要树请用本模块的目录生成接口）。"
    ),
    responses={200: {"model": TOCExtractResponse}},
)
async def extract_toc(
    content: str = Body(..., embed=True),
    max_depth: int = Body(3, embed=True),
):
    """
    提取标题

    返回扁平的标题列表，不构建树结构。
    """
    headings = extract_headings(content, max_depth)

    return {
        "headings": headings,
        "count": len(headings),
    }


@router.post(
    "/add-ids",
    summary="添加标题 ID",
    description=(
        "为 Markdown 内容中的标题添加 ID 属性。公开接口、无需鉴权。"
        "逐行匹配 ATX 标题并改写为带 id 的原生 HTML 标题标签，锚点 id 的推导规则与标题提取接口一致，"
        "id 与文本都做 HTML 转义以防注入；非标题行与 max_depth 无关（本接口不截断层级）。"
    ),
    responses={200: {"model": TOCAddIdsResponse}},
)
async def add_heading_ids(
    content: str = Body(..., embed=True),
):
    """
    添加标题 ID

    将 Markdown 标题转换为带 ID 的格式，用于锚点跳转。
    """

    def add_id(match: re.Match) -> str:
        level = len(match.group(1))
        text = match.group(2).strip()

        # 生成 ID
        heading_id = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower())
        heading_id = re.sub(r"-+", "-", heading_id).strip("-")

        # XSS 防护：标题文本转义后再入 HTML
        return (
            f'<h{level} id="{escape(heading_id, quote=True)}">{escape(text, quote=True)}</h{level}>'
        )

    # 替换标题
    pattern = r"^(#{1,6})\s+(.+)$"
    result = re.sub(pattern, add_id, content, flags=re.MULTILINE)

    return {"content": result}
