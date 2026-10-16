"""动态族（``/api/activities*`` + ``/api/admin/activities*``）的前后端路径契约。

这一族后端 8 条操作里，前台时间线页与后台管理此前只读到 6 条：
``POST /activities/{id}/like`` 前端没有按钮（计数只能看不能点），
``POST /activities`` 只有后台在用（登录用户的"说说"入口缺失）。
2026-10-16 一并接进 ``frontend/pages/activity.vue``。

同族路径只差一段（``/activities/{id}/like`` vs ``/admin/activities/{id}``），
写错的实测表现是 405/404 而不是编译错误，所以按 AGENTS.md §7.4 第 4 条的口径读
**生成后的** OpenAPI 文档对表，不去静态读 ``app.routes``（``_IncludedRouter`` 懒挂载会假通过）。
"""

import json
import re
from pathlib import Path

import pytest

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "frontend" / "pages" / "activity.vue"
SIDEBAR = REPO / "frontend" / "components" / "ActivitySidebarCard.vue"
ADMIN = REPO / "frontend" / "composables" / "useAdminManage.ts"
SCHEMA = REPO / "backend" / "schemas" / "activity.py"
COVERAGE_DOC = REPO / "frontend" / "docs" / "API_COVERAGE.md"

# (OpenAPI 里的操作, 前端字面量, 前端文件)
FRONTEND_CONSUMED: list[tuple[str, str, str]] = [
    ("GET /api/activities", "useAPI<Paginated<ActivityItem>>('/activities'", "page"),
    ("POST /api/activities", "apiFetch('/activities'", "page"),
    ("POST /api/activities/{activity_id}/like", "`/activities/${id}/like`", "page"),
    ("GET /api/admin/activities", "'/admin/activities', { query", "admin"),
    ("POST /api/admin/activities", "'/admin/activities', { method: 'POST'", "admin"),
    ("PUT /api/admin/activities/{activity_id}", "`/admin/activities/${id}`, { method: 'PUT'", "admin"),
    ("DELETE /api/admin/activities/{activity_id}", "`/admin/activities/${id}`, { method: 'DELETE'", "admin"),
]

# 后端保留、前端刻意不用：切换发布状态与 PUT 详情是同一件事的第二个入口，
# 后台已经用 PUT 提交 is_published，再造一个 toggle 按钮只是多一个真相来源。
INTENTIONALLY_UNUSED = [
    "PUT /api/admin/activities/{activity_id}/toggle",
]

_VERBS = ("get", "post", "put", "patch", "delete")


def _operations() -> set[str]:
    spec = app.openapi()
    out: set[str] = set()
    for path, item in spec["paths"].items():
        for verb in _VERBS:
            if item.get(verb) is not None:
                out.add(f"{verb.upper()} {path}")
    return out


def _frontend_text(which: str) -> str:
    return {"page": PAGE, "admin": ADMIN, "sidebar": SIDEBAR}[which].read_text(encoding="utf-8")


@pytest.mark.parametrize(("operation", "literal", "where"), FRONTEND_CONSUMED)
def test_activity_operation_exists_and_has_a_frontend_call_site(operation, literal, where):
    """端点存在（router 没掉线、路径没改名），且前端有对应的字面量调用点。"""
    ops = _operations()
    assert operation in ops, f"后端已无 {operation}；前端消费点需要同步撤销"
    assert literal in _frontend_text(where), f"{where} 里找不到 {operation} 的调用字面量 {literal}"


@pytest.mark.parametrize("operation", INTENTIONALLY_UNUSED)
def test_unused_operations_are_documented_as_a_decision(operation):
    """toggle 仍是后端能力，但覆盖度文档必须写明这是决定而不是缺口。"""
    assert operation in _operations(), f"{operation} 已从后端消失，文档记录可以一并撤掉"
    verb, path = operation.split(" ", 1)
    assert path in COVERAGE_DOC.read_text(encoding="utf-8"), (
        f"{verb} {path} 未在 frontend/docs/API_COVERAGE.md 记录为刻意不消费"
    )


