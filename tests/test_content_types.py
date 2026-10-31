"""自定义内容类型（``content_types`` + ``Post.meta_fields``）四段接通的回归测试。

这一族此前是"数据契约完整、执行链为空"的典型：``ContentTypeDefinition`` 表、
``Post.post_type`` / ``Post.meta_fields`` 两列都在，但没有任何写口会写、没有任何读口会回、
没有任何页面会渲染。本文件钉住接通之后的口径：

1. **定义 CRUD**：key 不可改（请求体带 key 直接 422）、重复 key 409、被文章引用时删除 409。
2. **写口校验**：未知类型 / 内置 post 带自定义字段 / 缺必填 / 未知字段 / 类型不符 / 选项外取值
   一律 422，且错误带上字段级 details（前端可直接标到输入框）。
3. **四段连通**：写口落库是归一化后的 JSON（数字串转数、布尔串转布尔、朴素 datetime 按 UTC），
   ``GET /posts/{slug}``、``GET /posts/{id}``、``GET /posts/{id}/edit`` 都回 ``post_type`` + ``meta_fields``。
4. **读侧比写侧宽**：定义改了（新增必填字段）之后，只改标题的 PUT 不得重校验库存 meta_fields；
   库里脏成裸字符串的 meta_fields 不得把详情/编辑页打成 500。
5. **列表可见性**：`GET /blog/posts` 的缺省是"全部类型"（自定义类型文章因此在前台列表、
   首页、作者页、后台文章列表都存在），`?post_type=<key>` 只做显式收窄；判别位必须进响应
   缓存键且缺省段是 `all`；列表项带出**必填**的 `post_type`；sitemap 的作者清单与子表
   lastmod 按同一口径（不再只看内置类型）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.blog import _get_post_list_cache_key, _iso8601, _sitemap_taxonomy_lastmod
from backend.core.cache import cache
from backend.models.blog import Post

# 项目用 backend.utils.compat.UTC：运行时是 Python 3.10，datetime.UTC 要 3.11+ 才有
from backend.utils.compat import UTC

BOOK_FIELDS = [
    {"key": "author", "label": "作者", "field_type": "text", "required": True},
    {"key": "pages", "label": "页数", "field_type": "number"},
    {"key": "finished", "label": "已读完", "field_type": "boolean"},
    {"key": "format", "label": "装帧", "field_type": "select", "options": ["精装", "平装"]},
    {"key": "published_on", "label": "出版日期", "field_type": "date"},
    {"key": "read_at", "label": "读完时间", "field_type": "datetime"},
    {"key": "cover", "label": "封面", "field_type": "image"},
    {"key": "detail_link", "label": "详情链接", "field_type": "url"},
    {"key": "notes", "label": "笔记", "field_type": "markdown"},
    {"key": "summary", "label": "简介", "field_type": "textarea"},
]


def _payload(body: dict) -> dict:
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


def _key(prefix: str = "book") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _slug() -> str:
    return f"ct-{uuid.uuid4().hex[:10]}"


async def _create_type(
    client: AsyncClient, headers: dict, *, key: str | None = None, **overrides
) -> dict:
    payload = {
        "key": key or _key(),
        "name": "书籍",
        "icon": "book-open",
        "description": "书目元数据",
        "fields": BOOK_FIELDS,
    }
    payload.update(overrides)
    response = await client.post("/api/admin/content-types", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return _payload(response.json())


async def _create_post(
    client: AsyncClient, headers: dict, *, slug: str | None = None, **overrides
) -> dict:
    payload: dict = {
        "title": {"zh": "内容类型测试文章"},
        "content": {"zh": "正文"},
        "slug": slug or _slug(),
        "status": "published",
    }
    payload.update(overrides)
    response = await client.post("/api/blog/posts", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return _payload(response.json())


@pytest.fixture(autouse=True)
async def _clear_public_cache():
    """公开定义缓存是进程级的，不清会让上一条用例的定义漏进下一条。"""
    await cache.delete("content_types:public")


class TestDefinitionCrud:
    @pytest.mark.asyncio
    async def test_create_and_public_list(self, client, admin_headers):
        key = _key()
        created = await _create_type(client, admin_headers, key=key)

        assert created["key"] == key
        assert created["posts_count"] == 0
        assert [f["key"] for f in created["fields"]] == [f["key"] for f in BOOK_FIELDS]

        public = await client.get("/api/content-types")
        assert public.status_code == 200
        rows = public.json()
        row = next(r for r in rows if r["key"] == key)
        assert row["name"] == "书籍"
        # 公开口不带 id：前台只需要 key 与字段形状
        assert "id" not in row
        assert row["fields"][2]["field_type"] == "boolean"

    @pytest.mark.asyncio
    async def test_duplicate_key_is_409(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        response = await client.post(
            "/api/admin/content-types",
            json={"key": key, "name": "重复", "fields": []},
            headers=admin_headers,
        )
        assert response.status_code == 409, response.text
        assert response.json()["error_code"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_key_is_immutable(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        response = await client.put(
            f"/api/admin/content-types/{key}",
            json={"key": "renamed", "name": "改名"},
            headers=admin_headers,
        )
        # ContentTypeUpdate 不带 key + extra=forbid：带 key 的请求体整体被拒，
        # 而不是"静默忽略 key 只改 name"——后者会让调用方以为改名成功了。
        assert response.status_code == 422, response.text

    @pytest.mark.asyncio
    async def test_update_fields_invalidates_public_cache(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        first = await client.get("/api/content-types")
        assert any(r["key"] == key and r["name"] == "书籍" for r in first.json())

        response = await client.put(
            f"/api/admin/content-types/{key}",
            json={"name": "图鉴"},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text

        second = await client.get("/api/content-types")
        assert any(r["key"] == key and r["name"] == "图鉴" for r in second.json())

    @pytest.mark.asyncio
    async def test_delete_blocked_while_referenced(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        await _create_post(client, admin_headers, post_type=key, meta_fields={"author": "某作者"})

        blocked = await client.delete(f"/api/admin/content-types/{key}", headers=admin_headers)
        assert blocked.status_code == 409, blocked.text
        assert "1 篇文章" in blocked.json()["message"]

    @pytest.mark.asyncio
    async def test_delete_unused(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        response = await client.delete(f"/api/admin/content-types/{key}", headers=admin_headers)
        assert response.status_code == 200, response.text

        public = await client.get("/api/content-types")
        assert all(r["key"] != key for r in public.json())

    @pytest.mark.asyncio
    async def test_fields_require_select_options(self, client, admin_headers):
        response = await client.post(
            "/api/admin/content-types",
            json={
                "key": _key(),
                "name": "坏定义",
                "fields": [{"key": "fmt", "label": "装帧", "field_type": "select"}],
            },
            headers=admin_headers,
        )
        assert response.status_code == 422, response.text


class TestPostMetaValidation:
    @pytest.mark.asyncio
    async def test_unknown_post_type_is_422(self, client, admin_headers):
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": {"zh": "未知类型"},
                "content": {"zh": "正文"},
                "slug": _slug(),
                "status": "draft",
                "post_type": "no_such_type",
            },
            headers=admin_headers,
        )
        assert response.status_code == 422, response.text
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert "未定义的内容类型" in body["message"]

    @pytest.mark.asyncio
    async def test_builtin_post_rejects_meta_fields(self, client, admin_headers):
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": {"zh": "标准文章"},
                "content": {"zh": "正文"},
                "slug": _slug(),
                "status": "draft",
                "meta_fields": {"anything": 1},
            },
            headers=admin_headers,
        )
        assert response.status_code == 422, response.text
        assert "不接受自定义字段" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_required_missing(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": {"zh": "缺必填"},
                "content": {"zh": "正文"},
                "slug": _slug(),
                "status": "draft",
                "post_type": key,
                "meta_fields": {"pages": 100},
            },
            headers=admin_headers,
        )
        assert response.status_code == 422, response.text
        assert "「作者」是必填字段" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_unknown_meta_key(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": {"zh": "未知字段"},
                "content": {"zh": "正文"},
                "slug": _slug(),
                "status": "draft",
                "post_type": key,
                "meta_fields": {"author": "某人", "junk": "x"},
            },
            headers=admin_headers,
        )
        assert response.status_code == 422, response.text
        assert "junk" in response.json()["message"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "meta",
        [
            {"author": "某人", "pages": "not-a-number"},
            {"author": "某人", "finished": "maybe"},
            {"author": "某人", "format": "线装"},
            {"author": "某人", "published_on": "2026-13-01"},
            {"author": "某人", "read_at": "昨天"},
            {"author": "某人", "cover": "javascript:alert(1)"},
            {"author": "某人", "detail_link": "ftp://x/y"},
        ],
    )
    async def test_field_type_mismatch(self, client, admin_headers, meta):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": {"zh": "类型不符"},
                "content": {"zh": "正文"},
                "slug": _slug(),
                "status": "draft",
                "post_type": key,
                "meta_fields": meta,
            },
            headers=admin_headers,
        )
        assert response.status_code == 422, response.text


class TestRoundtrip:
    @pytest.mark.asyncio
    async def test_create_detail_and_edit_share_the_values(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        slug = _slug()
        meta = {
            "author": "  高德纳  ",
            "pages": "352",
            "finished": "false",
            "format": "精装",
            "published_on": "2026-01-02",
            "read_at": "2026-02-03T04:05:06",
            "cover": "/media/covers/book.png",
            "detail_link": "https://example.com/book",
            "notes": "## 笔记\n- 第一行",
            "summary": "",
        }
        created = await _create_post(
            client, admin_headers, slug=slug, post_type=key, meta_fields=meta
        )
        assert created["post_type"] == key
        normalized = created["meta_fields"]
        assert normalized["author"] == "高德纳"  # text 去首尾空白
        assert normalized["pages"] == 352  # 数字串转 int
        assert normalized["finished"] is False  # 布尔串转 bool
        assert normalized["read_at"] == "2026-02-03T04:05:06+00:00"  # 朴素按 UTC
        assert "summary" not in normalized  # 空串视作没填，不落键

        detail = await client.get(f"/api/blog/posts/{slug}")
        assert detail.status_code == 200, detail.text
        detail_body = detail.json()
        assert detail_body["post_type"] == key
        assert detail_body["meta_fields"] == normalized

        edit = await client.get(f"/api/blog/posts/{created['id']}/edit", headers=admin_headers)
        assert edit.status_code == 200, edit.text
        edit_body = _payload(edit.json())
        assert edit_body["post_type"] == key
        assert edit_body["meta_fields"] == normalized

        by_id = await client.get(f"/api/blog/posts/id/{created['id']}")
        assert by_id.status_code == 200, by_id.text
        assert by_id.json()["meta_fields"] == normalized

    @pytest.mark.asyncio
    async def test_update_meta_only_keeps_type_and_merges(
        self, client, admin_headers, db_session: AsyncSession
    ):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        created = await _create_post(
            client,
            admin_headers,
            post_type=key,
            meta_fields={"author": "甲", "pages": 10},
        )

        response = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"meta_fields": {"author": "乙"}},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["post_type"] == key

        row = await db_session.get(Post, created["id"])
        await db_session.refresh(row)
        # 只提交的键参与校验；没提交的 pages 被保留（normalize 只重建已提交键）
        assert row.meta_fields == {"author": "乙"}

    @pytest.mark.asyncio
    async def test_title_only_update_does_not_revalidate_stored_meta(
        self, client, admin_headers, db_session: AsyncSession
    ):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        created = await _create_post(
            client, admin_headers, post_type=key, meta_fields={"author": "甲"}
        )

        # 定义后来收紧：新增一个必填字段。历史文章没有它，但也不该因此改不了标题。
        response = await client.put(
            f"/api/admin/content-types/{key}",
            json={
                "fields": [
                    {"key": "author", "label": "作者", "field_type": "text", "required": True},
                    {"key": "isbn", "label": "ISBN", "field_type": "text", "required": True},
                ]
            },
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text

        updated = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"title": {"zh": "只改标题"}},
            headers=admin_headers,
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["meta_fields"] == {"author": "甲"}

    @pytest.mark.asyncio
    async def test_switching_type_requires_new_required_fields(self, client, admin_headers):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        created = await _create_post(
            client, admin_headers, post_type=key, meta_fields={"author": "甲"}
        )

        response = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"post_type": key, "meta_fields": {}},
            headers=admin_headers,
        )
        # 显式给出空 meta_fields = 用户清空；必填校验照常生效
        assert response.status_code == 422
        assert "「作者」是必填字段" in response.json()["message"]

        # 切回内置 post（无自定义字段）应当成功，meta 一起清掉
        back = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"post_type": "post"},
            headers=admin_headers,
        )
        assert back.status_code == 200, back.text
        assert back.json()["post_type"] == "post"
        assert back.json()["meta_fields"] is None

    @pytest.mark.asyncio
    async def test_explicit_null_meta_fields_clears(self, client, admin_headers):
        key = _key()
        await _create_type(
            client,
            admin_headers,
            key=key,
            fields=[{"key": "author", "label": "作者", "field_type": "text"}],
        )
        created = await _create_post(
            client, admin_headers, post_type=key, meta_fields={"author": "甲"}
        )

        response = await client.put(
            f"/api/blog/posts/{created['id']}",
            json={"meta_fields": None},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["meta_fields"] is None
        assert response.json()["post_type"] == key

    @pytest.mark.asyncio
    async def test_dirty_stored_meta_is_tolerated_on_read(
        self, client, admin_headers, db_session: AsyncSession
    ):
        key = _key()
        await _create_type(client, admin_headers, key=key)
        created = await _create_post(
            client, admin_headers, post_type=key, meta_fields={"author": "甲"}
        )
        slug = created["slug"]

        row = await db_session.get(Post, created["id"])
        row.meta_fields = "这不是 dict"
        await db_session.commit()

        detail = await client.get(f"/api/blog/posts/{slug}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["meta_fields"] is None

        edit = await client.get(f"/api/blog/posts/{created['id']}/edit", headers=admin_headers)
        assert edit.status_code == 200, edit.text
        assert _payload(edit.json())["meta_fields"] is None


async def _seed_post(
    db_session: AsyncSession,
    author_id: int,
    *,
    slug: str,
    post_type: str = "post",
    published_at: datetime | None = None,
) -> Post:
    """直接落一条"已发布且已到期"的行，绕开写口的 i18n/校验噪声。

    `published_at` 默认用 Python 侧的 aware now（而不是 `func.now()`）：集合谓词
    `publicly_listable_posts()` 比较的是同一个时钟，SQLite 里两边都带 `+00:00`
    后缀、字符串比较才成立。留 NULL 同样可见，但那样就测不到"到点"这一半。
    """
    post = Post(
        title={"zh": slug, "en": slug},
        content={"zh": "正文", "en": "content"},
        slug=slug,
        author_id=author_id,
        status="published",
        post_type=post_type,
        published_at=published_at if published_at is not None else datetime.now(UTC),
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _list_slugs(client: AsyncClient, **params: object) -> dict[str, str]:
    """匿名列表口 → {slug: post_type}，顺带钉住"列表项必须带出类型"这一段。"""
    response = await client.get("/api/blog/posts", params={"lang": "zh", **params})
    assert response.status_code == 200, response.text
    items = _payload(response.json())["items"]
    return {item["slug"]: item["post_type"] for item in items}


class TestListVisibility:
    """自定义类型文章的**列表可见性**：默认列全部类型，`?post_type=` 只做显式收窄。

    接完四段之后剩下的缺陷形态是"详情页漂亮、列表里查无此文"：列表口曾把缺省写成
    `post_type == "post"`，而全站没有任何列表消费方传过这个参数——编辑器一旦把文章
    存成自定义类型，它就同时从前台列表、首页、作者页和后台文章列表消失，且没有任何
    入口能找回来（详情口、RSS、sitemap 却都不看类型，于是同一篇文章"订阅得到、点得进，
    却在任何列表里不存在"）。
    """

    @pytest.mark.asyncio
    async def test_default_list_includes_every_type(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ):
        key = _key()
        builtin = _slug()
        custom = _slug()
        await _seed_post(db_session, test_user.id, slug=builtin)
        await _seed_post(db_session, test_user.id, slug=custom, post_type=key)

        rows = await _list_slugs(client)
        assert rows[builtin] == "post"
        # 缺省不再只列内置类型：自定义类型文章必须出现在同一份列表里，
        # 且列表项要带出真实 post_type（管理员看到混排时得能分辨）。
        assert rows[custom] == key

    @pytest.mark.asyncio
    async def test_explicit_type_narrows_the_list(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ):
        key = _key()
        builtin = _slug()
        custom = _slug()
        await _seed_post(db_session, test_user.id, slug=builtin)
        await _seed_post(db_session, test_user.id, slug=custom, post_type=key)

        only_post = await _list_slugs(client, post_type="post")
        assert builtin in only_post
        assert custom not in only_post

        only_custom = await _list_slugs(client, post_type=key)
        assert list(only_custom) == [custom]

    @pytest.mark.asyncio
    async def test_admin_list_includes_every_type(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers, test_user
    ):
        """后台文章列表走同一条口（`?status=all`）：管理员也必须看得到自定义类型稿，
        否则"改完类型稿子就找不到"在后台同样无解。"""
        key = _key()
        custom = _slug()
        await _seed_post(db_session, test_user.id, slug=custom, post_type=key)

        response = await client.get(
            "/api/blog/posts",
            params={"lang": "zh", "status": "all"},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        items = _payload(response.json())["items"]
        row = next(item for item in items if item["slug"] == custom)
        assert row["post_type"] == key

    @pytest.mark.asyncio
    async def test_cache_key_isolates_every_type_view(self):
        """默认列表必须占**自己的**键位：`?post_type=` 的每一种取值（含查不到东西的垃圾值）
        都自成一条键，否则匿名访客能用一发垃圾值把空列表写进全站首页/列表页共用的键位，
        在整个 TTL 内对访客投毒（旧缺陷是 post_type 进 SQL 却不进键）。

        缺省段还要是"全部类型"而不是某个类型 key：写成 `pt{post_type or 'post'}` 时
        "不传参数"与"`?post_type=post`"命中同一个键，而后者是显式收窄的结果集——
        它先落进缓存，前者就在整个 TTL 内少掉全部自定义类型文章。
        """
        base = {
            "language": "zh",
            "page": 1,
            "page_size": 12,
            "category": None,
            "tag": None,
            "search": None,
            "status_filter": None,
            "author": None,
        }
        default_key = await _get_post_list_cache_key(**base)
        builtin_key = await _get_post_list_cache_key(**base, post_type="post")
        custom_key = await _get_post_list_cache_key(**base, post_type="book_x")
        ghost_key = await _get_post_list_cache_key(**base, post_type="__ghost__")
        keys = {default_key, builtin_key, custom_key, ghost_key}
        assert len(keys) == 4, "四种视图必须占四条键位"
        assert default_key.endswith("ptall")

    @pytest.mark.asyncio
    async def test_author_archive_includes_every_type(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ):
        """作者归档页读的就是这条口（`?author=`），它也不能只认内置类型。"""
        key = _key()
        custom = _slug()
        await _seed_post(db_session, test_user.id, slug=custom, post_type=key)

        rows = await _list_slugs(client, author=test_user.username)
        assert rows.get(custom) == key

    @pytest.mark.asyncio
    async def test_author_with_only_custom_type_stays_in_sitemap(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ):
        """作者归档清单与子表 lastmod 用的那条分组查询也不能只看内置类型。

        `test_user` 在这个用例里**只**发过一篇自定义类型文章：他的 /authors/<u>
        有真实内容（列表口现在按全部类型供数据），却被旧的硬过滤整条漏出 sitemap，
        等于让爬虫永远找不到这个归档页；同一条查询还喂 taxonomies 子表的
        `<lastmod>`，漏掉时索引里那一行要么没有 lastmod、要么停在更早的文章上。
        """
        key = _key()
        await _seed_post(db_session, test_user.id, slug=_slug(), post_type=key)

        response = await client.get("/api/blog/sitemap-taxonomies.xml")
        assert response.status_code == 200, response.text
        assert f"/authors/{test_user.username}" in response.text

        lastmod = await _sitemap_taxonomy_lastmod(db_session)
        assert lastmod is not None, "站点只有自定义类型文章时 taxonomies 子表不该没有 lastmod"

    @pytest.mark.asyncio
    async def test_ghost_type_cannot_empty_the_default_list(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ):
        """先打一发不存在的类型（结果为空页，且这条空页被写进缓存），再打默认列表。

        默认列表必须照常有条目——判别位进了键位才是这样。
        """
        custom = _slug()
        await _seed_post(db_session, test_user.id, slug=custom, post_type=_key())

        poison = await client.get(
            "/api/blog/posts", params={"lang": "zh", "post_type": "__ghost__"}
        )
        assert poison.status_code == 200, poison.text
        assert _payload(poison.json())["items"] == [], "前置条件：不存在的类型确实查出空页"

        assert custom in await _list_slugs(client)

    @pytest.mark.asyncio
    async def test_author_added_after_custom_type_published_is_listed(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ):
        """反面证据：sitemap 的那条分组查询一旦被改回只看内置类型，这条必须红。

        上面那条用例让作者只发过自定义稿，只测到"作者条目在不在清单里"；这里让作者
        **先**有一篇内置旧稿（分组查询照旧命中他，清单断言恒真），随后才发出新稿——
        子表 `<lastmod>` 取的是这条分组查询的 `max(published_at)`，带旧过滤时它停在
        两天前的内置稿上，而不是新稿。时间差刻意拉到 2 天：`_iso8601` 只到秒，
        同一秒内发的两篇会给出相同的 lastmod（假通过 / 假失败都可能）。
        """
        key = _key()
        await _seed_post(
            db_session,
            test_user.id,
            slug=_slug(),
            published_at=datetime.now(UTC) - timedelta(days=2),
        )
        custom = await _seed_post(db_session, test_user.id, slug=_slug(), post_type=key)

        response = await client.get("/api/blog/sitemap-taxonomies.xml")
        assert f"/authors/{test_user.username}" in response.text

        lastmod = await _sitemap_taxonomy_lastmod(db_session)
        assert lastmod == _iso8601(custom.published_at), (
            "taxonomies 子表 lastmod 没跟上自定义类型稿的发布时间——那条分组查询又在只看内置类型"
        )
