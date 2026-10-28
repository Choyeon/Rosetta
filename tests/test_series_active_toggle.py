"""系列 ``is_active`` 启停族的两端与强制点回归（批次 #37）。

后端这一族早就写完了（toggle 口、公开列表过滤、详情 404、sitemap 剔除、清页面缓存），
缺的是后台那一头：系列页把 ``is_active`` 取回前端却一个像素都没渲染、也没有任何调用点，
于是"停用系列"这件事只有会直接打 API 的运营者做得到。缺一条断言就是回到
"能力躺在后端、界面看不见"的那一类缺陷，所以这里把两端都钉住。

覆盖面（每条都对应一个真实的失效形态）：
1. schema：Create/Update/Response 三处都声明，Create 缺省必须是启用（否则新建即前台不可见），
   Update 缺省必须是 ``None``（否则每次"只改标题"都顺手改一次启停）；
2. 写口：``PUT /api/admin/series/{id}/toggle`` 翻值可逆、缺行 404、非 staff 不可用，
   并且必须清前台页面缓存——purge 是 fire-and-forget，漏了不报错，
   只在 SWR 窗口内让访客继续读到已停用的系列 HTML；
3. 后台列表必须继续显示停用行，否则"停用"是单向按钮：点完找不到入口，只能靠 URL 恢复；
   管理口的 ``?is_active=`` 是真过滤而不是摆设；
4. 强制点：公开 ``GET /api/series`` 不收停用行、``GET /api/series/{slug}`` 停用后 404；
5. 投递面：系列 sitemap 不向爬虫投递停用系列（``/series`` 根路径是静态条目，不受影响）；
6. 代价范围：停用只摘入口，不清空文章上的系列关联、也不摘名下已发布文章按 slug 的可访问性。
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.models.blog import Post
from backend.models.post_series import PostSeries

SERIES = "/api/series"
ADMIN_SERIES = "/api/admin/series"
BLOG = "/api/blog"


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 list/dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _mk_series(db, slug: str, *, is_active: bool = True) -> PostSeries:
    series = PostSeries(
        title={"zh": f"系列{slug}", "en": slug},
        slug=slug,
        is_active=is_active,
    )
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


async def _mk_post_in_series(db, series: PostSeries, author_id: int, slug: str) -> Post:
    post = Post(
        title={"zh": f"《{slug}》", "en": slug},
        slug=slug,
        content={"zh": "正文", "en": "body"},
        author_id=author_id,
        series_id=series.id,
        status="published",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def _public_slugs(client: AsyncClient) -> list[str]:
    resp = await client.get(SERIES)
    assert resp.status_code == 200, resp.text
    return [row["slug"] for row in _unwrap(resp.json())]


async def _admin_rows(client: AsyncClient, headers: dict, params: dict | None = None) -> list[dict]:
    resp = await client.get(ADMIN_SERIES, headers=headers, params=params or {})
    assert resp.status_code == 200, resp.text
    return _unwrap(resp.json())


async def _db_row(db, model, pk: int):
    """接口回 200 之后到库里读回这一行。两点口径：先 ``expire_all`` 清身份缓存
    （写的那次提交发生在另一个会话上），并且只用 SELECT——``session.get()`` 在
    AsyncSession 上是同步入口，属性一失效就直接 MissingGreenlet。"""
    await db.rollback()
    db.expire_all()
    return (await db.execute(select(model).where(model.id == pk))).scalar_one()


class TestSchemaDeclaresTheFlag:
    def test_create_update_response_all_declare(self):
        from backend.schemas.post_series import (
            PostSeriesCreate,
            PostSeriesResponse,
            PostSeriesUpdate,
        )

        for model in (PostSeriesCreate, PostSeriesUpdate, PostSeriesResponse):
            assert "is_active" in model.model_fields, f"{model.__name__} 缺 is_active"
        # Create 侧缺省必须启用：默认 False 会让"新建系列"直接前台不可见
        assert PostSeriesCreate.model_fields["is_active"].default is True

    def test_update_leaves_the_flag_unset_by_default(self):
        """Update 侧缺省必须是 None：apply_partial_update 靠 exclude_unset 决定写哪些列，
        给个布尔缺省等于每次"只改标题"都顺手改一次启停状态。"""
        from backend.schemas.post_series import PostSeriesUpdate

        assert PostSeriesUpdate.model_fields["is_active"].default is None


class TestWriteSide:
    @pytest.mark.asyncio
    async def test_toggle_flips_off_and_back_on(
        self, client: AsyncClient, admin_headers: dict, db_session
    ):
        series = await _mk_series(db_session, "flip-me")

        off = await client.put(f"{ADMIN_SERIES}/{series.id}/toggle", headers=admin_headers)
        assert off.status_code == 200, off.text
        assert _unwrap(off.json())["is_active"] is False
        assert _unwrap(off.json())["slug"] == "flip-me"

        on = await client.put(f"{ADMIN_SERIES}/{series.id}/toggle", headers=admin_headers)
        assert _unwrap(on.json())["is_active"] is True

        row = await _db_row(db_session, PostSeries, series.id)
        assert row.is_active is True, "接口回 200 而库里没变（脱离会话写列的典型形态）"

    @pytest.mark.asyncio
    async def test_missing_series_is_404(self, client: AsyncClient, admin_headers: dict):
        resp = await client.put(f"{ADMIN_SERIES}/999999/toggle", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_staff_cannot_toggle(self, client: AsyncClient, subscriber_headers: dict):
        resp = await client.put(f"{ADMIN_SERIES}/1/toggle", headers=subscriber_headers)
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_can_start_inactive(
        self, client: AsyncClient, admin_headers: dict, db_session
    ):
        """运营者要能做"先建好、写好内容再上线"——建好即停用的系列不得进公开列表。"""
        resp = await client.post(
            ADMIN_SERIES,
            headers=admin_headers,
            json={
                "title": {"zh": "草稿系列", "en": "Draft Series"},
                "slug": "born-off",
                "is_active": False,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        assert _unwrap(resp.json())["is_active"] is False
        assert "born-off" not in await _public_slugs(client)

    @pytest.mark.asyncio
    async def test_partial_update_does_not_clobber_flag(
        self, client: AsyncClient, admin_headers: dict, db_session
    ):
        series = await _mk_series(db_session, "keep-flag", is_active=False)
        resp = await client.put(
            f"{ADMIN_SERIES}/{series.id}",
            headers=admin_headers,
            json={"title": {"zh": "只改名", "en": "Renamed"}},
        )
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["is_active"] is False


class TestAdminListKeepsInactiveVisible:
    @pytest.mark.asyncio
    async def test_default_admin_list_shows_inactive_with_the_flag(
        self, client: AsyncClient, admin_headers: dict, db_session
    ):
        """后台口必须仍然返回停用行、且带上 is_active——
        前端画得出状态、也点得回启用，否则停用是单向按钮。"""
        await _mk_series(db_session, "admin-visible-off", is_active=False)

        rows = await _admin_rows(client, admin_headers)
        by_slug = {row["slug"]: row for row in rows}
        assert "admin-visible-off" in by_slug, "停用系列从后台列表消失，运营者再也点不回来"
        assert by_slug["admin-visible-off"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_is_active_query_is_a_real_filter(
        self, client: AsyncClient, admin_headers: dict, db_session
    ):
        await _mk_series(db_session, "flt-on", is_active=True)
        await _mk_series(db_session, "flt-off", is_active=False)

        only_on = {
            row["slug"] for row in await _admin_rows(client, admin_headers, {"is_active": "true"})
        }
        only_off = {
            row["slug"] for row in await _admin_rows(client, admin_headers, {"is_active": "false"})
        }
        assert "flt-on" in only_on and "flt-off" not in only_on
        assert "flt-off" in only_off and "flt-on" not in only_off


class TestPublicReadSideEnforcement:
    @pytest.mark.asyncio
    async def test_public_list_hides_inactive(self, client: AsyncClient, test_post, db_session):
        on = await _mk_series(db_session, "pub-on")
        off = await _mk_series(db_session, "pub-off", is_active=False)
        await _mk_post_in_series(db_session, on, test_post.author_id, "pub-on-post")
        await _mk_post_in_series(db_session, off, test_post.author_id, "pub-off-post")

        slugs = await _public_slugs(client)
        assert "pub-on" in slugs
        assert "pub-off" not in slugs, "停用系列仍在公开列表里，点进去却是 404"

    @pytest.mark.asyncio
    async def test_detail_is_404_when_inactive_and_200_when_reenabled(
        self, client: AsyncClient, test_post, db_session, admin_headers: dict
    ):
        series = await _mk_series(db_session, "detail-off")
        await _mk_post_in_series(db_session, series, test_post.author_id, "detail-off-post")

        assert (await client.get(f"{SERIES}/detail-off")).status_code == 200

        resp = await client.put(f"{ADMIN_SERIES}/{series.id}/toggle", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["is_active"] is False
        assert (await client.get(f"{SERIES}/detail-off")).status_code == 404

        back = await client.put(f"{ADMIN_SERIES}/{series.id}/toggle", headers=admin_headers)
        assert _unwrap(back.json())["is_active"] is True
        assert (await client.get(f"{SERIES}/detail-off")).status_code == 200

    @pytest.mark.asyncio
    async def test_posts_keep_their_series_link_and_stay_reachable(
        self, client: AsyncClient, test_post, db_session, admin_headers: dict
    ):
        """停用摘的是入口，不是内容：文章本身仍可达、``series_id`` 也还留着——
        否则"临时下线一个系列"会变成把系列内的文章集体打散。"""
        series = await _mk_series(db_session, "keep-links")
        post = await _mk_post_in_series(db_session, series, test_post.author_id, "keep-links-post")

        await client.put(f"{ADMIN_SERIES}/{series.id}/toggle", headers=admin_headers)

        detail = await client.get(f"{BLOG}/posts/keep-links-post")
        assert detail.status_code == 200, detail.text

        # 先把主键拿到手上再读库：_db_row 会 expire 整个身份缓存，
        # 那时候再碰 series.id 就是在同步上下文里触发懒加载了。
        series_id = series.id
        stored = await _db_row(db_session, Post, post.id)
        assert stored.series_id == series_id


class TestSitemapDelivery:
    @pytest.mark.asyncio
    async def test_taxonomy_sitemap_excludes_inactive(self, client: AsyncClient, db_session):
        await _mk_series(db_session, "sm-on")
        await _mk_series(db_session, "sm-off", is_active=False)

        resp = await client.get(f"{BLOG}/sitemap-taxonomies.xml")
        assert resp.status_code == 200, resp.text
        assert "/series/sm-on" in resp.text, "启用系列没进爬虫投递面"
        assert "/series/sm-off" not in resp.text, "仍在向爬虫投递停用系列"

    def test_series_lastmod_ignores_inactive_rows(self):
        text = Path("backend/api/blog.py").read_text(encoding="utf-8")
        block = text[text.index("async def _sitemap_taxonomy_lastmod") :]
        block = block[: block.index("\n@router") if "\n@router" in block else len(block)]
        assert "PostSeries.is_active.is_(True)" in block


class TestPurgeIsWired:
    @pytest.mark.asyncio
    async def test_toggle_purges_frontend_page_cache(
        self, client: AsyncClient, admin_headers: dict, db_session, monkeypatch
    ):
        """purge 是 fire-and-forget：漏调用不会让接口变红，只会让已停用的系列
        在 SWR 窗口（/series/** 是 3600s）内继续以旧 HTML 面向访客。"""
        from backend.api import post_series as ps_api

        calls: list[str] = []
        monkeypatch.setattr(
            ps_api, "purge_frontend_page_cache", lambda reason=None: calls.append(str(reason))
        )

        series = await _mk_series(db_session, "purge-me")
        resp = await client.put(f"{ADMIN_SERIES}/{series.id}/toggle", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert len(calls) == 1, f"toggle 后没有清前台页面缓存：{calls}"


class TestFrontendHasARealControlPoint:
    """后端有口、前端没人点＝这一族仍然是死的（本批次就是因为这个才做的）。

    读源文本而不是跑浏览器：CI 与生产门禁都能判，而且这里要钉的恰好是
    "调用点 + 状态渲染 + 可点击"三件事同时存在——少任何一件，运营者都点不动它。
    """

    def test_composable_wraps_the_toggle_endpoint(self):
        text = Path("frontend/composables/useAdminManage.ts").read_text(encoding="utf-8")
        block = text[text.index("export async function toggleAdminSeries") :]
        block = block[: block.index("\n}") + 2]
        assert "/admin/series/${id}/toggle" in block
        assert "method: 'PUT'" in block, "toggle 口是 PUT，写成 POST 会 405"

    def test_series_page_calls_it_and_renders_the_state(self):
        page = Path("frontend/pages/admin/content/series.vue").read_text(encoding="utf-8")
        assert "toggleAdminSeries(" in page, "系列页必须真的调用 toggle 口"
        assert "s.is_active" in page, "取回的状态必须渲染，否则改了也看不见"
        assert 'aria-label="s.is_active' in page, "状态徽标必须是可点击控件（带无障碍名）"
        assert "import" in page and "toggleAdminSeries," in page, "必须从 useAdminManage 引入"
