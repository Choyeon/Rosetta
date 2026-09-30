"""
相册（Gallery）与媒体（Media）写路径的横切契约测试。

钉住三条容易被"接口跑通就算完"漏掉的约束：

1. **前台页面缓存必须失效。** ``/gallery`` 是 SSR 页且 Nitro routeRules ``swr: 600``，
   相册封面与照片数直接渲染进访客拿到的 HTML；写操作只清后端 ``gallery:*`` 缓存的话，
   管理员改完最长十分钟才生效。
2. **写路径必须发钩子。** AGENTS §1.1.7 要求任何写路径（含批量入口）与单篇路径
   同构地 ``do_action``，且事件名必须在 ``WEBHOOK_EVENTS`` 里登记——那是后台订阅 UI
   的唯一数据源。批量分支漏发钩子的表现是"用户改用多选后监听方静默失聪"。
3. **媒体落盘目录必须与 main.py 挂载 StaticFiles 的那一处同源。** 两边口径不一致时，
   文件写到旧目录、Nginx/StaticFiles 提供新目录 → 上传成功却 404。

另有两条是本次审查新加的业务守卫：
- 照片跨相册移动时目标相册必须存在（否则 SQLite 下产生孤儿行，管理员会以为照片丢了）；
- 媒体删除/更新也要发钩子（此前只有上传发）。
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.api import gallery as gallery_api
from backend.api import media as media_api
from backend.api.webhook import WEBHOOK_EVENTS
from backend.core import hooks as hooks_core
from backend.core.config import settings
from backend.core.paths import BASE_DIR
from backend.models.core import Media
from backend.models.gallery import Album, Photo


@pytest.fixture
def hook_sink():
    """订阅一批总线事件，收集 (event, payload) 并在用例结束后注销。

    全局钩子表跨用例残留，不注销会污染其它测试（webhook 模块自己的
    unregister_webhook_listeners 也是这个原因）。
    """
    events = [
        "album.created",
        "album.updated",
        "album.deleted",
        "photo.created",
        "photo.updated",
        "photo.deleted",
        "media.updated",
        "media.deleted",
    ]
    seen: list[tuple[str, dict]] = []

    def _make_capture(event_name: str):
        # `_safe_call` 会把 `_hook_name` 自己吃掉用于日志，处理器拿不到，
        # 所以事件名必须在闭包里绑死，不能指望从 kwargs 里读出来。
        async def _capture(*_args, **kwargs):
            payload = kwargs.get("webhook_payload")
            seen.append((event_name, payload if isinstance(payload, dict) else {}))
            return None

        return _capture

    handlers = {name: _make_capture(name) for name in events}
    for name, handler in handlers.items():
        hooks_core.add_action(name, handler)
    yield seen
    for name, handler in handlers.items():
        hooks_core.remove_action(name, handler)


@pytest.fixture
def purge_sink(monkeypatch):
    """拦截 purge_frontend_page_cache，记录被调用的 reason。"""
    calls: list[str] = []

    def _fake(reason: str = "", **_kwargs):
        calls.append(reason)

    monkeypatch.setattr(gallery_api, "purge_frontend_page_cache", _fake)
    return calls


async def _create_album(client: AsyncClient, staff_headers: dict, title: str = "契") -> int:
    r = await client.post(
        "/api/admin/gallery/albums",
        headers=staff_headers,
        json={"title": title, "is_published": True},
    )
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def _create_photo(client: AsyncClient, staff_headers: dict, album_id: int, url: str) -> int:
    r = await client.post(
        "/api/admin/gallery/photos",
        headers=staff_headers,
        json={"album_id": album_id, "url": url, "sort_order": 1},
    )
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


# ==================== 1. 前台页面缓存失效 ====================


class TestGalleryFrontendCachePurge:
    """/gallery 是 SSR + swr 600，写操作必须通知 Nitro 清 HTML 缓存"""

    @pytest.mark.asyncio
    async def test_album_create_purges(self, client: AsyncClient, staff_headers: dict, purge_sink):
        await _create_album(client, staff_headers)
        assert len(purge_sink) == 1

    @pytest.mark.asyncio
    async def test_album_update_purges(
        self, client: AsyncClient, staff_headers: dict, purge_sink, db_session
    ):
        album_id = await _create_album(client, staff_headers)
        purge_sink.clear()
        r = await client.put(
            f"/api/admin/gallery/albums/{album_id}",
            headers=staff_headers,
            json={"title": "改名"},
        )
        assert r.status_code == 200
        assert len(purge_sink) == 1

    @pytest.mark.asyncio
    async def test_album_delete_purges(
        self, client: AsyncClient, staff_headers: dict, purge_sink
    ):
        album_id = await _create_album(client, staff_headers)
        purge_sink.clear()
        r = await client.delete(
            f"/api/admin/gallery/albums/{album_id}", headers=staff_headers
        )
        assert r.status_code == 200
        assert len(purge_sink) == 1

    @pytest.mark.asyncio
    async def test_photo_write_paths_purge(
        self, client: AsyncClient, staff_headers: dict, purge_sink
    ):
        album_id = await _create_album(client, staff_headers)
        photo_id = await _create_photo(client, staff_headers, album_id, "/a.jpg")

        purge_sink.clear()
        r = await client.put(
            f"/api/admin/gallery/photos/{photo_id}",
            headers=staff_headers,
            json={"title": "新"},
        )
        assert r.status_code == 200
        assert len(purge_sink) == 1

        purge_sink.clear()
        r = await client.delete(
            f"/api/admin/gallery/photos/{photo_id}", headers=staff_headers
        )
        assert r.status_code == 200
        assert len(purge_sink) == 1

    @pytest.mark.asyncio
    async def test_photo_batch_delete_purges_once(
        self, client: AsyncClient, staff_headers: dict, purge_sink
    ):
        """批量删除只清一次缓存：N 张照片不该变成 N 次全量失效。"""
        album_id = await _create_album(client, staff_headers)
        ids = [
            await _create_photo(client, staff_headers, album_id, f"/b{i}.jpg")
            for i in range(3)
        ]
        purge_sink.clear()
        r = await client.request(
            "DELETE",
            "/api/admin/gallery/photos/batch",
            headers=staff_headers,
            json={"ids": ids},
        )
        assert r.status_code == 200
        assert len(purge_sink) == 1


# ==================== 2. 钩子 ====================


class TestGalleryHooks:
    @pytest.mark.asyncio
    async def test_album_lifecycle_emits_events(
        self, client: AsyncClient, staff_headers: dict, hook_sink
    ):
        album_id = await _create_album(client, staff_headers)

        r = await client.put(
            f"/api/admin/gallery/albums/{album_id}",
            headers=staff_headers,
            json={"title": "改名"},
        )
        assert r.status_code == 200

        r = await client.delete(
            f"/api/admin/gallery/albums/{album_id}", headers=staff_headers
        )
        assert r.status_code == 200

        names = [name for name, _ in hook_sink]
        assert names == ["album.created", "album.updated", "album.deleted"]

        # 删除事件必须自带 id：行已经没了，监听方拿不到别的信息
        payload = dict(hook_sink[-1][1])
        assert payload.get("id") == album_id

    @pytest.mark.asyncio
    async def test_photo_lifecycle_emits_events(
        self, client: AsyncClient, staff_headers: dict, hook_sink
    ):
        album_id = await _create_album(client, staff_headers)
        photo_id = await _create_photo(client, staff_headers, album_id, "/c.jpg")

        r = await client.put(
            f"/api/admin/gallery/photos/{photo_id}",
            headers=staff_headers,
            json={"title": "新"},
        )
        assert r.status_code == 200

        r = await client.delete(
            f"/api/admin/gallery/photos/{photo_id}", headers=staff_headers
        )
        assert r.status_code == 200

        names = [name for name, _ in hook_sink]
        assert names == ["album.created", "photo.created", "photo.updated", "photo.deleted"]

        created = dict([p for n, p in hook_sink if n == "photo.created"][0])
        assert created.get("id") == photo_id
        assert created.get("album_id") == album_id

    @pytest.mark.asyncio
    async def test_batch_delete_emits_one_event_per_photo(
        self, client: AsyncClient, staff_headers: dict, hook_sink
    ):
        """批量入口必须与单条同构发钩子，事件名同样是 photo.deleted。"""
        album_id = await _create_album(client, staff_headers)
        ids = [
            await _create_photo(client, staff_headers, album_id, f"/d{i}.jpg")
            for i in range(3)
        ]
        hook_sink.clear()

        r = await client.request(
            "DELETE",
            "/api/admin/gallery/photos/batch",
            headers=staff_headers,
            json={"ids": ids + [999999]},
        )
        assert r.status_code == 200
        assert r.json()["deleted_count"] == 3
        assert r.json()["missing_ids"] == [999999]

        deleted = [p.get("id") for n, p in hook_sink if n == "photo.deleted"]
        assert deleted == ids, "批量删除必须对每张实际删除的照片各发一条"

    @pytest.mark.asyncio
    async def test_all_gallery_events_are_registered(self):
        """WEBHOOK_EVENTS 是后台订阅 UI 的唯一数据源，漏登记 = 用户订阅不到。"""
        for name in (
            "album.created",
            "album.updated",
            "album.deleted",
            "photo.created",
            "photo.updated",
            "photo.deleted",
            "media.updated",
            "media.deleted",
        ):
            assert name in WEBHOOK_EVENTS, f"{name} 未在 WEBHOOK_EVENTS 登记"


# ==================== 3. 跨相册移动的守卫 ====================


class TestPhotoMoveGuard:
    @pytest.mark.asyncio
    async def test_move_to_missing_album_returns_404_and_keeps_photo(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """目标相册不存在时必须拒绝。

        SQLite 默认不开外键约束，写进去就是一张 album_id 悬空的孤儿照片——
        它在「某个相册的照片列表」里永远查不到，管理员会认为照片丢了。
        """
        album_id = await _create_album(client, staff_headers)
        photo_id = await _create_photo(client, staff_headers, album_id, "/e.jpg")

        r = await client.put(
            f"/api/admin/gallery/photos/{photo_id}",
            headers=staff_headers,
            json={"album_id": 999999},
        )
        assert r.status_code == 404

        db_session.expire_all()
        photo = await db_session.get(Photo, photo_id)
        assert photo is not None
        assert photo.album_id == album_id, "被拒绝的请求不得改动照片归属"

    @pytest.mark.asyncio
    async def test_move_to_existing_album_recomputes_both_counts(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        src = await _create_album(client, staff_headers, "源")
        dst = await _create_album(client, staff_headers, "目标")
        photo_id = await _create_photo(client, staff_headers, src, "/f.jpg")

        r = await client.put(
            f"/api/admin/gallery/photos/{photo_id}",
            headers=staff_headers,
            json={"album_id": dst},
        )
        assert r.status_code == 200

        db_session.expire_all()
        counts = {
            row[0]: row[1]
            for row in (
                await db_session.execute(select(Photo.album_id, Photo.id).where(Photo.id == photo_id))
            ).all()
        }
        assert list(counts) == [dst]

        src_row = await db_session.get(Album, src)
        dst_row = await db_session.get(Album, dst)
        assert src_row.photo_count == 0
        assert dst_row.photo_count == 1


# ==================== 4. 媒体：目录同源 + 删除/更新钩子 ====================


class TestMediaDirAndHooks:
    def test_media_dir_derives_from_settings(self):
        """落盘根目录必须跟着 settings.media_dir，不能写死相对路径 \"media\"。"""
        assert media_api.MEDIA_DIR == Path(settings.media_dir)

    def test_media_dir_agrees_with_static_mount(self):
        """main.py 挂载的是 BASE_DIR / settings.media_dir，两处必须算到同一个目录。"""
        mounted = BASE_DIR / settings.media_dir
        # 相对 media_dir 是相对 CWD 的相对路径，绝对路径时要求完全相等
        if media_api.MEDIA_DIR.is_absolute():
            assert media_api.MEDIA_DIR.resolve() == mounted.resolve()

    @pytest.mark.asyncio
    async def test_media_update_emits_hook(
        self, client: AsyncClient, staff_headers: dict, db_session, hook_sink
    ):
        media = Media(file="/media/uploads/image/x.jpg", filename="x.jpg", file_type="image")
        db_session.add(media)
        await db_session.commit()
        await db_session.refresh(media)

        r = await client.put(
            f"/api/media/library/{media.id}",
            headers=staff_headers,
            json={"title": "标题", "alt_text": "alt"},
        )
        assert r.status_code == 200
        assert [n for n, _ in hook_sink] == ["media.updated"]
        payload = dict(hook_sink[0][1])
        assert payload.get("id") == media.id
        assert payload.get("title") == "标题"

    @pytest.mark.asyncio
    async def test_media_delete_emits_hook(
        self, client: AsyncClient, staff_headers: dict, db_session, hook_sink, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
        media = Media(file="/not-local/x.jpg", filename="x.jpg", file_type="image")
        db_session.add(media)
        await db_session.commit()
        await db_session.refresh(media)
        media_id = media.id

        r = await client.delete(
            f"/api/media/library/{media_id}", headers=staff_headers
        )
        assert r.status_code == 200
        assert [n for n, _ in hook_sink] == ["media.deleted"]
        payload = dict(hook_sink[0][1])
        assert payload.get("id") == media_id

    @pytest.mark.asyncio
    async def test_media_batch_delete_emits_one_hook_per_record(
        self, client: AsyncClient, staff_headers: dict, db_session, hook_sink, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(media_api, "MEDIA_DIR", tmp_path)
        rows = []
        for i in range(2):
            m = Media(file=f"/not-local/{i}.jpg", filename=f"{i}.jpg", file_type="image")
            db_session.add(m)
            rows.append(m)
        await db_session.commit()
        ids = [m.id for m in rows]
        hook_sink.clear()

        r = await client.request(
            "DELETE",
            "/api/media/library/batch",
            headers=staff_headers,
            json={"ids": ids},
        )
        assert r.status_code == 200
        assert r.json()["deleted_count"] == 2
        deleted = sorted(p.get("id") for n, p in hook_sink if n == "media.deleted")
        assert deleted == ids
