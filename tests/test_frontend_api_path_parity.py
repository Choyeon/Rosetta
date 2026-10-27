"""前后端路径协同门禁：前端字面量调用的 API 路径必须能被 OpenAPI 解析。

扫描 ``frontend/``（composables / pages / components / server / plugins / lib / stores）
中 ``useAPI / apiFetch / silentApiFetch / $fetch / $get / $post / $put / $patch / $del``
的**静态字符串**首参（``'...'`` / ``"..."`` / 以字面量开头的模板串），归一化后对照
``app.openapi()["paths"]``。任何调用打到不存在的 path/前缀即红。

归一化口径：
- ``${...}`` 与 ``{param}`` 统一压成 ``{}``（动态段占位）；
- 带模板的串要求**逐段命中**：段数相同，且每段相等或任一侧是动态段（任一侧 ``{}``）。
  ``/seo/open-graph/article/${id}`` 命不中 ``/api/seo/open-graph/{}/{}`` 的"精确相等"旧口径，
  但 ``article`` 只是 ``resource_type`` 的**取值**，路径本身确实注册了；反向的同一条也成立
  （``/admin/guestbook/${entryId}/${action}`` 的末段是 approve/reject/spam 里挑一个）。
  取值合法性是运行时的事，不是这张路径登记表的事。
  动态串**不接受前缀兜底**：``/admin/x/${id}`` 打向 ``/admin/x/{id}/settings`` 是真缺陷；
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
    r"(?:'([^']*)'|\"([^\"]*)\"|`([^`]*)`)",
)


def _collect_frontend_calls() -> set[tuple[str, str]]:
    """返回 {(路径字面量, 来源文件)}；只收以 / 开头且不含空白/查询串的单行路径字面量。"""
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
                # 模板串整段捕获后会带进多行文案/反引号内的注释；带空白的一律不是路径。
                if literal and literal.startswith("/") and not re.search(r"\s", literal):
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


def _matches_segment_wise(candidate: str, specs: frozenset[str]) -> bool:
    """逐段比对：段数相同，且每段要么相等、要么任一侧是动态段（``{}``）。

    双向通配是被 ``/admin/guestbook/${entryId}/${action}`` 这类写法逼出来的：末段是
    approve/reject/spam 三个**固定值**里挑一个，前端只能用变量拼。这里管的是"路径登记不登记"，
    不是"取值合不合法"——静态段拼错（``guestboook``、``comment`` 少个 s）照旧拦得住，
    段数对不上（漏了 ``/settings``）也照旧拦得住。
    """
    if candidate in specs:
        return True
    segs = candidate.strip("/").split("/")
    for sp in specs:
        sp_segs = sp.strip("/").split("/")
        if len(sp_segs) != len(segs):
            continue
        if all(c == s or c == "{}" or s == "{}" for c, s in zip(segs, sp_segs)):
            return True
    return False


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
    if "{}" in candidate:
        # 动态串只认逐段命中，不给前缀兜底——少写一段是缺陷，不是"前缀合法"。
        assert _matches_segment_wise(candidate, specs), (
            f"{origin}: 调用 {literal!r}（→ {candidate}）在 OpenAPI 中"
            f"没有任何段数一致且静态段逐段相等的路径"
        )
        return
    if candidate in specs:
        return
    prefixes = (candidate + "/").replace("//", "/")
    assert any(sp.startswith(prefixes) or sp == candidate for sp in specs), (
        f"{origin}: 调用 {literal!r}（→ {candidate}）在 OpenAPI 中既非精确路径也非任何路径前缀"
    )


def test_scan_found_a_meaningful_number_of_calls() -> None:
    """守卫扫描本身：正则退化导致 0 命中时不许假通过。"""
    calls = _collect_frontend_calls()
    assert len(calls) >= 100, f"前端调用扫描异常（仅 {len(calls)} 条），检查 CALL_RE"


def test_template_literals_are_captured_whole() -> None:
    """整段捕获守卫：截断回旧口径时这两条调用会重新变成假通过（末段静态值看不见）。"""
    calls = {lit for lit, _ in _collect_frontend_calls()}
    assert "/admin/guestbook/${entryId}/${action}" in calls
    assert "/seo/open-graph/article/${resourceId}" in calls


def test_segment_matcher_still_rejects_wrong_paths() -> None:
    """双向通配不许退化成"段数一致就放行"：拼错的静态段与漏掉的尾段仍必须判不成。"""
    specs = _spec_norms()
    dynamic = "/api/admin/guestbook/{}/{}"
    assert _matches_segment_wise(dynamic, specs), dynamic
    # 静态段拼错 / 少一段 / 多一段
    assert not _matches_segment_wise("/api/admin/guestboook/1/2", specs)
    assert not _matches_segment_wise("/api/admin/guestbook/comment/1", specs)
    assert not _matches_segment_wise("/api/admin/guestbook/1/2/settings", specs)
    assert not _matches_segment_wise("/api/seo/no-such-thing/1", specs)