def test_like_uses_server_authoritative_count_not_local_increment():
    """``POST /activities/{id}/like`` 不返回新计数：点完必须 refresh 取服务端值。

    本页是 swr 600 的共享缓存页，本地 +1 会让这一屏的读数与其它访客长期对不上，
    而且后端只增不减（无取消语义），把按钮做成可取消即成假象。
    """
    page = _frontend_text("page")
    assert re.search(r"await apiFetch\(`/activities/\$\{id\}/like`", page)
    assert "await refresh()" in page
    assert "likes_count+1" not in page.replace(" ", "")


def test_like_button_is_not_gated_behind_nonzero_count():
    """0 赞也要有按钮：首赞没有入口，计数永远停在 0（此前就是这个问题）。"""
    page = _frontend_text("page")
    assert "(item.likes_count ?? 0) > 0" not in page
    assert "likeActivity(item.id)" in page
    # v-memo 的依赖里必须带上这一条：列表项做了记忆化，漏掉进行中的点赞 id，
    # 按钮的 disabled/转圈分支不会重渲染，表现是"点了没反应但也按不动第二下"。
    assert "pendingLikeId === item.id]" in page


def test_composer_is_client_only_and_login_gated():
    """发布框是登录态 UI，必须包在 ClientOnly 里并判 authStore。

    ``/activity`` 是 SSR + swr 600 的公开页：auth store 是 skipHydrate（SSR 期无 token），
    服务端渲染出的"已登录"外壳会把某一个访客的登录态冻进共享 HTML 里。
    """
    page = _frontend_text("page")
    assert "useAuthStore" in page and "authStore.isAuthenticated" in page
    assert re.search(r"<ClientOnly>[\s\S]{0,400}?v-if=\"authStore\.isAuthenticated\"", page)
    assert re.search(r"<Textarea[\s\S]{0,400}?v-model=\"draft\"", page)


def test_publish_sends_only_current_locale_content():
    """``content`` 是多语言 dict，用户只写当前语言那一份。

    其余语言由后端 ``get_i18n_value`` 的回退链兜住（AGENTS.md §7.3：UGC 存明文、禁止自动翻译），
    前端造四份重复文本或调翻译接口都是错的。
    """
    page = _frontend_text("page")
    assert "content: { [locale.value]: text }" in page
    assert "translate" not in page.lower()


def test_four_locales_have_the_new_activity_keys():
    """like / publish / composerPlaceholder 四语齐备：缺一种语言就是那个语言下按钮没有名字。"""
    needed = {"like", "publish", "composerPlaceholder"}
    for code in ("zh", "en", "ja", "zh_Hant"):
        text = (REPO / "frontend" / "i18n" / "locales" / f"{code}.json").read_text(encoding="utf-8")
        activity = json.loads(text)["activity"]
        missing = needed - {k for k, v in activity.items() if isinstance(v, str) and v.strip()}
        assert not missing, f"{code}.json 的 activity 段缺 {sorted(missing)}"


def test_frontend_char_bound_matches_backend_schema_constant():
    """输入框的 maxlength 与后端 ``MAX_ACTIVITY_CONTENT_CHARS`` 同值。

    两处各写一份必然漂移：后端先改小就变成"用户写满才被 422"，改大则边界形同虚设。
    """
    limit = re.search(r"^MAX_ACTIVITY_CONTENT_CHARS\s*=\s*(\d+)", SCHEMA.read_text(encoding="utf-8"), re.M)
    assert limit, "backend/schemas/activity.py 里的 MAX_ACTIVITY_CONTENT_CHARS 不见了"
    page = _frontend_text("page")
    assert f"const MAX_CONTENT = {limit.group(1)}" in page, (
        f"前端 MAX_CONTENT 与后端 {limit.group(1)} 不一致"
    )


def test_public_write_mouth_has_a_length_bound():
    """``POST /activities`` 对任何登录用户开放，正文必须有上限。

    没有上限时一条几十万字的动态会把公开列表的响应缓存（activities:<lang>:p*:ps*，TTL 300s）
    撑成大对象，之后每个访客都要读它。
    """
    schema = SCHEMA.read_text(encoding="utf-8")
    assert "MAX_ACTIVITY_CONTENT_CHARS" in schema
    assert schema.count("@field_validator") >= 2, "创建与更新两个模型都要带上限校验"
