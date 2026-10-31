"""列表口的媒体存在性三位（``has_audio`` / ``has_video`` / ``has_embed``）回归。

批次 #118 接通了详情页的播放器，但读者在列表里看不出来哪篇带音频/视频，音频稿
（长文朗读）就失去了"值得点进去"的提示。这一族最容易复现的老错法是**构造点漏写**：
``PostListItemLocalized`` 有四个手写构造点（主列表与搜索 / 推荐 / 相似 / 热榜），
批次 #118 的创建口漏三列就是同一个形状——所以本文件按**接口**逐个断言，而不是数代码。

三条口径：

1. **只带存在性，不带地址**：列表载荷被更多缓存与更多消费方复用，媒体路径仍只在详情口回。
2. **三个键必须有默认值**：列表载荷进响应缓存，旧载荷没这三键时 ``model_validate``
   会因为缺必填而整口 500（与「新增必填字段是反向同一条路」同源）。
3. **清空跟着变**：写口把音轨清掉后，下一次列表读数必须回到 False（否则徽标长期撒谎）。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Category, Post
from backend.models.user import User
from backend.schemas import PostListItemLocalized

GOOD_AUDIO = "/media/2026/03/podcast.mp3"
GOOD_VIDEO = "/media/2026/03/clip.mp4"
GOOD_EMBED = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
MEDIA_KEYS = ("has_audio", "has_video", "has_embed")


def _payload(body: dict) -> dict:
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


def _items(body: dict) -> list[dict]:
    data = _payload(body)
    if isinstance(data, list):
        return data
    return data.get("items") or data.get("posts") or []


def _find(items: list[dict], slug: str) -> dict:
    for item in items:
        if item.get("slug") == slug:
            return item
    raise AssertionError(f"列表里没有 {slug}：{[i.get('slug') for i in items]}")


async def _make_post(
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
    *,
    slug: str,
    audio: str | None = GOOD_AUDIO,
    video: str | None = None,
    video_url: str | None = GOOD_EMBED,
) -> Post:
    post = Post(
        title={"zh": "带音视频的文章", "en": "Post With Media"},
        slug=slug,
        content={"zh": "正文内容", "en": "body text"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="published",
        visibility="public",
        audio=audio,
        video=video,
        video_url=video_url,
        views=50,
        allow_comments=True,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


class TestEveryListSurface:
    """四条真实列表口都带出这三位——构造点漏一处，那一族的卡片就没有徽标。"""

    @pytest.mark.asyncio
    async def test_main_list_carries_media_flags_and_no_addresses(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="flags-list",
            video=GOOD_VIDEO,
        )
        await cache.clear()
        response = await client.get("/api/blog/posts", params={"page_size": 50})
        assert response.status_code == 200, response.text
        item = _find(_items(response.json()), "flags-list")
        assert item["has_audio"] is True
        assert item["has_video"] is True
        assert item["has_embed"] is True
        for key in ("audio", "video", "video_url"):
            assert key not in item, "列表载荷不得带媒体地址（只有详情口回）"

    @pytest.mark.asyncio
    async def test_plain_post_reads_all_three_false(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="flags-plain",
            audio=None,
            video=None,
            video_url=None,
        )
        await cache.clear()
        items = _items((await client.get("/api/blog/posts", params={"page_size": 50})).json())
        item = _find(items, "flags-plain")
        for key in MEDIA_KEYS:
            assert item[key] is False, f"{key} 恒真等于给每篇都挂徽标"

    @pytest.mark.asyncio
    async def test_hot_surface_carries_media_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        await _make_post(db_session, test_user, test_category, slug="flags-hot")
        await cache.clear()
        response = await client.get("/api/blog/posts/hot", params={"limit": 50})
        assert response.status_code == 200, response.text
        item = _find(_items(response.json()), "flags-hot")
        assert item["has_audio"] is True
        assert item["has_embed"] is True

    @pytest.mark.asyncio
    async def test_recommended_surface_carries_media_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        await _make_post(db_session, test_user, test_category, slug="flags-reco")
        await cache.clear()
        response = await client.get("/api/blog/posts/recommended", params={"page_size": 50})
        assert response.status_code == 200, response.text
        item = _find(_items(response.json()), "flags-reco")
        assert item["has_audio"] is True

    @pytest.mark.asyncio
    async def test_similar_surface_declares_the_three_keys(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """相似口按标签/分类取邻居，这里钉"键在载荷里"（漏写构造点时键根本不存在）。"""
        base = await _make_post(
            db_session,
            test_user,
            test_category,
            slug="flags-similar-base",
            audio=None,
            video=None,
            video_url=None,
        )
        await _make_post(db_session, test_user, test_category, slug="flags-similar-peer")
        await cache.clear()
        response = await client.get(f"/api/blog/posts/{base.id}/similar")
        assert response.status_code == 200, response.text
        items = _items(response.json())
        assert items, "同分类同作者却回空，相似口的构造分支没被跑到（假通过）"
        for item in items:
            for key in MEDIA_KEYS:
                assert key in item
        # 键存在不算数（模型默认值就能造出"存在但恒 False"）：得有一篇真的带音频
        assert any(item["has_audio"] for item in items), "相似口这一族徽标永远不亮"


class TestClearingMediaUpdatesFlags:
    @pytest.mark.asyncio
    async def test_clearing_audio_removes_the_flag(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        post = await _make_post(db_session, test_user, test_category, slug="flags-clear")
        await cache.clear()
        before = _find(_items((await client.get("/api/blog/posts")).json()), "flags-clear")
        assert before["has_audio"] is True

        cleared = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"audio": "", "video_url": ""},
        )
        assert cleared.status_code == 200, cleared.text
        await cache.clear()
        after = _find(_items((await client.get("/api/blog/posts")).json()), "flags-clear")
        assert after["has_audio"] is False
        assert after["has_embed"] is False


class TestWriterSideMergesCurrentRow:
    @pytest.mark.asyncio
    async def test_put_with_only_video_keeps_audio_flag(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        """PUT 只提交 video 时 audio 仍在（exclude_unset 增量语义），徽标两位都得在。"""
        post = await _make_post(
            db_session,
            test_user,
            test_category,
            slug="flags-partial",
            video=None,
        )
        await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"video": GOOD_VIDEO},
        )
        await cache.clear()
        item = _find(_items((await client.get("/api/blog/posts")).json()), "flags-partial")
        assert item["has_audio"] is True
        assert item["has_video"] is True


class TestLegacyCachedPayloadStillValidates:
    """旧载荷缺这三个键必须仍能解出来——列表载荷是进响应缓存的。"""

    def test_payload_without_the_three_keys_still_validates(self):
        legacy = {
            "id": 1,
            "title": "旧载荷",
            "slug": "legacy",
            "author": {
                "id": 1,
                "username": "admin",
                "nickname": "Admin",
                "avatar": None,
                "title": None,
                "created_at": "2026-01-01T00:00:00",
            },
            "status": "published",
            "post_type": "post",
            "views": 0,
            "is_pinned": False,
            "created_at": "2026-01-01T00:00:00",
        }
        item = PostListItemLocalized.model_validate(legacy)
        for key in MEDIA_KEYS:
            assert getattr(item, key) is False

    def test_flags_are_optional_in_the_model(self):
        for key in MEDIA_KEYS:
            field = PostListItemLocalized.model_fields[key]
            assert field.is_required() is False, f"{key} 给了必填 = 旧缓存载荷整口 500"
