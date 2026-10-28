"""分类 / 标签 ``is_active`` 启停族的两端与强制点回归（批次 #22）。

覆盖面（缺一条就是"写了列却没人执行"或"能改却看不见"的那一类缺陷）：
1. schema：Create/Update/Response 三处都声明，缺任何一处即写不进或读不出；
2. 写口：创建即可停用、更新可来回切，且 PUT 必须同时清掉公开与后台两种列表缓存；
3. 强制点：公开列表默认只回启用行、``?all=true`` 回全部（后台数据源，否则停用是单向按钮）、
   响应缓存键位必须带这一判别位（否则后台一次 all=true 就能把停用行投毒给前台）；
4. 投递面：两处 sitemap 与站点统计都不收停用行；
5. 搬迁面：导出 ZIP 带这一项，两处导入器把停用状态写回行里，缺键（旧导出包）按启用导入；
6. 可达性面：停用只摘入口，不摘它名下已发布文章按 slug 筛选的结果。
"""

import io
import json
import zipfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.cache import (
    CACHE_KEY_CATEGORIES,
    CACHE_KEY_CATEGORIES_ALL,
    CACHE_KEY_TAGS,
    CACHE_KEY_TAGS_ALL,
    cache,
)
from backend.models.blog import Category, Post, Tag

