"""照片缩略图投影（``Media.sizes`` → ``PhotoResponse.thumbnail_url``）回归。

口径：photos 表**没有**缩略图列，缩略档是读取时按 ``Media.file == Photo.url`` 从媒体库
现算的派生值，因此：

1. 派生值只写响应对象，绝不 ``setattr`` 到 ORM 实例上（``test_partial_update_guard``
   禁止照片实例带非映射属性）；
2. 无缩略档（外链、SVG、上传时后处理失败）回 null，消费方 ``thumbnail_url or url`` 回落原图；
3. 它是**展示字段**，可以随 600s 详情缓存一起滞后——原图 ``url`` 才是真值。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, event, select
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.api.gallery import _photo_responses, _photo_thumb_map
from backend.models.core import Media
from backend.models.gallery import Album, Photo
from backend.services.media_service import thumbnail_from_sizes

ORIGIN = "/media/uploads/image/1700000000_abc.jpg"
THUMB = "/media/uploads/image/1700000000_abc-thumbnail.jpg"
MEDIUM = "/media/uploads/image/1700000000_abc-medium.jpg"
LARGE = "/media/uploads/image/1700000000_abc-large.jpg"

FULL_SIZES = {
    "thumbnail": {"url": THUMB, "width": 150, "height": 150},
    "medium": {"url": MEDIUM, "width": 300, "height": 300},
    "large": {"url": LARGE, "width": 1024, "height": 1024},
}


# ==================== 纯函数：档位回落链 ====================


class TestThumbnailFromSizes:
    """脏值一律回 None，展示路径上不能因为一个坏形状把整个相册接口打成 500。"""

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            "裸字符串",
            [],
            {},
            {"thumbnail": None},
            {"thumbnail": "https://cdn/x.jpg"},
            {"thumbnail": {"width": 150}},
            {"thumbnail": {"url": ""}},
            {"thumbnail": {"url": 123}},
        ],
    )
    def test_unusable_shapes_return_none(self, value: object) -> None:
        assert thumbnail_from_sizes(value) is None

    def test_prefers_smallest_available_tier(self) -> None:
        assert thumbnail_from_sizes(FULL_SIZES) == THUMB

    def test_falls_back_through_the_chain(self) -> None:
        assert thumbnail_from_sizes({"medium": {"url": MEDIUM}, "large": {"url": LARGE}}) == MEDIUM
        assert thumbnail_from_sizes({"large": {"url": LARGE}}) == LARGE

    def test_skips_tiers_without_url(self) -> None:
        sizes = {"thumbnail": {"width": 150}, "medium": {"url": MEDIUM}}
        assert thumbnail_from_sizes(sizes) == MEDIUM

    def test_unknown_tier_keys_are_ignored(self) -> None:
        assert thumbnail_from_sizes({"full": {"url": ORIGIN}}) is None


# ==================== 读取面投影 ====================


async def _seed(db_session, photos: list[tuple[str, dict | None]]) -> Album:
    """建一个公开相册：每个元组是 ``(照片 URL, 对应媒体行的 sizes)``。

    ``sizes`` 为 None 表示这条照片在媒体库里没有对应行（外链/手工录入）。
    """
    album = Album(title="投影测试", is_published=True, photo_count=len(photos), cover=ORIGIN)
    db_session.add(album)
    await db_session.commit()
    await db_session.refresh(album)

    for index, (url, sizes) in enumerate(photos):
        if sizes is not None:
            db_session.add(
                Media(file=url, filename=url.rsplit("/", 1)[-1], file_type="image", sizes=sizes)
            )
        db_session.add(Photo(album_id=album.id, url=url, sort_order=index))
    await db_session.commit()
    await db_session.refresh(album)
    return album


class TestPhotoThumbnailProjection:
    @pytest.mark.asyncio
    async def test_public_album_detail_projects_the_thumbnail(
        self, client: AsyncClient, db_session
    ) -> None:
        album = await _seed(
            db_session, [(ORIGIN, FULL_SIZES), ("https://ext.example.com/a.jpg", None)]
        )

        r = await client.get(f"/api/gallery/albums/{album.id}")
        assert r.status_code == 200

        by_url = {p["url"]: p for p in r.json()["photos"]}
        assert by_url[ORIGIN]["thumbnail_url"] == THUMB
        # 原图地址是灯箱与下载的唯一真值，投影绝不覆写它
        assert by_url[ORIGIN]["url"] == ORIGIN
        assert by_url[ORIGIN]["original_url"] == ORIGIN
        # 媒体库对不上的外链照片回 null，由消费方回落原图
        assert by_url["https://ext.example.com/a.jpg"]["thumbnail_url"] is None

    @pytest.mark.asyncio
    async def test_album_cover_is_not_replaced_by_a_thumbnail(
        self, client: AsyncClient, db_session
    ) -> None:
        album = await _seed(db_session, [(ORIGIN, FULL_SIZES)])

        body = (await client.get(f"/api/gallery/albums/{album.id}")).json()
        assert body["cover"] == ORIGIN

    @pytest.mark.asyncio
    async def test_admin_photo_list_projects_the_thumbnail(
        self, client: AsyncClient, db_session, staff_headers: dict
    ) -> None:
        album = await _seed(db_session, [(ORIGIN, {"medium": {"url": MEDIUM}})])

        r = await client.get(f"/api/admin/gallery/albums/{album.id}/photos", headers=staff_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        assert items[0]["thumbnail_url"] == MEDIUM
        assert items[0]["url"] == ORIGIN

    @pytest.mark.asyncio
    async def test_thumbnail_equal_to_the_original_is_not_projected(
        self, client: AsyncClient, db_session
    ) -> None:
        """档位 URL 与原图相同（占位/自引用）时不给映射，否则网格会多下一遍同一个字节。"""
        album = await _seed(db_session, [(ORIGIN, {"thumbnail": {"url": ORIGIN}})])

        body = (await client.get(f"/api/gallery/albums/{album.id}")).json()
        assert body["photos"][0]["thumbnail_url"] is None

    @pytest.mark.asyncio
    async def test_projection_is_one_query_for_the_whole_page(
        self, client: AsyncClient, db_session, test_engine: AsyncEngine
    ) -> None:
        """整页照片共用一次 media SELECT，不在循环里逐个查（1 + page_size 次往返）。"""
        rows = [(f"/media/uploads/image/{i}.jpg", FULL_SIZES) for i in range(5)]
        album = await _seed(db_session, rows)

        media_reads: list[str] = []

        def _count(conn, cursor, statement, parameters, context, executemany):
            if "FROM media" in statement:
                media_reads.append(statement)

        event.listen(test_engine.sync_engine, "before_cursor_execute", _count)
        try:
            body = (await client.get(f"/api/gallery/albums/{album.id}")).json()
        finally:
            event.remove(test_engine.sync_engine, "before_cursor_execute", _count)

        assert len(body["photos"]) == 5
        assert all(p["thumbnail_url"] == THUMB for p in body["photos"])
        assert len(media_reads) == 1, f"照片缩略图对齐查了 {len(media_reads)} 次媒体表"

    @pytest.mark.asyncio
    async def test_oldest_media_row_wins_when_the_file_is_registered_twice(
        self, client: AsyncClient, db_session
    ) -> None:
        """media.file 没有唯一约束，重复登记时必须按 id 取第一条（读数不能随返回顺序漂）。"""
        album = await _seed(db_session, [(ORIGIN, FULL_SIZES)])
        db_session.add(
            Media(
                file=ORIGIN, filename="dup.jpg", file_type="image", sizes={"large": {"url": LARGE}}
            )
        )
        await db_session.commit()

        r = await client.get(f"/api/gallery/albums/{album.id}")
        assert r.json()["photos"][0]["thumbnail_url"] == THUMB

    @pytest.mark.asyncio
    async def test_derived_thumbnail_lives_inside_the_detail_cache_window(
        self, client: AsyncClient, db_session
    ) -> None:
        """缩略档是展示字段：媒体行被删掉后，TTL 内的详情响应仍回旧投影，``url`` 不受影响。"""
        album = await _seed(db_session, [(ORIGIN, FULL_SIZES)])

        first = (await client.get(f"/api/gallery/albums/{album.id}")).json()
        assert first["photos"][0]["thumbnail_url"] == THUMB

        await db_session.execute(delete(Media))
        await db_session.commit()

        second = (await client.get(f"/api/gallery/albums/{album.id}")).json()
        assert second["photos"][0]["thumbnail_url"] == THUMB
        assert second["photos"][0]["url"] == ORIGIN


# ==================== ORM 实例必须保持干净 ====================


class TestProjectionNeverMutatesTheOrm:
    @pytest.mark.asyncio
    async def test_helper_writes_the_response_not_the_photo_instance(self, db_session) -> None:
        album = Album(title="脏对象检查", is_published=True, photo_count=1)
        db_session.add(album)
        await db_session.commit()
        db_session.add(Photo(album_id=album.id, url=ORIGIN))
        db_session.add(Media(file=ORIGIN, filename="x.jpg", file_type="image", sizes=FULL_SIZES))
        await db_session.commit()

        photo = (
            await db_session.execute(select(Photo).where(Photo.album_id == album.id))
        ).scalar_one()

        thumbs = await _photo_thumb_map(db_session, [photo.url])
        responses = _photo_responses([photo], thumbs)

        assert responses[0].thumbnail_url == THUMB
        assert "thumbnail_url" not in photo.__dict__
        # commit 会 autoflush：脏属性一旦挂上去，这里就会因未知列报错
        await db_session.commit()
