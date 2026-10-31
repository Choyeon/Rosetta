"""
分类 / 标签订阅源（批次 #131）：`GET /api/blog/rss?category=<slug>` / `?tag=<slug>`。

钉住五件事：
① 收窄是真的进了 SQL（不是只在频道标题上做样子）；
② 频道 title / link / atom:self 跟着该范围走——三份都指回全站，阅读器会把分类源
   判成全站源的副本去重，订阅者以为在跟分类实际收到的是最新文章；
③ 可见性判据与全站 feed 同源（草稿 / 私密 / 定时未到不得出现）；
④ category / tag 进了缓存键（漏了的那一半＝分类 feed 与全站 feed 互相串味）；
⑤ 查无此 slug 回 200 空 feed 且**不写缓存**（slug 是调用方自备的任意串，
   缓存它等于给匿名请求开一个无界键空间）。
"""

import re
from datetime import datetime

import pytest
from httpx import AsyncClient

from backend.core.auth import get_password_hash
from backend.models.blog import Category, Post, Tag
from backend.models.user import User


async def _clear_feeds() -> None:
    """RSS 载荷缓存在 core.cache 与 core.cache_v2 两层，测试要一起清（否则上一轮的键位会串到下一轮）。"""
    import backend.core.cache as _c

    await _c.cache.clear()
    try:
        import backend.core.cache_v2 as _cv2

        await _cv2.cache.clear()
    except Exception:
        pass