BLOG = "/api/blog"


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 list/dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _mk_category(db, slug: str, *, is_active: bool = True) -> Category:
    category = Category(
        name={"zh": f"分类{slug}", "en": slug},
        slug=slug,
        color="#3B82F6",
        is_active=is_active,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _mk_tag(db, slug: str, *, is_active: bool = True) -> Tag:
    tag = Tag(
        name={"zh": f"标签{slug}", "en": slug},
        slug=slug,
        color="#3776AB",
        is_active=is_active,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def _slugs(client: AsyncClient, params: dict | None = None) -> list[str]:
    resp = await client.get(f"{BLOG}/categories", params=params or {})
    assert resp.status_code == 200, resp.text
    return [row["slug"] for row in _unwrap(resp.json())]


def _zip(categories: list, tags: list) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("posts.json", json.dumps([]))
        zf.writestr("categories.json", json.dumps(categories))
        zf.writestr("tags.json", json.dumps(tags))
    return buffer.getvalue()


class TestSchemaDeclaresTheFlag:
    def test_create_update_response_all_declare(self):
        from backend.schemas import CategoryCreate, CategoryResponse, CategoryUpdate

        for model in (CategoryCreate, CategoryUpdate, CategoryResponse):
            assert "is_active" in model.model_fields, f"{model.__name__} 缺 is_active"
        # Create 侧缺省必须是启用：默认 False 会让"新建分类"直接前台不可见
        assert CategoryCreate.model_fields["is_active"].default is True
        assert CategoryResponse.model_fields["is_active"].is_required()


class TestWriteSide:
    @pytest.mark.asyncio
    async def test_create_defaults_to_active(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            f"{BLOG}/categories",
            headers=admin_headers,
            json={"name": {"zh": "默认启用", "en": "Default On"}, "slug": "default-on"},
        )
        assert resp.status_code in (200, 201), resp.text
        assert _unwrap(resp.json())["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_can_start_inactive(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            f"{BLOG}/categories",
            headers=admin_headers,
            json={
                "name": {"zh": "建好即停用", "en": "Born Off"},
                "slug": "born-off",
                "is_active": False,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        assert _unwrap(resp.json())["is_active"] is False

    @pytest.mark.asyncio
    async def test_toggle_off_and_back_on(self, client: AsyncClient, admin_headers: dict):
        created = await client.post(
            f"{BLOG}/categories",
            headers=admin_headers,
            json={"name": {"zh": "可切换", "en": "Toggle"}, "slug": "toggle-me"},
        )
        cid = _unwrap(created.json())["id"]

        off = await client.put(
            f"{BLOG}/categories/{cid}", headers=admin_headers, json={"is_active": False}
        )
        assert _unwrap(off.json())["is_active"] is False
        on = await client.put(
            f"{BLOG}/categories/{cid}", headers=admin_headers, json={"is_active": True}
        )
        assert _unwrap(on.json())["is_active"] is True

    @pytest.mark.asyncio
    async def test_partial_update_does_not_clobber_flag(
        self, client: AsyncClient, admin_headers: dict, db_session
    ):
        category = await _mk_category(db_session, "keep-flag", is_active=False)
        resp = await client.put(
            f"{BLOG}/categories/{category.id}",
            headers=admin_headers,
            json={"name": {"zh": "只改名", "en": "Renamed"}},
        )
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["is_active"] is False


class TestReadSideEnforcement:
    @pytest.mark.asyncio
    async def test_public_list_hides_inactive_admin_list_shows_it(
        self, client: AsyncClient, db_session
    ):
        await _mk_category(db_session, "on-cat", is_active=True)
        await _mk_category(db_session, "off-cat", is_active=False)

        assert "on-cat" in await _slugs(client)
        assert "off-cat" not in await _slugs(client)

        admin = await _slugs(client, {"all": "true"})
        assert {"on-cat", "off-cat"} <= set(admin)

    @pytest.mark.asyncio
    async def test_list_cache_keys_carry_the_discriminator(self, client: AsyncClient, db_session):
        """后台先打 ?all=true，前台默认口不得因此看见停用行（缓存投毒面）。"""
        await _mk_category(db_session, "poison-off", is_active=False)

        assert "poison-off" in await _slugs(client, {"all": "true"})
        assert "poison-off" not in await _slugs(client)
        # 反向也要成立：默认口写过的缓存不能把停用行带进后台口
        assert await cache.get(CACHE_KEY_CATEGORIES) is not None
        assert await cache.get(CACHE_KEY_CATEGORIES_ALL) is not None
        assert CACHE_KEY_CATEGORIES != CACHE_KEY_CATEGORIES_ALL

    @pytest.mark.asyncio
    async def test_update_clears_both_cache_shapes(
        self, client: AsyncClient, admin_headers: dict, db_session
    ):
        category = await _mk_category(db_session, "purge-me", is_active=True)
        await cache.set(CACHE_KEY_CATEGORIES, [{"slug": "stale"}], ttl=600)
        await cache.set(CACHE_KEY_CATEGORIES_ALL, [{"slug": "stale"}], ttl=600)

        resp = await client.put(
            f"{BLOG}/categories/{category.id}",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert resp.status_code == 200, resp.text
        assert await cache.get(CACHE_KEY_CATEGORIES) is None, "公开列表缓存未清"
        assert await cache.get(CACHE_KEY_CATEGORIES_ALL) is None, "后台列表缓存未清"

    @pytest.mark.asyncio
    async def test_by_slug_reports_the_flag(self, client: AsyncClient, db_session):
        """停用的分类直接 URL 仍可解析：文章页的分类链接不能因停用变 404。"""
        category = await _mk_category(db_session, "reachable-off", is_active=False)
        resp = await client.get(f"{BLOG}/categories/slug/reachable-off")
        assert resp.status_code == 200, resp.text
        body = _unwrap(resp.json())
        assert body["id"] == category.id
        assert body["is_active"] is False


class TestTagSideKeepsPace:
    @pytest.mark.asyncio
    async def test_tags_default_hides_and_all_shows(self, client: AsyncClient, db_session):
        await _mk_tag(db_session, "on-tag", is_active=True)
        await _mk_tag(db_session, "off-tag", is_active=False)

        async def slugs(params: dict) -> list[str]:
            resp = await client.get(f"{BLOG}/tags", params=params)
            assert resp.status_code == 200, resp.text
            return [row["slug"] for row in _unwrap(resp.json())]

        assert "off-tag" not in await slugs({})
        assert "off-tag" in await slugs({"all": "true"})

    @pytest.mark.asyncio
    async def test_tag_list_cache_keys_are_separate(self, client: AsyncClient, db_session):
        await _mk_tag(db_session, "poison-tag", is_active=False)
        resp = await client.get(f"{BLOG}/tags", params={"all": "true"})
        assert resp.status_code == 200
        assert await cache.get(CACHE_KEY_TAGS_ALL) is not None
        assert await cache.get(CACHE_KEY_TAGS) is None, "后台口的缓存串到了前台口键位"
        assert CACHE_KEY_TAGS != CACHE_KEY_TAGS_ALL


class TestSeoAndStatsSurfaces:
    @pytest.mark.asyncio
    async def test_sitemap_and_seo_alias_exclude_inactive(self, client: AsyncClient, db_session):
        await _mk_category(db_session, "sm-on", is_active=True)
        await _mk_category(db_session, "sm-off", is_active=False)

        for path in ("/api/blog/sitemap-taxonomies.xml", "/api/seo/sitemap.xml"):
            resp = await client.get(path)
            assert resp.status_code == 200, f"{path} -> {resp.status_code}"
            body = resp.text
            assert "/categories/sm-on" in body, f"{path} 少了启用分类"
            assert "/categories/sm-off" not in body, f"{path} 仍在向爬虫投递停用分类"

    @pytest.mark.asyncio
    async def test_site_stats_count_only_active(self, client: AsyncClient, db_session, test_post):
        """停用分类即使挂着已发布文章，公开统计也不能数它——访客点不到那个归档页。"""
        inactive = await _mk_category(db_session, "stat-off", is_active=False)
        hidden = Post(
            title={"zh": "停用分类里的文章", "en": "Hidden"},
            slug="stat-off-post",
            content={"zh": "内容", "en": "body"},
            author_id=test_post.author_id,
            category_id=inactive.id,
            status="published",
        )
        db_session.add(hidden)
        await db_session.commit()

        resp = await client.get(f"{BLOG}/site-stats")
        assert resp.status_code == 200, resp.text
        stats = _unwrap(resp.json())
        assert stats["total_categories"] == 1  # 只有 test_category 那一条被数到
        assert stats["total_posts"] == 2


class TestMigrationRoundTrip:
    @pytest.mark.asyncio
    async def test_export_zip_carries_the_flag_for_both_taxonomies(
        self, client: AsyncClient, staff_headers, db_session
    ):
        await _mk_category(db_session, "exp-off", is_active=False)
        await _mk_category(db_session, "exp-on", is_active=True)
        await _mk_tag(db_session, "exp-tag-off", is_active=False)
        await _mk_tag(db_session, "exp-tag-on", is_active=True)

        resp = await client.get(
            "/api/admin/export/posts", params={"include_drafts": True}, headers=staff_headers
        )
        assert resp.status_code == 200, resp.text
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            cats = json.loads(zf.read("categories.json"))
            tags = json.loads(zf.read("tags.json"))

        by_slug = {c["slug"]: c for c in cats}
        assert by_slug["exp-off"]["is_active"] is False
        assert by_slug["exp-on"]["is_active"] is True
        by_tag_slug = {t["slug"]: t for t in tags}
        assert by_tag_slug["exp-tag-off"]["is_active"] is False
        assert by_tag_slug["exp-tag-on"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_zip_importer_restores_the_flag(
        self, client: AsyncClient, staff_headers, db_session
    ):
        """导入侧必须把这一项写回新建的行里（分类此前整块漏掉，标签已做）。"""
        content = _zip(
            [
                {"slug": "rt-off", "name": {"zh": "停用", "en": "off"}, "is_active": False},
                {"slug": "rt-on", "name": {"zh": "启用", "en": "on"}, "is_active": True},
            ],
            [{"slug": "rt-tag-off", "name": {"zh": "停用标签", "en": "off"}, "is_active": False}],
        )
        resp = await client.post(
            "/api/admin/import/posts",
            files={"file": ("rosetta_export.zip", content, "application/zip")},
            headers=staff_headers,
        )
        assert resp.status_code == 200, resp.text
        db_session.expire_all()
        rows = {
            c.slug: c.is_active
            for c in (await db_session.execute(select(Category))).scalars().all()
        }
        assert rows["rt-off"] is False
        assert rows["rt-on"] is True
        tag_rows = {
            t.slug: t.is_active for t in (await db_session.execute(select(Tag))).scalars().all()
        }
        assert tag_rows["rt-tag-off"] is False

    @pytest.mark.asyncio
    async def test_zip_importer_defaults_missing_key_to_active(
        self, client: AsyncClient, staff_headers, db_session
    ):
        """旧导出文件里没有这一项：缺键必须按启用导入，否则升级后一次搬迁让全站分类集体停用。"""
        content = _zip([{"slug": "legacy-cat", "name": {"zh": "旧包", "en": "legacy"}}], [])
        resp = await client.post(
            "/api/admin/import/posts",
            files={"file": ("legacy.zip", content, "application/zip")},
            headers=staff_headers,
        )
        assert resp.status_code == 200, resp.text
        db_session.expire_all()
        legacy = (
            await db_session.execute(select(Category).where(Category.slug == "legacy-cat"))
        ).scalar_one()
        assert legacy.is_active is True

    def test_restore_importer_covers_both_taxonomy_branches(self):
        """整站恢复导入器（backup/restore）的两个分支同样要带上启停状态。

        这一段用源文本守卫而不是跑一次恢复：恢复流程会重建全站表，
        在测试库里驱动它的成本与风险都远高于断言这两行存在。
        """
        text = Path("backend/api/import_export.py").read_text(encoding="utf-8")
        cats_block = text[text.index("# === 3. categories ===") : text.index("# === 4. tags ===")]
        tags_block = text[text.index("# === 4. tags ===") : text.index("# === 5. navigations ===")]
        for name, block in (("分类", cats_block), ("标签", tags_block)):
            assert (
                'existing_obj.is_active = item.get("is_active", existing_obj.is_active)' in block
            ), f"覆盖既有{name}时没有搬运启停状态"
            assert 'is_active=item.get("is_active", True)' in block, f"新建{name}时缺启停状态"


class TestWarmerShapeMatchesReadSide:
    def test_cache_warmer_warms_only_active_categories(self):
        """预热门面与读侧形状必须同步演化：预热写入 CACHE_KEY_CATEGORIES，
        若它把停用行也烘进去，TTL 内前台列表就会显示一个点不到的分类。"""
        text = Path("backend/core/cache_warmer.py").read_text(encoding="utf-8")
        block = text[text.index("async def _warmup_categories") :].split("async def _warmup_tags")[
            0
        ]
        assert ".where(Category.is_active.is_(True))" in block
        assert "is_active=row.Category.is_active" in block

    def test_taxonomy_lastmod_ignores_inactive_rows(self):
        text = Path("backend/api/blog.py").read_text(encoding="utf-8")
        block = text[text.index("async def _sitemap_taxonomy_lastmod") :]
        block = block[: block.index("\n@router") if "\n@router" in block else len(block)]
        assert "Category.is_active.is_(True)" in block
        assert "Tag.is_active.is_(True)" in block


@pytest.mark.asyncio
async def test_inactive_category_posts_stay_reachable_by_slug(
    client: AsyncClient, db_session, test_post
):
    """停用只把分类从公开列表/导航/sitemap/统计里摘掉，不摘它名下已发布文章的可访问性。

    与 ``test_site_stats_count_only_active`` 是同一口径的两面：前台不再生成指向停用
    分类的入口，但已经存在的入口（文章页上的分类链接、外部已收录的 URL）不得变 404。
    """
    category = await _mk_category(db_session, "filter-off", is_active=False)
    hidden = Post(
        title={"zh": "停用分类里的文章", "en": "Reachable"},
        slug="filter-off-post",
        content={"zh": "内容", "en": "body"},
        author_id=test_post.author_id,
        category_id=category.id,
        status="published",
    )
    db_session.add(hidden)
    await db_session.commit()

    resp = await client.get(f"{BLOG}/posts", params={"category": "filter-off"})
    assert resp.status_code == 200, resp.text
    assert "filter-off-post" in [row["slug"] for row in _unwrap(resp.json())["items"]]
