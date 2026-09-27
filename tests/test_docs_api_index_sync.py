"""钉住 `api_reference.md` 的端点总索引与运行时 OpenAPI spec 一致。

三重保证：
1. 生成区块逐字等于脚本输出（改接口不改文档 → 红）；
2. spec 里每个非插件操作都出现在索引中（覆盖率 100%，杜绝"文档漏了新端点"）；
3. 两个已删除端点不得作为活文档行重新出现（历史漂移点）。

事实来源是 `app.openapi()`——不是 AST 扫 `app.routes`（本 FastAPI 版本把
`include_router()` 结果懒挂载成 `_IncludedRouter`，静态扫会假通过，见 AGENTS.md §7.4）。
"""

from __future__ import annotations

from backend.scripts.gen_api_index import (
    BEGIN_MARKER,
    DOC_PATH,
    END_MARKER,
    _is_plugin_tag,
    build,
    collect_operations,
)

# 代码里早已移除、旧文档却留着的幽灵端点。
_REMOVED_ENDPOINTS = ("/api/admin/view-trends", "/api/admin/category-stats")


def _spec() -> dict:
    from backend.main import app

    return app.openapi()


def test_doc_carries_auto_generated_markers():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert BEGIN_MARKER in doc, "api_reference.md 缺少 BEGIN 标记，生成脚本无处写回"
    assert END_MARKER in doc, "api_reference.md 缺少 END 标记，生成脚本无处写回"


def test_index_matches_spec_byte_for_byte():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert build(doc, _spec()) == doc, (
        "api_reference.md 的端点索引与 OpenAPI spec 不一致，请运行：uv run python -m backend.scripts.gen_api_index --write"
    )


def test_every_non_plugin_operation_is_documented():
    """覆盖率 100%：spec 里每个非插件 `METHOD path` 都必须在生成区块的表格里。"""
    spec = _spec()
    grouped = collect_operations(spec)
    expected = {(m, p) for ops in grouped.values() for m, p, _ in ops}

    doc = DOC_PATH.read_text(encoding="utf-8")
    block = doc[doc.find(BEGIN_MARKER) + len(BEGIN_MARKER) : doc.find(END_MARKER)]

    missing = {(m, p) for (m, p) in expected if f"| `{m}` | `{p}` |" not in block}
    assert not missing, f"以下端点未进入索引表：{sorted(missing)}"


def test_removed_endpoints_are_not_live_again():
    """两个已删除端点既不在 spec，也不作为活文档行（带方法|路径的行）出现。"""
    spec = _spec()
    paths = set(spec.get("paths", {}))
    for ep in _REMOVED_ENDPOINTS:
        assert ep not in paths, f"{ep} 不应重新出现在 OpenAPI spec 中"
        doc = DOC_PATH.read_text(encoding="utf-8")
        live_rows = [
            line
            for line in doc.splitlines()
            if ep in line
            and line.strip().startswith("|")
            and (
                "`GET" in line
                or "`POST" in line
                or "`PUT" in line
                or "`DELETE" in line
                or "`PATCH" in line
            )
        ]
        assert not live_rows, f"{ep} 作为活端点行重新出现在文档中：{live_rows}"


def test_plugin_tags_are_excluded_from_index():
    """插件路由（tag 前缀 Plugin:/Plugin-Public:）不进索引——否则随本地插件开关漂移。"""
    spec = _spec()
    grouped = collect_operations(spec)
    assert all(not _is_plugin_tag(tag) for tag in grouped), "插件 tag 不应出现在索引分组里"
