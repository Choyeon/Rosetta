"""管理员删除用户的引用清理契约

`DELETE /api/admin/users/{id}` 实际是软删除（ban + deactivate），用户行仍在，
但会顺手清理可空外键引用：

- ``Comment.user_id``（nullable, SET NULL）→ 匿名保留
- ``GuestbookEntry.user_id``（nullable）→ 匿名保留
- ``Post.author_id``（NOT NULL + CASCADE）→ **不能**置空，文章继续归属原作者

删除用户时的引用清理原先包在 ``try / except Exception: pass`` 里，SQL 错误被吞掉后
照样返回"用户已删除"。本文件钉住两件事：清理真的发生，且清理失败必须让请求失败。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.auth import get_password_hash
from backend.models.blog import Comment, Post
from backend.models.guestbook import GuestbookEntry
from backend.models.user import User


async def _make_target_user(db_session) -> User:
    user = User(
        username="refs_target",
        email="refs_target@t.com",
        password_hash=get_password_hash("Str@Pass1!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_references(db_session, target: User):
    """给目标用户各建 1 条文章 / 评论 / 留言板引用"""
    post = Post(
        title={"zh": "引用清理测试文章"},
        slug=f"refs-post-{target.id}",
        content={"zh": "正文"},
        author_id=target.id,
        status="publish",
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    comment = Comment(
        post_id=post.id,
        user_id=target.id,
        author_name="refs_target",
        author_email="refs_target@t.com",
        content="一条来自目标用户的评论",
        status="approved",
        active=True,
    )
    guestbook = GuestbookEntry(
        user_id=target.id,
        author_name="refs_target",
        author_email="refs_target@t.com",
        content="一条来自目标用户的留言",
    )
    db_session.add_all([comment, guestbook])
    await db_session.commit()
    await db_session.refresh(comment)
    await db_session.refresh(guestbook)
    return post, comment, guestbook


@pytest.mark.asyncio
async def test_delete_user_anonymizes_nullable_refs_and_keeps_posts(
    client: AsyncClient, db_session, admin_headers: dict
):
    """可空引用置空、文章归属不动、请求成功"""
    target = await _make_target_user(db_session)
    post, comment, guestbook = await _seed_references(db_session, target)

    r = await client.delete(f"/api/admin/users/{target.id}", headers=admin_headers)
    assert r.status_code == 200, r.text

    comment_user_id = await db_session.scalar(
        select(Comment.user_id).where(Comment.id == comment.id)
    )
    guestbook_user_id = await db_session.scalar(
        select(GuestbookEntry.user_id).where(GuestbookEntry.id == guestbook.id)
    )
    post_author_id = await db_session.scalar(select(Post.author_id).where(Post.id == post.id))
    assert comment_user_id is None, "评论 user_id 未置空，仍指向已删除用户"
    assert guestbook_user_id is None, "留言板 user_id 未置空"
    assert post_author_id == target.id, "Post.author_id NOT NULL，不应被置空"


@pytest.mark.asyncio
async def test_delete_user_fails_loudly_when_cleanup_errors(
    client: AsyncClient, db_session, admin_headers: dict, monkeypatch
):
    """引用清理报错必须 500，不得吞掉后返回"用户已删除" """
    target = await _make_target_user(db_session)
    await _seed_references(db_session, target)

    def boom(*_args, **_kwargs):
        raise RuntimeError("cleanup exploded")

    monkeypatch.setattr("backend.api.admin.update", boom)

    # 测试客户端 raise_app_exceptions=True：异常能冒到调用方 == 没有被 except 吞掉。
    # 生产链路上同一异常由异常中间件转成 5xx，用户看到失败而不是假成功。
    with pytest.raises(RuntimeError, match="cleanup exploded"):
        await client.delete(f"/api/admin/users/{target.id}", headers=admin_headers)
