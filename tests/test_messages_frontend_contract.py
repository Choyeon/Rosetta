"""私信族（``/api/messages*``）的前后端路径契约。

后端这一族就绪已久，前端此前**零消费**——用户能收到点赞与评论通知，却没有任何地方读私信。
2026-10-16 随 ``frontend/pages/account/messages.vue`` + ``frontend/composables/useMessages.ts``
接入 5 条（会话列表 / 会话正文 / 发送 / 整段标已读 / 未读总数），留 1 条刻意不消费。

同族路径只差一段（``/messages/{message_id}/read`` vs ``/messages/read-all/{user_id}``），
写错的实测表现是 405/404 而不是编译错误，所以按 AGENTS.md §7.4 第 4 条的口径读
**生成后的** OpenAPI 文档对表，不去静态读 ``app.routes``（``_IncludedRouter`` 懒挂载会假通过）。
"""

import re
from pathlib import Path

import pytest

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
COMPOSABLE = REPO / "frontend" / "composables" / "useMessages.ts"
PAGE = REPO / "frontend" / "pages" / "account" / "messages.vue"
AUTHOR_PAGE = REPO / "frontend" / "pages" / "authors" / "[username].vue"
HEADER = REPO / "frontend" / "components" / "AppHeader.vue"
COVERAGE_DOC = REPO / "frontend" / "docs" / "API_COVERAGE.md"

# (OpenAPI 里的操作, 前端字面量, 前端文件)
FRONTEND_CONSUMED: list[tuple[str, str, str]] = [
    ("GET /api/messages/conversations", "'/messages/conversations'", "page"),
    ("GET /api/messages/{user_id}", "`/messages/${peerId.value ?? 0}`", "page"),
    ("GET /api/messages/unread/count", "'/messages/unread/count'", "composable"),
    ("POST /api/messages", "apiFetch<MessageSendResult>('/messages'", "composable"),
    ("PUT /api/messages/read-all/{user_id}", "`/messages/read-all/${peerId}`", "composable"),
]

# 后端保留、前端刻意不用：读正文那一条已经带副作用把整个会话置为已读，
# 前端不存在「同一会话里只有某几条未读」的状态可展示。
INTENTIONALLY_UNUSED = [
    "PUT /api/messages/{message_id}/read",
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
    return {
        "composable": COMPOSABLE,
        "page": PAGE,
        "author": AUTHOR_PAGE,
        "header": HEADER,
    }[which].read_text(encoding="utf-8")


@pytest.mark.parametrize(("operation", "literal", "where"), FRONTEND_CONSUMED)
def test_message_operation_exists_and_has_a_frontend_call_site(operation, literal, where):
    """端点存在（router 没掉线、路径没改名），且前端有对应的字面量调用点。"""
    ops = _operations()
    assert operation in ops, f"后端已无 {operation}；前端消费点需要同步撤销"
    assert literal in _frontend_text(where), f"{where} 里找不到 {operation} 的调用字面量 {literal}"


def test_conversation_thread_side_effect_is_documented_at_the_call_site():
    """``GET /messages/{user_id}`` 读即置已读：页面必须据此在正文到手后刷新列表与角标。"""
    page = _frontend_text("page")
    assert "watch(threadData" in page and "void refreshConv()" in page, (
        "读会话正文会把该对端的未读清掉；少了这次回刷，未读角标会停在旧值"
    )


@pytest.mark.parametrize("operation", INTENTIONALLY_UNUSED)
def test_unused_by_row_variants_stay_documented(operation):
    """按单条标已读仍未被前端使用，但覆盖度文档必须写明这是决定而不是缺口。"""
    assert operation in _operations(), f"{operation} 已从后端消失，文档记录可以一并撤掉"
    text = _frontend_text("composable") + _frontend_text("page")
    # 前端没有 /messages/{消息 ID}/read 形态的调用点。用正则而不是子串：两个文件的文档注释里
    # 都要写明这条是「刻意不消费」，裸子串 `/read\`` 会命中注释本身。read-all 形态是
    # `/messages/read-all/${peerId}`，不带 `${}` 段，同样不会命中。
    assert re.search(r"/messages/\$\{[^}]+\}/read(?![\w-])", text) is None, (
        f"前端出现了按单条消息 ID 标已读的调用点：要么把它补进 FRONTEND_CONSUMED，"
        f"要么撤销 {operation} 的『刻意不消费』记录"
    )
    verb, path = operation.split(" ", 1)
    doc = COVERAGE_DOC.read_text(encoding="utf-8")
    assert path in doc, f"{verb} {path} 未在 frontend/docs/API_COVERAGE.md 记录为刻意不消费"


def test_messages_page_is_client_only_and_noindex():
    """/account/** 由 routeRules 精准反选成 ssr:false 私有页；页面不得自宣 ssr，但要自带 noindex。

    口径与 ``pages/account/index.vue`` 同源：ssr 档位只写在 nuxt.config（两处各写一份必然漂移），
    而登录态内容页必须 ``useNoindexPage()``，否则服务端补 meta 的名单（server/utils/noindex-shell.ts）
    与实际声明对不上。
    """
    page = _frontend_text("page")
    assert "definePageMeta({ layout: 'default', middleware: 'auth-required' })" in page
    assert re.search(r"definePageMeta\([^)]*ssr", page) is None, (
        "ssr 档位归 routeRules 单源（/account/**），页面里不要再写一份"
    )
    assert "useNoindexPage()" in page


def test_private_message_entry_points_exist():
    """两个入口：顶栏登录菜单（桌面 + 移动抽屉）与作者主页的「发私信」。"""
    header = _frontend_text("header")
    assert header.count("navigateTo('/account/messages')") == 2, (
        "AppHeader 的桌面下拉与移动抽屉各需要一个私信入口，少一个就是那端进不去"
    )
    author = _frontend_text("author")
    assert "canMessage" in author and "ClientOnly" in author, (
        "作者主页的私信入口依赖登录态：SSR 期拿不到 token，不包 ClientOnly 就是 hydration mismatch"
    )
