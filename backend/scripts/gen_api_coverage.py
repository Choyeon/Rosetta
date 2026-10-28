"""生成 `frontend/docs/API_COVERAGE.md` 的「全模块汇总表 + 未消费清单」区块。

为什么要有这个脚本：这张表此前只有两份互相矛盾的数（2026-09-26 全量快照 + 各轮手加的增量），
文档里写着"下次全量刷新时以扫描器重算"，但从没有扫描器——于是"前端缺口清单"这件事
实际是靠记忆和过时表格在做（实例：`messages` 行写 0 ✅，而 `/account/messages` 早接了 5 条）。
缺口清单错了，后面每个切片都会挑错目标。

手法（与文档口径一致）：
* 后端清单 = 逐个 `backend/api/*.py` 的 `module.router.routes`（路径 + methods），
  再按 `backend/main.py` 的 `include_router(..., prefix=...)` 还原完整路径；
  最后与 `app.openapi()["paths"]` 的 operation 数对账，对不上直接报错——
  这一步同时挡住"整条路由消失了"（AGENTS §7.4 第 4 条：核对存在性要读生成后的文档）。
* 前端清单 = 扫 `frontend/**`（排除 node_modules/.output/.nuxt/dist/.cache）里以 `/` 开头的
  字符串与模板字面量，`${x}` 归一成 `*`，剥掉查询串；按 §4.2 的铁律补 `/api` 前缀。
* 动词来自字面量之后窗口里的 `method: 'post'`；读不到按 GET；
  `method:` 的值不是字面量（变量传入）时该路径的所有动词都算已消费——
  静态扫描判不出变量，宁可少报缺口，不可虚报缺口。
* ✅ = 浏览器侧文件命中且动词对得上；🟡 = 只在 `frontend/server/`（Nitro BFF）或
  `.vue` 的 `<template>` 区（URL 拼接）命中；❌ = 没有任何调用点。

用法：
    PYTHONPATH=. python backend/scripts/gen_api_coverage.py --write
    PYTHONPATH=. python backend/scripts/gen_api_coverage.py --check   # 漂移时退出码 1
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_API = REPO_ROOT / "backend" / "api"
MAIN_PY = REPO_ROOT / "backend" / "main.py"
DOC_PATH = REPO_ROOT / "frontend" / "docs" / "API_COVERAGE.md"
FRONTEND = REPO_ROOT / "frontend"

BEGIN_MARK = "<!-- COVERAGE-AUTO:BEGIN 由 backend/scripts/gen_api_coverage.py 生成，勿手改 -->"
END_MARK = "<!-- COVERAGE-AUTO:END -->"

_SKIP_DIR_NAMES = {"node_modules", ".output", ".nuxt", "dist", ".cache", "tests", "types"}
_SCAN_SUFFIXES = {".ts", ".vue", ".js", ".tsx"}
_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

_INCLUDE_RE = re.compile(r"""app\.include_router\(\s*([\w.]+)\s*,\s*prefix=["']([^"']+)["']""")
_IMPORT_ALIAS_RE = re.compile(
    r"""from\s+backend\.api\.([\w]+)\s+import\s+([\w]+)(?:\s+as\s+([\w]+))?"""
)
# 以 / 开头的字符串字面量：单/双引号
_LITERAL_RE = re.compile(r"""(['"])(/[^'"\n]*?)\1""")
# 反引号模板串：内容里可以带引号（`` `/market${force ? '?force=true' : ''}` ``），
# 所以不能和上一条共用"内容不含引号"的字符类
_TEMPLATE_LITERAL_RE = re.compile(r"""`(/[^`\n]*)`""")
_TEMPLATE_VAR_RE = re.compile(r"\$\{[^{}]*\}")
# 粘在最后一段尾部的模板表达式（查询串/形态后缀），不是路径参数
_GLUED_VAR_RE = re.compile(r"[^\}/]+\$\{[^{}]*\}$")
_METHOD_AFTER_RE = re.compile(
    r"""method\s*[:=]\s*(['"`])([A-Za-z]+)\1""",
)
_METHOD_VAR_RE = re.compile(r"""method\s*[:=]\s*(?!['"`])(\w+)""")
# 这些调用的字符串参数是**站内路由**，不是 API 路径（`/guestbook` 两者同形）
_ROUTE_NAV_CALLEES = frozenset(
    {
        "navigateTo",
        "localePath",
        "localeHref",
        "switchLocalePath",
        "push",
        "replace",
        "prefetchRoutes",
        "preloadRouteComponents",
        "hasPermission",
        "startsWith",
        "endsWith",
        "includes",
        "isThemeVisualExcluded",
        "stripLocalePathPrefix",
        "applyLocalePrefix",
        "stripLocalePrefix",
        "useState",
        "definePageMeta",
        "middleware",
    }
)
_URL_ATTR_NEAR_RE = re.compile(r"""(?:src|href|action)\s*=\s*['"`]{0,2}\s*$""")
# 白名单：出现在三元分支/对象属性位时，只有这些调用名算"真的发请求"
_REQUEST_CALLEES = frozenset(
    {
        "apiFetch",
        "silentApiFetch",
        "useAPI",
        "useApi",
        "useAsyncData",
        "request",
        "resolveBackendEndpoint",
        "$fetch",
        "$get",
        "$post",
        "$put",
        "$patch",
        "$delete",
    }
)
# `const LIST_URL = '/admin/shortcodes'` 这一族：字面量不在实参位，但名字说明它就是请求路径。
# 光认大写后缀会漏掉 `const url = tab === 'favorites' ? '/favorites' : ...`（个人中心就是这么写的），
# 所以额外允许这几个小写名；`path` 不收（它 overwhelmingly 是站内路由，不是 API 路径）。
_URL_NAMED_ASSIGN_RE = re.compile(
    r"\b([A-Za-z_$][\w$]*(?:URL|Url|ENDPOINT|Endpoint)|url|apiUrl|apiPath|endpoint)\s*=\s*$"
)
# 同一族的另一种写法：`const listUrl = computed(() => a ? '/favorites' : \`/blog/users/me/${x}\`)`。
# 字面量躺在 computed 体里，`=` 后面隔着一整棵表达式树，实参位判定与上一条都对不上；
# 真正的请求发生在 `useAPI(() => listUrl.value, …)` 那个**使用点**上，所以这里只交名字，
# 动词仍由 `_verbs_for_const` 从使用点读回来（个人中心四个档位曾被整族误报成未消费）。
_URL_COMPUTED_DECL_RE = re.compile(
    r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*(?:URL|Url|ENDPOINT|Endpoint)|url|apiUrl|apiPath|endpoint)"
    r"\s*=\s*computed(\s*<[^<>]*>)?\s*\("
)
# 任意名字的常量声明（配合"用法判据"用，见 `_declared_request_const`）
_CONST_DECL_RE = re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=")

_NITRO_PREFIX = "server/"


class Operation(NamedTuple):
    module: str
    method: str
    path: str

    @property
    def norm(self) -> str:
        return _norm_backend_path(self.path)


class Call(NamedTuple):
    """前端一条 URL 字面量：候选路径、所在文件、动词集合、以及它在发请求还是拼 URL。"""

    candidate: str
    rel: str
    verbs: set[str] | None
    context: str  # fetch / url


def _norm_backend_path(path: str) -> str:
    """`/api/x/{notification_id}/read` → `/api/x/*/read`（catchall `{x:path}` → `**`）。"""
    out = re.sub(r"\{[\w:]+\}", lambda m: "**" if ":path" in m.group(0) else "*", path)
    return re.sub(r"/{2,}", "/", out)


def _iter_source_files() -> list[tuple[str, Path]]:
    """返回 (相对 frontend/ 的路径, 绝对路径)，跳过构建产物与依赖。"""
    out: list[tuple[str, Path]] = []
    for path in FRONTEND.rglob("*"):
        if not path.is_file() or path.suffix not in _SCAN_SUFFIXES:
            continue
        rel = path.relative_to(FRONTEND).as_posix()
        parts = rel.split("/")[:-1]
        if _SKIP_DIR_NAMES.intersection(parts):
            continue
        out.append((rel, path))
    return out


def _front_calls() -> list[Call]:
    """扫前端字面量 → Call(候选路径, 相对文件, 动词集合或 None=全部动词, 是否真的发请求).

    只认"紧邻 fetch 类调用"或"URL 拼接属性"的字面量：导航链接、后台菜单表、
    `definePageMeta` 里的路由名与 API 路径长得一样（`/guestbook` 既是页面也是
    `GET /api/guestbook`），全量计入会把没接线的端点报成已消费。
    """
    hits: list[Call] = []
    for rel, path in _iter_source_files():
        text = path.read_text(encoding="utf-8")
        literals = list(_LITERAL_RE.finditer(text)) + list(_TEMPLATE_LITERAL_RE.finditer(text))
        for m in literals:
            context, const_name, callee = _context_of(text, m.start())
            if context == "none":
                continue
            raw = m.group(m.lastindex or 1)
            candidates = _candidate_paths(raw)
            if const_name is not None:
                verbs = _verbs_for_const(text, const_name, m.start())
            elif context == "fetch":
                verbs = _verbs_at(text, m.start(), m.end(), callee)
            else:
                verbs = {"get"}
            for cand in candidates:
                hits.append(Call(cand, rel, verbs, context))
    return hits


def _candidate_paths(raw: str) -> set[str]:
    """一条字面量能请求到哪些路径（已带 `/api` 前缀的候选集合）。"""
    forms = {raw}
    # `${...}` 粘在**最后一段尾部**通常是查询串或形态后缀
    # （`/admin/themes/market${force ? "?force=true" : ""}`），这条字面量同时也请求了
    # 去掉尾巴的父路径；单独占一段的 `${id}` 是路径参数，不能算成父路径。
    glued = _GLUED_VAR_RE.search(raw)
    if glued:
        forms.add(raw[: raw.rindex("${")])
    # 变量前不是 `/` 同样说明 `${…}` 开的是查询串；这条还兜住嵌套模板串——
    # `/blog/rss${qs ? `?${qs}` : ''}` 的反引号会让模板正则只能取到第一个 `${` 为止，
    # 而 rss.xml 就是 GET /api/blog/rss 的真实消费点。
    var_at = raw.find("${")
    if var_at > 0 and raw[var_at - 1] != "/":
        forms.add(raw[:var_at])
    candidates: set[str] = set()
    for form in forms:
        normed = _TEMPLATE_VAR_RE.sub("*", form)
        normed = normed.split("?")[0].split("#")[0]
        if normed.endswith("/"):
            normed = normed[:-1]
        candidates.add(f"/api{normed}")
        if normed.startswith("/api/"):
            candidates.add(normed)
    return candidates


def _verb_from_callee(callee: str | None) -> str | None:
    """动词写在封装名里的形态：`$get/$post/$patch/$delete`（主题与插件管理器就是这么包的）。

    不认这一族，`DELETE /admin/themes/{slug}`、`PATCH /admin/themes/{slug}/mods` 会被判成
    "这条路径只消费了 GET"——封装内部已经把 method 固定住了，调用点上没有 `method:` 字面量。
    """
    if not callee:
        return None
    name = callee.lstrip("$").lower()
    return name if name in _HTTP_METHODS else None


def _verbs_at(text: str, lit_start: int, lit_end: int, callee: str | None) -> set[str] | None:
    """一次调用点的动词集合；None = 变量传入，该路径的所有动词都算。"""
    explicit, saw_var = _methods_in_window(_window_after(text, lit_end))
    if explicit:
        return explicit
    verb = _verb_from_callee(callee)
    if verb is not None:
        return {verb}
    return None if saw_var else {"get"}


def _verbs_for_const(text: str, name: str, anchor: int) -> set[str] | None:
    """`const LIST_URL = '/x'` 这一族：动词写在**使用点**上，不在声明点。

    不往回看使用点就会把 `POST /admin/shortcodes`（预览口，复用 LIST_URL）判成未消费。
    只看声明之后 1500 字符内的使用点：`const url = …` 这种通用名在一个文件里会出现多次，
    不收口就会把别的函数里 `method: 'PUT'` 记到这条路径头上（那是"发明覆盖率"，比漏判更坏）。
    """
    verbs: set[str] = set()
    # 大写常量名（LIST_URL）是文件作用域，使用点散在整份文件里；小写名（url）是函数内的
    # 临时变量，只认声明后 1500 字符内的使用点。
    limit = len(text) if name[:1].isupper() or name[:1] == "$" else 1500
    for m in re.finditer(rf"\b{re.escape(name)}\b", text):
        if m.start() <= anchor:
            continue  # 声明自身，以及声明之前属于别的函数的同名变量
        if m.start() > anchor + limit:
            break
        found = _verbs_at(text, m.start(), m.end(), _callee_of(text[: m.start()].rstrip()))
        if found is None:
            return None
        verbs |= found
    return verbs or {"get"}


def _context_of(text: str, start: int) -> tuple[str, str | None, str | None]:
    """字面量在干什么：(fetch/url/none, URL 常量名, 调用名)。

    判"发请求"用**它是某个调用的参数**，而不是"附近 140 字符里有 apiFetch"：
    后者两头都错——`request('/oobe/status')`（OOBE 自己的封装）漏判成未消费，
    而 AppHeader 里导航用的 `'/guestbook'` 会因为上文有 apiFetch 被误判成已消费。
    参数位 = 引号前（跳过 `<泛型>`）是 `(`、`,`、`:` 或 `?`；调用名在拉黑名单里的（跳转/路由类）不算。
    字面量不在实参位时，还有三条"隔了一层"的写法：URL 命名的直接赋值、URL 命名的
    `computed(() => …)`，以及任意名但**确曾被请求封装当实参用过**的常量（`_declared_request_const`）。
    """
    prefix = text[max(0, start - 40) : start]
    if _URL_ATTR_NEAR_RE.search(prefix):
        return "url", None, None
    named = _URL_NAMED_ASSIGN_RE.search(prefix)
    if named:
        # const LIST_URL = '/admin/shortcodes' 再传给 apiFetch：字面量本身不是实参位
        return "fetch", named.group(1), None
    callee = _callee_of(text[:start].rstrip())
    if callee is not None and callee not in _ROUTE_NAV_CALLEES:
        # 三元分支 / 对象属性位（`? '/favorites' : \`/blog/users/me/${tab}\``、`url: '/x'`）：
        # 只有包住它的调用名确属"发请求"那一族才算消费点，否则后台菜单表里的导航项会被误判成已接线
        blocked = prefix.rstrip()[-1:] in (":", "?") and callee not in _REQUEST_CALLEES
        if not blocked:
            return "fetch", None, callee
    declared = _computed_url_const(text, start)
    if declared is not None:
        return "fetch", declared, None
    by_use = _declared_request_const(text, start)
    if by_use is not None:
        return "fetch", by_use, None
    return "none", None, None


def _declared_request_const(text: str, start: int) -> str | None:
    """字面量躺在 `const path = isMd ? '/admin/export/markdown' : '/admin/export/posts'` 里。

    这类"先声明、再把变量交给请求封装"的写法不看名字（`path` 这种通用名恰恰最常用），
    而是看**这个变量后来有没有真的被请求封装当实参用**：名字判据会漏，用法判据不会。
    声明与字面量之间不得跨过语句边界（`;` 或空行），否则认到的是上一条语句的变量。
    """
    if not text[:start].rstrip().endswith(("?", ":")):
        return None
    window_start = max(0, start - 240)
    for m in reversed(list(_CONST_DECL_RE.finditer(text[window_start:start]))):
        # m 的偏移是相对窗口的，换算回全文再用
        decl_end = window_start + m.end()
        gap = text[decl_end:start]
        if ";" in gap or "\n\n" in gap:
            continue
        if _uses_name_for_request(text, m.group(1), start):
            return m.group(1)
    return None


def _uses_name_for_request(text: str, name: str, anchor: int) -> bool:
    """声明之后 1500 字符内，这个名字是否出现在请求封装的实参位上。"""
    for m in re.finditer(rf"\b{re.escape(name)}\b", text):
        if m.start() <= anchor:
            continue
        if m.start() > anchor + 1500:
            break
        if _request_callee_before(text, m.start()) in _REQUEST_CALLEES:
            return True
    return False


def _request_callee_before(text: str, pos: int) -> str | None:
    """位置上的名字是谁的实参；两种真实形态都认。

    ① 直接实参：`apiFetch<Blob>(path, { method: 'GET' })`；
    ② 惰性 getter 实参：`useAPI<AccountList>(() => listUrl.value, { … })`——
    箭头函数整体才是第一个实参，所以要先剥掉 `=>` 和它的参数表 `()` 才够到封装名。
    """
    before = text[:pos].rstrip()
    callee = _callee_of(before)
    if callee is not None:
        return callee
    if not before.endswith("=>"):
        return None
    arrow_at = _match_open_paren(before[:-2])
    if arrow_at is None:
        return None
    return _callee_of(before[:arrow_at].rstrip())


def _computed_url_const(text: str, start: int) -> str | None:
    """字面量是否躺在一个 URL 命名的 `computed(` 体里；是则返回那个变量名。

    必须确认那个 `(` 到字面量为止还没闭合，且声明在 240 字符以内：不看配对就往前找声明，
    会把"上一个 computed 早就关了"的导航字符串也认成请求路径（那是发明覆盖率，比漏判更坏）。
    """
    window_start = max(0, start - 240)
    for m in reversed(list(_URL_COMPUTED_DECL_RE.finditer(text[window_start:start]))):
        open_pos = window_start + m.end() - 1
        if _paren_still_open(text, start, open_pos):
            return m.group(1)
    return None


def _paren_still_open(text: str, start: int, open_pos: int) -> bool:
    """`open_pos` 处那个 `(` 在 `start` 之前还没闭合。"""
    depth = 0
    for i in range(start - 1, open_pos - 1, -1):
        ch = text[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            depth -= 1
    return depth < 0


def _callee_of(before: str) -> str | None:
    """从引号前的文本回退到调用名；不是调用参数就返回 None。

    真实形态是 `名字<泛型>(实参…'URL'`，所以从引号往回要依次剥掉
    `(`（首实参）或 `,`（后续实参）、再剥掉泛型实参 `<…>`，剩下的才是调用名。
    顺序反了会把 `useAPI<MessageThread>(` 判成"不是调用"（实测整站掉到 15%）。
    """
    if before.endswith("("):
        before = before[:-1].rstrip()
    elif before.endswith((",", ":", "?")):
        # 后续实参：resolveBackendEndpoint(runtime, '/blog/rss')
        # 冒号/问号位：三元两个分支与对象属性
        # （`apiFetch(isMd ? '/admin/import/markdown' : '/admin/import/posts', …)`、`{ url: '/x' }`）
        open_at = _match_open_paren(before[:-1])
        if open_at is None:
            return None
        before = before[:open_at].rstrip()
    else:
        return None
    while before.endswith(">"):
        angle_at = _match_open_angle(before)
        if angle_at is None:
            return None
        before = before[:angle_at].rstrip()
    m = re.search(r"([A-Za-z_$][\w.$]*)\s*$", before)
    if not m:
        return None
    name = m.group(1)
    return name.split(".")[-1] if "." in name else name


def _match_open_paren(text: str) -> int | None:
    """从尾部回扫，找到包住当前实参列表的那个 `(` 的位置。"""
    depth = 0
    for i in range(len(text) - 1, -1, -1):
        ch = text[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            if depth == 0:
                return i
            depth -= 1
    return None


def _match_open_angle(text: str) -> int | None:
    """从尾部的 `>` 回扫配对的 `<`。

    泛型实参里可以带对象类型（`request<OOBEStatus & { success?: boolean }>`），
    所以 `{}`/`()`/`[]` 要各自记账，只在它们都归零时才认 `<`/`>`；
    不这样做就会在 `}` 上误判"这不是泛型"，把 OOBE 整族报成未消费。
    泛型体里同样能出现字符串字面量类型（`issues: Array<{ level: 'error' | 'warn' }>`），
    所以引号不是"到此为止"，而是整段跳过——`POST /oobe/preflight` 就因为这条被漏了一轮。
    找不到配对的开引号就仍按"不是泛型"处理（少计比多计安全）。
    """
    angle = 0
    braces = 0
    brackets = 0
    parens = 0
    i = len(text) - 1
    while i >= 0:
        ch = text[i]
        if ch in "\"'`":
            open_at = _find_open_quote(text, i, ch)
            if open_at is None:
                return None
            i = open_at - 1
            continue
        if ch == "}":
            braces += 1
        elif ch == "{":
            braces -= 1
        elif ch == "]":
            brackets += 1
        elif ch == "[":
            brackets -= 1
        elif ch == ")":
            parens += 1
        elif ch == "(":
            parens -= 1
        elif braces == 0 and brackets == 0 and parens == 0:
            if ch == ">":
                angle += 1
            elif ch == "<":
                angle -= 1
                if angle == 0:
                    return i
        if braces < 0 or brackets < 0 or parens < 0:
            return None
        i -= 1
    return None


def _find_open_quote(text: str, close_pos: int, quote: str) -> int | None:
    """回扫到这段字符串/模板的开引号；跳过 `\\'` 这类转义引号。"""
    i = close_pos - 1
    while i >= 0:
        if text[i] == "\\":
            i -= 2
            continue
        if text[i] == quote:
            return i
        i -= 1
    return None


def _window_after(text: str, end_pos: int) -> str:
    """字面量之后的调用上下文窗口，在**第一个空行**截断。

    `apiFetch('/x', { query })` 与下一条 `apiFetch('/y/${id}', { method: 'POST' })`
    之间必然空行隔开，不截断就会把后一条的 POST 记到前一条头上
    （实测把 GET /admin/guestbook 判成未消费）。
    """
    window = text[end_pos : end_pos + 400]
    blank = window.find("\n\n")
    return window[:blank] if blank != -1 else window


def _methods_in_window(window: str) -> tuple[set[str], bool]:
    """窗口里写明的 method 集合，以及"method 是变量传入"的标记。"""
    found = {mm.group(2).lower() for mm in _METHOD_AFTER_RE.finditer(window)}
    found = {v for v in found if v in _HTTP_METHODS}
    return found, bool(_METHOD_VAR_RE.search(window))


def _segments_match(pattern: str, candidate: str) -> bool:
    """`*` 恰配一段，`**` 配剩余若干段；**两边**的 `*` 都是通配。

    前端写 `` `/admin/guestbook/${id}/${action}` `` 归一后是 `/admin/guestbook/*/*`，
    后端形态是 `/api/admin/guestbook/*/approve`——只让模式侧通配的话，
    approve/reject/spam 三条全会被判成未消费（动态动作段在前端是变量）。
    """
    ps = pattern.strip("/").split("/")
    cs = candidate.strip("/").split("/")
    if len(ps) != len(cs):
        # catchall（`**`）允许候选更长
        return "**" in ps and len(cs) >= len(ps)
    return all(a == b or a == "*" or b == "*" for a, b in zip(ps, cs, strict=True))


def _module_route_map() -> dict[tuple[str, str], str]:
    """逐个模块 router 取路由，按 main.py 的 prefix 还原完整路径 → 模块名。

    同一条路由可能对应两种写法（`@router.get("/")` 与 `@router.get("")` 在 FastAPI
    里分别产出 `/api/users/` 与 `/api/users`），两种都登记，归属才不会落空。
    """
    main_text = MAIN_PY.read_text(encoding="utf-8")
    alias_to_attr: dict[str, tuple[str, str]] = {}
    for m in _IMPORT_ALIAS_RE.finditer(main_text):
        mod, orig, alias = m.group(1), m.group(2), m.group(3)
        alias_to_attr[alias or orig] = (mod, orig)

    lookup: dict[tuple[str, str], str] = {}
    for router_arg, prefix in _INCLUDE_RE.findall(main_text):
        if router_arg.endswith(".router"):
            module = router_arg[: -len(".router")]
            router = importlib.import_module(f"backend.api.{module}").router
        else:
            # 裸名是在函数里 `from backend.api.X import y as 裸名` 进来的别名
            # （`gallery_public_router` 就是），backend.main 的模块属性上找不到它。
            module, orig_attr = alias_to_attr.get(router_arg, (router_arg, router_arg))
            router = getattr(importlib.import_module(f"backend.api.{module}"), orig_attr)
        for route in router.routes:
            # route.methods 是大写集合（{"GET","POST"}），与小写清单求交前先归一
            methods = {str(x).lower() for x in getattr(route, "methods", None) or ()}
            if not methods:
                continue  # WebSocket / ASGI 路由不进 HTTP 清单
            joined = prefix + route.path
            variants = {joined, joined.rstrip("/"), prefix + route.path.replace("//", "/")}
            for meth in methods & _HTTP_METHODS:
                for variant in variants:
                    lookup.setdefault((meth, variant), module)
                    lookup.setdefault((meth, variant + "/"), module)
    return lookup


def _backend_operations() -> tuple[list[Operation], list[str]]:
    """清单以生成后的 `app.openapi()["paths"]` 为准，再回填模块归属。

    这样计数不可能与文档不一致（AGENTS §7.4 第 4 条：AST/`app.routes` 看不见
    "整条路由消失了"）；归不到模块的挂到 `app`（根级 `/`、`/health` 这类直接写在
    `app` 上的路由），单独列出来，数量异常就能看见。
    """
    from backend.main import app

    lookup = _module_route_map()
    ops: list[Operation] = []
    unattributed: list[str] = []
    for path, verbs in app.openapi()["paths"].items():
        for meth in sorted(verbs):
            if meth not in _HTTP_METHODS:
                continue
            module = lookup.get((meth, path)) or lookup.get((meth, path.rstrip("/")))
            if module is None:
                module = "app"
                unattributed.append(f"{meth.upper()} {path}")
            ops.append(Operation(module, meth, path))
    return ops, unattributed


def _classify(op: Operation, calls: list[Call]) -> tuple[str, list[str]]:
    """返回 (✅/🟡/❌, 命中的相对文件)。"""
    matched: list[Call] = []
    for call in calls:
        if not _segments_match(op.norm, call.candidate):
            continue
        if call.verbs is not None and op.method not in call.verbs:
            continue
        matched.append(call)
    if not matched:
        return "❌", []
    browser = [
        c.rel for c in matched if c.context == "fetch" and not c.rel.startswith(_NITRO_PREFIX)
    ]
    if browser:
        return "✅", browser
    # 只剩 Nitro BFF 在发这条请求，或只有 <img src> 之类的 URL 拼接：浏览器不直接调
    return "🟡", [c.rel for c in matched]


def build_block() -> str:
    ops, unattributed = _backend_operations()
    total = len(ops)
    calls = _front_calls()

    per_module: dict[str, dict[str, list]] = {}
    uncovered: dict[str, list[Operation]] = {}
    counts = {"✅": 0, "🟡": 0, "❌": 0}
    for op in sorted(ops, key=lambda o: (o.module, o.path, o.method)):
        mark, _files = _classify(op, calls)
        counts[mark] += 1
        bucket = per_module.setdefault(op.module, {"total": 0, "✅": 0, "🟡": 0, "❌": 0})
        bucket["total"] += 1
        bucket[mark] += 1
        if mark == "❌":
            uncovered.setdefault(op.module, []).append(op)

    covered = counts["✅"] + counts["🟡"]
    lines: list[str] = [BEGIN_MARK]
    lines.append(
        f"> 本区块由 `backend/scripts/gen_api_coverage.py` 扫描生成（后端 {total} 条 operation "
        f"× 前端 `frontend/**` 字面量）。**勿手改**：改接口或接线后执行 "
        f"`PYTHONPATH=. python backend/scripts/gen_api_coverage.py --write` 重算。"
    )
    lines.append("")
    lines.append(
        f"**总计：{total} 个端点操作；✅ {counts['✅']} + 🟡 {counts['🟡']} = 已消费 {covered} 个，"
        f"未消费 {counts['❌']} 个，覆盖率 {covered / total * 100:.1f}%。**"
    )
    if unattributed:
        lines.append("")
        lines.append(
            f"> 归不到 `backend/api/*.py` 模块的 {len(unattributed)} 条挂在 `app` 上"
            f"（根级路由）：" + "、".join(f"`{u}`" for u in sorted(unattributed))
        )
    lines.append("")
    lines.append("| 模块（backend/api） | 端点数 | ✅ | 🟡 | ❌ | 覆盖率 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for module, b in sorted(per_module.items(), key=lambda kv: (-kv[1]["total"], kv[0])):
        rate = (b["✅"] + b["🟡"]) / b["total"] * 100
        lines.append(
            f"| {module} | {b['total']} | {b['✅']} | {b['🟡']} | {b['❌']} | {rate:.0f}% |"
        )
    lines.append("")
    lines.append(f"## 未消费清单（自动生成，共 {counts['❌']} 条）")
    lines.append("")
    lines.append("> 判据是「前端源码里没有这条 URL 字面量」。接线前逐条人工确认它是不是")
    lines.append("> 刻意不消费（后台口、内部口、被别的口覆盖），确认后在对应模块小节写一句理由。")
    if uncovered:
        for module, items in sorted(uncovered.items()):
            lines.append(
                f"- **{module}**（{len(items)}）："
                + "、".join(f"`{o.method.upper()} {o.path}`" for o in items)
            )
    else:
        lines.append("- （无）")
    lines.append(END_MARK)
    return "\n".join(lines) + "\n"


def _render(doc_text: str, block: str) -> str:
    if BEGIN_MARK in doc_text and END_MARK in doc_text:
        head, rest = doc_text.split(BEGIN_MARK, 1)
        _old, tail = rest.split(END_MARK, 1)
        # `split(END_MARK)` 已经把标记本身吃掉了，tail 从区块**之后**第一个字符开始；
        # 再按 len(END_MARK) 切一次会吞掉紧随其后的正文（实测少了「## 分模块明细」整行）。
        # tail 的前导空行由本函数负责（区块后恰好留一个空行），否则每跑一次多长一行。
        return head + block + "\n" + tail.lstrip("\n")
    # 首次接入：插在「## 全模块汇总表」之后，替换掉手写的旧表格
    marker = "## 全模块汇总表\n"
    if marker not in doc_text:
        msg = "API_COVERAGE.md 里没有「## 全模块汇总表」标题，无法定位自动区块"
        raise SystemExit(msg)
    head, tail = doc_text.split(marker, 1)
    # 旧表格直到下一个 "## " 标题为止，整段由扫描器接管
    nxt = tail.find("\n## ")
    remainder = tail[nxt + 1 :] if nxt != -1 else ""
    return head + marker + block + "\n" + remainder


def main() -> int:
    # Windows 控制台默认 GBK，✅/🟡 直接写 stdout 会 UnicodeEncodeError
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="生成 API 覆盖度自动区块")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="写回文档")
    group.add_argument("--check", action="store_true", help="检查漂移，漂移时退出码 1")
    group.add_argument("--print", dest="print_only", action="store_true", help="只打印区块")
    args = parser.parse_args()

    block = build_block()
    if args.print_only:
        sys.stdout.write(block)
        return 0

    doc = DOC_PATH.read_text(encoding="utf-8")
    new_doc = _render(doc, block)
    if args.check:
        if new_doc != doc:
            sys.stderr.write(
                "API_COVERAGE.md 的覆盖度区块与扫描结果不一致，"
                "请执行：PYTHONPATH=. python backend/scripts/gen_api_coverage.py --write\n"
            )
            return 1
        sys.stdout.write("覆盖度区块与扫描结果一致\n")
        return 0
    if new_doc == doc:
        sys.stdout.write("内容未变化\n")
        return 0
    DOC_PATH.write_text(new_doc, encoding="utf-8")
    sys.stdout.write(f"已写回 {DOC_PATH.relative_to(REPO_ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
