"""网站动态（Activity）API 回归测试

覆盖前台"说说/动态"页与后台 `/admin/interaction/activities` 用到的全部入口：
- GET  /api/activities                     公开列表（SSR 首屏 + 缓存）
- POST /api/activities                     登录用户发布
- POST /api/activities/{id}/like           点赞
- GET/POST/PUT/DELETE /api/admin/activities 后台 CRUD + 切换发布

写路径另有一条按表计数的断言：flush 之后 `created_at/updated_at` 过期、
`ActivityResponse.author` 又是必填，所以必须回读一次；但"回读"应当只有一条
带 selectinload 的 SELECT，不多发 refresh 的重复查询。
"""

import pytest
from httpx import AsyncClient

CONTENT_ZH = "第一次发动态"
CONTENT_EN = "My first activity"


def _payload(content: str = CONTENT_ZH, **extra) -> dict:
    body = {
        "content": {
            "zh": content,
            "en": CONTENT_EN,
            "ja": content,
            "zh_Hant": content,
        },
        "type": "say",
        "is_published": True,
    }
    body.update(extra)
    return body


class TestActivityPublicList:
    """公开列表：分页契约 + 语言回显 + 只出已发布"""

    @pytest.mark.asyncio
    async def test_unpublished_activity_hidden_from_public_list(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        await client.post("/api/activities", headers=auth_headers, json=_payload("公开的"))
        await client.post(
            "/api/activities",
            headers=auth_headers,
            json=_payload("草稿的", is_published=False),
        )

        r = await client.get("/api/activities", params={"page_size": 50})
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        texts = [i["content"] for i in items]
        assert any("公开的" in t for t in texts), items
        assert not any("草稿的" in t for t in texts), "未发布动态泄漏到公开列表"

    @pytest.mark.asyncio
    async def test_public_list_localizes_content_by_lang(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post("/api/activities", headers=auth_headers, json=_payload())

        r = await client.get("/api/activities", params={"lang": "en", "page_size": 50})
        assert r.status_code == 200, r.text
        target = r.json()["items"][0]
        assert target["content"] == CONTENT_EN, target
        # author 是必填字段：缺失即 500 或 schema 校验失败
        assert target["author"]["id"], target

    @pytest.mark.asyncio
    async def test_public_list_pagination_fields(self, client: AsyncClient, auth_headers: dict):
        for i in range(3):
            await client.post("/api/activities", headers=auth_headers, json=_payload(f"n{i}"))

        r = await client.get("/api/activities", params={"page": 1, "page_size": 2})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 3, body
        assert body["page"] == 1 and body["page_size"] == 2
        assert body["total_pages"] == 2, body
        assert len(body["items"]) == 2

        r2 = await client.get("/api/activities", params={"page": 2, "page_size": 2})
        first_page_ids = {i["id"] for i in body["items"]}
        assert first_page_ids.isdisjoint({i["id"] for i in r2.json()["items"]}), "分页偏移重叠"

    @pytest.mark.asyncio
    async def test_public_list_cached_payload_matches_db(
        self, client: AsyncClient, auth_headers: dict
    ):
        """预热/缓存路径与冷读必须一致：先读缓存，再写一条，缓存必须已失效"""
        first = await client.get("/api/activities")
        assert first.status_code == 200
        assert first.json()["total"] == 0, first.json()

        await client.post("/api/activities", headers=auth_headers, json=_payload())

        second = await client.get("/api/activities")
        assert second.json()["total"] == 1, "写操作后列表缓存未按 pattern 清退，前台会一直看到旧页"


class TestActivityCreate:
    @pytest.mark.asyncio
    async def test_anonymous_create_rejected_with_error_code(self, client: AsyncClient):
        r = await client.post("/api/activities", json=_payload())
        assert r.status_code == 401, r.text
        assert r.json()["error_code"] == "AUTH_REQUIRED", r.json()

    @pytest.mark.asyncio
    async def test_logged_in_create_returns_author_snapshot(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        r = await client.post("/api/activities", headers=auth_headers, json=_payload())
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["content"]["zh"] == CONTENT_ZH
        assert body["type"] == "say"
        assert body["is_published"] is True
        assert body["likes_count"] == 0
        assert body["author"]["id"] == test_user.id, "author 关联未随响应带出"
        assert body["created_at"] and body["updated_at"], "服务端生成列未回读"

    @pytest.mark.asyncio
    async def test_admin_create_activity_reads_activities_once(
        self, client: AsyncClient, admin_headers: dict, test_engine
    ):
        """写路径只允许"INSERT + 一次带预加载的重读"。

        旧实现是 `execute(带 selectinload，结果丢弃)` + `db.refresh()` + 序列化，
        refresh 自己会把 author/title 再查一遍，等于每次创建多发 1~2 条 SELECT。
        这里按语句命中的表计数，把"多发的那条"钉死。
        """
        from sqlalchemy import event

        statements: list[str] = []

        def _record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        # AsyncEngine 不接受同步事件监听，必须挂到 .sync_engine 上
        target = test_engine.sync_engine
        event.listen(target, "before_cursor_execute", _record)
        try:
            r = await client.post(
                "/api/admin/activities", headers=admin_headers, json=_payload("计数用")
            )
        finally:
            event.remove(target, "before_cursor_execute", _record)

        assert r.status_code == 201, r.text
        activity_reads = [s for s in statements if "FROM activities" in s]
        activity_writes = [s for s in statements if "INSERT INTO activities" in s]
        assert len(activity_writes) == 1, activity_writes
        assert len(activity_reads) == 1, (
            f"activities 表被读了 {len(activity_reads)} 次：{activity_reads}"
        )


class TestActivityAdminCrud:
    @pytest.mark.asyncio
    async def test_admin_create_and_list_with_filters(
        self, client: AsyncClient, admin_headers: dict
    ):
        created = await client.post(
            "/api/admin/activities",
            headers=admin_headers,
            json=_payload("后台通知", type="notice", is_published=False),
        )
        assert created.status_code == 201, created.text
        aid = created.json()["id"]

        only_notice = await client.get(
            "/api/admin/activities", headers=admin_headers, params={"type": "notice"}
        )
        assert only_notice.status_code == 200, only_notice.text
        assert {i["id"] for i in only_notice.json()["items"]} == {aid}

        only_published = await client.get(
            "/api/admin/activities", headers=admin_headers, params={"is_published": True}
        )
        assert only_published.json()["items"] == [], "未发布项出现在 is_published=true 结果里"

        only_draft = await client.get(
            "/api/admin/activities", headers=admin_headers, params={"is_published": False}
        )
        assert {i["id"] for i in only_draft.json()["items"]} == {aid}

    @pytest.mark.asyncio
    async def test_admin_list_rejects_unknown_type(self, client: AsyncClient, admin_headers: dict):
        r = await client.get(
            "/api/admin/activities", headers=admin_headers, params={"type": "bogus"}
        )
        assert r.status_code == 422, r.text

    @pytest.mark.asyncio
    async def test_admin_requires_staff(self, client: AsyncClient, subscriber_headers: dict):
        r = await client.get("/api/admin/activities", headers=subscriber_headers)
        assert r.status_code in (401, 403), r.text

    @pytest.mark.asyncio
    async def test_update_persists_and_returns_loaded_author(
        self, client: AsyncClient, admin_headers: dict
    ):
        aid = (
            await client.post("/api/admin/activities", headers=admin_headers, json=_payload("原文"))
        ).json()["id"]

        r = await client.put(
            f"/api/admin/activities/{aid}",
            headers=admin_headers,
            json={"content": {"zh": "改后", "en": "edited", "ja": "改后", "zh_Hant": "改后"}},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["content"]["zh"] == "改后"
        assert body["type"] == "say", "部分更新不应清空未提交字段"
        assert body["author"]["id"], "PUT 响应缺少 author 关联"

    @pytest.mark.asyncio
    async def test_toggle_flips_publish_state(self, client: AsyncClient, admin_headers: dict):
        aid = (
            await client.post(
                "/api/admin/activities", headers=admin_headers, json=_payload("待切换")
            )
        ).json()["id"]

        r = await client.put(f"/api/admin/activities/{aid}/toggle", headers=admin_headers)
        assert r.status_code == 200, r.text
        assert r.json()["is_published"] is False
        assert r.json()["author"]["id"]

        r2 = await client.put(f"/api/admin/activities/{aid}/toggle", headers=admin_headers)
        assert r2.json()["is_published"] is True

    @pytest.mark.asyncio
    async def test_like_increments_count(self, client: AsyncClient, admin_headers: dict):
        aid = (
            await client.post("/api/admin/activities", headers=admin_headers, json=_payload())
        ).json()["id"]

        for _ in range(2):
            r = await client.post(f"/api/activities/{aid}/like")
            assert r.status_code == 200, r.text

        listed = await client.get("/api/admin/activities", headers=admin_headers)
        target = next(i for i in listed.json()["items"] if i["id"] == aid)
        assert target["likes_count"] == 2, target

    @pytest.mark.asyncio
    async def test_like_missing_activity_is_404(self, client: AsyncClient):
        r = await client.post("/api/activities/999999/like")
        assert r.status_code == 404, r.text

    @pytest.mark.asyncio
    async def test_delete_removes_and_blocks_further_update(
        self, client: AsyncClient, admin_headers: dict
    ):
        aid = (
            await client.post("/api/admin/activities", headers=admin_headers, json=_payload())
        ).json()["id"]

        r = await client.delete(f"/api/admin/activities/{aid}", headers=admin_headers)
        assert r.status_code == 200, r.text

        listed = await client.get("/api/admin/activities", headers=admin_headers)
        assert aid not in {i["id"] for i in listed.json()["items"]}

        r2 = await client.put(
            f"/api/admin/activities/{aid}", headers=admin_headers, json={"type": "link"}
        )
        assert r2.status_code == 404, r2.text
