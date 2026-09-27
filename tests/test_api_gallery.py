"""
相册（Gallery）API 自动化测试

覆盖范围：
- 公开接口：相册列表 / 相册详情（含照片）
- 管理接口：相册 CRUD、照片 CRUD
- 权限：未登录 / 普通用户 / staff 用户的访问边界
- photo_count 自动维护
- 批量删除照片（一次请求 + missing_ids 上报）
- 缓存失效
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update

from backend.models.gallery import Album, Photo

# ==================== 公开接口 ====================


class TestPublicGallery:
    """公开相册接口：所有人可见，仅返回 is_published=True 的相册"""

    @pytest.mark.asyncio
    async def test_public_album_list_empty(self, client: AsyncClient):
        """无相册时返回空列表"""
        r = await client.get("/api/gallery/albums", params={"page_size": 50})
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_public_album_list_only_published(
        self, client: AsyncClient, db_session, staff_headers
    ):
        """公开列表只返回 is_published=True 的相册"""
        # 创建两个相册：一个公开，一个私密
        pub = Album(title="公开相册", description="desc", is_published=True, photo_count=0)
        priv = Album(title="私密相册", description="desc", is_published=False, photo_count=0)
        db_session.add_all([pub, priv])
        await db_session.commit()

        r = await client.get("/api/gallery/albums", params={"page_size": 50})
        assert r.status_code == 200
        titles = [a["title"] for a in r.json()["items"]]
        assert "公开相册" in titles
        assert "私密相册" not in titles

    @pytest.mark.asyncio
    async def test_public_album_detail_with_photos(
        self, client: AsyncClient, db_session, staff_headers
    ):
        """公开相册详情包含照片列表"""
        album = Album(title="旅行", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        photos = [
            Photo(album_id=album.id, url="/media/uploads/a.jpg", title="p1", sort_order=1),
            Photo(album_id=album.id, url="/media/uploads/b.jpg", title="p2", sort_order=2),
        ]
        db_session.add_all(photos)
        await db_session.commit()

        r = await client.get(f"/api/gallery/albums/{album.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "旅行"
        assert len(data["photos"]) == 2
        assert data["photos"][0]["url"] == "/media/uploads/a.jpg"

    @pytest.mark.asyncio
    async def test_public_album_detail_private_404(
        self, client: AsyncClient, db_session, staff_headers
    ):
        """私密相册通过公开接口返回 404"""
        album = Album(title="私密", is_published=False, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        r = await client.get(f"/api/gallery/albums/{album.id}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_public_album_detail_not_found(self, client: AsyncClient):
        """不存在的相册返回 404"""
        r = await client.get("/api/gallery/albums/99999")
        assert r.status_code == 404


# ==================== 管理接口 - 相册 CRUD ====================


class TestAdminAlbumCrud:
    """管理员相册增删改查"""

    @pytest.mark.asyncio
    async def test_admin_create_album(self, client: AsyncClient, staff_headers: dict):
        """创建相册成功"""
        r = await client.post(
            "/api/admin/gallery/albums",
            headers=staff_headers,
            json={"title": "新建相册", "description": "测试", "is_published": True},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "新建相册"
        assert data["is_published"] is True
        assert data["photo_count"] == 0

    @pytest.mark.asyncio
    async def test_admin_create_album_validation(self, client: AsyncClient, staff_headers: dict):
        """标题为空时返回 422"""
        r = await client.post(
            "/api/admin/gallery/albums",
            headers=staff_headers,
            json={"title": "", "is_published": True},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_admin_list_albums(self, client: AsyncClient, staff_headers: dict, db_session):
        """管理员列表返回所有相册（含私密）"""
        db_session.add_all(
            [
                Album(title="A1", is_published=True, photo_count=0),
                Album(title="A2", is_published=False, photo_count=0),
            ]
        )
        await db_session.commit()

        r = await client.get(
            "/api/admin/gallery/albums",
            headers=staff_headers,
            params={"page_size": 50},
        )
        assert r.status_code == 200
        titles = [a["title"] for a in r.json()["items"]]
        assert "A1" in titles
        assert "A2" in titles

    @pytest.mark.asyncio
    async def test_admin_update_album(self, client: AsyncClient, staff_headers: dict, db_session):
        """更新相册字段"""
        album = Album(title="旧标题", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        r = await client.put(
            f"/api/admin/gallery/albums/{album.id}",
            headers=staff_headers,
            json={"title": "新标题", "is_published": False},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "新标题"
        assert r.json()["is_published"] is False

    @pytest.mark.asyncio
    async def test_admin_delete_album(self, client: AsyncClient, staff_headers: dict, db_session):
        """删除相册成功"""
        album = Album(title="待删", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)
        album_id = album.id

        r = await client.delete(f"/api/admin/gallery/albums/{album_id}", headers=staff_headers)
        assert r.status_code == 200

        # 确认已删除（刷新 session 缓存）
        db_session.expire_all()
        result = await db_session.get(Album, album_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_admin_delete_album_cascades_photos(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """删除相册时级联删除照片"""
        album = Album(title="级联", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)
        album_id = album.id

        photo = Photo(album_id=album_id, url="/x.jpg", sort_order=1)
        db_session.add(photo)
        await db_session.commit()

        await client.delete(f"/api/admin/gallery/albums/{album_id}", headers=staff_headers)

        # 照片应被级联删除
        from sqlalchemy import select

        photos = (
            (await db_session.execute(select(Photo).where(Photo.album_id == album_id)))
            .scalars()
            .all()
        )
        assert photos == []


# ==================== 管理接口 - 照片 CRUD ====================


class TestAdminPhotoCrud:
    """管理员照片增删改查"""

    @pytest.mark.asyncio
    async def test_admin_create_photo(self, client: AsyncClient, staff_headers: dict, db_session):
        """添加照片到相册"""
        album = Album(title="P", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        r = await client.post(
            "/api/admin/gallery/photos",
            headers=staff_headers,
            json={
                "album_id": album.id,
                "url": "/media/uploads/photo.jpg",
                "title": "我的照片",
                "sort_order": 1,
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["url"] == "/media/uploads/photo.jpg"
        assert data["original_url"] == "/media/uploads/photo.jpg"  # alias

    @pytest.mark.asyncio
    async def test_admin_create_photo_invalid_album(self, client: AsyncClient, staff_headers: dict):
        """添加照片到不存在的相册返回 404"""
        r = await client.post(
            "/api/admin/gallery/photos",
            headers=staff_headers,
            json={"album_id": 99999, "url": "/x.jpg"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_photo_count_maintained(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """添加/删除照片后 photo_count 自动维护"""
        album = Album(title="计数", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)
        album_id = album.id

        # 添加 2 张
        for i in range(2):
            r = await client.post(
                "/api/admin/gallery/photos",
                headers=staff_headers,
                json={"album_id": album_id, "url": f"/p{i}.jpg", "sort_order": i + 1},
            )
            assert r.status_code == 201

        db_session.expire_all()
        album = await db_session.get(Album, album_id)
        assert album.photo_count == 2

        # 删除 1 张
        photos = (
            (
                await db_session.execute(
                    __import__("sqlalchemy").select(Photo).where(Photo.album_id == album_id)
                )
            )
            .scalars()
            .all()
        )
        if photos:
            await client.delete(f"/api/admin/gallery/photos/{photos[0].id}", headers=staff_headers)

        db_session.expire_all()
        album = await db_session.get(Album, album_id)
        assert album.photo_count == 1

    @pytest.mark.asyncio
    async def test_admin_update_photo(self, client: AsyncClient, staff_headers: dict, db_session):
        """更新照片标题"""
        album = Album(title="U", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        photo = Photo(album_id=album.id, url="/old.jpg", title="旧", sort_order=1)
        db_session.add(photo)
        await db_session.commit()
        await db_session.refresh(photo)

        r = await client.put(
            f"/api/admin/gallery/photos/{photo.id}",
            headers=staff_headers,
            json={"title": "新标题", "description": "新描述"},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "新标题"
        assert r.json()["description"] == "新描述"

    @pytest.mark.asyncio
    async def test_admin_delete_photo(self, client: AsyncClient, staff_headers: dict, db_session):
        """删除照片成功"""
        album = Album(title="D", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        photo = Photo(album_id=album.id, url="/d.jpg", sort_order=1)
        db_session.add(photo)
        await db_session.commit()
        await db_session.refresh(photo)
        photo_id = photo.id

        r = await client.delete(f"/api/admin/gallery/photos/{photo_id}", headers=staff_headers)
        assert r.status_code == 200

        db_session.expire_all()
        result = await db_session.get(Photo, photo_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_admin_list_photos_pagination(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """照片列表分页正常"""
        album = Album(title="分页", is_published=True, photo_count=0)
        db_session.add(album)
        await db_session.commit()
        await db_session.refresh(album)

        for i in range(5):
            db_session.add(Photo(album_id=album.id, url=f"/{i}.jpg", sort_order=i + 1))
        await db_session.commit()

        r = await client.get(
            f"/api/admin/gallery/albums/{album.id}/photos",
            headers=staff_headers,
            params={"page": 1, "page_size": 2},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


# ==================== 权限边界 ====================


class TestGalleryPermissions:
    """未登录 / 普通用户无权访问管理接口"""

    @pytest.mark.asyncio
    async def test_admin_requires_auth(self, client: AsyncClient):
        """未登录访问管理相册列表返回 401"""
        r = await client.get("/api/admin/gallery/albums")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_requires_staff(self, client: AsyncClient, subscriber_headers: dict):
        """普通用户访问管理相册列表返回 403"""
        r = await client.get("/api/admin/gallery/albums", headers=subscriber_headers)
        assert r.status_code in (401, 403)


# ==================== 批量删除照片 ====================


async def _count(db_session, album_id: int) -> int:
    """某相册剩余照片数"""
    return await db_session.scalar(
        select(func.count()).select_from(Photo).where(Photo.album_id == album_id)
    )


async def _photo_count(db_session, album_id: int) -> int:
    """某相册 DB 里记录的 photo_count 字段值"""
    return await db_session.scalar(select(Album.photo_count).where(Album.id == album_id))


class TestAdminPhotoBatchDelete:
    """一次请求删一组照片：替代前端逐张 DELETE 的 N 次往返"""

    async def _seed(self, db_session):
        """建 2 个相册，A 内 3 张、B 内 2 张，返回 (album_a, album_b, photo_ids)"""
        album_a = Album(title="相册A", is_published=True, photo_count=0)
        album_b = Album(title="相册B", is_published=True, photo_count=0)
        db_session.add_all([album_a, album_b])
        await db_session.commit()
        await db_session.refresh(album_a)
        await db_session.refresh(album_b)

        for album, count in ((album_a, 3), (album_b, 2)):
            for i in range(count):
                photo = Photo(
                    album_id=album.id,
                    url=f"/media/uploads/{album.id}-{i}.jpg",
                    sort_order=i + 1,
                )
                db_session.add(photo)
            await db_session.commit()
        rows = (await db_session.execute(select(Photo.id).order_by(Photo.id.asc()))).scalars().all()
        return album_a, album_b, list(rows)

    @pytest.mark.asyncio
    async def test_batch_delete_spans_albums_and_recounts(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """跨相册批量删除：各相册 photo_count 各重算一次"""
        album_a, album_b, all_ids = await self._seed(db_session)
        await db_session.execute(update(Album).where(Album.id == album_a.id).values(photo_count=3))
        await db_session.execute(update(Album).where(Album.id == album_b.id).values(photo_count=2))
        await db_session.commit()

        r = await client.request(
            "DELETE",
            "/api/admin/gallery/photos/batch",
            headers=staff_headers,
            json={"ids": all_ids[:3]},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert data["deleted_count"] == 3
        assert data["missing_ids"] == []

        # 用列投影查询而不是取回 ORM 对象：app 侧会话删改后，测试会话的
        # identity map 可能 still 缓存旧行，直接读属性会触发同步 IO（MissingGreenlet）
        assert await _count(db_session, album_a.id) == 0
        assert await _count(db_session, album_b.id) == 2
        assert await _photo_count(db_session, album_a.id) == 0
        assert await _photo_count(db_session, album_b.id) == 2

    @pytest.mark.asyncio
    async def test_batch_delete_reports_missing_ids(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """请求里混入不存在的 ID：删除成功，但 missing_ids 必须如实上报"""
        album_a, _album_b, all_ids = await self._seed(db_session)
        target = all_ids[0]

        r = await client.request(
            "DELETE",
            "/api/admin/gallery/photos/batch",
            headers=staff_headers,
            json={"ids": [target, 999_998, 999_999]},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["deleted_count"] == 1
        assert data["missing_ids"] == [999_998, 999_999]
        assert "不存在" in data["message"]
        assert (
            await db_session.scalar(
                select(func.count()).select_from(Photo).where(Photo.id == target)
            )
            == 0
        )
        assert await db_session.scalar(select(func.count()).select_from(Photo)) == 4

    @pytest.mark.asyncio
    async def test_batch_delete_rejects_empty_ids(self, client: AsyncClient, staff_headers: dict):
        """空 ID 列表返回 400，而不是静默成功"""
        r = await client.request(
            "DELETE", "/api/admin/gallery/photos/batch", headers=staff_headers, json={"ids": []}
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_batch_delete_all_unknown_returns_404(
        self, client: AsyncClient, staff_headers: dict
    ):
        """全部 ID 不存在返回 404（没有任何东西被删）"""
        r = await client.request(
            "DELETE",
            "/api/admin/gallery/photos/batch",
            headers=staff_headers,
            json={"ids": [424242]},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_delete_requires_staff(self, client: AsyncClient, subscriber_headers: dict):
        """普通用户不能批量删照片"""
        r = await client.request(
            "DELETE",
            "/api/admin/gallery/photos/batch",
            headers=subscriber_headers,
            json={"ids": [1]},
        )
        assert r.status_code in (401, 403)
