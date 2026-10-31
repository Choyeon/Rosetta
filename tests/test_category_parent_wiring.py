"""层级分类（``Category.parent_id``）读写两端的回归测试（批次 #114）。

这一族此前的形状是"列与关系都在、schema 与两端界面全断"：

* 模型有 `parent_id`（还带 FK、索引与 `parent`/`children` 关系），迁移早就建好了列；
* 但 `CategoryBase` / `CategoryUpdate` / `CategoryResponse` **都没有**这一项，
  所以 `POST`/`PUT /blog/categories` 收不到、`GET /blog/categories` 也回吐不出；
* 后台分类弹窗没有任何父分类控件、列表是纯平铺，前台分类页的面包屑只有「分类 / 当前」。

结果是"子分类"这件事在界面上根本不存在——库里躺着的那一列只可能由直连 SQL 写进去，
而写进去也没有任何一个渲染面读它。本文件钉住接通之后的口径：创建即可定父级、PUT 能改能清、
省略键不动它、父级必须存在且不成环、三个读口（含预热载荷）回吐同一条值。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import CACHE_KEY_CATEGORIES, cache
from backend.models.blog import Category
from backend.schemas import CategoryBase, CategoryCreate, CategoryResponse, CategoryUpdate

BLOG = "/api/blog"


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 list/dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _mk_category(db: AsyncSession, slug: str, *, parent_id: int | None = None) -> Category:
    category = Category(
        name={"zh": f"分类{slug}", "en": slug},
        slug=slug,
        color="#3B82F6",
        is_active=True,
        parent_id=parent_id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _row_parent(db: AsyncSession, category_id: int) -> int | None:
    return await db.scalar(select(Category.parent_id).where(Category.id == category_id))


class TestSchemaDeclaresParent:
    """四段里最先断的一段：schema 不收这个键，后面全部界面都是空转。"""

    def test_write_and_read_models_all_declare_it(self):
        for model in (CategoryBase, CategoryCreate, CategoryUpdate, CategoryResponse):
            assert "parent_id" in model.model_fields, f"{model.__name__} 缺 parent_id"

    def test_zero_is_top_level_not_a_dangling_parent(self):
        """后台下拉用 value=0 表示「顶级分类」（select 的 value 不能是 null）。
        不归一就等于让每次"改成顶级"都提交一个指向不存在的 id 422/400。"""
        assert CategoryBase(name={"zh": "零父级"}, parent_id=0).parent_id is None
        assert CategoryUpdate(parent_id=0).model_dump(exclude_unset=True) == {"parent_id": None}

    def test_response_tolerates_a_stale_cached_row(self):
        """分类列表整份进响应缓存：上线前烘好的载荷没有这个键，
        必填会让"命中缓存"那条路径当场校验失败（冷路径反而正常）。"""
        assert (
            CategoryResponse(
                id=1,
                name={"zh": "旧载荷"},
                slug="stale-shape",
                color="#3B82F6",
                is_active=True,
                created_at="2026-01-01T00:00:00Z",
            ).parent_id
            is None
        )


class TestCreateAcceptsParent:
    @pytest.mark.asyncio
    async def test_post_stores_and_echoes_parent(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        parent = await _mk_category(db_session, "p-create")
        resp = await client.post(
            f"{BLOG}/categories",
            json={"name": {"zh": "子分类创建", "en": "Child Create"}, "parent_id": parent.id},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201), resp.text
        data = _unwrap(resp.json())
        assert data["parent_id"] == parent.id
        assert await _row_parent(db_session, int(data["id"])) == parent.id

    @pytest.mark.asyncio
    async def test_post_without_parent_is_top_level(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        resp = await client.post(
            f"{BLOG}/categories",
            json={"name": {"zh": "顶级分类", "en": "Top Level"}},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201), resp.text
        data = _unwrap(resp.json())
        assert data["parent_id"] is None
        assert await _row_parent(db_session, int(data["id"])) is None

    @pytest.mark.asyncio
    async def test_post_with_unknown_parent_is_400(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """父分类不存在就建档，等于造一条永远不在任何树里的孤儿；
        400 而不是 500/404：这是取值非法，不是路由缺失。"""
        resp = await client.post(
            f"{BLOG}/categories",
            json={"name": {"zh": "悬空子分类", "en": "Dangling"}, "parent_id": 999_999},
            headers=admin_headers,
        )
        assert resp.status_code == 400, resp.text


class TestUpdateParent:
    @pytest.mark.asyncio
    async def test_put_moves_under_parent_and_back_to_top(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        parent = await _mk_category(db_session, "p-move")
        child = await _mk_category(db_session, "c-move")
        await cache.clear()

        moved = await client.put(
            f"{BLOG}/categories/{child.id}",
            json={"parent_id": parent.id},
            headers=admin_headers,
        )
        assert moved.status_code == 200, moved.text
        assert _unwrap(moved.json())["parent_id"] == parent.id
        assert await _row_parent(db_session, child.id) == parent.id

        topped = await client.put(
            f"{BLOG}/categories/{child.id}",
            json={"parent_id": None},
            headers=admin_headers,
        )
        assert topped.status_code == 200, topped.text
        assert _unwrap(topped.json())["parent_id"] is None
        assert await _row_parent(db_session, child.id) is None

    @pytest.mark.asyncio
    async def test_put_omitting_the_key_does_not_touch_it(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """PUT 是 exclude_unset 增量语义：改个描述就把层级抹掉，
        表现是"没碰父分类这一栏，保存后分类从树上掉下来"，而接口回 200。"""
        parent = await _mk_category(db_session, "p-omit")
        child = await _mk_category(db_session, "c-omit", parent_id=parent.id)
        resp = await client.put(
            f"{BLOG}/categories/{child.id}",
            json={"name": {"zh": "只改名", "en": "Rename only"}},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["parent_id"] == parent.id
        assert await _row_parent(db_session, child.id) == parent.id

    @pytest.mark.asyncio
    async def test_self_parent_is_rejected(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        cat = await _mk_category(db_session, "self-parent")
        resp = await client.put(
            f"{BLOG}/categories/{cat.id}",
            json={"parent_id": cat.id},
            headers=admin_headers,
        )
        assert resp.status_code == 400, resp.text
        assert await _row_parent(db_session, cat.id) is None

    @pytest.mark.asyncio
    async def test_descendant_parent_is_rejected_and_row_untouched(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """A→B→C 之后把 A 挂到 C 下面就是环。闸门必须排在写入之前：
        先落库再回 400 会留下一条谁也到不了的子树（FK 是 SET NULL，级联查不出）。"""
        a = await _mk_category(db_session, "ring-a")
        b = await _mk_category(db_session, "ring-b", parent_id=a.id)
        c = await _mk_category(db_session, "ring-c", parent_id=b.id)

        resp = await client.put(
            f"{BLOG}/categories/{a.id}",
            json={"parent_id": c.id},
            headers=admin_headers,
        )
        assert resp.status_code == 400, resp.text
        assert await _row_parent(db_session, a.id) is None
        assert await _row_parent(db_session, b.id) == a.id
        assert await _row_parent(db_session, c.id) == b.id

    @pytest.mark.asyncio
    async def test_unknown_parent_is_rejected(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        cat = await _mk_category(db_session, "unknown-parent")
        resp = await client.put(
            f"{BLOG}/categories/{cat.id}",
            json={"parent_id": 999_998},
            headers=admin_headers,
        )
        assert resp.status_code == 400, resp.text
        assert await _row_parent(db_session, cat.id) is None


class TestReadSurfacesCarryParent:
    """写口落值之后，三个读面必须是同一条值——少一个就有一处界面看不见层级。"""

    @pytest.mark.asyncio
    async def test_detail_public_list_and_admin_list_agree(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        parent = await _mk_category(db_session, "p-read")
        await _mk_category(db_session, "c-read", parent_id=parent.id)
        await cache.clear()

        by_slug = await client.get(f"{BLOG}/categories/slug/c-read")
        assert by_slug.status_code == 200, by_slug.text
        detail = _unwrap(by_slug.json())["parent_id"]

        public = await client.get(f"{BLOG}/categories")
        assert public.status_code == 200, public.text
        admin = await client.get(f"{BLOG}/categories", params={"all": "true"})
        assert admin.status_code == 200, admin.text

        public_row = next(r for r in _unwrap(public.json()) if r["slug"] == "c-read")
        admin_row = next(r for r in _unwrap(admin.json()) if r["slug"] == "c-read")
        assert (detail, public_row["parent_id"], admin_row["parent_id"]) == (
            parent.id,
            parent.id,
            parent.id,
        )

    @pytest.mark.asyncio
    async def test_warmer_projection_carries_parent(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """预热载荷与读侧同键同形：预热不带这个键时，命中预热的匿名请求会稳定拿到
        扁平列表（整个 TTL 内前台看不到层级），而直连数据库的那次请求是对的。"""
        parent = await _mk_category(db_session, "p-warm")
        child = await _mk_category(db_session, "c-warm", parent_id=parent.id)

        # 直接跑那一个预热任务：`warmup_cache()` 还带全局开关与"只跑一次"的状态机，
        # 在测试进程里会被提前 return，那样这条断言就永远只是空通过。
        from backend.core.cache_warmer import cache_warmer

        await cache.delete(CACHE_KEY_CATEGORIES)
        assert await cache_warmer._warmup_categories() == 1
        warmed = await cache.get(CACHE_KEY_CATEGORIES)
        assert warmed is not None, "预热没写进这个键位，对照断言会退化成空通过"
        row = next((r for r in warmed if r.get("slug") == child.slug), None)
        assert row is not None, f"预热载荷里没有该分类：{str(warmed)[:120]}"
        assert row.get("parent_id") == parent.id, (
            f"预热投影丢了 parent_id（拿到 {row.get('parent_id')!r}），"
            "命中预热的匿名请求会在整个 TTL 内看不到层级"
        )
        # 预热写的就是匿名读侧回放的键位：两边必须是同一条值
        public = await client.get(f"{BLOG}/categories")
        assert public.status_code == 200, public.text
        cached_row = next(r for r in _unwrap(public.json()) if r["slug"] == child.slug)
        assert cached_row["parent_id"] == parent.id


class TestDeleteKeepsChildrenAloft:
    @pytest.mark.asyncio
    async def test_deleting_a_parent_lifts_children_to_top_level(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """`parent_id` 的 FK 是 SET NULL：子分类不该随父级一起消失。
        这里连删带验，防止以后有人把级联改成 CASCADE 而界面毫无提示。"""
        parent = await _mk_category(db_session, "p-drop")
        child = await _mk_category(db_session, "c-drop", parent_id=parent.id)

        resp = await client.delete(f"{BLOG}/categories/{parent.id}", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert await _row_parent(db_session, child.id) is None
        assert await db_session.scalar(select(Category.id).where(Category.id == child.id))
