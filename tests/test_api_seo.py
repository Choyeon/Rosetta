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
    """后台写的 `SEO_ROBOTS` 全文必须真的出现在 robots.txt 里。

    历史缺陷有两层，都要守：
    1. 读取键写成未声明的 `ROBOTS_TXT` → 配置项写了却永远不生效（后台显示已保存）；
    2. 缓存键写成裸 `robots_txt` → `PUT /seo/config` 清的是 `seo:*` 模式，
       改完还要等 1 小时 TTL 才对爬虫生效。这里刻意不预先清缓存，让第 2 条也过闸门。
    """
    marker = "# rosetta-robots-marker"
    put = await client.put(
        "/api/seo/config",
        json={"SEO_ROBOTS": f"User-agent: *\n{marker}\nDisallow: /admin/"},
        headers=staff_headers,
    )
    assert put.status_code == 200, put.text

    r = await client.get("/api/seo/robots.txt")
    assert r.status_code == 200
    assert marker in r.text, "SEO_ROBOTS 没生效（读错键，或缓存键不在 seo:* 清理范围内）"


@pytest.mark.asyncio
async def test_default_robots_txt_has_spaced_disallow_and_locale_admin(
    client: AsyncClient, staff_headers: dict
):
    """缺省 robots.txt：`Disallow: ` 带空格，且后台四语前缀一个都不能少。

    `/login` `/register` `/account` `/search` `/oobe` 不在名单里——它们自带
    `noindex, follow`，被 Disallow 挡住抓取反而读不到那行 meta。
    """
    import backend.core.cache as _c

    # 清空自定义全文（上一例写过 SEO_ROBOTS；站点配置是共享表，不留空就会读到它）
    await client.put("/api/seo/config", json={"SEO_ROBOTS": ""}, headers=staff_headers)
    await _c.cache.delete_pattern("seo:robots_txt")
    r = await client.get("/api/seo/robots.txt")
    assert r.status_code == 200
    text = r.text

    for prefix in ("", "/en", "/ja", "/zh_Hant"):
        assert f"Disallow: {prefix}/admin/" in text, f"缺 Disallow: {prefix}/admin/\n{text}"
    assert "Disallow: /api/" in text
    assert text.count("Disallow: /api/") == 1, "/api/ 重复提交（模板与交叉积各写了一份）"
    for moved in ("/login", "/register", "/account", "/search", "/oobe"):
        assert f"Disallow: {moved}" not in text, f"{moved} 应交给页面 noindex，而不是 Disallow"


@pytest.mark.asyncio
async def test_robots_cache_key_roundtrip(client: AsyncClient):
    """robots 的读键与写键必须是同一个 namespaced 键。

    写成裸 `robots_txt` 的历史形态有两处坏：这条缓存永远不会被下一次请求读到
    （读的是 `seo:robots_txt`，等于每次请求重算），而那个裸键又不落在 `seo:*`
    清理模式里，`PUT /seo/config` 永远删不掉它。
    """
    import backend.core.cache as _c
    from backend.core.cache import make_cache_key

    namespaced = make_cache_key("seo", "robots_txt")
    await _c.cache.delete_pattern("seo:*")
    await _c.cache.delete("robots_txt")

    r = await client.get("/api/seo/robots.txt")
    assert r.status_code == 200
    assert await _c.cache.get(namespaced), "响应生成了内容却没写进读的那把键（缓存永不命中）"
    assert (await _c.cache.get("robots_txt")) is None, "写了裸键 robots_txt，seo:* 清理模式覆盖不到"


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


