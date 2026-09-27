"""Admin 工具端点测试：Alembic 迁移状态 + 缓存状态/清退 + 检索字段体检与补全

覆盖 `backend/api/admin_tools.py`：
- GET  /api/admin/alembic/status   状态读取（关键：读取失败必须 500，不能谎报"已是最新"）
- POST /api/admin/alembic/upgrade  失败传播（不打真实 DB，只验证错误路径）
- GET  /api/admin/cache/status     统计形状
- POST /api/admin/cache/flush      按模式清退 + 未知模式 400
- 全部端点的 staff 权限门禁

覆盖 `backend/api/admin.py` 的检索字段工具：
- GET  /api/admin/tools/search-stats     缺 slug/摘要/标签计数与 recommendations 自洽
- POST /api/admin/tools/optimize-search  补 slug（查重重名后缀、中文转拼音）+ 逐语言摘要
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Post
from backend.models.user import User

# ==================== Alembic 状态 ====================


@pytest.mark.asyncio
async def test_alembic_status_shape(client: AsyncClient, staff_headers: dict):
    """状态响应字段齐全，且 is_latest 与 pending 列表自洽"""
    r = await client.get("/api/admin/alembic/status", headers=staff_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in ("current_version", "latest_version", "is_latest", "pending", "applied"):
        assert key in data, f"缺少字段 {key}: {data}"

    applied_versions = {row["version"] for row in data["applied"]}
    pending_versions = {row["version"] for row in data["pending"]}
    assert applied_versions.isdisjoint(pending_versions), "同一版本不可能既已应用又待应用"

    if data["latest_version"]:
        assert data["is_latest"] == (len(data["pending"]) == 0), (
            f"is_latest={data['is_latest']} 与 pending={data['pending']} 不一致"
        )


@pytest.mark.asyncio
async def test_alembic_status_fails_loudly_when_collection_errors(
    client: AsyncClient, staff_headers: dict, monkeypatch
):
    """状态读取异常必须 500。

    旧实现返回 is_latest=True 的空壳 200：迁移页把"读不到状态"显示成"已是最新"，
    运维会据此跳过本该执行的升级。
    """

    def boom(_fn):
        raise RuntimeError("alembic 配置丢失")

    monkeypatch.setattr("backend.api.admin_tools._run_in_thread", boom)

    r = await client.get("/api/admin/alembic/status", headers=staff_headers)
    assert r.status_code == 500, f"读取失败被伪装成成功：{r.status_code} {r.text[:200]}"
    assert "无法读取迁移状态" in r.text


@pytest.mark.asyncio
async def test_alembic_upgrade_reports_failure(
    client: AsyncClient, staff_headers: dict, monkeypatch
):
    """upgrade 失败时 500，而不是 success=True。

    通过让 get_alembic_config 抛错来触发失败路径：不会真正碰到任何数据库。
    """

    def boom():
        raise RuntimeError("migration config unavailable")

    monkeypatch.setattr("backend.migrations.config.get_alembic_config", boom)

    r = await client.post("/api/admin/alembic/upgrade", headers=staff_headers)
    assert r.status_code == 500, r.text
    assert "alembic upgrade head 执行失败" in r.text


# ==================== 缓存 ====================


@pytest.mark.asyncio
async def test_cache_status_shape(client: AsyncClient, staff_headers: dict):
    r = await client.get("/api/admin/cache/status", headers=staff_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["backend"] in ("memory", "redis")
    assert isinstance(data["keys"], int)


@pytest.mark.asyncio
async def test_cache_flush_accepts_known_mode(client: AsyncClient, staff_headers: dict):
    r = await client.post(
        "/api/admin/cache/flush", headers=staff_headers, json={"mode": "post_list"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mode"] == "post_list"
    assert data["deleted_keys"] >= 0


@pytest.mark.asyncio
async def test_cache_flush_rejects_unknown_mode(client: AsyncClient, staff_headers: dict):
    """未登记的 mode 走 Pydantic Literal 校验 -> 422，不允许静默"什么都没清" """
    r = await client.post(
        "/api/admin/cache/flush", headers=staff_headers, json={"mode": "everything"}
    )
    assert r.status_code == 422, r.text


# ==================== 权限门禁 ====================


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/admin/alembic/status"),
        ("POST", "/api/admin/alembic/upgrade"),
        ("GET", "/api/admin/cache/status"),
        ("POST", "/api/admin/cache/flush"),
        ("GET", "/api/admin/tools/search-stats"),
        ("POST", "/api/admin/tools/optimize-search"),
    ],
)
@pytest.mark.asyncio
async def test_admin_tools_require_auth(client: AsyncClient, method: str, path: str):
    r = await client.request(method, path, json={})
    assert r.status_code in (401, 403), f"{method} {path} 未鉴权却返回 {r.status_code}"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/admin/alembic/status"),
        ("POST", "/api/admin/alembic/upgrade"),
        ("GET", "/api/admin/cache/status"),
        ("POST", "/api/admin/cache/flush"),
        ("GET", "/api/admin/tools/search-stats"),
        ("POST", "/api/admin/tools/optimize-search"),
    ],
)
@pytest.mark.asyncio
async def test_admin_tools_reject_non_staff(
    client: AsyncClient, subscriber_headers: dict, method: str, path: str
):
    r = await client.request(method, path, json={})
    assert r.status_code in (401, 403), f"{method} {path} 普通用户却返回 {r.status_code}"


# ==================== 检索字段体检 / 补全 ====================


async def _seed_post(
    db_session: AsyncSession,
    author: User,
    category: Category,
    *,
    slug: str,
    title: dict[str, str],
    content: dict[str, str],
    excerpt: dict[str, str] | None,
) -> Post:
    post = Post(
        title=title,
        slug=slug,
        content=content,
        excerpt=excerpt,
        author_id=author.id,
        category_id=category.id,
        status="published",
        allow_comments=True,
    )
    db_session.add(post)
    await db_session.commit()
    return post


async def _reload(db_session: AsyncSession, post_id: int) -> Post:
    # 接口用的是另一个 Session，先过期掉本地身份缓存再回读
    db_session.expire_all()
    return await db_session.scalar(select(Post).where(Post.id == post_id))


@pytest.mark.asyncio
async def test_search_stats_counts_and_recommendations_agree(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
):
    """体检计数字段齐全，且 recommendations 里的数字与顶层计数同源。"""
    await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="no-excerpt",
        title={"zh": "缺摘要", "en": "No excerpt"},
        content={"zh": "内容", "en": "Body"},
        excerpt=None,
    )
    await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="",
        title={"zh": "缺 slug", "en": "No slug"},
        content={"zh": "内容", "en": "Body"},
        excerpt={"zh": "有摘要", "en": "Has excerpt"},
    )

    r = await client.get("/api/admin/tools/search-stats", headers=staff_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in (
        "total_posts",
        "total_categories",
        "posts_without_excerpt",
        "posts_without_slug",
        "posts_without_tags",
        "avg_slug_length",
        "avg_excerpt_length",
        "recommendations",
    ):
        assert key in data, f"缺少字段 {key}: {data}"

    assert data["posts_without_excerpt"] >= 1
    assert data["posts_without_slug"] >= 1
    by_type = {item["type"]: item["count"] for item in data["recommendations"]}
    # recommendations 只列 count>0 的缺口，所以用 get 比对（缺项即 0）
    for key in ("excerpt", "slug", "tags"):
        assert by_type.get(key, 0) == data[f"posts_without_{key}"]

    assert all(item["count"] > 0 for item in data["recommendations"]), (
        f"零缺口不该出现在建议列表里：{data['recommendations']}"
    )


@pytest.mark.asyncio
async def test_optimize_search_writes_excerpt_per_language(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
):
    """摘要按各自语言的正文生成。

    旧实现只取 zh（其次 en）正文，然后把同一段文字同时写进 zh 和 en——
    等于给英文读者一条中文"译文"。
    """
    post = await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="multi-lang-body",
        title={"zh": "多语正文", "en": "Multi lang"},
        content={
            "zh": "# 中文标题\n这里是中文正文内容。",
            "en": "## English heading\nEnglish body text here.",
        },
        excerpt=None,
    )

    r = await client.post("/api/admin/tools/optimize-search", headers=staff_headers)
    assert r.status_code == 200, r.text
    assert r.json()["excerpt_filled_count"] >= 1

    excerpt = (await _reload(db_session, post.id)).excerpt
    assert set(excerpt) == {"zh", "en"}, excerpt
    assert "这里是中文正文内容" in excerpt["zh"]
    assert "English body text" in excerpt["en"]
    assert excerpt["zh"] != excerpt["en"], "两种语言写入同一段文字"
    assert "#" not in excerpt["zh"] and "#" not in excerpt["en"], "Markdown 记号未剥离"


@pytest.mark.asyncio
async def test_optimize_search_avoids_existing_slug_collision(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
):
    """补 slug 必须查重。

    旧实现直接写死 `_slugify(title)`：与库里已有 slug 同名时，异常要等到请求
    结尾 commit 才抛，整个事务被回滚，接口却已经回了"已优化 1 篇"——
    实际什么都没写进去（这里是 500 或 slug 仍为空）。
    """
    await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="hello-world",
        title={"en": "Hello World"},
        content={"en": "Occupant"},
        excerpt={"en": "Taken"},
    )
    target = await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="",
        title={"en": "Hello World"},
        content={"en": "Body"},
        excerpt={"en": "Already there"},
    )

    r = await client.post("/api/admin/tools/optimize-search", headers=staff_headers)
    assert r.status_code == 200, r.text
    assert r.json()["slug_filled_count"] == 1

    fresh = await _reload(db_session, target.id)
    assert fresh.slug == "hello-world-2", f"未避开已有 slug：{fresh.slug!r}"


@pytest.mark.asyncio
async def test_optimize_search_slug_is_ascii_for_chinese_title(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
):
    """中文标题要转拼音，且兜底名不能是内存地址。

    旧实现自己写的 `_slugify` 用 `\\w`（Python 下匹配 CJK），中文原样进 URL；
    标题为空时兜底 `post-{id(text)}`——CPython 对象地址，跨进程不稳定，
    还会把内存布局泄漏进公开链接。
    """
    post = await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="",
        title={"zh": "测试中文标题"},
        content={"zh": "内容"},
        excerpt={"zh": "摘要"},
    )

    r = await client.post("/api/admin/tools/optimize-search", headers=staff_headers)
    assert r.status_code == 200, r.text

    fresh = await _reload(db_session, post.id)
    assert fresh.slug.isascii(), f"中文 slug 未转拼音：{fresh.slug!r}"
    assert fresh.slug == "ce-shi-zhong-wen-biao-ti"


@pytest.mark.asyncio
async def test_optimize_search_is_idempotent(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
):
    """第二次跑不该再改任何字段（也不该重复追加 -2/-3 后缀）。"""
    post = await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="",
        title={"en": "Idempotent Post"},
        content={"en": "Body text"},
        excerpt=None,
    )

    first = await client.post("/api/admin/tools/optimize-search", headers=staff_headers)
    assert first.status_code == 200, first.text
    slug_after_first = (await _reload(db_session, post.id)).slug
    assert slug_after_first == "idempotent-post"

    second = await client.post("/api/admin/tools/optimize-search", headers=staff_headers)
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["slug_filled_count"] == 0
    assert (await _reload(db_session, post.id)).slug == slug_after_first


@pytest.mark.asyncio
async def test_optimize_search_invalidates_post_caches(
    client: AsyncClient,
    staff_headers: dict,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
):
    """补完摘要/ slug 后必须清文章详情与列表缓存。

    详情键 `post:{slug}:{lang}` 不在 "posts" 前缀下，与单篇 update_post 一样要显式清；
    否则 TTL 内匿名访客仍读到"无摘要 / 旧 slug"的缓存正文（补字段等于白做）。
    """
    from backend.core.cache import cache, make_cache_key

    post = await _seed_post(
        db_session,
        test_user,
        test_category,
        slug="cached-body",
        title={"zh": "缓存正文", "en": "Cached"},
        content={"zh": "这里是中文正文内容。", "en": "Body text"},
        excerpt=None,
    )

    detail_key = make_cache_key("post", post.slug, "zh")
    list_key = make_cache_key("posts", "list", "zh")
    await cache.set(detail_key, {"stale": True}, ttl=600)
    await cache.set(list_key, {"stale": True}, ttl=600)
    assert await cache.get(detail_key) is not None
    assert await cache.get(list_key) is not None

    r = await client.post("/api/admin/tools/optimize-search", headers=staff_headers)
    assert r.status_code == 200, r.text
    assert r.json()["excerpt_filled_count"] >= 1

    assert await cache.get(detail_key) is None, "详情缓存未清：访客仍读旧正文"
    assert await cache.get(list_key) is None, "列表缓存未清"
