"""归档出口的 the_title 契约（f8eb37bd 的行为级回归）

`/archive` · `/archive/{year}` · `/archive/{year}/{month}` 曾经直出 i18n dict 里的裸字符串，
而列表 / RSS / 详情页统一走 `render_title`。挂上标题类插件（hello-rosetta 追加 `· hello`）后，
同一篇文章在归档入口不带后缀、在列表带——插件对同一篇内容呈现两套标题。

本文件不依赖插件是否激活：直接在 hooks 总线上临时注册一个 `the_title` filter，
断言三个归档出口都把它应用到了每篇标题上，并同时钉住"渲染发生在写响应缓存之前"
（第二次调用取自缓存，仍必须是渲染后的口径；否则缓存里固化的就是旧钩子集）。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from backend.api import blog as blog_api
from backend.core.hooks import add_filter, remove_filter
from backend.models.blog import Post
from backend.models.user import User

# 用测试独有的年份/语言组合，避开与其它归档测试的缓存键相互污染。
TEST_YEAR = 2031
TEST_MONTH = 5
TEST_LANG = "ja"
MARK = "<<T>>"


def _request() -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/api/blog/archive",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
    }
    return Request(scope)


async def _mk_post(db: AsyncSession, author: User, slug: str) -> Post:
    post = Post(
        title={"zh": slug, "en": slug, "ja": slug},
        slug=slug,
        content={"zh": "内容", "en": "content", "ja": "内容"},
        author_id=author.id,
        status="published",
        published_at=datetime(TEST_YEAR, TEST_MONTH, 10, 12, 0),
    )
    db.add(post)
    await db.commit()
    return post


def _titles_of(payload) -> list[str]:
    """兼容 /archive(/{year}) 的分组数组与 /archive/{year}/{month} 的分页对象。"""
    groups = payload if isinstance(payload, list) else [payload]
    return [item["title"] for group in groups for item in group.get("posts", [])]


@pytest.mark.asyncio
async def test_archive_endpoints_apply_the_title_filter(
    db_session: AsyncSession, test_user: User
):
    """三个归档出口的标题都必须带上当前 the_title 链的渲染结果"""
    await _mk_post(db_session, test_user, f"arch-title-{TEST_YEAR}")

    async def suffix(title, **_kw):
        return f"{title} {MARK}" if isinstance(title, str) else title

    add_filter("the_title", suffix, priority=10, plugin="test-archive-title")
    try:
        monthly = await blog_api.get_archive(_request(), db_session, TEST_LANG, 50)
        yearly = await blog_api.get_archive_by_year(TEST_YEAR, _request(), db_session, TEST_LANG)
        monthly_one = await blog_api.get_archive_by_month(
            TEST_YEAR, TEST_MONTH, _request(), db_session, TEST_LANG, 1, 20
        )

        for name, payload in (
            ("/archive", monthly),
            (f"/archive/{TEST_YEAR}", yearly),
            (f"/archive/{TEST_YEAR}/{TEST_MONTH}", monthly_one),
        ):
            titles = _titles_of(payload)
            assert titles, f"{name} 没有取到测试文章"
            for title in titles:
                assert title.endswith(MARK), f"{name} 标题未经过 the_title 链：{title!r}"
    finally:
        remove_filter("the_title", suffix)


@pytest.mark.asyncio
async def test_archive_render_happens_before_cache_write(
    db_session: AsyncSession, test_user: User
):
    """渲染必须在写缓存之前：摘掉 filter 后第二次调用取自缓存，标题仍是渲染后的口径。

    如果闸门写在 `cache.set` 之后，第一次响应看起来正确，但缓存里存的是裸字符串，
    摘掉插件后 TTL 内访客仍会看到两套标题——正是这次要修的现象。
    """
    slug = f"arch-cached-{TEST_YEAR}"
    await _mk_post(db_session, test_user, slug)

    async def suffix(title, **_kw):
        return f"{title} {MARK}" if isinstance(title, str) else title

    add_filter("the_title", suffix, priority=10, plugin="test-archive-title")
    try:
        first = await blog_api.get_archive_by_year(TEST_YEAR, _request(), db_session, TEST_LANG)
    finally:
        remove_filter("the_title", suffix)
    assert _titles_of(first) and all(t.endswith(MARK) for t in _titles_of(first))

    second = await blog_api.get_archive_by_year(TEST_YEAR, _request(), db_session, TEST_LANG)
    hit = [t for t in _titles_of(second) if t.startswith(slug)]
    assert hit, "第二次调用应当命中缓存并返回同一篇"
    for title in hit:
        assert title.endswith(MARK), f"缓存里存的是未渲染标题：{title!r}"
