"""评论写入口只剩一个：POST /api/posts/{post_id_or_slug}/comments（comments.py）。

blog.py 里曾有第二份登录态实现（POST /api/blog/posts/{post_id}/comments），它自己
`Comment(...)` 建对象，不读 comments 分组的 max_length / enable_nested，也不过 CSRF
与 IP 频控——表现是"后台关了嵌套，后台回复仍能写出多层链；超长评论返回 201 但前台渲染不出来"。
闸门写在服务层（CommentService.create_comment）只有在**只有一个调用者**时才等于全站口径。
"""

from __future__ import annotations

from httpx import AsyncClient

LEGACY_PATH = "/blog/posts/{post_id}/comments"
CANONICAL_PATH = "/posts/{post_id_or_slug}/comments"


def test_legacy_comment_post_is_retired_in_openapi() -> None:
    from backend.main import app

    paths = app.openapi()["paths"]
    # 读口（评论树）仍由 blog.py 提供，前端 SSR 在用——只有写口退役
    assert LEGACY_PATH in paths
    assert "get" in paths[LEGACY_PATH]
    assert "post" not in paths[LEGACY_PATH], "评论写入必须只有一个口，否则闸门会分叉"
    assert CANONICAL_PATH in paths
    assert "post" in paths[CANONICAL_PATH]


async def test_legacy_comment_post_returns_404(client: AsyncClient, staff_headers: dict) -> None:
    resp = await client.post(
        "/api/blog/posts/1/comments",
        json={"content": "这条不应该写得进来"},
        headers=staff_headers,
    )
    assert resp.status_code == 404
