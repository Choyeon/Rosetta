"""
文档公开 API：开发文档 Markdown 的列表与单篇读取。

- GET /api/docs/list             ：返回所有文档条目（slug / title / order / category）
- GET /api/docs/{slug}           ：返回 {markdown, title}，其中 markdown 为原始文本
                                  （由前端 Marked + highlight.js 渲染，或在必要时回退为
                                  纯 marked 渲染避免依赖缺失）

文档来源：仓库根目录的 docs/plugins-themes/zh-CN/*.md，附带一个内置的
「开发文档首页 index.md」 —— 如果磁盘上不存在该首页，就由后端动态生成目录卡片，
保证 /admin/docs/index 永远能打开。
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Final

from fastapi import APIRouter, HTTPException, status
from fastapi import Path as PathParam
from pydantic import BaseModel, Field

from backend.core.paths import BASE_DIR

router = APIRouter(tags=["开发文档"])

# ── 文档根目录：docs/plugins-themes/zh-CN ─────────────────────────────
DOCS_DIR: Final[Path] = BASE_DIR / "docs" / "plugins-themes" / "zh-CN"

# slug 到 (标题, 顺序, 分类) 的静态目录 —— 保证菜单顺序稳定，且不依赖 Markdown 内部标题。
DOC_CATALOG: Final[list[dict]] = [
    {
        "slug": "index",
        "title": "开发文档首页",
        "category": "概览",
        "order": 0,
        "description": "插件与主题开发文档总览与快速入口。",
    },
    {
        "slug": "rest-api",
        "title": "REST API 参考",
        "category": "接口",
        "order": 10,
        "description": "插件、主题、Mods、Shortcodes、Marketplace 的完整接口清单与错误码。",
    },
    {
        "slug": "theme-tutorial",
        "title": "主题开发教程",
        "category": "教程",
        "order": 20,
        "description": "rosetta-theme.json 清单、mods_schema、CSS 前缀规范与完整示例。",
    },
    {
        "slug": "plugin-tutorial",
        "title": "插件开发教程",
        "category": "教程",
        "order": 30,
        "description": "插件结构、清单、register(ctx) 10 个能力、完整钩子目录、生命周期与安全清单。",
    },
]

_KNOWN_SLUGS: Final[set[str]] = {row["slug"] for row in DOC_CATALOG}

_SLUG_RE = re.compile(r"^[a-z][a-z0-9\-]{1,63}$")


def _title_from_markdown(text: str, fallback: str) -> str:
    """尝试提取首个 H1 标题作为文档标题；否则用 fallback。"""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip().split("\n")[0]
    return fallback


def _build_index_markdown() -> str:
    """当 docs/plugins-themes/zh-CN/index.md 不存在时，动态合成目录页。"""
    lines: list[str] = []
    lines.append("# Rosetta 插件与主题 · 开发文档")
    lines.append("")
    lines.append("> 版本：1.0.0 · 语言：zh-CN")
    lines.append("")
    lines.append(
        "本文档集合覆盖 Rosetta 平台为插件/主题作者开放的所有能力："
        "清单规范、REST API、五类扩展点、安全提示与完整示例。"
    )
    lines.append("")
    lines.append("## 📚 文档目录")
    lines.append("")
    for row in sorted(DOC_CATALOG, key=lambda r: r["order"]):
        if row["slug"] == "index":
            continue
        lines.append(
            f"- **[{row['title']}](/admin/docs/{row['slug']})**  <br/>{row['description']}"
        )
    lines.append("")
    lines.append("## 🧩 扩展点速查")
    lines.append("")
    lines.append(
        "| 类型 | 说明 | 参考章节 |\n"
        "| --- | --- | --- |\n"
        "| Action 钩子 | 在某个执行点触发副作用，不返回值 | 插件教程 §6.1 |\n"
        "| Filter 过滤器 | 对某个值做变换并返回 | 插件教程 §6.2 |\n"
        "| Shortcode 短代码 | 在文章内容中用 `[tag]` 语法嵌入组件 | 插件教程 §6.3 |\n"
        "| 独立路由 | 插件声明 admin/public APIRouter 与自动鉴权 | 插件教程 §6.4 |\n"
        "| 后台菜单 | 插件在 Admin 侧边栏注册菜单项 | 插件教程 §6.5 |\n"
        "| 主题 Mods | JSON Schema 驱动的 Customizer 动态表单 | 主题教程 §2.1 |\n"
    )
    lines.append("")
    lines.append("## 🔌 支持的安装方式")
    lines.append("")
    lines.append(
        "插件与主题均支持三种安装来源：**本地目录扫描**、**ZIP 上传**、**官方市场远程安装**。"
        "详细参数与 curl 示例见《REST API 参考》第 2 / 3 节。"
    )
    lines.append("")
    lines.append("## 🚧 帮助与反馈")
    lines.append("")
    lines.append(
        "如在开发过程中遇到问题，可先查阅《REST API 参考》末尾的错误码表；"
        "仍无法解决时请在 Rosetta 的 GitHub 仓库提交 Issue，并附上 `rosetta.json` 中"
        "的 `environment=development` 日志。"
    )
    lines.append("")
    return "\n".join(lines)


def _read_markdown(slug: str) -> tuple[str, str]:
    """读取 markdown 文本并提取标题；slug 必须已在 _KNOWN_SLUGS 中。

    返回：(markdown, title)
    """
    catalog_row = next((r for r in DOC_CATALOG if r["slug"] == slug), None)
    fallback_title = catalog_row["title"] if catalog_row else slug

    if slug == "index":
        index_path = DOCS_DIR / "index.md"
        if index_path.exists():
            text = index_path.read_text(encoding="utf-8")
            return text, _title_from_markdown(text, fallback_title)
        text = _build_index_markdown()
        return text, _title_from_markdown(text, fallback_title)

    path = DOCS_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档不存在: {slug}",
        )
    # 防御性路径检查：防止 ../ 越权（实际 slug 已由正则限制，但保留一层保险）
    try:
        path_resolved = path.resolve()
        docs_resolved = DOCS_DIR.resolve()
        path_resolved.relative_to(docs_resolved)
    except ValueError as exc:  # pragma: no cover - 基本不会触发
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法文档路径",
        ) from exc

    text = path.read_text(encoding="utf-8")
    return text, _title_from_markdown(text, fallback_title)


# ═══════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════


class DocCatalogItemDoc(BaseModel):
    """目录接口返回的单条文档条目（来自静态 DOC_CATALOG + 磁盘存在性探测）。"""

    slug: str = Field(..., description="文档 slug，用于拼 /docs/{slug} 详情请求")
    title: str = Field(..., description="目录里登记的中文标题（不读 Markdown 内部标题）")
    category: str = Field(..., description="分类名（概览 / 接口 / 教程…），侧边栏分组用")
    order: int = Field(..., description="菜单排序权重，越小越靠前")
    description: str = Field("", description="条目描述；目录行未写 description 时是空串")
    available: bool = Field(
        ..., description="磁盘上对应 <slug>.md 是否存在；index 恒为 true（缺文件时动态合成）"
    )


class DocListDataDoc(BaseModel):
    """目录接口的 data 载荷。"""

    items: list[DocCatalogItemDoc] = Field(default_factory=list, description="按 order 升序的条目")
    language: str = Field("zh-CN", description="文档语言标识（当前内建目录仅中文，固定值）")


class DocListResponse(BaseModel):
    """``GET /api/docs/list`` 的响应体（success/data 信封）。"""

    success: bool = Field(True, description="固定为 true（本接口成功路径无分支）")
    data: DocListDataDoc = Field(..., description="目录数据；不回传 DOCS_DIR 磁盘绝对路径")


class DocDetailDataDoc(BaseModel):
    """单篇文档接口的 data 载荷。"""

    slug: str = Field(..., description="请求的文档 slug")
    title: str = Field(..., description="优先取 Markdown 首个 H1，缺省回退目录标题/slug")
    markdown: str = Field(..., description="原始 Markdown 全文，由前端 marked + highlight.js 渲染")
    language: str = Field("zh-CN", description="文档语言标识（固定值）")


class DocDetailResponse(BaseModel):
    """``GET /api/docs/{slug}`` 的响应体（success/data 信封）。"""

    success: bool = Field(True, description="固定为 true（slug 未注册 / 文件缺失走 404 错误信封）")
    data: DocDetailDataDoc = Field(..., description="单篇文档数据")


# ═══════════════════════════════════════════════════════════════════════
# 公开接口
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/docs/list",
    summary="列出所有开发文档条目",
    description=(
        "返回菜单排序、分类与描述；用于侧边栏 / TOC 渲染。公开接口、无需鉴权。"
        "响应为 success/data 信封，data.items 按 order 升序，available 反映磁盘文件是否存在。"
    ),
    responses={200: {"model": DocListResponse}},
)
async def list_docs():
    items = []
    # 批量检查磁盘存在性（path.exists 为同步 I/O，放入线程池避免阻塞事件循环）
    slug_rows = sorted(DOC_CATALOG, key=lambda r: r["order"])
    non_index_slugs = [r["slug"] for r in slug_rows if r["slug"] != "index"]

    def _check_exists() -> set[str]:
        return {s for s in non_index_slugs if (DOCS_DIR / f"{s}.md").exists()}

    existing = await asyncio.to_thread(_check_exists) if non_index_slugs else set()

    for row in slug_rows:
        exists = row["slug"] == "index" or row["slug"] in existing
        items.append(
            {
                "slug": row["slug"],
                "title": row["title"],
                "category": row["category"],
                "order": row["order"],
                "description": row.get("description", ""),
                "available": exists,
            }
        )
    return {
        "success": True,
        "data": {
            "items": items,
            "language": "zh-CN",
            # 不回传 DOCS_DIR 绝对路径：这是未鉴权接口，磁盘路径属于内部实现细节
        },
    }


@router.get(
    "/docs/{slug}",
    summary="读取单篇文档",
    description="返回 {markdown, title}；markdown 为原始 Markdown 文本，"
    "由前端 marked + highlight.js 渲染为 HTML。"
    "响应为 success/data 信封（data 含 slug/title/markdown/language）；"
    "slug 未注册或磁盘文件缺失返回 404 错误信封。",
    responses={200: {"model": DocDetailResponse}},
)
async def get_doc(
    slug: str = PathParam(
        ...,
        pattern=r"^[a-z][a-z0-9\-]{1,63}$",
        description="文档 slug，例如 index / rest-api / theme-tutorial / plugin-tutorial",
    ),
):
    if slug not in _KNOWN_SLUGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 slug 未注册: {slug}",
        )
    # _read_markdown 内部调用 path.exists / path.read_text（同步 I/O），放入线程池
    markdown, title = await asyncio.to_thread(_read_markdown, slug)
    return {
        "success": True,
        "data": {
            "slug": slug,
            "title": title,
            "markdown": markdown,
            "language": "zh-CN",
        },
    }
