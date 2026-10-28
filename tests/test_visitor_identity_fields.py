"""访客身份字段（`qq` / `github`）的写入闸门与真实消费面（批次 #35）。

这两列在库里、在响应模型里、在头像解析器里都已经存在，唯独**前台表单从不发送**，于是：

1. 留言板与评论的访客头像在生产库里长期只有 gravatar 一档（`email` 有值才有），解析器的
   `github → github.com/{u}.png` 与 `qq → q1.qlogo.cn` 两条分支是死代码；
2. 更坏的一半：公开写入口对这两列**不设形态限制**，`github="<img src=x onerror=…>"`、
   `github="https://github.com/evil"` 都写得进去。它不会 XSS（渲染侧是文本插值），但解析器会
   把它原样拼进 `https://github.com/{value}.png` 变成头像 URL，而 `author_name` 缺省时评论口
   还会拿 `raw.github` 当显示名发出去。口径见 AGENTS.md §12.8：会进访客页面的短字符串，
   **写入侧**必须拒掉标记语言，只守渲染侧不算守。

三条实现决定，都有对应断言：

- 形态定义**只有一份**（`backend/utils/ugc_fields.py`）。过去解析器自带正则、写入侧不设限，
  两边就会漂移：能写进库的值不等于能解析出头像的值。所以这里既测"脏值 422"，也测"两处吃同一份常量"。
- 422 之后必须**一行没写**。只断 422 会放过"先落库再校验"的坏实现——那条路径脏数据照样进了库，
  接口只是回了个错。
- 合法值必须**解析出对应头像**（github.png / q1.qlogo.cn），否则表单发得出去、消费面仍是空，
  这一批就算没做完。
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Comment, Post
from backend.models.guestbook import GuestbookEntry
from backend.utils.ugc_fields import (
    GITHUB_USERNAME_PATTERN,
    GITHUB_USERNAME_RE,
    QQ_PATTERN,
    QQ_RE,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

# 每一个值都在某一档上非法：标记语言、URL 形态（解析器过去会"顺手兼容"，正因如此写入侧必须挡）、
# 位数不足 / 超长、含非数字、超长用户名。
DIRTY_GITHUB = [
    "<img src=x onerror=alert(1)>",
    "https://github.com/octocat",
    "octo cat",
    "a" * 40,
]
DIRTY_QQ = ["1234", "123456789012", "12345678a", "https://wpa.qq.com/x"]


async def _counts(db: AsyncSession) -> tuple[int, int]:
    comments = (await db.execute(select(func.count()).select_from(Comment))).scalar() or 0
    entries = (await db.execute(select(func.count()).select_from(GuestbookEntry))).scalar() or 0
    return comments, entries


def _upstream(resolved: str | None) -> str:
    """`resolved_avatar_url` 是代理包装形态 `/api/media/avatar?src=<urlsafe-b64>`。

    直接对这个字符串断"含 github.com/xxx.png"永远为假——断的是**解码后**的上游 URL，
    那才是解析器真正选出来的分支。
    """
    if not resolved or "?src=" not in resolved:
        return resolved or ""
    token = resolved.split("?src=", 1)[1]
    return base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("utf-8", "replace")


class TestShapeIsDefinedOnce:
    """形态常量单源：新增第二份正则等于把"能写"与"能解析"重新拆成两套口径。"""

    def test_compiled_regexes_are_the_declared_patterns(self):
        assert GITHUB_USERNAME_RE.pattern == GITHUB_USERNAME_PATTERN
        assert QQ_RE.pattern == QQ_PATTERN

    def test_resolver_does_not_own_a_second_definition(self):
        source = (BACKEND_DIR / "services" / "avatar_resolver.py").read_text(encoding="utf-8")
        assert "from backend.utils.ugc_fields import" in source
        # 解析器可以保留自己那条"从 URL 里抠用户名"的兼容逻辑，但不得再 compile 身份形态正则
        assert "GITHUB_USERNAME_RE = re.compile" not in source
        assert "QQ_RE = re.compile" not in source

    def test_write_models_gate_both_fields(self):
        source = (BACKEND_DIR / "schemas" / "__init__.py").read_text(encoding="utf-8")
        assert source.count("pattern=_QQ_PATTERN") == 2, "评论与留言两个访客写口都要闸门"
        assert source.count("pattern=_GITHUB_USERNAME_PATTERN") == 2


class TestDirtyValuesRejectedBeforeWrite:
    async def test_comment_surface(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post
    ):
        before = await _counts(db_session)
        for field, values in (("github", DIRTY_GITHUB), ("qq", DIRTY_QQ)):
            for value in values:
                response = await client.post(
                    f"/api/posts/{test_post.id}/comments",
                    json={
                        "author_name": "形态闸门访客",
                        "content": "脏身份字段不应写进库",
                        field: value,
                    },
                )
                assert response.status_code == 422, f"{field}={value!r} → {response.status_code}"
        assert await _counts(db_session) == before, "422 之前已经把行写下去了"

    async def test_guestbook_surface(self, client: AsyncClient, db_session: AsyncSession):
        before = await _counts(db_session)
        for field, values in (("github", DIRTY_GITHUB), ("qq", DIRTY_QQ)):
            for value in values:
                response = await client.post(
                    "/api/guestbook",
                    json={
                        "author_name": "形态闸门访客",
                        "content": "脏身份字段不应写进库",
                        field: value,
                    },
                )
                assert response.status_code == 422, f"{field}={value!r} → {response.status_code}"
        assert await _counts(db_session) == before


class TestValidValuesReachTheAvatar:
    """合法值要一路走到头像 URL，否则这批只做了"能存"那一半。"""

    async def test_comment_guest_github_resolves_to_github_png(
        self, client: AsyncClient, test_post
    ):
        response = await client.post(
            f"/api/posts/{test_post.id}/comments",
            json={
                "author_name": "GitHub 访客",
                "content": "带 GitHub 用户名的访客评论",
                "github": "octocat",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["github"] == "octocat"
        assert "github.com/octocat.png" in _upstream(body["resolved_avatar_url"]), body

    async def test_comment_guest_qq_resolves_to_qlogo(self, client: AsyncClient, test_post):
        response = await client.post(
            f"/api/posts/{test_post.id}/comments",
            json={
                "author_name": "QQ 访客",
                "content": "带 QQ 号的访客评论",
                "qq": "1234567",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["qq"] == "1234567"
        assert "q1.qlogo.cn" in _upstream(body["resolved_avatar_url"]), body

    async def test_guestbook_qq_resolves_to_qlogo(self, client: AsyncClient):
        response = await client.post(
            "/api/guestbook",
            json={
                "author_name": "QQ 留言访客",
                "content": "带 QQ 号的留言，审核开关关闭时应直接返回头像。",
                "qq": "7777777",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["qq"] == "7777777"
        assert "q1.qlogo.cn" in _upstream(body["resolved_avatar_url"]), body

    async def test_hyphenated_github_username_is_legal(self, client: AsyncClient, test_post):
        """GitHub 用户名可以带连字符：闸门太紧会把真实账号挡在门外（表现是头像永远解析不出来）。"""
        response = await client.post(
            f"/api/posts/{test_post.id}/comments",
            json={
                "author_name": "连字符访客",
                "content": "带连字符的 GitHub 用户名应被接受",
                "github": "octocat-dev",
            },
        )
        assert response.status_code == 201, response.text
        assert "github.com/octocat-dev.png" in _upstream(response.json()["resolved_avatar_url"])


@pytest.mark.parametrize(
    ("which", "value", "legal"),
    [
        ("github", "octocat", True),
        ("github", "Octocat-9", True),
        ("github", "octocat-dev", True),
        # 纯数字串会被 GitHub 那条正则收下，所以边界必须逐条正则各测各的，
        # 用"两条里任意一条通过"当判据会把 QQ 的位数下限整个测成永真。
        ("qq", "9" * 5, True),
        ("qq", "9" * 11, True),
        ("qq", "9" * 4, False),
        ("qq", "9" * 12, False),
        ("qq", "1234567a", False),
        ("github", "-octocat", False),
        ("github", "octo_cat", False),
        ("github", "octo.cat", False),
    ],
)
def test_ugc_field_patterns_themselves(which: str, value: str, legal: bool):
    """单源常量自身的边界（写口与解析器共用，所以只在常量层测一次）。"""
    regex = GITHUB_USERNAME_RE if which == "github" else QQ_RE
    assert bool(regex.fullmatch(value)) is legal, f"{which} RE.fullmatch({value!r})"
