"""CSRF 这一层"到底挂在哪些口、为什么只挂这些"的集中守卫（批次 #46）。

起因是一次线上门禁的假 FAIL：chain121 的探针拿 `PUT /api/admin/series/{id}/toggle` 断言
"带站外 Origin 必须 403"，实测 200 就判红。看代码才把这件事说清楚——

1. `require_csrf` 是 **per-route 依赖**，本仓只挂在评论的创建与删除两条写口上；
   其余约 200 条写接口按站外 Origin 请求照样通过。
2. 这**不是漏洞**：本站登录态只在 `Authorization` 头里、`set_cookie` 全仓零命中，
   没有环境凭证就没有经典 CSRF——跨站页面既读不到 localStorage 里的 token，
   浏览器也不会替它带上这个头。
3. 真正危险的动作是"照探针的猜测去补线"：给所有 admin 写口挂上 Origin 白名单，
   等于让任何一处 CORS/csrf_origins 配置不齐都变成后台整片 403
   （2026 年评论 403 那次就是同源/白名单没对齐）。

所以这里守的是**口径本身**，不是重复那条"恶意 Origin 回 403"的功能断言
（已有 `test_comment_author_delete.py` / `test_api_security_hardening.py` 各测一遍）：
挂在哪儿、前提还成不成立、文档有没有又开始讲一个不存在的 `GET /api/csrf`。
"""

import re
from pathlib import Path

from httpx import AsyncClient

API_DIR = Path(__file__).resolve().parent.parent / "backend" / "api"
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
DOCS_PATH = BACKEND_DIR / "docs" / "api_endpoints.md"
GEN_PATH = BACKEND_DIR / "scripts" / "gen_api_detail.py"

# 依赖挂载点的唯一清单：改动必须是有意的，并同时更新这里的名字
WIRED_ROUTES = {
    ("backend/api/comments.py", "create_comment"),
    ("backend/api/comments.py", "delete_own_comment"),
}


def _routed_functions_with_csrf() -> set[tuple[str, str]]:
    """扫描 `@router.<verb>(...)` 装饰器块里的 `Depends(require_csrf)`，收集 (文件, 函数名)。

    判"装饰器参数里有"而不是"整个文件里出现过 require_csrf"：后者会把导入、注释、
    以及哪天有人写下一个没人用的 `RequireCSRF` 别名都算成挂载点。
    """
    found: set[tuple[str, str]] = set()
    for path in sorted(API_DIR.rglob("*.py")):
        src = path.read_text(encoding="utf-8")
        rel = f"backend/api/{path.name}"
        for block in re.finditer(r"@router\.\w+\((.*?)\)\n(?=\s*(?:async )?def )", src, re.S):
            if "require_csrf" not in block.group(1):
                continue
            tail = src[block.end() :]
            name = re.match(r"\s*(?:async )?def (\w+)", tail)
            if name:
                found.add((rel, name.group(1)))
    return found


class TestWiredSetIsDeclared:
    def test_csrf_dependency_is_wired_exactly_where_documented(self):
        wired = _routed_functions_with_csrf()
        assert wired == WIRED_ROUTES, (
            f"CSRF 挂载点与清单不一致：多={wired - WIRED_ROUTES} 少={WIRED_ROUTES - wired}"
        )

    def test_no_dead_csrf_alias_came_back(self):
        """`RequireCSRF` 别名曾零消费方挂在 deps 里——留着它就是"到处都防 CSRF"的错觉来源。"""
        deps = (BACKEND_DIR / "core" / "deps.py").read_text(encoding="utf-8")
        assert "RequireCSRF" not in deps
        assert "require_csrf" not in deps

    def test_premise_holds_no_ambient_credential_is_issued(self):
        """整套口径建立在"不发 cookie"上；哪天发了 cookie，这条必须红，逼着重审挂载点。"""
        issuers = [
            f"{p.relative_to(BACKEND_DIR)}:{i + 1}"
            for p in BACKEND_DIR.rglob("*.py")
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines())
            if re.search(r"\.set_cookie\s*\(", line)
        ]
        assert issuers == [], f"后端开始下发 cookie，CSRF 挂载清单必须重审：{issuers}"


