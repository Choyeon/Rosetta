"""收藏是"按 post_id 定位"的读口，必须与正文同源的可见性闸门。

``POST /api/favorites`` 原先只判"这行在不在"，``GET /api/favorites`` 又原样回显
``post.title / slug / cover_image / views``。于是任意登录用户可以把草稿 id 逐个
收藏（全局限流 100 req/min 足够遍历几万个 id），再一次性读回未发布文章的标题、
slug 与封面——和已经修过的"评论口泄漏草稿正文"是同一族，只是换了一个出口。

口径：
1. 写侧：草稿 / 待审 / 未来定时文章与不存在同形（404），作者本人例外；
2. 读侧：SQL 层过滤（``Favorite.post.has(...)``），与 ``total`` / ``total_pages``
   共用同一套 WHERE，避免"宣称还有下一页、拉过去是空的"；
3. staff 不过滤（后台需要能核对任何收藏行的真实内容）。
"""

from datetime import datetime, timedelta

import pytest

from backend.api.favorite import Favorite
from backend.core.auth import get_password_hash
from backend.models.blog import Post
from backend.models.user import User
from backend.utils.compat import UTC


async def _other_author(db_session) -> User:
    user = User(
        username="fav_other_author",
        email="fav_other_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _post(db_session, author: User, slug: str, status: str, **kwargs) -> Post:
    post = Post(
        title={"zh": f"标题-{slug}"},
        slug=slug,
        status=status,
        content="正文",
        excerpt={"zh": "摘要"},
        author_id=author.id,
        **kwargs,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.mark.asyncio
async def test_cannot_favorite_someone_elses_draft(client, db_session, auth_headers):
    """收藏别人的草稿必须 404（与"文章不存在"同形），不能建立引用行。"""
    author = await _other_author(db_session)
    draft = await _post(db_session, author, "fav-draft-hidden", "draft")

    response = await client.post("/api/favorites", json={"post_id": draft.id}, headers=auth_headers)
    assert response.status_code == 404, response.text

    listed = await client.get("/api/favorites", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_hides_legacy_rows_for_unpublished_posts(
    client, db_session, auth_headers, test_user, test_post
):
    """历史引用行（文章后来转草稿）不能继续回显标题，且 total 必须同步收缩。"""
    author = await _other_author(db_session)
    draft = await _post(db_session, author, "fav-legacy-draft", "draft")

    db_session.add_all(
        [
            Favorite(user_id=test_user.id, post_id=test_post.id),
            Favorite(user_id=test_user.id, post_id=draft.id),
        ]
    )
    await db_session.commit()

    body = (await client.get("/api/favorites", headers=auth_headers)).json()
    assert body["total"] == 1, "草稿引用仍被计入 total，分页会宣称拉不出来的内容"
    assert [item["post"]["id"] for item in body["items"]] == [test_post.id]
    assert body["total_pages"] == 1


@pytest.mark.asyncio
async def test_author_can_favorite_own_draft(client, db_session, test_user, auth_headers):
    """可见性闸门对作者本人放行：草稿是作者自己的工作集，不是别人的枚举面。"""
    own_draft = await _post(db_session, test_user, "fav-own-draft", "draft")

    response = await client.post(
        "/api/favorites", json={"post_id": own_draft.id}, headers=auth_headers
    )
    assert response.status_code == 200, response.text

    body = (await client.get("/api/favorites", headers=auth_headers)).json()
    assert [item["post"]["id"] for item in body["items"]] == [own_draft.id]


@pytest.mark.asyncio
async def test_scheduled_future_post_is_hidden(client, db_session, auth_headers):
    """status=published 但 published_at 在未来的定时文章，同样按不可见处理。"""
    author = await _other_author(db_session)
    future = await _post(
        db_session,
        author,
        "fav-future-post",
        "published",
        published_at=datetime.now(UTC) + timedelta(days=2),
    )

    response = await client.post(
        "/api/favorites", json={"post_id": future.id}, headers=auth_headers
    )
    assert response.status_code == 404, response.text
