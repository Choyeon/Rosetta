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


@pytest.mark.asyncio
async def test_pages_sitemap_submits_canonical_slug_not_legacy_alias(
    client: AsyncClient, db_session
):
    """独立页只提交规范地址 `/<slug>`，不再提交旧兼容口 `/page/<slug>`。

    历史缺陷：`generate_pages_sitemap` 一直输出 `/page/<slug>`，而那张壳页自己把
    canonical 指回顶级 catchall 的 `/<slug>`（`frontend/pages/page/[slug].vue` 写明
    `/page/<slug>` 只是旧 WordPress 链接的兼容口）。于是爬虫从 sitemap 拿到的"规范版"
    与页面 `<link rel=canonical>` 声明的"规范版"是两个不同地址——同一份内容被要求
    按两份互相矛盾的信号处理，Search Console 侧表现为"已提交但被规范到别的 URL"。

    撞名 slug（about / guestbook / gallery …）在顶级由内建页面承担，独立页记录只剩
    一个 canonical 指向别处的壳，没有可提交的规范地址，必须整条跳过——顺带保证
    `/about` 不会因为库里多一条同名 Page 而被提交两次。
    """
    import re
    from urllib.parse import urlsplit

    import backend.core.cache as _c
    import backend.core.cache_v2 as _cv2
    from backend.models.core import Page

    await _c.cache.clear()
    try:
        await _cv2.cache.clear()
    except Exception:
        pass

    db_session.add_all(
        [
            Page(
                title={"zh": "隐私政策"},
                slug="privacy-policy-probe",
                content={"zh": "<p>正文</p>"},
                status="published",
            ),
            Page(
                title={"zh": "关于壳"},
                slug="about",
                content={"zh": "<p>壳</p>"},
                status="published",
            ),
        ]
    )
    await db_session.commit()

    r = await client.get("/api/blog/sitemap-pages.xml")
    assert r.status_code == 200
    paths = [urlsplit(u).path for u in re.findall(r"<loc>(.*?)</loc>", r.text)]
    assert paths, "sitemap 为空，断言会变成假通过"

    aliases = [p for p in paths if p.startswith("/page/")]
    assert not aliases, f"兼容口不该进 sitemap（canonical 指向别处）：{aliases}"

    for expected in (
        "/privacy-policy-probe",
        "/en/privacy-policy-probe",
        "/ja/privacy-policy-probe",
        "/zh_Hant/privacy-policy-probe",
    ):
        assert paths.count(expected) == 1, f"独立页规范地址缺失或重复：{expected}"

    # 撞名 slug 的独立页记录被跳过 → /about 仍只由固定路由表提交，每种语言一次
    assert paths.count("/about") == 1
    assert paths.count("/en/about") == 1


