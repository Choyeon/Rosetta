"""
SEO API 测试

覆盖：config 读写、sitemap 缓存清理、sitemap-check、scores 评分、
robots.txt 生成、Open Graph、结构化数据。
"""

import pytest
from httpx import AsyncClient

from backend.core.auth import get_password_hash
from backend.models.blog import Post, Tag
from backend.models.user import User


def _unwrap(body: dict) -> dict:
    """兼容 {success, data} 包装与直接返回两种形式"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


@pytest.mark.asyncio
async def test_get_seo_config_returns_dict(client: AsyncClient):
    """获取 SEO 配置返回 dict（get_site_config_value 走全局 DB，不假设为空）"""
    import backend.core.cache as _c

    await _c.cache.clear()
    try:
        import backend.core.cache_v2 as _cv2

        await _cv2.cache.clear()
    except Exception:
        pass
    r = await client.get("/api/seo/config")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


@pytest.mark.asyncio
async def test_update_seo_config_requires_auth(client: AsyncClient):
    """未认证更新 SEO 配置 → 401"""
    r = await client.put("/api/seo/config", json={"SEO_TITLE": "test"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_update_seo_config_invalid_payload(client: AsyncClient, staff_headers: dict):
    """非 dict payload → 400"""
    r = await client.put("/api/seo/config", json="not-a-dict", headers=staff_headers)
    assert r.status_code == 422  # Pydantic 校验层拦截（dict 类型不匹配）


@pytest.mark.asyncio
async def test_update_and_get_seo_config(client: AsyncClient, staff_headers: dict):
    """更新后能读取到配置，且非法 key 被忽略"""
    payload = {
        "SEO_TITLE": "Rosetta Blog",
        "SEO_DESCRIPTION": "A test blog",
        "INVALID_KEY": "should-be-ignored",
    }
    r = await client.put("/api/seo/config", json=payload, headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert data["SEO_TITLE"] == "Rosetta Blog"
    assert data["SEO_DESCRIPTION"] == "A test blog"
    assert "INVALID_KEY" not in data

    # GET 能读到
    r2 = await client.get("/api/seo/config")
    assert r2.status_code == 200
    assert r2.json()["SEO_TITLE"] == "Rosetta Blog"


@pytest.mark.asyncio
async def test_generate_sitemap_cache(client: AsyncClient, staff_headers: dict):
    """清理 sitemap 缓存"""
    r = await client.post("/api/seo/sitemap/generate", headers=staff_headers)
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.asyncio
async def test_sitemap_check_no_posts(client: AsyncClient, staff_headers: dict):
    """无文章时 sitemap-check 返回 ok=True"""
    r = await client.get("/api/seo/sitemap-check", headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["ok"] is True
    assert body["data"]["url_count"] == 0


@pytest.mark.asyncio
async def test_sitemap_check_with_incomplete_post(
    client: AsyncClient, staff_headers: dict, db_session
):
    """缺少标题/摘要/封面的文章会被检出"""
    author = User(
        username="seo_author",
        email="seo_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()

    post = Post(
        title="",
        slug="empty-post",
        status="published",
        content="hello",
        author_id=author.id,
    )
    db_session.add(post)
    await db_session.commit()

    r = await client.get("/api/seo/sitemap-check", headers=staff_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["ok"] is False
    assert body["data"]["url_count"] == 1
    assert any("缺少标题" in e for e in body["data"]["errors"])
    assert any("缺少摘要" in e for e in body["data"]["errors"])
    assert any("缺少封面图" in e for e in body["data"]["errors"])


@pytest.mark.asyncio
async def test_seo_scores_no_posts(client: AsyncClient, staff_headers: dict):
    """无文章时 scores 返回空分页"""
    r = await client.get("/api/seo/scores", headers=staff_headers)
    assert r.status_code == 200
    body = _unwrap(r.json())
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_seo_scores_complete_post(client: AsyncClient, staff_headers: dict, db_session):
    """完整文章应得高分（标题长度合适、有摘要、封面、长正文、有标签）"""
    author = User(
        username="seo_author2",
        email="seo_author2@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()

    post = Post(
        title="这是一篇长度合适的测试文章标题",
        slug="complete-post",
        status="published",
        excerpt="文章摘要内容",
        cover_image="/uploads/cover.jpg",
        content="x" * 400,
        author_id=author.id,
    )
    tag = Tag(name="python", slug="python")
    post.tags.append(tag)
    db_session.add_all([post, tag])
    await db_session.commit()

    r = await client.get("/api/seo/scores", headers=staff_headers)
    assert r.status_code == 200
    body = _unwrap(r.json())
    assert body["total"] == 1
    item = body["items"][0]
    assert item["score"] >= 90
    assert item["suggestions"] == []


@pytest.mark.asyncio
async def test_seo_scores_short_title(client: AsyncClient, staff_headers: dict, db_session):
    """标题长度不合适会扣分并给出建议"""
    author = User(
        username="seo_author3",
        email="seo_author3@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()

    post = Post(
        title="短",
        slug="short-title",
        status="published",
        excerpt="有摘要",
        cover_image="/c.jpg",
        content="x" * 400,
        author_id=author.id,
    )
    db_session.add(post)
    await db_session.commit()

    r = await client.get("/api/seo/scores", headers=staff_headers)
    body = _unwrap(r.json())
    item = body["items"][0]
    assert item["score"] < 100
    assert any("标题长度" in s for s in item["suggestions"])


@pytest.mark.asyncio
async def test_get_robots_txt(client: AsyncClient):
    """robots.txt 返回 text/plain 且包含 Sitemap 行"""
    r = await client.get("/api/seo/robots.txt")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    text = r.text
    assert "User-agent" in text
    assert "Sitemap" in text


@pytest.mark.asyncio
async def test_get_robots_txt_with_config(client: AsyncClient, staff_headers: dict):
    """SEO_ROBOTS 配置会注入 robots.txt"""
    await client.put(
        "/api/seo/config",
        json={"SEO_ROBOTS": "Disallow: /admin/"},
        headers=staff_headers,
    )
    r = await client.get("/api/seo/robots.txt")
    assert r.status_code == 200
    assert "Disallow: /admin/" in r.text


@pytest.mark.asyncio
async def test_schema_unsupported_type(client: AsyncClient):
    """不支持的 resource_type 返回 error"""
    r = await client.get("/api/seo/schema/unknown/1")
    assert r.status_code == 200
    body = r.json()
    assert body.get("error") == "Unsupported resource type"


@pytest.mark.asyncio
async def test_schema_website(client: AsyncClient):
    """website 类型返回 WebSite 结构化数据"""
    r = await client.get("/api/seo/schema/website/1")
    assert r.status_code == 200
    body = r.json()
    assert body["@type"] == "WebSite"
    assert "name" in body
    assert "potentialAction" in body


@pytest.mark.asyncio
async def test_schema_breadcrumb(client: AsyncClient):
    """breadcrumb 类型返回 BreadcrumbList"""
    r = await client.get("/api/seo/schema/breadcrumb/1")
    assert r.status_code == 200
    body = r.json()
    assert body["@type"] == "BreadcrumbList"
    assert len(body["itemListElement"]) >= 1
