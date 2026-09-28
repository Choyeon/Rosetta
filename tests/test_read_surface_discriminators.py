"""读取面的"判别位"契约：缓存键、权限档位与计数口径必须与它服务的查询一致。

四条各自对应一类可复用的缺陷（都不是风格问题，而是能写出复现步骤的读取错误）：

1. **加密状态翻转必须清公开详情缓存。** `GET /blog/posts/{slug}` 的缓存命中发生在
   密码/状态判定**之前**（性能换来的次序），所以"先公开读过、管理员后加密码"这条路
   若不清键，访客在 TTL 内照读全文——密码门形同虚设。同口径见
   `core.cache.invalidate_post_detail_cache` 的说明。
2. **列表缓存键必须带齐查询侧真正用的过滤位。** `post_type` 曾进 SQL 却不进键，
   匿名访客可以用 `?post_type=<不存在的值>` 把空列表灌进首页/列表共用的键位，
   在 TTL 内对全站投毒。
3. **同一资源族的权限档位不得有孤立缺口。** 媒体库列表/统计/改/删全要 staff，
   唯独详情只要求登录，任意注册用户就能枚举别人的内部路径与上传者身份。
4. **同一数字在两个公开出口必须同源。** 分类详情的 `post_count` 曾数全部状态，
   而分类列表只数 published——侧栏与分类落地页对同一个分类报两个数，
   多出来的那部分是草稿。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.blog import _get_post_list_cache_key
from backend.core.cache import cache, make_cache_key
from backend.models.blog import Post


def _unwrap(body: dict):
    """成功信封 {success,data} 与裸分页响应并存，两种都读得到业务体。"""
    return body["data"] if isinstance(body, dict) and "data" in body else body


@pytest_asyncio.fixture
async def draft_in_category(db_session: AsyncSession, test_user, test_category) -> Post:
    """同一分类下的一篇草稿：用来验证公开计数不得把它算进去。"""
    draft = Post(
        title={"zh": "草稿文章", "en": "Draft Post"},
        slug="draft-in-category",
        content={"zh": "还没写完", "en": "unfinished"},
        excerpt={"zh": "草稿摘要", "en": "draft excerpt"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="draft",
        allow_comments=True,
    )
    db_session.add(draft)
    await db_session.commit()
    await db_session.refresh(draft)
    return draft


class TestEncryptEvictsPublicDetailCache:
    @pytest.mark.asyncio
    async def test_setting_a_password_drops_the_cached_plaintext(
        self, client: AsyncClient, test_post: Post, staff_headers: dict
    ):
        key = make_cache_key("post", test_post.slug, "zh")

        first = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert first.status_code == 200
        assert _unwrap(first.json())["content"], "前置条件：公开文章应返回全文"
        assert await cache.get(key) is not None, "前置条件：匿名公开读必须已写入详情缓存"

        encrypt = await client.post(
            f"/api/admin/posts/{test_post.id}/encrypt",
            json={"password": "correct horse", "content": "仅订阅者可见的正文"},
            headers=staff_headers,
        )
        assert encrypt.status_code == 200, encrypt.text
        assert await cache.get(key) is None, "加密码后旧明文缓存必须被清掉"

        # 清完再匿名读：要么明确"需要密码"，总之不得吐正文。
        again = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert again.status_code == 200
        body = _unwrap(again.json())
        assert body["is_password_protected"] is True
        assert not body["content"], "加密文章不得对无密码访客返回正文"

    @pytest.mark.asyncio
    async def test_removing_the_password_also_drops_the_stale_entry(
        self, client: AsyncClient, test_post: Post, staff_headers: dict
    ):
        """关闭加密同样要清键：否则缓存里那份"隐藏内容"的空壳会在 TTL 内继续糊住刚公开的正文。"""
        setup = await client.post(
            f"/api/admin/posts/{test_post.id}/encrypt",
            json={"password": "correct horse", "content": "仅订阅者可见的正文"},
            headers=staff_headers,
        )
        assert setup.status_code == 200, setup.text

        hidden = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert not _unwrap(hidden.json())["content"]

        disable = await client.delete(
            f"/api/admin/posts/{test_post.id}/encrypt", headers=staff_headers
        )
        assert disable.status_code == 200, disable.text

        visible = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert _unwrap(visible.json())["content"], "关闭加密后正文应立即恢复可见"


class TestPostTypeIsPartOfTheListCacheKey:
    @pytest.mark.asyncio
    async def test_key_builder_isolates_post_type(self):
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
        ghost_key = await _get_post_list_cache_key(**base, post_type="__ghost__")
        assert default_key != ghost_key

    @pytest.mark.asyncio
    async def test_unauthenticated_poisoning_attempt_cannot_empty_the_public_list(
        self, client: AsyncClient, test_post: Post
    ):
        """先打一发不存在的 post_type（结果为空页），再打默认列表：默认列表必须照常有条目。"""
        poison = await client.get(
            "/api/blog/posts", params={"lang": "zh", "post_type": "__ghost__"}
        )
        assert poison.status_code == 200
        assert _unwrap(poison.json())["items"] == [], "前置条件：不存在的类型确实查出空页"

        normal = await client.get("/api/blog/posts", params={"lang": "zh"})
        assert normal.status_code == 200
        items = _unwrap(normal.json())["items"]
        assert [item["slug"] for item in items] == [test_post.slug], (
            "空结果被写进了默认列表的缓存键位——缓存键漏了 post_type 判别位"
        )


class TestMediaDetailPermissionTier:
    @pytest.mark.asyncio
    async def test_requires_staff_like_its_siblings(
        self, client: AsyncClient, auth_headers: dict, staff_headers: dict
    ):
        anonymous = await client.get("/api/media/library/1")
        assert anonymous.status_code == 401

        regular_user = await client.get("/api/media/library/1", headers=auth_headers)
        assert regular_user.status_code == 403, (
            "普通注册用户不得读到媒体库详情（内部路径 + 上传者身份）"
        )

        # 依赖已过，只是没这条记录——用 404 证明"挡住的是权限而不是路由"。
        staff = await client.get("/api/media/library/999999", headers=staff_headers)
        assert staff.status_code == 404


class TestCategoryCountIsSameSourceEverywhere:
    @pytest.mark.asyncio
    async def test_detail_excludes_drafts_and_matches_the_list(
        self,
        client: AsyncClient,
        test_post: Post,
        test_category,
        draft_in_category: Post,
    ):
        detail = await client.get(f"/api/blog/categories/slug/{test_category.slug}")
        assert detail.status_code == 200
        count = _unwrap(detail.json())["post_count"]
        assert count == 1, f"公开详情把草稿数进去了：{count}"

        listed = await client.get("/api/blog/categories")
        assert listed.status_code == 200
        rows = _unwrap(listed.json())
        row = next(item for item in rows if item["slug"] == test_category.slug)
        assert row["post_count"] == count, "分类列表与分类详情对同一个分类报了两个数"