@pytest.mark.asyncio
async def test_pages_sitemap_submits_sponsor_only_when_donate_is_live(
    client: AsyncClient, staff_headers
):
    """``/sponsor`` 只在捐助页真的可索引时才进 sitemap。

    前端 ``pages/sponsor.vue`` 的 ``sponsorEmpty``（``enable`` 关掉或 ``methods`` 为空）
    会给这一页输出 ``noindex, follow``。两处必须同口径：默认（donate 分组未保存）时
    不提交，配置齐全后补一条四语条目——否则"可索引的捐助页永远没有发现入口"，
    反过来把自我声明 noindex 的地址提交给爬虫等于两份互相矛盾的信号。
    """
    import re
    from urllib.parse import urlsplit

    import backend.core.cache as _c

    await _c.cache.clear()

    def _paths(text: str) -> list[str]:
        return [urlsplit(u).path for u in re.findall(r"<loc>(.*?)</loc>", text)]

    # ① 未配置 donate（read_group 回 {}）⇒ 与前端默认 methods: [] 一致，不提交
    r = await client.get("/api/blog/sitemap-pages.xml")
    assert r.status_code == 200
    assert "/sponsor" not in _paths(r.text), "空壳捐助页是 noindex，不该提交"

    # ② 有收款方式 ⇒ 四语各一条，且带 hreflang 集群
    resp = await client.patch(
        "/api/settings/donate",
        json={
            "enable": True,
            "methods": [{"name": "支付宝", "image": "/media/qr.png", "note": ""}],
        },
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    r2 = await client.get("/api/blog/sitemap-pages.xml")
    paths = _paths(r2.text)
    for expected in ("/sponsor", "/en/sponsor", "/ja/sponsor", "/zh_Hant/sponsor"):
        assert paths.count(expected) == 1, f"捐助页变体缺失或重复：{expected}"
    assert 'hreflang="en"' in r2.text

    # ③ 关掉开关（methods 仍在）⇒ 再次不提交：可索引性看 enable ∧ methods
    resp = await client.patch(
        "/api/settings/donate",
        json={"enable": False},
        headers=staff_headers,
    )
    assert resp.status_code == 200, resp.text
    r3 = await client.get("/api/blog/sitemap-pages.xml")
    assert "/sponsor" not in _paths(r3.text)


@pytest.mark.asyncio
async def test_sitemap_index_child_lastmod_is_max_updated(client: AsyncClient, db_session):
    """索引里每个子表的 <lastmod> = 该表节点的最大更新日期，不再恒等于今天。

    历史缺陷：三份子表一律写当日日期——没有内容变化时 lastmod 也在天天变，
    爬虫被迫每次全量重抓；而真正改过文章的 lastmod 反而不比"今天"新。
    """
    import re
    from datetime import datetime, timezone

    author = User(
        username="seo_lm_author",
        email="seo_lm_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()

    old = Post(
        title={"zh": "旧文章"},
        slug="lm-old-post",
        status="published",
        content="正文",
        author_id=author.id,
        published_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 2),
    )
    new = Post(
        title={"zh": "新文章"},
        slug="lm-new-post",
        status="published",
        content="正文",
        author_id=author.id,
        published_at=datetime(2025, 6, 1),
        updated_at=datetime(2025, 6, 15),
    )
    db_session.add_all([old, new])
    await db_session.commit()

    r = await client.get("/api/blog/sitemap.xml")
    assert r.status_code == 200

    blocks = re.findall(r"<sitemap>(.*?)</sitemap>", r.text, re.S)
    assert blocks, "索引必须列出子表"

    # posts 子表取两篇文章里最大的 updated_at（与节点级口径一致）
    posts_blocks = [b for b in blocks if "sitemap-posts.xml" in b]
    assert len(posts_blocks) == 1, "两篇文章应落在同一页 posts 子表"
    match = re.search(r"<lastmod>(.*?)</lastmod>", posts_blocks[0])
    assert match and match.group(1) == "2025-06-15T00:00:00+00:00"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for block in blocks:
        m = re.search(r"<lastmod>(.*?)</lastmod>", block)
        if m:
            # 不再是纯日期的"今天"，而是完整 ISO datetime
            assert "T" in m.group(1), m.group(1)
            assert m.group(1) != today

    # 本用例没有独立页面：pages 子表为空 → 省略 lastmod 节点
    pages_block = next(b for b in blocks if "sitemap-pages.xml" in b)
    assert "<lastmod>" not in pages_block


@pytest.mark.asyncio
async def test_rss_lastbuild_date_is_build_time(client: AsyncClient, db_session):
    """<lastBuildDate> 是本次构建时刻，恒 >= feed 内任何 pubDate。

    旧口径取"最新文章时间"：缓存 TTL 到点重建的 feed 里 lastBuildDate 纹丝不动，
    聚合器据此判断"没有新内容"，永远不重拉。
    """
    import re
    from datetime import datetime, timezone
    from email.utils import parsedate_to_datetime

    author = User(
        username="seo_rss_author",
        email="seo_rss_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()
    post = Post(
        title={"zh": "RSS 时间口径"},
        slug="rss-time-post",
        status="published",
        content={"zh": "<p>正文</p>"},
        excerpt={"zh": "摘要"},
        author_id=author.id,
        published_at=datetime(2020, 1, 1),
    )
    db_session.add(post)
    await db_session.commit()

    r = await client.get("/api/blog/rss", params={"lang": "zh"})
    assert r.status_code == 200

    match = re.search(r"<lastBuildDate>(.*?)</lastBuildDate>", r.text)
    assert match, "lastBuildDate 必须存在（构建时刻与文章清单无关）"
    last_build = parsedate_to_datetime(match.group(1))

    pub_dates = [parsedate_to_datetime(v) for v in re.findall(r"<pubDate>(.*?)</pubDate>", r.text)]
    assert pub_dates
    assert last_build >= max(pub_dates)
    # 旧口径会把 2020 年那篇的发布时间写成 lastBuildDate；新口径必须贴近此刻
    drift = abs(datetime.now(timezone.utc) - last_build).total_seconds()
    assert drift < 120, f"lastBuildDate 应为构建时刻，偏移 {drift}s"


@pytest.mark.asyncio
async def test_schema_urls_match_frontend_routes(client: AsyncClient, db_session):
    """JSON-LD / Open Graph 的 URL 必须与前端真实路由同形。

    前端路由是 /posts/{slug}（复数，zh 裸路径）与 /authors/{username}；
    旧实现输出 /post/{slug} 与 /users/{id}，爬虫按声明地址去抓会落进
    catchall/404。同时验证无封面时 image 回落站内默认 OG 图而非 picsum 外链。
    """
    import json

    from backend.core.config import settings as _settings

    author = User(
        username="seo_route_author",
        email="seo_route_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()
    post = Post(
        title={"zh": "路由核对文章"},
        slug="route-check-post",
        status="published",
        content="正文",
        excerpt={"zh": "摘要"},
        author_id=author.id,
    )
    db_session.add(post)
    await db_session.commit()

    base = getattr(_settings, "site_url", "http://localhost:4321")

    r1 = await client.get(f"/api/seo/schema/article/{post.id}")
    assert r1.status_code == 200
    schema = r1.json()
    text1 = json.dumps(schema, ensure_ascii=False)
    assert "/post/" not in text1, "不允许再出现单数 /post/ 段"
    assert "/users/" not in text1, "作者链接必须走 /authors/{username}"
    assert schema["url"] == f"{base}/posts/route-check-post"
    assert schema["mainEntityOfPage"]["@id"] == f"{base}/posts/route-check-post"
    assert schema["author"]["url"] == f"{base}/authors/seo_route_author"
    assert schema["image"].endswith("/og-default.png")
    assert "picsum" not in schema["image"]

    r2 = await client.get(f"/api/seo/open-graph/article/{post.id}")
    assert r2.status_code == 200
    og = r2.json()
    assert og["og:url"] == f"{base}/posts/route-check-post"
    assert og["og:image"].endswith("/og-default.png")
    assert og["twitter:image"].endswith("/og-default.png")
    assert og["article:author"] == f"{base}/authors/seo_route_author"

    r3 = await client.get(f"/api/seo/schema/person/{author.id}")
    assert r3.status_code == 200
    person = r3.json()
    assert person["url"] == f"{base}/authors/seo_route_author"


# ======================================================================
# 匿名 SEO 口的可见性闸门
#
# 这两条端点无需鉴权、按 id 取值，且没有任何地方核对"这篇文章对外是否存在"。
# 结果是：草稿 / 待审 / 未来定时文章的标题、摘要、slug、作者可以从 id=1 开始
# 逐个枚举出来，而 GET /posts/{slug} 对同一篇是 404——同一份内容两套可见性。
# 作者侧同理：public_profile=false 的主页对外是"不存在"，但 person schema 照样
# 吐 bio / github / website。
# ======================================================================


@pytest.mark.asyncio
async def test_seo_article_endpoints_hide_unpublished_posts(client: AsyncClient, db_session):
    """草稿与未来定时文章在 schema / open-graph 两个口都必须按"不存在"返回。"""
    from datetime import datetime, timedelta

    from backend.utils.compat import UTC

    author = User(
        username="seo_gate_author",
        email="seo_gate_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()

    draft = Post(
        title={"zh": "未发布草稿标题"},
        slug="seo-gate-draft",
        status="draft",
        content="草稿正文",
        excerpt={"zh": "未发布草稿摘要"},
        author_id=author.id,
    )
    scheduled = Post(
        title={"zh": "未来定时文章标题"},
        slug="seo-gate-scheduled",
        status="published",
        content="定时正文",
        excerpt={"zh": "未来定时摘要"},
        author_id=author.id,
        published_at=datetime.now(UTC) + timedelta(days=3),
    )
    live = Post(
        title={"zh": "已发布文章标题"},
        slug="seo-gate-live",
        status="published",
        content="正文",
        excerpt={"zh": "已发布摘要"},
        author_id=author.id,
        published_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add_all([draft, scheduled, live])
    await db_session.commit()

    for hidden in (draft, scheduled):
        schema = await client.get(f"/api/seo/schema/article/{hidden.id}")
        assert schema.status_code == 200
        assert set(schema.json()) == {"error"}, f"草稿/定时文章泄漏了 JSON-LD: {schema.json()}"

        og = await client.get(f"/api/seo/open-graph/article/{hidden.id}")
        assert og.status_code == 200
        assert set(og.json()) == {"error"}, f"草稿/定时文章泄漏了 Open Graph: {og.json()}"

    # 闸门不能把正常文章一起关掉：已发布且发布时间已过必须照常输出
    ok_schema = await client.get(f"/api/seo/schema/article/{live.id}")
    assert ok_schema.json()["headline"] == "已发布文章标题"
    ok_og = await client.get(f"/api/seo/open-graph/article/{live.id}")
    assert ok_og.json()["og:title"] == "已发布文章标题"


@pytest.mark.asyncio
async def test_seo_person_schema_respects_hidden_profile(client: AsyncClient, db_session):
    """public_profile=false 的账号在 person schema 里必须与"查无此人"同形。"""
    from backend.models.user import UserPreference

    hidden = User(
        username="seo_hidden_person",
        email="seo_hidden_person@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
        bio="不应外泄的简介",
        github="https://github.com/hidden-person",
    )
    visible = User(
        username="seo_visible_person",
        email="seo_visible_person@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
        bio="公开简介",
    )
    db_session.add_all([hidden, visible])
    await db_session.flush()
    db_session.add(UserPreference(user_id=hidden.id, public_profile=False))
    await db_session.commit()

    response = await client.get(f"/api/seo/schema/person/{hidden.id}")
    assert response.status_code == 200
    assert set(response.json()) == {"error"}, f"隐藏主页被绕过: {response.json()}"

    ok = await client.get(f"/api/seo/schema/person/{visible.id}")
    assert ok.status_code == 200
    assert ok.json()["@type"] == "Person"
    assert ok.json()["description"] == "公开简介"
