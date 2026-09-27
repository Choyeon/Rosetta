"""
生成 `backend/docs/api_reference.md` 的「端点总索引」区块。

动机：手写文档只覆盖了 355 个 OpenAPI 操作里的 97 个（27%），剩下 260 个只能去
读代码或开 `/docs`；而"文档列了已删除端点"这类漂移此前无人发现（`/api/admin/
view-trends`、`/api/admin/category-stats` 在代码里早已移除，文档却留着）。
本脚本把**运行时 spec** 当作唯一事实来源重新生成索引，配合
`tests/test_docs_api_index_sync.py` 做逐字比对，改接口不改文档会直接红。

用法::

    uv run python -m backend.scripts.gen_api_index --write   # 写回文档
    uv run python -m backend.scripts.gen_api_index --check   # 只检查漂移（CI 用）

约束：
- 插件路由（tag 形如 `Plugin: <slug>` / `Plugin-Public: <slug>`）**不进索引**。
  它们只有在对应插件启用后才存在，索引若包含就会随本地插件开关漂移。
- 输出必须完全确定（不写时间戳），否则逐字比对没有意义。
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "backend" / "docs" / "api_reference.md"

BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED:ENDPOINT_INDEX 由 backend/scripts/gen_api_index.py 生成，请勿手改 -->"  # noqa: E501
END_MARKER = "<!-- END AUTO-GENERATED:ENDPOINT_INDEX -->"

METHOD_ORDER = ("get", "post", "put", "patch", "delete")
HTTP_METHODS = set(METHOD_ORDER)


def _is_plugin_tag(tag: str) -> bool:
    """插件路由的 tag 前缀判定（见 core/routing_registry.py 的 _mount_router）。"""
    return tag.startswith("Plugin:") or tag.startswith("Plugin-Public:")


def collect_operations(spec: dict[str, Any]) -> dict[str, list[tuple[str, str, str]]]:
    """按 tag 分组收集 `(METHOD, path, summary)`，剔除插件路由。"""
    grouped: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for path, operations in spec.get("paths", {}).items():
        for method, operation in operations.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            tags = [t for t in operation.get("tags", []) if not _is_plugin_tag(t)]
            tag = tags[0] if tags else "未标签"
            summary = (operation.get("summary") or "").strip() or "—"
            grouped[tag].append((method.upper(), path, summary))
    return grouped


def _ordered_tags(spec: dict[str, Any], grouped: dict[str, list[Any]]) -> list[str]:
    """先按 spec 的 tags 元数据顺序（= 文档阅读顺序），补上元数据里没声明的 tag。"""
    declared = [
        t["name"]
        for t in spec.get("tags", [])
        if isinstance(t, dict) and t.get("name") and not _is_plugin_tag(t["name"])
    ]
    extra = sorted(name for name in grouped if name not in declared)
    return [name for name in declared if name in grouped] + extra


def render_index(spec: dict[str, Any]) -> str:
    """渲染索引区块（不含标记本身）。"""
    grouped = collect_operations(spec)
    total_ops = sum(len(v) for v in grouped.values())
    total_paths = len(spec.get("paths", {}))

    lines: list[str] = [
        "## 端点总索引（自动生成）",
        "",
        f"本区块由 `backend/scripts/gen_api_index.py` 从运行时 `app.openapi()` 生成，"
        f"共 **{total_ops} 个操作 / {total_paths} 条路径**。",
        "上面各章节是手写的重点说明（请求体、响应口径、坑），本区块是完整清单；"
        "两者互补，字段级契约以 `/openapi.json` 为准。",
        "",
        "- 插件自带的路由（tag 为 `Plugin:*` / `Plugin-Public:*`）不在本清单内："
        "它们只在对应插件启用后存在，需要实时清单就看 `/docs` 或 `/openapi.json`。",
        "- 改动接口后请跑 `uv run python -m backend.scripts.gen_api_index --write`，"
        "否则 `tests/test_docs_api_index_sync.py` 会失败。",
        "",
    ]
    for tag in _ordered_tags(spec, grouped):
        ops = sorted(grouped[tag], key=lambda o: (o[1], METHOD_ORDER.index(o[0].lower())))
        lines += [f"### {tag}（{len(ops)}）", "", "| 方法 | 路径 | 摘要 |", "| --- | --- | --- |"]
        for method, path, summary in ops:
            # 摘要里出现 `|` 会截断表格，转义即可；反引号保留原样。
            safe = summary.replace("|", "\\|")
            lines.append(f"| `{method}` | `{path}` | {safe} |")
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def splice(doc: str, body: str) -> str:
    """把 body 写进文档的标记区块之间；标记缺失视为错误（避免静默追加）。"""
    start = doc.find(BEGIN_MARKER)
    end = doc.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise SystemExit(
            f"文档缺少自动生成标记，请手工补上：\n{BEGIN_MARKER}\n{END_MARKER}\n位置：{DOC_PATH}"
        )
    head = doc[: start + len(BEGIN_MARKER)]
    tail = doc[end:]
    return f"{head}\n\n{body}\n\n{tail}"


def build(doc: str, spec: dict[str, Any]) -> str:
    return splice(doc, render_index(spec))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 api_reference.md 端点总索引")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="写回文档")
    group.add_argument("--check", action="store_true", help="检查漂移，漂移时退出码 1")
    group.add_argument("--print", dest="print_only", action="store_true", help="只打印区块")
    args = parser.parse_args(argv)

    # 延迟导入：--help 不必付出加载整个 FastAPI 应用的成本。
    from backend.main import app

    doc = DOC_PATH.read_text(encoding="utf-8")
    new_doc = build(doc, app.openapi())

    if args.print_only:
        sys.stdout.write(
            new_doc[new_doc.find(BEGIN_MARKER) + len(BEGIN_MARKER) : new_doc.find(END_MARKER)]
        )
        return 0
    if args.check:
        if new_doc != doc:
            sys.stderr.write(
                "api_reference.md 的端点索引与 OpenAPI spec 不一致，"
                "请执行：uv run python -m backend.scripts.gen_api_index --write\n"
            )
            return 1
        sys.stdout.write("端点索引与 OpenAPI spec 一致\n")
        return 0

    if new_doc != doc:
        DOC_PATH.write_text(new_doc, encoding="utf-8")
        sys.stdout.write(f"已写回 {DOC_PATH.relative_to(REPO_ROOT)}\n")
    else:
        sys.stdout.write("内容未变化\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