@pytest.mark.asyncio
async def test_meta_descriptions_strip_shortcodes_and_html(client: AsyncClient, db_session):
    """公开元数据（JSON-LD / Open Graph）不得泄漏短代码字面量或 HTML 标签。"""
    author = User(
        username="seo_meta_author",
        email="seo_meta_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()

    post = Post(
        title={"zh": "元数据测试文章标题"},
        slug="meta-strip-post",
        status="published",
        content="正文内容",
        excerpt={
            "zh": '看图 <p>[gallery ids="1,2"]</p> 这是纯文本摘要',
        },
        author_id=author.id,
    )
    db_session.add(post)
    await db_session.commit()

    r1 = await client.get(f"/api/seo/schema/article/{post.id}")
    assert r1.status_code == 200
    desc1 = r1.json()["description"]
    assert "[" not in desc1 and "<" not in desc1
    assert "这是纯文本摘要" in desc1

    r2 = await client.get(f"/api/seo/open-graph/article/{post.id}")
    assert r2.status_code == 200
    desc2 = r2.json()["og:description"]
    assert "[" not in desc2 and "<" not in desc2
    assert "这是纯文本摘要" in desc2


@pytest.mark.asyncio
async def test_sitemap_children_have_no_duplicate_loc(client: AsyncClient):
    """三份子 sitemap 合并后不得出现重复 `<loc>`，且语言变体必须各自成条。

    历史缺陷一：`/categories` `/tags` `/series` 同时写在固定路由表和分类学表里，
    索引对同一 URL 提交两次，Search Console 报"重复网址"。这里按 URL 集合守，
    任何人再往 `_STATIC_SITEMAP_ROUTES` 塞分类学根路径都会立刻红。

    历史缺陷二（prefix_except_default 之后）：`<url>` 只提交默认语言那条，
    英/日/繁仅作为 `<xhtml:link>` 的 alternate 出现。Google 要求带 hreflang 标注的
    **每个** URL 都在 sitemap 里，只写 alternate 时语言变体只剩"页面内的 hreflang"
    这一个发现入口——没有内链指向它的那些变体连被发现都谈不上。
    """
    import re
    from collections import Counter
    from urllib.parse import urlsplit

    import backend.core.cache as _c
    import backend.core.cache_v2 as _cv2

    await _c.cache.clear()
    try:
        await _cv2.cache.clear()
    except Exception:
        pass

    children = [
        "/api/blog/sitemap-pages.xml",
        "/api/blog/sitemap-posts.xml",
        "/api/blog/sitemap-taxonomies.xml",
    ]
    locs: list[str] = []
    bodies: list[str] = []
    for path in children:
        r = await client.get(path)
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith("application/xml"), path
        locs.extend(re.findall(r"<loc>(.*?)</loc>", r.text))
        bodies.append(r.text)

    assert locs, "三份子 sitemap 全空，断言会变成假通过"
    dupes = [url for url, n in Counter(locs).items() if n > 1]
    assert not dupes, f"重复提交的 sitemap URL: {dupes}"

    def strip_locale_prefix(path: str) -> str:
        for code in ("en", "ja", "zh_Hant"):
            if path == f"/{code}":
                return "/"
            if path.startswith(f"/{code}/"):
                return path[len(f"/{code}") :]
        return path

    # 三个根路径必须每种语言各提交一次（由分类学表负责，哪怕站点还没有任何分类）
    for root in ("/categories", "/tags", "/series"):
        hits = [u for u in locs if urlsplit(u).path.endswith(root)]
        paths = {urlsplit(u).path for u in hits}
        assert len(hits) == 4, f"{root} 应提交 4 个语言变体，实际 {len(hits)} 次: {hits}"
        # zh 裸路径 + 三语前缀，一个都不能缺，也不许混进别的页面
        assert paths == {
            root,
            f"/en{root}",
            f"/ja{root}",
            f"/zh_Hant{root}",
        }, f"{root} 的语言变体不齐：{paths}"

    # 每条 `<url>` 都要带完整 alternates（4 语 + x-default）；只给默认语言那条挂
    # alternate 等于其它三语没有自指声明。
    for body in bodies:
        for block in re.findall(r"<url>(.*?)</url>", body, re.S):
            if "xhtml:link" not in block:
                continue
            assert block.count('hreflang="x-default"') == 1, block
            for hl in ("zh-CN", "en", "ja", "zh-Hant"):
                assert f'hreflang="{hl}"' in block, f"条目缺 {hl} alternate: {block}"

    # noindex / 后台路由永不收录：先剥语言前缀，否则 /en/admin 会从这条闸门漏出去
    banned_prefixes = ("/admin", "/login", "/register", "/oobe", "/search")
    for url in locs:
        path = strip_locale_prefix(urlsplit(url).path)
        assert not any(
            path == prefix or path.startswith(f"{prefix}/") for prefix in banned_prefixes
        ), f"{url} 不应出现在 sitemap"
