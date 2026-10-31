"""作者统计口（批次 #148）：读数必须有消费方，且每一族归到自己的开关下。

`GET /api/users/{user_id}/stats` 四段里缺的是最后一段：投影齐全（user_id / posts_count /
comments_count / total_views / total_likes / joined_at）、隐私 404 也接了，但前台
`/authors/<username>` 只在读数行显示「N 篇文章」（那个数来自文章列表的 `total`），
四个聚合从来没有第二个人读过。这一批把它接上，顺带收口两处跟着暴露出来的口径问题：

1. **by-id 口对前台没用**。作者主页按用户名寻址，统计口只认内部主键的话，页面必须等资料
   请求回来才能拼第二次请求的 URL——SSR 从并发三跳变成串行两跳。所以补了同口径的
   `/username/{username}/stats`（聚合与隐私判定共用 `_user_stats_payload`，不是第二份实现）。
2. **统计只认 `show_stats`，不认它聚合的那些族自己的开关**。`show_posts=False` 时文章列表
   已经回空页，统计口却仍按真实数据算出「累计阅读 1234」：主页同一段落里摆着
   「0 篇文章」+「1234 次浏览」，等于替作者宣布「有内容，只是不给看」——正是
   「隐藏即空」要避免的可区分状态。`show_comments` 同理。
3. **点赞数原先把草稿也算进去**（`where` 只圈了 `author_id`），匿名读数里就含着草稿收到的
   点赞；聚合口一律叠 `publicly_listable_posts()`，与文章数 / 浏览量同轨。
"""

from __future__ import annotations

from datetime import timedelta

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import create_access_token, get_password_hash
from backend.models.blog import Comment, Post, post_likes
from backend.models.user import User, UserPreference


@pytest_asyncio.fixture
async def stats_author(db_session: AsyncSession) -> User:
    """一位有 2 篇公开稿 + 1 篇草稿、公开稿带浏览量/点赞/评论的作者。

    首轮必须先读到"真实读数"，隐藏语义的断言才有意义：源数据全是 0 的话，
    "关了开关就是 0"会因为恒真而假绿。
    """
    user = User(
        username="statsauthor",
        email="statsauthor@example.invalid",
        password_hash=get_password_hash("Probe@12345"),
        nickname="统计作者",
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserPreference(
            user_id=user.id,
            public_profile=True,
            show_posts=True,
            show_comments=True,
            show_stats=True,
        )
    )

    # published_at 留 NULL：匿名谓词是 `IS NULL OR <= now()`，SQLite 把 aware datetime
    # 存成带 +00:00 的字符串后按字符串比较，刚写入的行会判成"在未来"而被筛空。
    open_one = Post(
        title={"zh": "统计样稿一"},
        slug="stats-sample-one",
        content={"zh": "正文"},
        author_id=user.id,
        status="published",
        views=40,
    )
    open_two = Post(
        title={"zh": "统计样稿二"},
        slug="stats-sample-two",
        content={"zh": "正文"},
        author_id=user.id,
        status="published",
        views=5,
    )
    draft = Post(
        title={"zh": "统计草稿"},
        slug="stats-draft-post",
        content={"zh": "正文"},
        author_id=user.id,
        status="draft",
        views=999,
    )
    db_session.add_all([open_one, open_two, draft])
    await db_session.flush()

    liker = User(
        username="statsliker",
        email="statsliker@example.invalid",
        password_hash=get_password_hash("Probe@12345"),
        is_active=True,
    )
    db_session.add(liker)
    await db_session.flush()
    # 公开稿各 1 赞，草稿 1 赞：草稿那条不该进匿名 total_likes。
    await db_session.execute(
        insert(post_likes).values(
            [
                {"post_id": open_one.id, "user_id": liker.id},
                {"post_id": open_two.id, "user_id": liker.id},
                {"post_id": draft.id, "user_id": liker.id},
            ]
        )
    )
    db_session.add(
        Comment(
            post_id=open_one.id,
            user_id=user.id,
            content="一条过审评论",
            author_name="statsauthor",
            status="approved",
            active=True,
        )
    )
    await db_session.commit()
    return user


async def stats_for(client: AsyncClient, user_id: int, username: str) -> dict:
    """两条口都读一遍，并断言它们给出同一个数（同一份实现才允许分叉成两个入口）。"""
    by_id = await client.get(f"/api/users/{user_id}/stats")
    by_name = await client.get(f"/api/users/username/{username}/stats")
    assert by_id.status_code == 200, by_id.text
    assert by_name.status_code == 200, by_name.text
    assert by_id.json() == by_name.json(), "by-username 口不得另写一套聚合口径"
    return by_id.json()


async def flip(db_session: AsyncSession, author: User, **switches: bool) -> None:
    pref = (
        await db_session.execute(select(UserPreference).where(UserPreference.user_id == author.id))
    ).scalar_one()
    for key, value in switches.items():
        setattr(pref, key, value)
    await db_session.commit()


