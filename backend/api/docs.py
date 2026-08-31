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

import re
from pathlib import Path
from typing import Final

from fastapi import APIRouter, HTTPException, Path as PathParam, status

from backend.core.paths import BASE_DIR

router = APIRouter(tags=["文档"])

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
        "description": "插件结构、register(ctx) 11 个能力、五类扩展点与安全清单。",
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
            f"- **[{row['title']}](/admin/docs/{row['slug']})**  "
            f"<br/>{row['description']}"
        )
    lines.append("")
    lines.append("## 🧩 扩展点速查")
    lines.append("")
    lines.append(
        "| 类型 | 说明 | 参考章节 |\n"
        "| --- | --- | --- |\n"
        "| Action 钩子 | 在某个执行点触发副作用，不返回值 | 插件教程 §3.1 |\n"
        "| Filter 过滤器 | 对某个值做变换并返回 | 插件教程 §3.2 |\n"
        "| Shortcode 短代码 | 在文章内容中用 `[tag]` 语法嵌入组件 | 插件教程 §3.3 |\n"
        "| 独立后台页 | 插件声明 `/api/admin/plugins/<slug>/**` 路由 | 插件教程 §3.4 |\n"
        "| 独立前台路由 | 插件声明 `/api/plugins/<slug>/**` 路由 | 插件教程 §3.5 |\n"
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
# 公开接口
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/docs/list",
    summary="列出所有开发文档条目",
    description="返回菜单排序、分类与描述；用于侧边栏 / TOC 渲染。",
)
async def list_docs():
    items = []
    for row in sorted(DOC_CATALOG, key=lambda r: r["order"]):
        # 检查磁盘存在性（除 index —— 它允许后端动态合成）
        exists = True
        if row["slug"] != "index":
            exists = (DOCS_DIR / f"{row['slug']}.md").exists()
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
            "docs_dir": str(DOCS_DIR),
        },
    }


@router.get(
    "/docs/{slug}",
    summary="读取单篇文档",
    description="返回 {markdown, title}；markdown 为原始 Markdown 文本，"
    "由前端 marked + highlight.js 渲染为 HTML。",
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
    markdown, title = _read_markdown(slug)
    return {
        "success": True,
        "data": {
            "slug": slug,
            "title": title,
            "markdown": markdown,
            "language": "zh-CN",
        },
    }
