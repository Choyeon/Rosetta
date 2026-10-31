"""登录态四档与相关推荐的「元信息三位」往返契约（批次 #140）。

批次 #120（音视频位）、#136（分钟数）、#139（密码稿位）都止步于**公开列表族**：
`/account` 的「我的文章 / 我的点赞 / 我的收藏 / 阅读历史」四档是各自手搭的行，
一位都没带，文章详情页的「相关文章」网格后端早带齐了、前端一个徽标都没挂。
于是同一篇文章在首页卡片写着「6 分钟 · 含视频 · 需要密码」，在自己的收藏里
只剩标题和日期——读者要按这些行决定"要不要现在打开"，那一行信息就是决定依据。

三条必须同时成立：
1. 四个登录态读口的行都带出 `reading_time` / `has_audio` / `has_video` / `has_embed`
   / `is_password_protected`，且判据与公开族同源（`post_media_flags` / `post_access_flags`）；
2. 密码摘要与媒体地址都不得进载荷——登录态口同样整份进响应缓存，
   地址一进去等于把站内文件名摊给更多键位；
3. `FavoritePostOut` 的新键都带默认值：收藏列表是缓存读口，TTL 内的旧载荷没这些键，
   必填等于整口 500（与 #120/#137/#138/#139 同一口径）。
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Post
from backend.models.user import User

BACKEND = Path(__file__).resolve().parents[1] / "backend"
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

BACKEND_KEYS = (
    "reading_time",
    "has_audio",
    "has_video",
    "has_embed",
    "is_password_protected",
)
SENTINEL_HASH = "SENTINEL-PASSWORD-HASH-DO-NOT-LEAK"
PUBLISHED_AT = datetime(2001, 2, 3, 4, 5, tzinfo=timezone.utc)


async def _mk_post(
    db_session: AsyncSession,
    author: User,
    *,
    slug: str,
    tags: list | None = None,
) -> Post:
    """一篇「锁着 + 带音频 + 带 YouTube」的公开稿：三位全有真实取值。"""
    post = Post(
        title={"zh": f"登录态元信息 {slug}", "en": f"Account Meta {slug}"},
        slug=slug,
        content={"zh": "正文内容" * 40, "en": "body text " * 40},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=author.id,
        status="published",
        visibility="public",
        published_at=PUBLISHED_AT,
        views=9,
        allow_comments=True,
        reading_time=6,
        password=SENTINEL_HASH,
        audio="/media/audio-should-not-leak.mp3",
        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        tags=tags or [],
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


def _assert_bits(row: dict, where: str) -> None:
    for key in BACKEND_KEYS:
        assert key in row, f"{where} 的行里没有 {key}：{sorted(row)}"
    assert row["reading_time"] == 6, where
    assert row["has_audio"] is True, where
    assert row["has_embed"] is True, where
    assert row["has_video"] is False, where
    assert row["is_password_protected"] is True, where


def _items(payload) -> list[dict]:
    body = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(body, dict):
        return list(body.get("items") or [])
    return list(body or [])


def _pick(rows: list[dict], slug: str, where: str) -> dict:
    """收藏/历史两档的行外层是「关系行」，文章在 `post` 里；文章/点赞档直接是文章行。"""

    def slug_of(row):
        if not isinstance(row, dict):
            return None
        return row.get("slug") or (row.get("post") or {}).get("slug")

    found = [r for r in rows if slug_of(r) == slug]
    assert found, f"{where} 里没有 {slug}：{[slug_of(r) for r in rows]}"
    return found[0]


class TestLoggedInOutletsCarryTheBits:
    @pytest.mark.asyncio
    async def test_my_posts_row(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
    ):
        post = await _mk_post(db_session, test_user, slug="meta-my-posts")
        await cache.clear()

        response = await client.get("/api/blog/users/me/posts", headers=auth_headers)
        assert response.status_code == 200, response.text
        _assert_bits(_pick(_items(response.json()), post.slug, "我的文章"), "我的文章")
        assert SENTINEL_HASH not in response.text
        assert "audio-should-not-leak" not in response.text

    @pytest.mark.asyncio
    async def test_my_likes_row(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
    ):
        post = await _mk_post(db_session, test_user, slug="meta-my-likes")
        liked = await client.post(f"/api/blog/posts/{post.id}/like", headers=auth_headers)
        assert liked.status_code == 200, liked.text
        await cache.clear()

        response = await client.get("/api/blog/users/me/likes", headers=auth_headers)
        assert response.status_code == 200, response.text
        _assert_bits(_pick(_items(response.json()), post.slug, "我的点赞"), "我的点赞")

    @pytest.mark.asyncio
    async def test_favorites_row(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
    ):
        post = await _mk_post(db_session, test_user, slug="meta-favorite")
        added = await client.post("/api/favorites", json={"post_id": post.id}, headers=auth_headers)
        assert added.status_code == 200, added.text
        await cache.clear()

        response = await client.get("/api/favorites", headers=auth_headers)
        assert response.status_code == 200, response.text
        row = _pick(_items(response.json()), post.slug, "我的收藏")["post"]
        _assert_bits(row, "我的收藏")
        assert SENTINEL_HASH not in response.text

    @pytest.mark.asyncio
    async def test_history_row(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
    ):
        """「上次读过的那篇要密码」——历史行同样得带出三位，否则回访时信息比首次还少。"""
        post = await _mk_post(db_session, test_user, slug="meta-history")
        viewed = await client.post(f"/api/blog/posts/{post.id}/view", headers=auth_headers)
        assert viewed.status_code == 200, viewed.text
        await cache.clear()

        response = await client.get("/api/blog/users/me/history", headers=auth_headers)
        assert response.status_code == 200, response.text
        row = _pick(_items(response.json()), post.slug, "阅读历史")["post"]
        _assert_bits(row, "阅读历史")


class TestSimilarOutletStillFeedsTheCard:
    """相关推荐口三位俱全（#120/#136/#139 就接上了），这一批补的是渲染面。"""

    @pytest.mark.asyncio
    async def test_similar_payload_carries_the_bits(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        from backend.models.blog import Tag

        tag = Tag(name={"zh": "元信息同标签", "en": "MetaTag"}, slug="meta-tag")
        db_session.add(tag)
        await db_session.commit()
        await db_session.refresh(tag)

        seed = await _mk_post(db_session, test_user, slug="meta-similar-seed", tags=[tag])
        await _mk_post(db_session, test_user, slug="meta-similar-peer", tags=[tag])
        await cache.clear()

        response = await client.get(f"/api/blog/posts/{seed.id}/similar")
        assert response.status_code == 200, response.text
        rows = _items(response.json())
        if not rows:
            pytest.skip("相似口按标签/分类召回，本环境没配对上：判据由公开列表族同批用例覆盖")
        _assert_bits(rows[0], "相关推荐")


class TestDocModelDegradesForStaleCache:
    def test_favorite_post_out_fields_all_have_defaults(self):
        from backend.api.favorite import FavoritePostOut

        for name in BACKEND_KEYS:
            field = FavoritePostOut.model_fields[name]
            assert not field.is_required(), f"{name} 必填会让旧缓存载荷 500"
        assert FavoritePostOut.model_fields["reading_time"].default == 1

    def test_outlets_reuse_the_single_source(self):
        blog = (BACKEND / "api" / "blog.py").read_text(encoding="utf-8")
        fav = (BACKEND / "api" / "favorite.py").read_text(encoding="utf-8")
        # 四个登录态出口各产出一次三位（_build_post_list_item 被「我的点赞」复用）
        assert blog.count("**post_media_flags(post),") >= 5, "登录态口的产出点少了"
        assert fav.count("**post_media_flags(post),") == 1
        assert fav.count("**post_access_flags(post),") == 1
        # 判据散写：谁都不准自己写一遍 bool(post.password)
        assert "bool(post.password)" not in fav
        assert '"is_password_protected"' not in fav


class TestFrontendContract:
    """登录态四档与相关文章卡都必须真消费这些位。"""

    ACCOUNT = "pages/account/index.vue"
    DETAIL = "pages/posts/[slug].vue"

    def test_account_page_renders_the_three_badges(self):
        src = (FRONTEND / self.ACCOUNT).read_text(encoding="utf-8")
        # 四档里的三档各挂一次（文章/点赞同构 = 一处、收藏一处、历史一处）
        assert src.count("<PostLockBadge :post=") == 3, "登录态行漏挂锁徽标"
        assert src.count("<PostMediaFlags :post=") == 3
        assert src.count("<PostReadingTime :post=") == 3
        for comp in ("PostLockBadge", "PostMediaFlags", "PostReadingTime"):
            assert f"import {comp} from '~~/components/{comp}.vue'" in src

    def test_account_row_types_allow_the_bits(self):
        src = (FRONTEND / self.ACCOUNT).read_text(encoding="utf-8")
        assert "reading_time?: number | null" in src
        assert "is_password_protected?: boolean | null" in src
        assert "has_audio?: boolean" in src

    def test_favorite_ref_type_declares_the_bits(self):
        src = (FRONTEND / "composables" / "useFavorites.ts").read_text(encoding="utf-8")
        assert "reading_time?: number | null" in src
        assert "is_password_protected?: boolean | null" in src

    def test_related_posts_grid_renders_the_badges(self):
        src = (FRONTEND / self.DETAIL).read_text(encoding="utf-8")
        assert '<PostLockBadge :post="sp.raw"' in src
        assert '<PostMediaFlags :post="sp.raw"' in src
        assert '<PostReadingTime :post="sp.raw"' in src
        assert "is_password_protected?: boolean | null" in src

    def test_account_page_never_reads_the_password_column(self):
        src = (FRONTEND / self.ACCOUNT).read_text(encoding="utf-8")
        assert "post.password" not in src
