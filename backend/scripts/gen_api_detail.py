"""
生成 `backend/docs/api_endpoints.md` —— **逐接口的完整字段级契约**。

动机：`api_reference.md` 的自动区块只是「方法 / 路径 / 摘要」三列索引，另有手写章节
只覆盖了少数重点接口。前端要真正对接一个接口时，仍然得回到 `/docs` 或读 Python 代码
才能知道「query 参数叫什么、哪个必填、body 里嵌套对象长什么样、401 之外还会吐什么」。

本脚本把运行时 ``app.openapi()`` 当作唯一事实来源，为每个操作输出：

- 路径与 HTTP 方法、鉴权要求
- 入参表（query / path / header / cookie + request body 字段）：类型、是否必填、默认值、说明
- 出参表：成功响应的字段树（``$ref`` 自动解引用，嵌套展开 2 层）
- 错误码表：该接口显式声明的响应 + 全局通用码，语义码清单指向 ``error_codes.md``
- 请求 / 响应示例（由 schema 推导，含枚举首值与数组元素结构）

用法::

    uv run python -m backend.scripts.gen_api_detail --write   # 写回文档
    uv run python -m backend.scripts.gen_api_detail --print   # 打印到 stdout

约束：
- 输出必须完全确定（不写时间戳、dict 遍历按名字排序），否则无法做逐字比对。
- 插件路由（tag 形如 ``Plugin:`` / ``Plugin-Public:``）不进文档：它们只在插件启用后
  存在，写进静态文档会随本地插件开关漂移（与 gen_api_index.py 同一口径）。
- 文档体积随接口数线性增长，描述文字超长时截断并提示去看 ``/docs``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "backend" / "docs" / "api_endpoints.md"

HEADER = """<!-- 本文件由 backend/scripts/gen_api_detail.py 生成，请勿手改 -->
"""

METHOD_ORDER = ("get", "post", "put", "patch", "delete")
HTTP_METHODS = frozenset(METHOD_ORDER)

# schema 递归展开的最大深度：再深下去字段数指数增长，收益低于噪音
MAX_DEPTH = 2
# 单张字段表的最大行数，超出用「… 其余 N 个字段见 /docs」收尾
MAX_ROWS = 40
# 单个描述的最大字符数（描述是开发者手写的长文，全量塞进表格会让文档不可读）
DESC_LIMIT = 320

# 全局通用状态码：main.py 的 exception handler 会对任意接口产出这些，
# 不需要每个接口重复写满，统一放文档头部，接口内只列**自定义**响应。
COMMON_STATUS_TEXT = {
    "400": "请求参数错误（`BAD_REQUEST`）",
    "401": "未登录或令牌失效（`UNAUTHORIZED`）——前端应触发 refresh 或跳登录",
    "403": "已登录但权限不足（`FORBIDDEN`）",
    "404": "资源不存在或不可见（`NOT_FOUND`）",
    "409": "资源冲突（`CONFLICT`，如 slug 已存在）",
    "413": "请求体过大（`PAYLOAD_TOO_LARGE`）",
    "422": "参数校验失败（`VALIDATION_ERROR`，`errors[]` 含字段级明细）",
    "423": "账户已锁定（`ACCOUNT_LOCKED`）",
    "429": "触发限流（`RATE_LIMIT_EXCEEDED`，响应头带 `X-RateLimit-*` / `Retry-After`）",
    "500": "服务端内部错误（`INTERNAL_SERVER_ERROR`）",
    "503": "服务不可用（`SERVICE_UNAVAILABLE` / OOBE 未完成时的 `OOBE_REQUIRED`）",
}


def _is_plugin_tag(tag: str) -> bool:
    """插件路由 tag 判定（见 core/routing_registry.py 的 _mount_router）。"""
    return tag.startswith("Plugin:") or tag.startswith("Plugin-Public:")


def _esc(text: str) -> str:
    """单元格内转义：竖线会截断表格，换行会撑破表格行。"""
    out = str(text).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    return " ".join(out.split())


def _clip(text: str, limit: int = DESC_LIMIT) -> str:
    """截断长描述，避免单个接口的描述占掉半页。"""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " … （完整说明见 `/docs`）"


def _resolve(spec: dict[str, Any], node: Any) -> dict[str, Any]:
    """跟随 $ref 直到拿到真身（带环检测，防止自引用模型死循环）。"""
    seen: set[str] = set()
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if ref in seen:
            return {}
        seen.add(ref)
        parts = ref.split("/")
        cursor: Any = spec
        for part in parts[1:]:
            if not isinstance(cursor, dict):
                return {}
            cursor = cursor.get(part)
        node = cursor
    return node if isinstance(node, dict) else {}


def _type_name(spec: dict[str, Any], schema: dict[str, Any], nullable: bool = False) -> str:
    """把 OpenAPI schema 渲染成人类可读的类型串。"""
    if not schema:
        return "any"
    if "oneOf" in schema or "anyOf" in schema:
        parts = [
            _type_name(spec, _resolve(spec, s))
            for s in (schema.get("oneOf") or schema.get("anyOf") or [])
        ]
        parts = [p for p in parts if p]
        base = " | ".join(dict.fromkeys(parts)) or "any"
        return f"{base} | null" if nullable else base
    if "allOf" in schema:
        names = []
        for sub in schema["allOf"]:
            resolved = _resolve(spec, sub)
            ref_name = _ref_name(sub)
            names.append(ref_name or _type_name(spec, resolved))
        return " & ".join(n for n in names if n) or "object"
    node_type = schema.get("type")
    if node_type == "array":
        items = _resolve(spec, schema.get("items"))
        inner = _type_name(spec, items) if items else "any"
        return f"{inner}[]"
    if not node_type:
        # 无 type 且无谓词的空 schema = 任意 JSON
        return "any" if not schema else "object"
    if node_type == "string" and schema.get("enum"):
        vals = ", ".join(f"`{v}`" for v in schema["enum"][:6])
        tail = " …" if len(schema["enum"]) > 6 else ""
        return f"enum({vals}{tail})"
    if node_type == "object":
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict) and extra:
            return f"object<string, {_type_name(spec, _resolve(spec, extra))}>"
        return "object"
    # integer/number/boolean/string
    return str(node_type)


def _ref_name(node: Any) -> str | None:
    """从 $ref 里取模型短名，用于把 User/Post 这类模型标出来。"""
    if isinstance(node, dict) and "$ref" in node:
        return str(node["$ref"]).rsplit("/", 1)[-1]
    return None


def _flatten(
    spec: dict[str, Any],
    schema: dict[str, Any],
    prefix: str = "",
    depth: int = 0,
    required: set[str] | None = None,
) -> list[tuple[str, str, str, str]]:
    """把 schema 摊平成表格行 `(字段, 类型, 必填, 说明)`。"""
    required = required or set()
    schema = _resolve(spec, schema)
    rows: list[tuple[str, str, str, str]] = []

    if not schema or not schema.get("properties"):
        # 纯 array：给一行占位，说明元素类型即可
        if schema.get("type") == "array":
            return [
                (
                    prefix or "(根)",
                    _type_name(spec, schema),
                    "—",
                    _clip(schema.get("description", ""), 120),
                )
            ]
        return rows

    for name in sorted(schema["properties"]):
        raw = schema["properties"][name]
        resolved = _resolve(spec, raw)
        nullable = bool(resolved.get("nullable")) or bool(raw and raw.get("nullable"))
        type_str = _type_name(spec, resolved, nullable)
        is_req = "是" if name in required else "否"
        desc = resolved.get("description") or raw.get("description") or ""
        path = f"{prefix}.{name}" if prefix else name
        rows.append((path, type_str, is_req, _clip(desc, 140)))

        children = resolved.get("properties")
        if children and depth + 1 < MAX_DEPTH:
            rows.extend(
                _flatten(
                    spec,
                    resolved,
                    prefix=path,
                    depth=depth + 1,
                    required=set(resolved.get("required") or []),
                )
            )
    return rows


def _example(spec: dict[str, Any], schema: dict[str, Any], depth: int = 0) -> Any:
    """由 schema 推导一个可读的示例值（不是随机数据，只取类型骨架 + 枚举首值）。"""
    if depth > 3:
        return "…"
    schema = _resolve(spec, schema)
    if not schema:
        return None
    if "default" in schema:
        return schema["default"]
    if schema.get("enum"):
        return schema["enum"][0]
    node_type = schema.get("type")
    if node_type == "object" or schema.get("properties"):
        props = schema.get("properties") or {}
        out: dict[str, Any] = {}
        for key in sorted(props):
            out[key] = _example(spec, props[key], depth + 1)
        return out
    if node_type == "array":
        items = _resolve(spec, schema.get("items"))
        return [_example(spec, items, depth + 1)] if items else []
    if node_type == "integer":
        return 0
    if node_type == "number":
        return 0.0
    if node_type == "boolean":
        return False
    return "string"


def _body_schema(
    spec: dict[str, Any], operation: dict[str, Any]
) -> tuple[str | None, dict[str, Any]]:
    """取 requestBody 的 JSON schema（只认 application/json）。"""
    body = _resolve(spec, operation.get("requestBody") or {})
    content = body.get("content") or {}
    media = content.get("application/json") or next(iter(content.values()), {}) if content else {}
    media = media or {}
    if isinstance(media, dict) and media.get("schema"):
        return _ref_name(media["schema"]), _resolve(spec, media["schema"])
    return None, {}


def _param_rows(
    spec: dict[str, Any], operation: dict[str, Any], path_item: dict[str, Any]
) -> list[tuple[str, str, str, str, str, str]]:
    """合并 path 级与 operation 级参数，返回 `(名称, 位置, 类型, 必填, 默认值, 说明)`。"""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for source in (path_item.get("parameters") or [], operation.get("parameters") or []):
        if not isinstance(source, dict):
            continue
        key = (source.get("name", ""), source.get("in", ""))
        merged[key] = source

    position_text = {"query": "query", "path": "path", "header": "header", "cookie": "cookie"}
    rows = []
    for name, where in sorted(merged):
        node = merged[(name, where)]
        schema = _resolve(spec, node.get("schema") or {})
        nullable = bool(schema.get("nullable"))
        type_str = _type_name(spec, schema, nullable)
        required = "是" if node.get("required") else "否"
        default = (
            node.get("schema", {}).get("default") if isinstance(node.get("schema"), dict) else None
        )
        default_text = json.dumps(default, ensure_ascii=False) if default is not None else "—"
        rows.append(
            (
                f"`{name}`",
                position_text.get(where, where),
                f"`{type_str}`",
                required,
                f"`{default_text}`",
                _clip(node.get("description") or schema.get("description") or "", 140),
            )
        )
    return rows


def _auth_text(operation: dict[str, Any], spec: dict[str, Any]) -> str:
    """鉴权要求：operation 上没写 security 就继承 spec 全局；空列表显式表示公开。"""
    security = operation.get("security")
    if security is None:
        security = spec.get("security")
    if not security:
        return "公开接口（无需鉴权）"
    schemes = sorted({name for item in security for name in item if isinstance(item, dict)})
    if not schemes:
        return "公开接口（无需鉴权）"
    return "需鉴权：" + "、".join(f"`{s}`" for s in schemes)


def _render_operation(
    spec: dict[str, Any],
    path: str,
    method: str,
    operation: dict[str, Any],
    path_item: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    summary = (operation.get("summary") or "").strip()
    lines.append(f"### `{method.upper()} {path}`")
    lines.append("")
    lines.append(f"- **摘要**：{summary or '—'}")
    lines.append(f"- **鉴权**：{_auth_text(operation, spec)}")

    deprecated = operation.get("deprecated")
    if deprecated:
        lines.append("- **⚠️ 已废弃**：请迁移到文档推荐的新接口")

    description = (operation.get("description") or "").replace(summary, "", 1).strip()
    if description:
        lines.append("")
        lines.append(_clip(description, 900))

    # ── 入参 ──
    lines.append("")
    lines.append("**入参**")
    lines.append("")
    param_rows = _param_rows(spec, operation, path_item)
    if param_rows:
        lines.append("| 名称 | 位置 | 类型 | 必填 | 默认值 | 说明 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in param_rows[:MAX_ROWS]:
            lines.append("| " + " | ".join(row) + " |")
        if len(param_rows) > MAX_ROWS:
            lines.append(f"| … 其余 {len(param_rows) - MAX_ROWS} 个参数 | | | | | 见 `/docs` |")
    else:
        lines.append("_无路径 / query 参数_")

    model_name, body_schema = _body_schema(spec, operation)
    if body_schema:
        lines.append("")
        lines.append(
            f"**请求体**（`application/json`{f'，模型 `{model_name}`' if model_name else ''}）"
        )
        lines.append("")
        body_rows = _flatten(spec, body_schema, required=set(body_schema.get("required") or []))
        if body_rows:
            lines.append("| 字段 | 类型 | 必填 | 说明 |")
            lines.append("| --- | --- | --- | --- |")
            for row in body_rows[:MAX_ROWS]:
                lines.append("| " + " | ".join(_esc(x) for x in row) + " |")
            if len(body_rows) > MAX_ROWS:
                lines.append(f"| … 其余 {len(body_rows) - MAX_ROWS} 个字段 | | | 见 `/docs` |")
        if operation.get("requestBody", {}).get("required", True):
            example = _example(spec, body_schema)
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(example, ensure_ascii=False, indent=2))
            lines.append("```")

    # ── 出参 ──
    lines.append("")
    lines.append("**出参**")
    lines.append("")
    responses = operation.get("responses") or {}
    success_key = next((k for k in responses if k.startswith(("2",)) and k != "204"), None)
    if success_key and success_key != "204":
        media = (responses[success_key].get("content") or {}).get("application/json") or {}
        resp_schema = _resolve(spec, media.get("schema") or {})
        if resp_schema:
            model_name = _ref_name(media.get("schema")) or ""
            lines.append(f"`{success_key}`{f' · 模型 `{model_name}`' if model_name else ''}")
            lines.append("")
            out_rows = _flatten(spec, resp_schema, required=set(resp_schema.get("required") or []))
            if out_rows:
                lines.append("| 字段 | 类型 | 必填 | 说明 |")
                lines.append("| --- | --- | --- | --- |")
                for row in out_rows[:MAX_ROWS]:
                    lines.append("| " + " | ".join(_esc(x) for x in row) + " |")
                if len(out_rows) > MAX_ROWS:
                    lines.append(f"| … 其余 {len(out_rows) - MAX_ROWS} 个字段 | | | 见 `/docs` |")
                lines.append("")
                lines.append("响应示例：")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(_example(spec, resp_schema), ensure_ascii=False, indent=2))
            lines.append("```")
        else:
            lines.append(f"`{success_key}` · 无响应体（或响应类型未在 OpenAPI 中声明）")
    elif success_key == "204":
        lines.append("`204` · 无响应体")
    else:
        lines.append("_未在 OpenAPI 中声明成功响应_")

    # ── 错误码 ──
    custom = {k: v for k, v in responses.items() if not k.startswith("2")}
    lines.append("")
    lines.append("**错误码**")
    lines.append("")
    if custom:
        lines.append("| 状态码 | 说明 |")
        lines.append("| --- | --- |")
        for code in sorted(custom):
            desc = (custom[code].get("description") or "").strip() or "—"
            lines.append(f"| `{code}` | {_esc(_clip(desc, 160))} |")
    else:
        lines.append("_除下方“全局通用错误码”外，本接口未声明自定义错误响应_")

    lines.append("")
    return lines


def render_detail(spec: dict[str, Any]) -> str:
    """渲染整份逐接口契约文档。"""
    grouped: dict[str, list[tuple[str, str, str]]] = {}
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            tags = [t for t in operation.get("tags", []) if not _is_plugin_tag(t)]
            if not tags:
                continue  # 插件专属路由，跳过
            tag = tags[0]
            grouped.setdefault(tag, []).append((method, path, operation.get("operationId") or ""))

    declared = [
        t["name"]
        for t in spec.get("tags", [])
        if isinstance(t, dict) and t.get("name") and not _is_plugin_tag(t["name"])
    ]
    tags = [t for t in declared if t in grouped] + sorted(t for t in grouped if t not in declared)

    total_ops = sum(len(v) for v in grouped.values())
    tag_desc = {
        t["name"]: (t.get("description") or "")
        for t in spec.get("tags", [])
        if isinstance(t, dict) and t.get("name")
    }

    lines: list[str] = [
        "# Rosetta API 逐接口参考（自动生成）",
        "",
        "> 本文件由 `backend/scripts/gen_api_detail.py` 从运行时 `app.openapi()` 生成，**请勿手改**。",
        "> 接口有增删 → 重跑 `uv run python -m backend.scripts.gen_api_detail --write`。",
        "",
        f"共 **{total_ops} 个操作**，字段级契约以本文件为准；语义错误码清单见 [error_codes.md](./error_codes.md)，"
        "重点接口的背景与坑见 [api_reference.md](./api_reference.md)。",
        "",
        "## 通用约定",
        "",
        "### 鉴权",
        "",
        "受保护接口的请求头格式：",
        "",
        "```",
        "Authorization: Bearer <access_token>",
        "X-CSRF-Token: <csrf_token>   # 写接口需要，从 GET /api/csrf 获取",
        "```",
        "",
        "`access_token` 有效期 1 小时，过期用 `POST /api/users/refresh` 换新。",
        "",
        "### 响应包络",
        "",
        '成功：`{"success": true, "data": {...}, "message": "..."}`（部分接口直出裸 dict，见各接口出参表）',
        "",
        '失败：`{"success": false, "error_code": "语义码", "message": "人类可读说明", "errors": [{field, message, type}]?}`',
        "",
        "前端判定刷新/OOBE 跳转依赖 `error_code` 而非裸状态码，见 `main.py::_STATUS_ERROR_CODES`。",
        "",
        "### 全局通用错误码",
        "",
        "以下状态码由全局异常处理器产出，任何接口都可能返回，正文章节不再重复：",
        "",
        "| 状态码 | 说明 |",
        "| --- | --- |",
    ]
    for code in sorted(COMMON_STATUS_TEXT, key=int):
        lines.append(f"| `{code}` | {COMMON_STATUS_TEXT[code]} |")

    lines += [
        "",
        "完整语义错误码清单（含业务码）见 [error_codes.md](./error_codes.md)。",
        "",
        "---",
        "",
    ]

    for tag in tags:
        entries = sorted(grouped[tag], key=lambda o: (o[1], METHOD_ORDER.index(o[0])))
        lines.append(f"## {tag}（{len(entries)}）")
        lines.append("")
        if tag_desc.get(tag):
            lines.append(tag_desc[tag].strip())
            lines.append("")
        for method, path, _op_id in entries:
            operation = spec["paths"][path][method]
            lines += _render_operation(spec, path, method, operation, spec["paths"][path])
        lines.append("---")
        lines.append("")

    return HEADER + "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成逐接口 API 契约文档")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="写回 backend/docs/api_endpoints.md")
    group.add_argument("--print", dest="print_only", action="store_true", help="打印到 stdout")
    args = parser.parse_args(argv)

    # 延迟导入：--help 不必付出加载整个 FastAPI 应用的成本
    from backend.main import app

    body = render_detail(app.openapi())

    if args.print_only:
        sys.stdout.write(body)
        return 0

    DOC_PATH.write_text(body, encoding="utf-8")
    rel = DOC_PATH.relative_to(REPO_ROOT)
    sys.stdout.write(
        f"已写入 {rel}（{len(body.encode('utf-8')) / 1024:.1f} KB，{body.count(chr(10)) + 1} 行）\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
