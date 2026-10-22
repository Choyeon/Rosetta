"""收藏族（``/api/favorites*``）的前后端路径契约。

前端这一族的调用点全部写成字符串字面量（``frontend/composables/useFavorites.ts`` +
个人中心 ``pages/account/index.vue`` 的列表档位）。同族里 by-row 与 by-post 变体只差一段
路径（``/favorites/{favorite_id}`` vs ``/favorites/post/{post_id}``），写错的实测表现是
405/404 而不是编译错误——TypeScript 帮不上忙，所以拿**生成后的** OpenAPI 文档对表
（口径见 AGENTS.md §7.4 第 4 条：静态读 ``app.routes`` 会因 ``_IncludedRouter`` 懒挂载而假通过）。

同时钉住"刻意不消费"的那两条：按收藏行 ID 的 PUT/DELETE 语义比 by-post 弱
（``favorites`` 表没有 (user_id, post_id) 唯一约束，按行删只删一条重复行），
前端不用它们，但必须在覆盖度文档里留下记录，否则下一个人会当成缺口重新一遍。
"""

from pathlib import Path

import pytest

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
COMPOSABLE = REPO / "frontend" / "composables" / "useFavorites.ts"
ACCOUNT_PAGE = REPO / "frontend" / "pages" / "account" / "index.vue"
COVERAGE_DOC = REPO / "frontend" / "docs" / "API_COVERAGE.md"

# (OpenAPI 里的操作, 前端字面量, 前端文件)
FRONTEND_CONSUMED: list[tuple[str, str, str]] = [
    ("GET /api/favorites", "'/favorites'", "account"),
    ("POST /api/favorites", "apiFetch<FavoriteActionResponse>('/favorites'", "composable"),
    ("DELETE /api/favorites/post/{post_id}", "`/favorites/post/${postId}`", "composable"),
    (
        "PATCH /api/favorites/post/{post_id}/folder",
        "`/favorites/post/${postId}/folder`",
        "composable",
    ),
    (
        "PATCH /api/favorites/post/{post_id}/note",
        "`/favorites/post/${postId}/note`",
        "composable",
    ),
    ("POST /api/favorites/check", "'/favorites/check'", "composable"),
    ("GET /api/favorites/folders", "'/favorites/folders'", "composable"),
    (
        "POST /api/favorites/folders",
        "apiFetch<FavoriteActionResponse>('/favorites/folders'",
        "composable",
    ),
    ("PUT /api/favorites/folders/{folder_id}", "`/favorites/folders/${folderId}`", "composable"),
    (
        "DELETE /api/favorites/folders/{folder_id}",
        "`/favorites/folders/${folderId}`",
        "composable",
    ),
    # 按收藏行 ID 删除：只在 post 为 null 的孤儿行上使用（by-post 变体拿不到 post_id）。
    (
        "DELETE /api/favorites/{favorite_id}",
        "`/favorites/${favoriteId}`",
        "composable",
    ),
]

# 后端保留、前端刻意不用（按收藏行 ID 的写变体）。
INTENTIONALLY_UNUSED = [
    "PUT /api/favorites/{favorite_id}",
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
    return (ACCOUNT_PAGE if which == "account" else COMPOSABLE).read_text(encoding="utf-8")


@pytest.mark.parametrize(("operation", "literal", "where"), FRONTEND_CONSUMED)
def test_favorite_operation_exists_and_has_a_frontend_call_site(operation, literal, where):
    """端点存在（router 没掉线、路径没改名），且前端有对应的字面量调用点。"""
    ops = _operations()
    assert operation in ops, f"后端已无 {operation}；前端消费点需要同步撤销"
    assert literal in _frontend_text(where), f"{where} 里找不到 {operation} 的调用字面量 {literal}"


@pytest.mark.parametrize("operation", INTENTIONALLY_UNUSED)
def test_unused_by_row_variants_stay_documented(operation):
    """按行 ID 的写变体仍未被前端使用，但覆盖度文档必须写明这是决定而不是缺口。"""
    assert operation in _operations(), f"{operation} 已从后端消失，文档记录可以一并撤掉"
    # 前端确有 /favorites/{行 ID} 形态的调用点（by-row DELETE，孤儿行唯一出口），
    # 所以只能按动词判定：那一行的调用里不得出现 PUT。
    by_row_lines = [
        line for line in _frontend_text("composable").splitlines() if "`/favorites/${" in line
    ]
    verb, path = operation.split(" ", 1)
    assert not any(verb in line for line in by_row_lines), (
        f"前端出现了 {operation} 的调用点：要么把它补进 FRONTEND_CONSUMED，"
        f"要么撤销 {operation} 的『刻意不消费』记录"
    )
    doc = COVERAGE_DOC.read_text(encoding="utf-8")
    assert path in doc, f"{verb} {path} 未在 frontend/docs/API_COVERAGE.md 记录为刻意不消费"