class TestDesignIsNotAMissingWire:
    async def test_wired_route_rejects_hostile_origin_before_the_handler(
        self, client: AsyncClient, admin_headers: dict
    ):
        """挂着的那条：依赖先于处理函数执行，所以连不存在的 id 都是 403 而不是 404。"""
        resp = await client.delete(
            "/api/comments/999999",
            headers={**admin_headers, "Origin": "http://evil-csrf.example"},
        )
        assert resp.status_code == 403, resp.text
        assert "CSRF_CHECK_FAILED" in resp.text

    async def test_unwired_route_is_not_expected_to_403(
        self, client: AsyncClient, admin_headers: dict
    ):
        """没挂的那条：同一种请求形态走到处理函数（不存在的 id = 404），不是被 CSRF 拦下。

        这条断言替下一轮探针说话——"某个 admin 写口带站外 Origin 没 403"不是缺陷，
        别靠补线消掉它；真要收紧，得连 CORS/csrf_origins 与所有客户端一起重审。
        """
        resp = await client.put(
            "/api/admin/series/999999/toggle",
            headers={**admin_headers, "Origin": "http://evil-csrf.example"},
        )
        assert resp.status_code != 403, (
            f"这条口的行为变了，挂载清单需要重审：{resp.status_code} {resp.text[:200]}"
        )
        assert resp.status_code == 404, (
            f"期望走到处理函数回 404，实测 {resp.status_code} {resp.text[:200]}"
        )

    async def test_anonymous_hostile_origin_write_is_passed_through_by_design(
        self, client: AsyncClient, test_post
    ):
        """无 Bearer 直接放行是设计（跨站表单本来就能发无凭证请求）；这一层挡不住游客评论刷量，
        挡它的是频控与敏感词过滤。把它改成 403 会连带打死所有游客评论。

        打的是**挂着 CSRF 的那条创建口**（`POST /api/posts/{id}/comments`，comments.py:233），
        不是 `/api/blog/posts/{id}/comments`——那条现在只剩读口，POST 会 405，什么都证明不了。
        """
        resp = await client.post(
            f"/api/posts/{test_post.id}/comments",
            json={"author_name": "Visitor", "content": "csrf probe wording check"},
            headers={"Origin": "http://evil-csrf.example"},
        )
        assert resp.status_code != 403 or "CSRF_CHECK_FAILED" not in resp.text, resp.text


# 文档里**允许**出现 `GET /api/csrf`——前提是同一句把它否定了（"也没有 GET /api/csrf 这类
# 取 token 的接口"）。守的是"教读者去调它 / 把它写成必需头"，不是"提到过它"。
# 上一版用整篇 `not in` 判，于是这句诚实的否定把测试自己判红了；而本仓后端 pytest 曾长期
# 被判成"开发机上跑不了"，那条就是这么写瞎、直到链上门禁才暴露。现在按句子切来判。
CSRF_ENDPOINT_MENTION = "GET /api/csrf"
CSRF_HEADER_EXAMPLE_MARK = "X-CSRF-Token:"
CSRF_NEGATIONS = ("没有", "不存在", "并非", "不是", "不含", "无消费方", "零消费方")
_SENTENCE_SPLIT = re.compile(r"[\n。；;！!，,]")


def _csrf_lies(text: str) -> list[str]:
    """返回把 CSRF 当成"有取 token 的接口 / 有必需头"来教的句子。"""
    offenders: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(text):
        if CSRF_ENDPOINT_MENTION not in sentence and CSRF_HEADER_EXAMPLE_MARK not in sentence:
            continue
        if any(mark in sentence for mark in CSRF_NEGATIONS):
            continue
        offenders.append(sentence.strip()[:160])
    return offenders


class TestDocsTellTheTruth:
    def test_the_lie_detector_itself_has_teeth(self, tmp_path):
        """守卫得能证明"红了是真的谎报"，而不是只会跟着文档措辞一起改口。"""
        honest = tmp_path / "honest.md"
        honest.write_text(
            "CSRF 不是全局中间件，也没有 `GET /api/csrf` 这类取 token 的接口。"
            "所以 `X-CSRF-Token` 当前没有消费方。",
            encoding="utf-8",
        )
        liar = tmp_path / "liar.md"
        liar.write_text(
            "写接口前请先调用 `GET /api/csrf` 拿到 token，"
            "并在请求头里带上 `X-CSRF-Token: <csrf_token>`。",
            encoding="utf-8",
        )
        assert _csrf_lies(honest.read_text(encoding="utf-8")) == []
        lies = _csrf_lies(liar.read_text(encoding="utf-8"))
        assert len(lies) == 2, lies

    def test_generated_doc_no_longer_claims_a_csrf_token_endpoint(self):
        for path in (DOCS_PATH, GEN_PATH):
            lies = _csrf_lies(path.read_text(encoding="utf-8"))
            assert lies == [], f"{path.name} 仍在教读者调一个不存在的接口/头：{lies}"

    def test_generated_doc_states_the_real_shape(self):
        text = DOCS_PATH.read_text(encoding="utf-8")
        assert "per-route" in text and "require_csrf" in text, "文档没交代这条依赖真实挂在哪"

    def test_no_csrf_route_in_openapi(self):
        """文档说的"没有取 token 的接口"要用生成后的文档来判，不能用源码字符串判。"""
        from backend.main import app

        paths = app.openapi()["paths"]
        csrf_paths = [p for p in paths if "csrf" in p.lower()]
        assert csrf_paths == [], f"OpenAPI 里出现了 CSRF 接口，挂载清单与文档要一起改：{csrf_paths}"
