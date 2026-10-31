"""评论表情反应族（``/api/comments/{comment_id}/reactions*``）的前后端路径契约。

三条口的路径形状很接近（POST 集合口带 body、DELETE 把 emoji 放在**路径**上、GET 同集合口
读统计），写错的表现是 405/404 或"点亮了取消不掉"，TypeScript 拦不住，所以拿**生成后的**
OpenAPI 文档对表（口径见 AGENTS.md §7.4 第 4 条）。

另一半契约是闸门本身：``GET``/``POST`` 两个口都必须先过
``services/comment_access.py::readable_comment_or_404``（它内部走 ``post_access`` 的判定），
否则草稿与加密文章的评论计数能按 comment_id
枚举。这条用源码级断言钉住——它描述的是"这个口有没有调那道闸门"，行为回归在
``tests/test_comment_reaction_gate.py``。
"""

from pathlib import Path

import pytest

from backend.main import app

REPO = Path(__file__).resolve().parents[1]
COMPOSABLE = REPO / "frontend" / "composables" / "useComments.ts"
COMMENT_ITEM = REPO / "frontend" / "components" / "CommentItem.vue"
BACKEND_ROUTES = REPO / "backend" / "api" / "comment_reactions.py"
COMMENT_ACCESS = REPO / "backend" / "services" / "comment_access.py"

# (OpenAPI 里的操作, 前端字面量, 前端文件)
FRONTEND_CONSUMED = [
    ("GET /api/comments/{comment_id}/reactions", "`/comments/${id}/reactions`", "composable"),
    (
        "POST /api/comments/{comment_id}/reactions",
        "`/comments/${id}/reactions`, {",
        "composable",
    ),
    (
        "DELETE /api/comments/{comment_id}/reactions/{emoji}",
        "`/comments/${id}/reactions/${encodeURIComponent(emoji)}`",
        "composable",
    ),
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


def _frontend_text() -> str:
    return "\n".join(f.read_text(encoding="utf-8") for f in (COMPOSABLE, COMMENT_ITEM))


@pytest.mark.parametrize(("operation", "literal", "where"), FRONTEND_CONSUMED)
def test_reaction_operation_exists_and_has_a_frontend_call_site(operation, literal, where):
    ops = _operations()
    assert operation in ops, f"后端已无 {operation}；前端消费点需要同步撤销"
    assert literal in _frontend_text(), f"{where} 里找不到 {operation} 的调用字面量 {literal}"


def test_read_and_add_mouths_go_through_the_post_access_gate():
    """GET 与 POST 都必须调 readable_comment_or_404；DELETE 刻意不接（见模块 docstring）。

    判据单源在 ``backend/services/comment_access.py``（它内部走 post_access 的
    status / 定时 / 密码三重判定），所以这里既钉"两个口各调一次闸门"，也钉
    "路由文件里没有第二套判定"——闸门改名要一起改这两处断言。
    """
    src = BACKEND_ROUTES.read_text(encoding="utf-8")
    assert src.count("await readable_comment_or_404(db, comment_id, current_user)") == 2, (
        "反应口只剩一处或涨到多处闸门调用都值得重看：GET/POST 两个口要各调一次，DELETE 不该调"
    )
    assert "from backend.services.comment_access import readable_comment_or_404" in src, (
        "闸门要走共享服务，不要在路由里就地展开评论可读性判定"
    )
    gate_src = COMMENT_ACCESS.read_text(encoding="utf-8")
    assert "post_is_publicly_visible" in gate_src and "post_content_unlocked" in gate_src, (
        "闸门必须复用 services/post_access 的判据，不要在路由里另写一套 status/密码判定"
    )
    assert 'status == "published"' not in src and "Post.password" not in src, (
        "路由文件里出现第二套可见性判定 = 两处会分叉，判据只在服务层那一份"
    )