class TestBaselineReads:
    """开关全开时给出真实读数——后面所有"归零"断言的前置，缺了它全是恒真。"""

    async def test_anonymous_sees_real_aggregates(
        self, db_session, client: AsyncClient, stats_author
    ):
        body = await stats_for(client, stats_author.id, stats_author.username)
        assert body["user_id"] == stats_author.id
        assert body["posts_count"] == 2, body
        assert body["total_views"] == 45, body
        assert body["comments_count"] == 1, body
        assert body["joined_at"]

    async def test_draft_likes_do_not_leak_into_anonymous_read(self, client, stats_author):
        """草稿收到 1 赞：匿名 total_likes 必须是 2 而不是 3。"""
        body = await stats_for(client, stats_author.id, stats_author.username)
        assert body["total_likes"] == 2, body

    async def test_username_lookup_is_case_insensitive(self, client, stats_author):
        res = await client.get("/api/users/username/StatsAuthor/stats")
        assert res.status_code == 200, res.text
        assert res.json()["total_views"] == 45


class TestHiddenMeansEmpty:
    async def test_show_stats_off_returns_all_zeros(
        self, db_session, client: AsyncClient, stats_author
    ):
        await flip(db_session, stats_author, show_stats=False)
        body = await stats_for(client, stats_author.id, stats_author.username)
        assert [
            body[k] for k in ("posts_count", "comments_count", "total_views", "total_likes")
        ] == [0, 0, 0, 0]
        # 注册时间不是活动读数，隐藏统计不该把它一起抹掉
        assert body["joined_at"]

    async def test_show_posts_off_zeroes_only_the_post_family(
        self, db_session, client: AsyncClient, stats_author
    ):
        """「0 篇文章」旁边不能同时摆出「45 次浏览」：文章族跟着归零，评论族不受牵连。"""
        await flip(db_session, stats_author, show_posts=False)
        body = await stats_for(client, stats_author.id, stats_author.username)
        assert body["posts_count"] == 0 and body["total_views"] == 0 and body["total_likes"] == 0, (
            body
        )
        assert body["comments_count"] == 1, body

    async def test_show_comments_off_zeroes_the_comment_count(
        self, db_session, client: AsyncClient, stats_author
    ):
        await flip(db_session, stats_author, show_comments=False)
        body = await stats_for(client, stats_author.id, stats_author.username)
        assert body["comments_count"] == 0, body
        assert body["total_views"] == 45, body

    async def test_author_and_staff_see_the_real_numbers(
        self, db_session, client: AsyncClient, stats_author
    ):
        await flip(
            db_session, stats_author, show_stats=False, show_posts=False, show_comments=False
        )
        token = create_access_token(
            {"sub": str(stats_author.id), "type": "access"},
            expires_delta=timedelta(minutes=5),
        )
        mine = await client.get(
            f"/api/users/username/{stats_author.username}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert mine.status_code == 200, mine.text
        assert mine.json()["total_views"] == 45
        assert mine.json()["comments_count"] == 1


class TestHiddenProfileIsFourOhFour:
    """`public_profile=False` 是主页级的「不存在」，统计是它的子资源，不能只放 404 给资料口。"""

    async def test_both_stats_routes_return_404_when_profile_hidden(
        self, db_session, client: AsyncClient, stats_author
    ):
        await flip(db_session, stats_author, public_profile=False)
        for path in (
            f"/api/users/{stats_author.id}/stats",
            f"/api/users/username/{stats_author.username}/stats",
        ):
            res = await client.get(path)
            assert res.status_code == 404, (path, res.text)

    async def test_unknown_username_is_404_not_500(self, client: AsyncClient):
        res = await client.get("/api/users/username/whohasneverexisted/stats")
        assert res.status_code == 404, res.text

    async def test_hidden_author_default_view_is_not_a_zero_read_but_absent(
        self, db_session, client: AsyncClient, stats_author
    ):
        """缺偏好行（从未动过设置）时按建表默认可见，且读数与有偏好行时一致。"""
        row = (
            await db_session.execute(
                select(UserPreference).where(UserPreference.user_id == stats_author.id)
            )
        ).scalar_one()
        await db_session.delete(row)
        await db_session.commit()
        body = await stats_for(client, stats_author.id, stats_author.username)
        assert body["total_views"] == 45


class TestSingleSourceContract:
    """两条口必须共用实现，且文档模型不能承诺第三种语义。"""

    @staticmethod
    def _src() -> str:
        from pathlib import Path

        return (Path(__file__).resolve().parents[1] / "backend" / "api" / "users.py").read_text(
            encoding="utf-8"
        )

    def test_aggregation_is_defined_once(self):
        src = self._src()
        assert src.count("func.sum(Post.views)") == 1, "浏览量聚合被抄第二份就是分叉的开始"
        assert "async def _user_stats_payload" in src
        # by-id 与 by-username 都只组装参数后转调同一 helper
        assert src.count("await _user_stats_payload(") == 2, src.count("await _user_stats_payload(")

    def test_stats_route_is_documented_and_draft_wording_gone(self):
        assert "/api/users/username/{username}/stats" in self._src()
        assert "本人全部文章（含草稿）收到的点赞总数" not in self._src()
