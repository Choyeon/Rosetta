"""文章级「允许评论」开关必须真的拦住写入。

缺陷类：``Post.allow_comments`` 四段里有三段都在——编辑器开关发送（PostForm）、
存储（NOT NULL 列）、详情/列表响应回传（``is_pinned`` 旁边的那个布尔）——唯独
**唯一评论写口** ``CommentService.create_comment`` 从不读它，前台详情页也照样渲染输入框。
运营者在编辑器里关掉「允许评论」，得到的是一张"看起来关了"的开关：访客照样能发表，
后台回复口也照样能写。这与 AGENTS §9.1「写口 → 存储 → 响应模型 → 消费方」四段口径
里"有值没人执行"的假开关同型。

这里按两侧钉住：关闭后游客与登录用户都拿 403（业务码 COMMENT_POST_CLOSED，不是 401——
403 是文章策略，401 会被 apiFetch 判成登录过期并清登录态），已有评论仍可正常读；
打开后照常 201。另有一条顺序断言：站点级「整站关闭评论」优先于文章级开关。
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.models.blog import Comment, Post

pytestmark = pytest.mark.asyncio


async def _make_post(db_session, author_id: int, *, allow_comments: bool = True) -> Post:
    post = Post(
        title={"zh": "评论开关测试", "en": "Allow comments test"},
        content={"zh": "正文", "en": "Body"},
        slug=f"allow-comments-{uuid.uuid4().hex[:10]}",
        author_id=author_id,
        status="published",
        allow_comments=allow_comments,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _make_comment(db_session, post_id: int, *, content: str = "历史评论") -> Comment:
    comment = Comment(
        post_id=post_id,
        content=content,
        author_name="老读者",
        author_email="old-reader@example.com",
        status="approved",
        active=True,
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


async def _comment_count(db_session, post_id: int) -> int:
    return int(
        await db_session.scalar(select(func.count(Comment.id)).where(Comment.post_id == post_id))
        or 0
    )


class TestClosedPostRejectsWrites:
    async def test_guest_comment_rejected_with_post_closed(
        self, client: AsyncClient, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id, allow_comments=False)
        # 请求提交后 ORM 实例会过期，主键先取出来再用（否则属性访问触发同步 IO）
        post_id = post.id

        resp = await client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "关评论了还想留言", "author_name": "路人甲"},
        )

        assert resp.status_code == 403, resp.text
        assert resp.json()["error_code"] == "COMMENT_POST_CLOSED"
        assert await _comment_count(db_session, post_id) == 0

    async def test_authenticated_comment_rejected_too(
        self, client: AsyncClient, db_session, test_user, auth_headers
    ):
        """登录用户不能绕过：文章级开关对所有人一致（后台回复口也是这条写口）。"""
        post = await _make_post(db_session, test_user.id, allow_comments=False)
        post_id = post.id

        resp = await client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "登录了也不能写"},
            headers=auth_headers,
        )

        assert resp.status_code == 403, resp.text
        assert resp.json()["error_code"] == "COMMENT_POST_CLOSED"
        assert await _comment_count(db_session, post_id) == 0

    async def test_reply_to_existing_comment_also_rejected(
        self, client: AsyncClient, db_session, test_user, auth_headers
    ):
        """回复分支同一条闸门：闸门在 parent 校验之前，关闭的文章连回复也不收。"""
        post = await _make_post(db_session, test_user.id, allow_comments=False)
        post_id = post.id
        root = await _make_comment(db_session, post_id)
        root_id = root.id

        resp = await client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "回复一句", "parent_id": root_id},
            headers=auth_headers,
        )

        assert resp.status_code == 403, resp.text
        assert resp.json()["error_code"] == "COMMENT_POST_CLOSED"

    async def test_existing_comments_stay_readable(
        self, client: AsyncClient, db_session, test_user
    ):
        """关闭的是"再写"，不是"已写的"——历史评论不能跟着一起消失。"""
        post = await _make_post(db_session, test_user.id, allow_comments=False)
        post_id = post.id
        await _make_comment(db_session, post_id, content="关闭前留下的评论")

        resp = await client.get(f"/api/posts/{post_id}/comments")

        assert resp.status_code == 200, resp.text
        assert [c["content"] for c in resp.json()["items"]] == ["关闭前留下的评论"]


class TestOpenPostStillAcceptsWrites:
    async def test_guest_comment_accepted_when_open(
        self, client: AsyncClient, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id, allow_comments=True)
        post_id = post.id

        resp = await client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "正常留言", "author_name": "路人乙"},
        )

        assert resp.status_code == 201, resp.text
        assert await _comment_count(db_session, post_id) == 1


class TestEditorToggleReachesTheGate:
    async def test_editor_put_false_then_write_is_blocked(
        self, client: AsyncClient, db_session, admin_user, admin_headers
    ):
        """四段闭环：编辑器写 allow_comments=false → 落库 → 详情响应 → 写口按它拦。"""
        post = await _make_post(db_session, admin_user.id, allow_comments=True)
        post_id = post.id
        post_slug = post.slug

        updated = await client.put(
            f"/api/blog/posts/{post_id}",
            json={"allow_comments": False},
            headers=admin_headers,
        )
        assert updated.status_code in (200, 201), updated.text

        detail = await client.get(f"/api/blog/posts/{post_slug}")
        assert detail.status_code == 200, detail.text
        # 详情口回裸 PostLocalizedResponse（无 success/data 信封）
        assert detail.json()["allow_comments"] is False

        blocked = await client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "改完之后再试", "author_name": "路人丙"},
        )
        assert blocked.status_code == 403, blocked.text
        assert blocked.json()["error_code"] == "COMMENT_POST_CLOSED"


class TestSiteSwitchWinsOverPostSwitch:
    async def test_site_level_disable_is_reported_first(self, monkeypatch, db_session, test_user):
        """整站关评论时那句话才是真相（顺序口径，不走 HTTP，避免改全局设置影响邻例）。"""
        from backend.services import comment_service as cs

        async def _closed(_group, _db):
            return {"enable": False, "allow_guest": True, "max_length": 3000}

        monkeypatch.setattr(cs, "read_group", _closed)

        post = await _make_post(db_session, test_user.id, allow_comments=False)
        with pytest.raises(ValueError) as exc:
            await cs.CommentService.create_comment(
                db_session,
                post=post,
                data=cs.CommentCreate(content="任意内容", author_name="路人丁"),
                client_ip="127.0.0.1",
                user_agent="pytest",
                current_user=None,
            )
        assert str(exc.value) == "COMMENTS_DISABLED"
