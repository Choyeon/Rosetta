"""列表口的媒体存在性三位（``has_audio`` / ``has_video`` / ``has_embed``）回归。

批次 #118 接通了详情页的播放器，但读者在列表里看不出来哪篇带音频/视频，音频稿
（长文朗读）就失去了"值得点进去"的提示。这一族最容易复现的老错法是**构造点漏写**：
``PostListItemLocalized`` 有四个手写构造点（主列表与搜索 / 推荐 / 相似 / 热榜），
批次 #118 的创建口漏三列就是同一个形状——所以本文件按**接口**逐个断言，而不是数代码。
批次 #121/#122 又把同一族推到**不走那个模型的裸 dict 投影**上：周期榜单、归档首页/年页/月页、
系列章节目录。它们各自是一条独立代码路径（列投影连 Post 实例都不建），少接一处的表现是
"列表页有徽标、归档页没有"这种没人报的缺陷。

四条口径：

1. **只带存在性，不带地址**：列表载荷被更多缓存与更多消费方复用，媒体路径仍只在详情口回。
2. **三个键必须有默认值**：列表载荷进响应缓存，旧载荷没这三键时 ``model_validate``
   会因为缺必填而整口 500（与「新增必填字段是反向同一条路」同源）。
3. **清空跟着变**：写口把音轨清掉后，下一次列表读数必须回到 False（否则徽标长期撒谎）。
4. **反向也要成立**（批次 #123）：`GET /api/blog/posts?media=audio|video` 筛出的集合必须
   与"这一批里徽标为真的集合"相等——判据分两处写就会分叉，且筛选取值必须进列表缓存键。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.post_series import SeriesPostItemDoc
from backend.core.cache import cache
from backend.models.blog import Category, Post
from backend.models.post_series import PostSeries
from backend.models.user import User
from backend.schemas import PostListItemLocalized
from backend.schemas.blog_reads import ArchivePostItem
from backend.services.post_access import MEDIA_FILTER_KINDS, media_presence_filter

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
    async def test_ranking_surface_carries_media_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """榜单口（/ranking/posts）自己手搭 dict，不经过 PostListItemLocalized。

        热门页的日/周/月/总榜四个页签都吃这条口，并把条目补齐成 PostCard 认得的形状，
        所以这里漏三位 = 「综合榜有徽标，切到周期榜整排消失」——构造点漏写的同一族。
        """
        await _make_post(db_session, test_user, test_category, slug="flags-ranking")
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="flags-ranking-plain",
            audio=None,
            video=None,
            video_url=None,
        )
        await cache.clear()
        # period=all 按累计 views 排序；周期榜走另一条候选查询，两条都要带三位
        for period in ("all", "week"):
            response = await client.get(
                "/api/ranking/posts", params={"period": period, "limit": 50}
            )
            assert response.status_code == 200, response.text
            items = _items(response.json())
            assert items, f"{period} 榜回空，候选查询没跑到（假通过）"
            for item in items:
                for addr in ("audio", "video", "video_url"):
                    assert addr not in item, f"{period} 榜不得带地址"
            media = _find(items, "flags-ranking")
            plain = _find(items, "flags-ranking-plain")
            assert media["has_audio"] is True, f"{period} 榜徽标永远不亮"
            assert media["has_embed"] is True
            assert media["has_video"] is False
            for key in MEDIA_KEYS:
                assert plain[key] is False, f"{period} 榜的 {key} 恒真"

    def test_ranking_doc_model_declares_the_three_keys(self):
        """文档模型漏声明 = OpenAPI 与真实载荷分叉，后台契约页看不到这三键。"""
        from backend.api.ranking import HotPostItemDoc

        fields = HotPostItemDoc.model_fields
        for key in MEDIA_KEYS:
            assert key in fields, f"HotPostItemDoc 缺 {key}"
            assert fields[key].is_required() is False, f"{key} 必填会让旧缓存载荷解不过去"

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


def _find_in_groups(payload, slug: str) -> dict:
    """归档口返回「年-月分组」数组，文章嵌在每组的 posts 里。"""
    groups = payload if isinstance(payload, list) else [payload]
    for group in groups:
        found = [p for p in (group.get("posts") or []) if p.get("slug") == slug]
        if found:
            return found[0]
    raise AssertionError(f"归档分组里找不到 {slug}")


class TestArchiveAndSeriesSurfaces:
    """批次 #122：归档三面与系列目录不走 ``PostListItemLocalized``，它们自己拼投影 dict。

    口径与前面完全一致（存在性三位、不带地址、键有默认值），但**代码路径是另一条**：
    归档首页走 ``PostRepository.get_archive_data`` 的列投影（连 Post 实例都不实例化），
    年页与月页走 blog.py 里的 ORM 行，系列目录走 post_series.py 的列投影。
    少接一处的表现是「列表页有徽标、归档页没有」——同一族的徽标只在部分页面亮。
    """

    # 测试独有年份：过去的月份，既不会被"定时未到"判据滤掉，也不会被别的用例塞满
    # （``get_archive_data`` 每月只留前 50 条）。
    YEAR = 2001
    MONTH = 2
    PUBLISHED_AT = datetime(2001, 2, 3, 4, 5, tzinfo=timezone.utc)

    async def _make_dated_post(
        self,
        db_session: AsyncSession,
        test_user: User,
        *,
        slug: str,
        audio: str | None = GOOD_AUDIO,
        video: str | None = None,
        video_url: str | None = GOOD_EMBED,
        series_id: int | None = None,
    ) -> Post:
        post = Post(
            title={"zh": "归档里的音视频稿", "en": "Archived Media Post"},
            slug=slug,
            content={"zh": "正文内容", "en": "body text"},
            excerpt={"zh": "摘要", "en": "excerpt"},
            author_id=test_user.id,
            status="published",
            visibility="public",
            published_at=self.PUBLISHED_AT,
            audio=audio,
            video=video,
            video_url=video_url,
            series_id=series_id,
            views=7,
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)
        return post

    @staticmethod
    def _assert_flags(item: dict, *, slug: str) -> None:
        assert item["has_audio"] is True, f"{slug} 归档口没带出音频位"
        assert item["has_embed"] is True, f"{slug} 归档口没带出嵌入位"
        assert item["has_video"] is False, f"{slug} 没写站内视频却报有视频"
        for addr in ("audio", "video", "video_url"):
            assert addr not in item, f"{slug} 的归档/目录载荷不得带媒体地址"

    @pytest.mark.asyncio
    async def test_archive_index_surface_carries_media_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        await self._make_dated_post(db_session, test_user, slug="flags-archive-index")
        await cache.clear()
        response = await client.get("/api/blog/archive")
        assert response.status_code == 200, response.text
        item = _find_in_groups(_payload(response.json()), "flags-archive-index")
        self._assert_flags(item, slug="flags-archive-index")

    @pytest.mark.asyncio
    async def test_archive_year_surface_carries_media_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        await self._make_dated_post(db_session, test_user, slug="flags-archive-year")
        await cache.clear()
        response = await client.get(f"/api/blog/archive/{self.YEAR}")
        assert response.status_code == 200, response.text
        item = _find_in_groups(_payload(response.json()), "flags-archive-year")
        self._assert_flags(item, slug="flags-archive-year")

    @pytest.mark.asyncio
    async def test_archive_month_surface_carries_media_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        await self._make_dated_post(db_session, test_user, slug="flags-archive-month")
        await cache.clear()
        response = await client.get(f"/api/blog/archive/{self.YEAR}/{self.MONTH}")
        assert response.status_code == 200, response.text
        data = _payload(response.json())
        item = _find(data["posts"], "flags-archive-month")
        self._assert_flags(item, slug="flags-archive-month")

    @pytest.mark.asyncio
    async def test_plain_post_reads_all_false_in_archive(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """恒 False 与恒 True 一样是缺陷：归档里每篇都挂徽标等于没有徽标。"""
        await self._make_dated_post(
            db_session,
            test_user,
            slug="flags-archive-plain",
            audio=None,
            video=None,
            video_url=None,
        )
        await cache.clear()
        data = _payload((await client.get(f"/api/blog/archive/{self.YEAR}")).json())
        item = _find_in_groups(data, "flags-archive-plain")
        for key in MEDIA_KEYS:
            assert item[key] is False, f"{key} 在无媒体的那篇上应回 False"

    @pytest.mark.asyncio
    async def test_series_chapter_list_carries_media_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        series = PostSeries(
            title={"zh": "音视频系列", "en": "Media Series"},
            slug="flags-media-series",
            is_active=True,
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        await self._make_dated_post(
            db_session,
            test_user,
            slug="flags-series-peer",
            series_id=series.id,
            audio=None,
            video_url=None,
        )
        await self._make_dated_post(
            db_session, test_user, slug="flags-series-row", series_id=series.id
        )

        response = await client.get("/api/series/flags-media-series")
        assert response.status_code == 200, response.text
        items = _payload(response.json())["posts"]
        for item in items:
            for key in MEDIA_KEYS:
                assert key in item, f"系列目录条目缺 {key}（构造点漏写）"
        # 键存在不算数：模型默认值就能造出"存在但恒 False"，所以同系列里必须有一篇真带音频
        row = _find(items, "flags-series-row")
        self._assert_flags(row, slug="flags-series-row")
        peer = _find(items, "flags-series-peer")
        assert [peer[k] for k in MEDIA_KEYS] == [False, False, False]


class TestNonModelDocPayloadsStillValidate:
    """归档与系列的文档模型同批给默认值——两条口的载荷都进缓存，旧载荷没这三键。"""

    def test_archive_item_defaults_the_three_keys(self):
        legacy = {
            "id": 1,
            "title": "旧归档载荷",
            "slug": "legacy-archive",
            "created_at": "2001-02-03T04:05:00",
            "published_at": "2001-02-03T04:05:00",
            "category": None,
            "views": 0,
        }
        item = ArchivePostItem.model_validate(legacy)
        for key in MEDIA_KEYS:
            assert getattr(item, key) is False
            assert ArchivePostItem.model_fields[key].is_required() is False

    def test_series_chapter_doc_defaults_the_three_keys(self):
        legacy = {
            "id": 1,
            "title": {"zh": "旧目录载荷"},
            "slug": "legacy-chapter",
            "cover_image": None,
            "series_order": 1,
            "views": 0,
            "published_at": "2001-02-03T04:05:00",
        }
        item = SeriesPostItemDoc.model_validate(legacy)
        for key in MEDIA_KEYS:
            assert getattr(item, key) is False
            assert SeriesPostItemDoc.model_fields[key].is_required() is False


class TestMediaFilterMatchesBadges:
    """``?media=audio|video`` 筛出来的必须正是"卡片上亮着同一个徽标"的那批文章。

    批次 #123 把徽标（存在性三位）反过来做成列表的筛选条件，于是判据第二次被需要：
    SQL 侧写成 ``IS NOT NULL``、Python 侧是 ``bool(col)`` 时，库里一条 ``audio=''``
    的文章会"筛得出来、却没有徽标"。所以这里的断言全部拿**同一份响应**里的三位
    去比筛选结果集合，而不是各自写一套期望值。
    """

    @staticmethod
    def _slugs(items: list[dict]) -> set[str]:
        return {item["slug"] for item in items}

    async def _seed(self, db_session, test_user, test_category):
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="filter-audio",
            audio=GOOD_AUDIO,
            video=None,
            video_url=None,
        )
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="filter-embed",
            audio=None,
            video=None,
            video_url=GOOD_EMBED,
        )
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="filter-empty-string",
            audio="",
            video="",
            video_url="",
        )
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="filter-plain",
            audio=None,
            video=None,
            video_url=None,
        )
        await cache.clear()

    @pytest.mark.asyncio
    async def test_audio_filter_equals_the_badged_set(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        await self._seed(db_session, test_user, test_category)
        everything = _items((await client.get("/api/blog/posts", params={"page_size": 50})).json())
        # 空串行在两判据里都算"没有"——这条先钉住 Python 侧，否则下面的集合相等可以恒真。
        assert _find(everything, "filter-empty-string")["has_audio"] is False
        assert _find(everything, "filter-audio")["has_audio"] is True
        badged = {item["slug"] for item in everything if item["has_audio"]}
        filtered = self._slugs(
            _items(
                (
                    await client.get("/api/blog/posts", params={"page_size": 50, "media": "audio"})
                ).json()
            )
        )
        assert filtered == badged
        assert "filter-embed" not in filtered

    @pytest.mark.asyncio
    async def test_video_filter_merges_site_video_and_embed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """`video` 档＝站内视频或第三方嵌入任一即可，与前端合成后的"有画面"徽标同集合。"""
        await self._seed(db_session, test_user, test_category)
        await _make_post(
            db_session,
            test_user,
            test_category,
            slug="filter-local-video",
            audio=None,
            video=GOOD_VIDEO,
            video_url=None,
        )
        await cache.clear()
        everything = _items((await client.get("/api/blog/posts", params={"page_size": 50})).json())
        badged = {item["slug"] for item in everything if item["has_video"] or item["has_embed"]}
        filtered = self._slugs(
            _items(
                (
                    await client.get("/api/blog/posts", params={"page_size": 50, "media": "video"})
                ).json()
            )
        )
        assert "filter-local-video" in badged
        assert "filter-embed" in badged
        assert filtered == badged

    @pytest.mark.asyncio
    async def test_unknown_media_value_behaves_like_no_filter(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """未知取值不过滤，也不 422：这是展示偏好，老链接不该因为一个多余参数就失效。"""
        await self._seed(db_session, test_user, test_category)
        everything = self._slugs(
            _items((await client.get("/api/blog/posts", params={"page_size": 50})).json())
        )
        for value in ("", "nonsense", "AUDIO", "audio; DROP TABLE posts"):
            response = await client.get("/api/blog/posts", params={"page_size": 50, "media": value})
            assert response.status_code == 200, response.text
            assert self._slugs(_items(response.json())) == everything

    @pytest.mark.asyncio
    async def test_media_bit_is_part_of_the_list_cache_key(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """判别位少了这一段＝筛选结果与全站列表共用一个键位（AGENTS §9.1 那条投毒面）。"""
        await self._seed(db_session, test_user, test_category)
        # 先暖"只看音频"这一档，再请求不带 media 的同参数列表：漏了判别位就会命中上一份。
        filtered = await client.get("/api/blog/posts", params={"page_size": 50, "media": "audio"})
        assert "filter-plain" not in self._slugs(_items(filtered.json()))
        plain = await client.get("/api/blog/posts", params={"page_size": 50})
        assert "filter-plain" in self._slugs(_items(plain.json()))
        # 缓存命中路径也必须仍是筛过的那一批（不是每次都回源）。
        again = await client.get("/api/blog/posts", params={"page_size": 50, "media": "audio"})
        slugs = self._slugs(_items(again.json()))
        assert "filter-plain" not in slugs
        assert slugs == self._slugs(_items(filtered.json()))


class TestMediaFilterPredicateIsDialectPortable:
    """谓词单源本身：白名单之外不产出条件，且两方言都编译成 COALESCE。"""

    def test_kind_whitelist(self):
        assert set(MEDIA_FILTER_KINDS) == {"audio", "video"}

    @pytest.mark.parametrize("kind", [None, "", "audio;", "images", "Video"])
    def test_non_whitelist_returns_none(self, kind):
        assert media_presence_filter(kind) is None

    @pytest.mark.parametrize("kind", MEDIA_FILTER_KINDS)
    def test_predicate_compiles_on_sqlite_and_postgres(self, kind):
        for dialect in (postgresql.dialect(), sqlite.dialect()):
            sql = str(media_presence_filter(kind).compile(dialect=dialect)).upper()
            # IS NOT NULL 只挡得住 None，空串会筛出没有徽标的文章；两方言都得是 COALESCE。
            assert "COALESCE" in sql
            assert "IS NOT NULL" not in sql