@pytest.fixture
async def rss_env(db_session):
    """作者 + 两个分类（A/B）+ 两个标签（x/y）+ 四篇文章。

    A 类一篇（同时带标签 x）、B 类一篇、A 类草稿一篇、B 类带标签 x 一篇。
    """
    author = User(
        username="rss131_author",
        email="rss131_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()

    cat_a = Category(name={"zh": "甲分类", "en": "Alpha"}, slug="rss131-cat-a")
    cat_b = Category(name={"zh": "乙分类", "en": "Beta"}, slug="rss131-cat-b")
    db_session.add_all([cat_a, cat_b])
    await db_session.flush()

    tag_x = Tag(name={"zh": "标签X", "en": "TagX"}, slug="rss131-tag-x")
    tag_y = Tag(name={"zh": "标签Y", "en": "TagY"}, slug="rss131-tag-y")
    db_session.add_all([tag_x, tag_y])
    await db_session.flush()

    def _post(
        slug: str, title: str, category: Category, tags: list[Tag], status: str = "published"
    ):
        return Post(
            title={"zh": title},
            slug=slug,
            status=status,
            content={"zh": f"<p>{title}正文</p>"},
            excerpt={"zh": f"{title}摘要"},
            author_id=author.id,
            category_id=category.id,
            tags=tags,
            published_at=datetime(2020, 1, 1),
        )

    db_session.add_all(
        [
            _post("rss131-p-a-x", "甲X", cat_a, [tag_x]),
            _post("rss131-p-b", "乙", cat_b, [tag_y]),
            _post("rss131-p-a-draft", "甲草稿", cat_a, [], status="draft"),
            _post("rss131-p-b-x", "乙X", cat_b, [tag_x]),
        ]
    )
    await db_session.commit()
    await _clear_feeds()
    yield {
        "cat_a": cat_a.slug,
        "cat_b": cat_b.slug,
        "tag_x": tag_x.slug,
        "tag_y": tag_y.slug,
    }


def _items(xml: str) -> list[str]:
    """feed 里每条 item 的 <link>（顺序即 SQL 顺序）。"""
    block = re.findall(r"<item>(.*?)</item>", xml, re.S)
    return [re.search(r"<link>(.*?)</link>", b, re.S).group(1) for b in block]


@pytest.mark.asyncio
async def test_category_feed_lists_only_that_category(client: AsyncClient, rss_env):
    await _clear_feeds()
    r = await client.get("/api/blog/rss", params={"category": rss_env["cat_a"]})
    assert r.status_code == 200
    links = _items(r.text)
    assert any("rss131-p-a-x" in link for link in links)
    assert not any("rss131-p-b" in link for link in links), "分类 feed 混进了别的分类"


@pytest.mark.asyncio
async def test_tag_feed_lists_only_that_tag(client: AsyncClient, rss_env):
    await _clear_feeds()
    r = await client.get("/api/blog/rss", params={"tag": rss_env["tag_x"]})
    assert r.status_code == 200
    links = _items(r.text)
    assert any("rss131-p-a-x" in link for link in links)
    assert any("rss131-p-b-x" in link for link in links)
    assert not any(link.endswith("rss131-p-b") for link in links)


@pytest.mark.asyncio
async def test_category_and_tag_intersect(client: AsyncClient, rss_env):
    await _clear_feeds()
    r = await client.get(
        "/api/blog/rss", params={"category": rss_env["cat_a"], "tag": rss_env["tag_x"]}
    )
    links = _items(r.text)
    assert [link for link in links if "rss131-p-a-x" in link]
    assert len(links) == 1, f"交集收窄没生效，拿到 {len(links)} 条"


@pytest.mark.asyncio
async def test_taxonomy_feed_channel_points_at_its_scope(client: AsyncClient, rss_env):
    """频道三件套（title / link / atom:self）都必须是"这一类"，不是全站。"""
    await _clear_feeds()
    r = await client.get("/api/blog/rss", params={"category": rss_env["cat_a"], "lang": "zh"})
    xml = r.text
    title = re.search(r"<title>(.*?)</title>", xml, re.S).group(1)
    assert "甲分类" in title, f"频道标题没带分类名：{title}"
    link = re.search(r"<link>(.*?)</link>", xml, re.S).group(1)
    assert link.endswith("/categories/rss131-cat-a"), f"频道 link 指回站点根：{link}"
    self_href = re.search(r'<atom:link href="([^"]+)"', xml).group(1)
    assert "category=rss131-cat-a" in self_href, f"self 链接没带收窄参数：{self_href}"
    assert "lang=zh" in self_href


@pytest.mark.asyncio
async def test_taxonomy_feed_hides_unvisible_posts(client: AsyncClient, rss_env):
    """草稿不得进分类 feed：判据与全站 feed 同源（publicly_listable_posts）。"""
    await _clear_feeds()
    r = await client.get("/api/blog/rss", params={"category": rss_env["cat_a"]})
    assert "rss131-p-a-draft" not in r.text


@pytest.mark.asyncio
async def test_full_feed_is_not_polluted_by_category_feed(client: AsyncClient, rss_env):
    """缓存键必须带 category：先请分类源、再请全站源，全站源仍要能看到别的分类。"""
    await _clear_feeds()
    await client.get("/api/blog/rss", params={"category": rss_env["cat_a"]})
    r_all = await client.get("/api/blog/rss")
    assert r_all.status_code == 200
    assert "rss131-p-b" in r_all.text, "全站 feed 命中了分类 feed 的缓存键位"
    assert "rss131-p-a-draft" not in r_all.text


@pytest.mark.asyncio
async def test_unknown_taxonomy_returns_empty_feed_and_is_not_cached(client: AsyncClient, rss_env):
    """查无此 slug：200 + 零条目 + 不写缓存（任意串不得换缓存条目）。"""
    await _clear_feeds()
    r = await client.get("/api/blog/rss", params={"category": "rss131-does-not-exist"})
    assert r.status_code == 200
    assert _items(r.text) == []
    assert "<channel>" in r.text, "空 feed 也必须是合法频道"

    from backend.core.cache import cache, make_cache_key

    key = make_cache_key("posts", "rss", "zh", "20", "rss131-does-not-exist", "-")
    assert await cache.get(key) in (None, ""), "不存在的 slug 被写进了缓存"


@pytest.mark.asyncio
async def test_blank_category_is_treated_as_full_feed(client: AsyncClient, rss_env):
    """`?category=` 空串＝没筛选：别让它生成一个与全站 feed 同内容、异键位的副本。"""
    await _clear_feeds()
    r = await client.get("/api/blog/rss", params={"category": "  ", "lang": "zh"})
    title = re.search(r"<title>(.*?)</title>", r.text, re.S).group(1)
    assert "·" not in title, f"空串被当成了一个分类：{title}"


@pytest.mark.asyncio
async def test_channel_description_is_localized(client: AsyncClient, rss_env):
    """频道 description 曾恒为中文「最新文章」，en/ja/zh_Hant 三种 feed 也跟着中文。"""
    await _clear_feeds()
    r_en = await client.get("/api/blog/rss", params={"lang": "en"})
    desc_en = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", r_en.text, re.S)
    assert desc_en and "Latest posts" in desc_en.group(1)

    r_zh = await client.get("/api/blog/rss", params={"lang": "zh"})
    desc_zh = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", r_zh.text, re.S)
    assert desc_zh and "最新文章" in desc_zh.group(1)


@pytest.mark.asyncio
async def test_non_ascii_taxonomy_slug_is_percent_encoded(client: AsyncClient, db_session):
    """中文 slug 在 <link> 里必须是百分号编码（RSS 阅读器按协议校验，原样中文会丢整条）。"""
    author = User(
        username="rss131_cjk_author",
        email="rss131_cjk@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(author)
    await db_session.flush()
    cjk = Category(name={"zh": "中文分类"}, slug="中文分类")
    db_session.add(cjk)
    await db_session.flush()
    db_session.add(
        Post(
            title={"zh": "CJK 分类文章"},
            slug="rss131-p-cjk",
            status="published",
            content={"zh": "<p>正文</p>"},
            author_id=author.id,
            category_id=cjk.id,
            published_at=datetime(2020, 1, 2),
        )
    )
    await db_session.commit()
    await _clear_feeds()

    r = await client.get("/api/blog/rss", params={"category": "中文分类", "lang": "zh"})
    assert r.status_code == 200
    channel_link = re.search(r"<link>(.*?)</link>", r.text, re.S).group(1)
    assert "中文" not in channel_link, f"频道 link 里有未编码的中文：{channel_link}"
    assert "%E4%B8%AD%E6%96%87" in channel_link
