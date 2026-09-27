"""前后端路径协同门禁：前端字面量调用的 API 路径必须能被 OpenAPI 解析。

扫描 ``frontend/``（composables / pages / components / server / plugins / lib / stores）
中 ``useAPI / apiFetch / silentApiFetch / $fetch / $get / $post / $put / $patch / $del``
的**静态字符串**首参（``'...'`` / ``"..."`` / 以字面量开头的模板串），归一化后对照
``app.openapi()["paths"]``。任何调用打到不存在的 path/前缀即红。

归一化口径：
- ``${...}`` 与 ``{param}`` 统一压成 ``{}``（动态段占位）；
- 带模板的串要求**精确相等**（``/admin/x/${id}`` → ``/api/admin/x/{} == /api/admin/x/{entry_id}``）；
- 纯静态串允许作为已注册路径的前缀（覆盖整段被模板吃掉的前缀写法，如
  ``'/admin/plugins/' + slug``、``/admin/plugins/guestbook-rss`` 命中 ``/{slug}``）。

``/blog/posts/...`` 这类文档省略号写法（段含 ``.``）不是合法 slug，直接跳过。
"""

from __future__ import annotations

import re
from functools import lru_cache
from glob import glob
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

SCAN_SUBDIRS = ("composables", "pages", "components", "server", "plugins", "lib", "stores")

CALL_RE = re.compile(
    r"(?:useAPI|apiFetch|silentApiFetch|\$fetch|\$get|\$post|\$put|\$patch|\$del)"
    r"(?:<[^<>]*>)?\s*\(\s*"
    r"(?:'([^']*)'|\"([^\"]*)\"|`([^'`\"$]*)\$\{)",
)


def _collect_frontend_calls() -> set[tuple[str, str]]:
    """返回 {(路径字面量, 来源文件)}；只收以 / 开头且不含 ? 之前的查询串。"""
    found: set[tuple[str, str]] = set()
    for sub in SCAN_SUBDIRS:
        root = FRONTEND / sub
        if not root.is_dir():
            continue
        for f in root.rglob("*"):
            if not f.is_file() or f.suffix not in {".ts", ".vue", ".js"}:
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            for m in CALL_RE.finditer(src):
                literal = m.group(1) or m.group(2) or m.group(3)
                if literal and literal.startswith("/"):
                    found.add((literal, f.relative_to(FRONTEND).as_posix()))
    return found


def _normalize(u: str) -> str:
    path = u.split("?")[0]
    path = re.sub(r"\$\{[^}]*\}?", "{}", path)
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return re.sub(r"/+$", "", path)


@lru_cache(maxsize=1)
def _plugin_slugs() -> frozenset[str]:
    """磁盘上的已安装插件 slug 集合（backend/plugins/{slug}/rosetta-plugin.json）。"""
    return frozenset(
        Path(m).parent.name
        for m in glob(str(FRONTEND.parent / "backend" / "plugins" / "*" / "rosetta-plugin.json"))
    )


@lru_cache(maxsize=1)
def _spec_norms() -> frozenset[str]:
    from backend.main import app

    # 插件自注册路由（如 guestbook-rss 的 /api/admin/plugins/<slug>/settings）由
    # routing_registry 在 startup 挂载，静态导入的 app 不含它们；判定口径：把已装
    # 插件 slug 代入含 {} 的模板路径视为合法。
    norms = {re.sub(r"\{[^}]*\}", "{}", p) for p in app.openapi()["paths"]}
    subs = set(norms)
    for slug in _plugin_slugs():
        for tmpl in norms:
            if "{}" in tmpl and tmpl.replace("{}", slug, 1) != tmpl:
                subs.add(tmpl.replace("{}", slug))
    return frozenset(subs)


@pytest.mark.parametrize(
    ("literal", "origin"),
    sorted(_collect_frontend_calls(), key=lambda x: (x[1], x[0])),
)
def test_frontend_call_path_resolves_in_openapi(literal: str, origin: str) -> None:
    segs = literal.strip("/").split("/")
    if any("." in s for s in segs):  # 文档省略号 / 文件名注释，非 API 路径
        pytest.skip(f"非路径字面量: {literal}")
    norm = _normalize(literal)
    candidate = norm if norm.startswith("/api/") else f"/api{norm}"
    specs = _spec_norms()
    if candidate in specs:
        return
    # 动态串（含 {}）必须精确命中，防止拼错中间段
    if "{}" in candidate:
        assert candidate in specs, f"{origin}: 调用 {literal!r} 无法匹配任何 OpenAPI 路径"
    prefixes = (candidate + "/").replace("//", "/")
    assert any(sp.startswith(prefixes) or sp == candidate for sp in specs), (
        f"{origin}: 调用 {literal!r}（→ {candidate}）在 OpenAPI 中既非精确路径也非任何路径前缀"
    )


def test_scan_found_a_meaningful_number_of_calls() -> None:
    """守卫扫描本身：正则退化导致 0 命中时不许假通过。"""
    calls = _collect_frontend_calls()
    assert len(calls) >= 100, f"前端调用扫描异常（仅 {len(calls)} 条），检查 CALL_RE"
