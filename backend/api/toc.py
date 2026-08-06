"""
文章目录（TOC）生成 API

从 Markdown 内容中提取标题生成目录。
"""

import re
from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel

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
        html_parts.append(f'{prefix}  <li class="toc-item toc-level-{item["level"]}">')
        html_parts.append(
            f'{prefix}    <a href="#{item["id"]}" class="toc-link">{item["text"]}</a>'
        )

        if item.get("children"):
            html_parts.append(generate_toc_html(item["children"], indent + 2))

        html_parts.append(f"{prefix}  </li>")

    html_parts.append(f"{prefix}</ul>")

    return "\n".join(html_parts)


@router.post(
    "/generate",
    response_model=TOCResponse,
    summary="生成目录",
    description="从 Markdown 内容中生成文章目录。",
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
    description="从 Markdown 内容中提取所有标题。",
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
    description="为 Markdown 内容中的标题添加 ID 属性。",
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

        return f'<h{level} id="{heading_id}">{text}</h{level}>'

    # 替换标题
    pattern = r"^(#{1,6})\s+(.+)$"
    result = re.sub(pattern, add_id, content, flags=re.MULTILINE)

    return {"content": result}
