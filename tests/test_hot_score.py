"""hot_score 物化列回归。

验证：
- recompute_hot_score / recompute_all_hot_scores 按公式回填
  （views + likes*5 + 有效评论*3，likes 来自 post_likes 关联表）。
- add_hot_score 原子自增/自减（写入事件增量维护用）。
- 模型 Post 含 hot_score 列且可排序（ranking 接口依赖）。
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.core.auth import get_password_hash
from backend.models.blog import Comment, Post
from backend.models.user import User
from backend.services.hot_score import (
    add_hot_score,
    recompute_all_hot_scores,
    recompute_hot_score,
)


def _make_user(db, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=get_password_hash("Testpass123"),
        is_active=True,
    )
    db.add(user)
    return user


def _make_post(db, slug: str, views: int = 0) -> Post:
    author = _make_user(db, f"{slug}-author")
    post = Post(
        title={"zh": f"t-{slug}"},
        content={"zh": f"c-{slug}"},
        slug=slug,
        status="published",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        views=views,
        author=author,
    )
    db.add(post)
    return post


def _add_likes(db, post: Post, n: int) -> None:
    """通过 post_likes 关联表给文章加 n 个点赞（Post 无 likes_count 列）。"""
    for i in range(n):
        user = _make_user(db, f"{post.slug}-like-{i}")
        post.likes.append(user)


@pytest.mark.asyncio
async def test_recompute_formula(db_session):
    post = _make_post(db_session, "hs-recompute", views=10)
    _add_likes(db_session, post, 2)
    await db_session.commit()
    await db_session.refresh(post)

    # 无评论：10 + 2*5 + 0 = 20
    new_score = await recompute_hot_score(db_session, post.id)
    assert new_score == 20

    # 加一条有效评论：10 + 10 + 3 = 23
    db_session.add(
        Comment(
            post_id=post.id,
            content="c1",
            status="approved",
            active=True,
            author_name="a",
        )
    )
    await db_session.commit()
    new_score = await recompute_hot_score(db_session, post.id)
    assert new_score == 23


@pytest.mark.asyncio
async def test_add_hot_score_atomic(db_session):
    post = _make_post(db_session, "hs-add", views=5)
    _add_likes(db_session, post, 1)
    await db_session.commit()
    await db_session.refresh(post)
    await recompute_hot_score(db_session, post.id)  # 5 + 5 = 10

    await add_hot_score(db_session, post.id, 5)
    await db_session.commit()
    score = (await db_session.execute(select(Post.hot_score).where(Post.id == post.id))).scalar()
    assert score == 15

    await add_hot_score(db_session, post.id, -3)
    await db_session.commit()
    score = (await db_session.execute(select(Post.hot_score).where(Post.id == post.id))).scalar()
    assert score == 12


@pytest.mark.asyncio
async def test_recompute_all(db_session):
    p1 = _make_post(db_session, "hs-all-1", views=100)
    p2 = _make_post(db_session, "hs-all-2", views=1)
    _add_likes(db_session, p1, 3)
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    db_session.add(
        Comment(
            post_id=p1.id,
            content="x",
            status="approved",
            active=True,
            author_name="a",
        )
    )
    await db_session.commit()

    affected = await recompute_all_hot_scores(db_session)
    assert affected >= 2
    s1 = (await db_session.execute(select(Post.hot_score).where(Post.id == p1.id))).scalar()
    # 100 + 3*5 + 3 = 118
    assert s1 == 118
    s2 = (await db_session.execute(select(Post.hot_score).where(Post.id == p2.id))).scalar()
    assert s2 == 1


@pytest.mark.asyncio
async def test_hot_score_ordering_column_exists(db_session):
    post = _make_post(db_session, "hs-order", views=7)
    _add_likes(db_session, post, 1)
    await db_session.commit()
    await db_session.refresh(post)
    await recompute_hot_score(db_session, post.id)
    # 能按 hot_score 排序（ranking 接口依赖）
    rows = (
        (await db_session.execute(select(Post.id).order_by(Post.hot_score.desc()))).scalars().all()
    )
    assert post.id in rows
