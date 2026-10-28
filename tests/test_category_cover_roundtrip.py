"""分类封面图（``Category.cover_image``）读写两端的回归测试。

这一族此前的形状是"列与读口都在、写口缺半"：

* 模型有列、``CategoryResponse`` / 公开列表 / 按 slug 详情都带这个键，前台
  ``pages/categories/[slug].vue`` 的类型里也声明了它；
* 但 ``CategoryBase`` **没有**这一项，于是 `POST /blog/categories` 根本不收，
  而 ``create_category`` 手搓 ``Category(...)`` 时也没带上（就算 schema 收了也会被静默丢弃）；
* 后台分类弹窗只有一个 140px 的封面**预览**，没有任何写入控件。

结果是"分类封面"这件事只能靠数据库里手工塞值，站主在界面上既写不进也看不到变化。
本文件钉住接通之后的四条口径：创建即可定封面、PUT 能改能清、读口与写口同一条值、
省略键不等于清空（``exclude_unset`` 增量语义）。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Category

BLOG = "/api/blog"
COVER = "https://cdn.example.com/covers/dev-512.png"
OTHER_COVER = "/uploads/covers/other.png"


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 list/dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _mk_category(db: AsyncSession, slug: str, *, cover: str | None = None) -> Category:
    category = Category(
        name={"zh": f"分类{slug}", "en": slug},
        slug=slug,
        color="#3B82F6",
        cover_image=cover,
        is_active=True,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _row_cover(db: AsyncSession, category_id: int) -> str | None:
    from sqlalchemy import select

    return await db.scalar(select(Category.cover_image).where(Category.id == category_id))


class TestCreateAcceptsCover:
    """创建口必须能定封面——否则新建分类永远没有封面，只能建完再补一次 PUT。"""

    @pytest.mark.asyncio
    async def test_category_base_declares_cover(self):
        from backend.schemas import CategoryBase, CategoryCreate, CategoryUpdate

        for model in (CategoryBase, CategoryCreate, CategoryUpdate):
            assert "cover_image" in model.model_fields, f"{model.__name__} 缺 cover_image"

    @pytest.mark.asyncio
    async def test_post_create_stores_and_echoes_cover(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        resp = await client.post(
            f"{BLOG}/categories",
            json={"name": {"zh": "封面创建分类", "en": "Cover Create"}, "cover_image": COVER},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201), resp.text
        data = _unwrap(resp.json())
        assert data["cover_image"] == COVER
        assert await _row_cover(db_session, int(data["id"])) == COVER

    @pytest.mark.asyncio
    async def test_post_without_cover_stays_null(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        resp = await client.post(
            f"{BLOG}/categories",
            json={"name": {"zh": "无封面分类", "en": "No Cover"}},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201), resp.text
        assert _unwrap(resp.json())["cover_image"] is None


class TestWriteAndReadAgree:
    """写口（POST/PUT）与读口（详情、公开列表、后台列表）必须同一条值。"""

    @pytest.mark.asyncio
    async def test_detail_and_lists_carry_the_same_value(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        category = await _mk_category(db_session, "cover-roundtrip")
        await cache.clear()

        put = await client.put(
            f"{BLOG}/categories/{category.id}",
            json={"cover_image": COVER},
            headers=admin_headers,
        )
        assert put.status_code == 200, put.text
        echoed = _unwrap(put.json())["cover_image"]

        by_slug = await client.get(f"{BLOG}/categories/slug/cover-roundtrip")
        assert by_slug.status_code == 200, by_slug.text
        listed = await client.get(f"{BLOG}/categories", params={"all": "true"})
        assert listed.status_code == 200, listed.text

        detail = _unwrap(by_slug.json())["cover_image"]
        row = next(r for r in _unwrap(listed.json()) if r["slug"] == "cover-roundtrip")
        assert (echoed, detail, row["cover_image"]) == (COVER, COVER, COVER)
        assert await _row_cover(db_session, category.id) == COVER

    @pytest.mark.asyncio
    async def test_overlong_cover_is_rejected_not_truncated(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """列是 String(500)：超长必须在 schema 就拒掉，否则 MySQL/PG 上静默截断成坏链。"""
        category = await _mk_category(db_session, "cover-overlong", cover=COVER)
        resp = await client.put(
            f"{BLOG}/categories/{category.id}",
            json={"cover_image": "https://x.test/" + "a" * 600},
            headers=admin_headers,
        )
        assert resp.status_code == 422, resp.text
        assert await _row_cover(db_session, category.id) == COVER


class TestClearAndOmit:
    """ "显式清空"与"没提这个键"是两回事——PUT 是 exclude_unset 增量语义。"""

    @pytest.mark.asyncio
    async def test_explicit_null_clears_cover(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        category = await _mk_category(db_session, "cover-clear", cover=COVER)
        resp = await client.put(
            f"{BLOG}/categories/{category.id}",
            json={"cover_image": None},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["cover_image"] is None
        assert await _row_cover(db_session, category.id) is None

    @pytest.mark.asyncio
    async def test_omitting_the_key_leaves_cover_untouched(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """改一次分类名不该把封面抹掉：这是"每次 PUT 提交全部字段"的表单最容易踩的坑。"""
        category = await _mk_category(db_session, "cover-keep", cover=COVER)
        resp = await client.put(
            f"{BLOG}/categories/{category.id}",
            json={"name": {"zh": "改过名的分类", "en": "Renamed"}},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert await _row_cover(db_session, category.id) == COVER

    @pytest.mark.asyncio
    async def test_empty_string_clears_rather_than_stores_blank(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """空串若原样落库，前台会拿到 `src=""` 而不是"没有封面"。"""
        category = await _mk_category(db_session, "cover-blank", cover=COVER)
        resp = await client.put(
            f"{BLOG}/categories/{category.id}",
            json={"cover_image": ""},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        stored = await _row_cover(db_session, category.id)
        assert stored in (None, ""), stored
        assert not stored


class TestLocalizedDelivery:
    """本地化响应模型也带这一项——前台页面若走本地化口，缺键就永远渲染不出封面。"""

    def test_localized_schema_and_builder_include_cover(self):
        from backend.schemas import CategoryLocalizedResponse

        assert "cover_image" in CategoryLocalizedResponse.model_fields
        fields = CategoryLocalizedResponse.from_category.__code__.co_names
        assert "cover_image" in fields

    @pytest.mark.asyncio
    async def test_localized_builder_passes_the_value(self, db_session: AsyncSession):
        from backend.schemas import CategoryLocalizedResponse

        category = await _mk_category(db_session, "cover-i18n", cover=OTHER_COVER)
        row = CategoryLocalizedResponse.from_category(category, "zh")
        assert row.cover_image == OTHER_COVER
