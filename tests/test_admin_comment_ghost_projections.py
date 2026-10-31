"""
批次 #153：后台评论投影里的「幽灵键」与 author_website 的四段接通。

`getattr(c, "author_url", None)` 读的是 `comments` 表上**根本不存在**的列，兜底值 None
让这个键看起来像"字段活着、只是这条没填"，OpenAPI 还给它写了说明——运营者在后台永远
看不到它，也没人知道它恒 null。同一族还有 `getattr(c, "avatar", None)`（无此列，且整个键
零消费方，前台读的是 `resolved_avatar_url`）与 `getattr(c, "author_avatar_source", None)`
（那是 schema 的**入参别名**，不是模型列）。三条一起退役。

另一端：`author_website` 是真实列（游客自填，登录作者回落账号 website），前台评论线程早就
在渲染，后台审核面一个消费点都没有——带外链的评论/留言在审核时看不出它给了访客一条外站链接。

四条守卫：
1. 源码与文档模型都不再有幽灵键，`author_website` 在两条口都在；
2. AST 扫描 `admin.py` 里对评论实例的 `getattr(..., 默认值)`，名字必须是真实列/关系
   （新增一条幽灵读取直接红，不必等人去 UI 里"发现某个字段一直是空"）；
3. GET 列表与 PATCH 响应的**实际键集**与各自文档模型字段集相等（文档不声明永不出现的键）；
4. `author_website` 的回落链在响应里成立。
"""

import ast
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.api.admin import CommentAdminItemDoc, CommentAdminUpdatedDoc
from backend.models.blog import Comment, Post

ADMIN_SRC = (Path(__file__).resolve().parents[1] / "backend" / "api" / "admin.py").read_text(
    encoding="utf-8"
)

GHOST_KEYS = ("author_url", "author_avatar")

COMMENT_REAL_ATTRS = set(Comment.__table__.columns.keys()) | set(
    Comment.__mapper__.relationships.keys()
)


def _rows(body: dict) -> list[dict]:
    return body["items"]


async def _make_post(db_session, author_id: int) -> Post:
    post = Post(
        title={"zh": "幽灵键测试文章", "en": "Ghost test"},
        content={"zh": "正文", "en": "Body"},
        slug=f"ghost-{uuid.uuid4().hex[:10]}",
        author_id=author_id,
        status="published",
        allow_comments=True,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _make_comment(db_session, post_id: int, **kwargs) -> Comment:
    defaults = {
        "post_id": post_id,
        "content": "幽灵键批次的测试评论正文。",
        "author_name": "访客甲",
        "status": "pending",
        "active": False,
    }
    defaults.update(kwargs)
    comment = Comment(**defaults)
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


class TestGhostKeysRetired:
    """投影、文档模型、OpenAPI 文档三处都不许留下恒 null 的幽灵键。"""

    @pytest.mark.parametrize("key", GHOST_KEYS)
    def test_doc_model_does_not_declare_ghost(self, key: str):
        assert key not in CommentAdminItemDoc.model_fields
        assert key not in CommentAdminUpdatedDoc.model_fields

    @pytest.mark.parametrize("key", GHOST_KEYS)
    def test_projection_does_not_emit_ghost(self, key: str):
        assert f'"{key}"' not in ADMIN_SRC, f"admin.py 仍在投影退役键 {key}"

    def test_ghost_attribute_reads_are_gone(self):
        """getattr(评论实例, "X", 默认值) 的 X 必须是真实列或关系名。

        兜底值把"读了一个不存在的列"伪装成"这条数据为空"，只能静态钉：
        删掉这条断言并恢复 `getattr(c, "author_url", None)` 会让本用例红。
        """
        offenders: list[str] = []
        for node in ast.walk(ast.parse(ADMIN_SRC)):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 3
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in {"c", "comment"}
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                continue
            name = node.args[1].value
            if name not in COMMENT_REAL_ATTRS:
                offenders.append(f"{node.args[0].id}.{name} (行 {node.lineno})")
        assert not offenders, f"评论投影在读模型上不存在的属性：{offenders}"

    def test_author_website_is_projected_on_both_verbs(self):
        assert ADMIN_SRC.count('"author_website":') == 2, "GET 与 PATCH 两条口都要投影它"
        assert "author_website" in CommentAdminItemDoc.model_fields
        assert "author_website" in CommentAdminUpdatedDoc.model_fields


class TestProjectionMatchesDocModel:
    """响应体键集 == 文档模型字段集，两条口各自成立。"""

    async def test_list_row_keys_match_item_doc(
        self, client: AsyncClient, staff_headers: dict, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(
            db_session, post.id, author_website="https://guest.example.com"
        )
        comment_id = comment.id
        resp = await client.get(
            "/api/admin/comments", headers=staff_headers, params={"page_size": 100}
        )
        assert resp.status_code == 200
        rows = [row for row in _rows(resp.json()) if row["id"] == comment_id]
        assert len(rows) == 1, "新建的评论没出现在列表里，键集断言会恒真"
        assert set(rows[0]) == set(CommentAdminItemDoc.model_fields)

    async def test_patch_body_keys_match_updated_doc(
        self, client: AsyncClient, staff_headers: dict, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)
        resp = await client.patch(
            f"/api/admin/comments/{comment.id}",
            headers=staff_headers,
            json={"status": "approved"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # 列表端点才输出头衔与举报标记：这两键不在 PATCH 的文档模型里，也不该出现在响应里
        assert set(body) == set(CommentAdminUpdatedDoc.model_fields)
        assert "title" not in body and "reported_at" not in body


class TestAuthorWebsiteFallback:
    """回落链：评论自填 → 登录作者账号 website → null。"""

    async def test_guest_value_and_login_fallback(
        self, client: AsyncClient, staff_headers: dict, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        guest = await _make_comment(db_session, post.id, author_website="https://guest.example.com")
        guest_id = guest.id
        # 网站在评论行上为空 → 投影回落到登录作者账号的 website
        test_user.website = "https://author.example.org"
        mine = await _make_comment(
            db_session, post.id, user_id=test_user.id, author_name="", author_website=None
        )
        mine_id = mine.id

        resp = await client.get(
            "/api/admin/comments", headers=staff_headers, params={"page_size": 100}
        )
        assert resp.status_code == 200
        by_id = {row["id"]: row for row in _rows(resp.json())}
        assert by_id[guest_id]["author_website"] == "https://guest.example.com"
        assert by_id[mine_id]["author_website"] == "https://author.example.org"
