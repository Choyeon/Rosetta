"""归档三级出口的「年月」必须是同一个 UTC 口径。

线上实测（2026-10-29）：两篇 ``published_at`` 为 2026-08-31T18:09Z / 23:09Z 的文章，
月份页 ``/archive/2026/09`` 把它们算进九月（共 23 篇），年度页 ``/archive/2026`` 却把
它们分组到「2026-08」（21 篇）。根因是 ``extract("month", Post.published_at)`` 按
**数据库会话时区**求值——生产 PG 会话是 ``Asia/Shanghai``，而年度页/``/archive``/
归档统计都在 Python 里读 UTC 值。用户看到的是"同一篇文章在两级归档里月份不一致"，
且月计数与年度页的月标题对不上。

SQLite 上 ``extract`` 与 Python 分组天然一致（都按墙钟），所以功能用例抓不到这个
回归；口径由源码断言 + utc_* 纯函数钉住，行为用例负责钉住"三级出口互相对齐"。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from backend.api import blog as blog_api
from backend.core.cache import cache
from backend.models.blog import Post
from backend.models.user import User
from backend.repositories.post import (
    PostRepository,
    utc_month_range,
    utc_year_month,
    utc_year_range,
)

# 隔离用：测试独有年份（过去年份，否则会被「定时未到」判据过滤）+ 独立语言。
YEAR = 2015
LANG = "zh_Hant"


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


def _post(author_id: int, slug: str, published_at: datetime) -> Post:
    return Post(
        title={"zh": slug, "en": slug, "ja": slug, "zh_Hant": slug},
        slug=slug,
        content={"zh": "内容", "en": "content"},
        author_id=author_id,
        status="published",
        published_at=published_at,
    )


# 每条都贴着月初/月末的 8 小时窗口——正是会话时区（+08）会改写归属的位置。
BOUNDARY_POSTS = {
    "utc-aug-last": datetime(2015, 8, 31, 23, 9, tzinfo=timezone.utc),
    "utc-sep-first": datetime(2015, 9, 1, 0, 30, tzinfo=timezone.utc),
    "utc-dec-last": datetime(2015, 12, 31, 22, 0, tzinfo=timezone.utc),
    "utc-jan-first": datetime(2016, 1, 1, 1, 0, tzinfo=timezone.utc),
}


class TestUtcHelpers:
    """utc_* 纯函数：边界、跨年、naive 值与年末溢出。"""

    def test_year_range_is_half_open(self):
        start, end = utc_year_range(YEAR)
        assert start == datetime(YEAR, 1, 1, tzinfo=timezone.utc)
        assert end == datetime(YEAR + 1, 1, 1, tzinfo=timezone.utc)

    def test_month_range_wraps_december(self):
        start, end = utc_month_range(YEAR, 12)
        assert start == datetime(YEAR, 12, 1, tzinfo=timezone.utc)
        assert end == datetime(YEAR + 1, 1, 1, tzinfo=timezone.utc)
        assert utc_month_range(YEAR, 9)[1] == datetime(YEAR, 10, 1, tzinfo=timezone.utc)

    def test_max_year_does_not_overflow(self):
        start, end = utc_year_range(9999)
        assert start < end, "9999 年的上界不能构造 datetime(10000, …) 抛 500"

    def test_year_month_normalises_to_utc(self):
        # naive 视为 UTC（本仓写入侧一律存 UTC）
        assert utc_year_month(datetime(2015, 8, 31, 23, 9)) == (2015, 8)
        # 带 +08 的时间戳：本地已是 9 月，UTC 仍是 8 月
        local = datetime(2015, 9, 1, 7, 9, tzinfo=timezone(timedelta(hours=8)))
        assert utc_year_month(local) == (2015, 8)


def test_archive_paths_do_not_use_session_timezone_extract():
    """源码断言：归档出口不得再用 ``extract("year"/"month", published_at)``。

    这条守的是 PG 专属回归：SQLite 上 ``extract`` 与 Python 分组等价，功能用例全绿；
    生产会话 ``Asia/Shanghai`` 下两者才会在月初/月末 8 小时窗口里分裂。
    """
    root = Path(__file__).resolve().parent.parent
    for rel in ("backend/api/blog.py", "backend/repositories/post.py"):
        # 只扫真正的代码行：注释里解释"为什么不能用 extract"是允许且必要的
        code = "\n".join(
            line
            for line in (root / rel).read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        for needle in ('extract("month"', 'extract("year", Post.published_at'):
            assert needle not in code, (
                f"{rel} 又出现了 {needle}：它按数据库会话时区求值，"
                "会与按 UTC 归一的归档分组分裂（改用 utc_year_range / utc_month_range）"
            )


@pytest.mark.asyncio
async def test_year_and_month_exits_agree_on_boundary_posts(
    db_session: AsyncSession, test_user: User
):
    """年度页的月分组、月页的成员、归档统计三处必须给同一份归属。"""
    await cache.clear()

    for slug, published_at in BOUNDARY_POSTS.items():
        db_session.add(_post(test_user.id, slug, published_at))
    await db_session.commit()

    yearly = await blog_api.get_archive_by_year(YEAR, _request(), db_session, LANG)
    months = {group["month"]: group for group in yearly}
    assert sorted(months, reverse=True) == [12, 9, 8]
    assert all(group["count"] == len(group["posts"]) == 1 for group in months.values())
    # 年度页里每条文章的所属月份必须就是它所在分组的月份
    assert [p["slug"] for p in months[8]["posts"]] == ["utc-aug-last"]
    assert [p["slug"] for p in months[9]["posts"]] == ["utc-sep-first"]
    assert [p["slug"] for p in months[12]["posts"]] == ["utc-dec-last"]

    # 月页：同一个月必须拿到同一批文章；相邻月不得串入
    sep = await blog_api.get_archive_by_month(YEAR, 9, _request(), db_session, LANG, 1, 20)
    assert sep["count"] == 1
    assert [p["slug"] for p in sep["posts"]] == ["utc-sep-first"]

    aug = await blog_api.get_archive_by_month(YEAR, 8, _request(), db_session, LANG, 1, 20)
    assert [p["slug"] for p in aug["posts"]] == ["utc-aug-last"]

    dec = await blog_api.get_archive_by_month(YEAR, 12, _request(), db_session, LANG, 1, 20)
    assert [p["slug"] for p in dec["posts"]] == ["utc-dec-last"]

    # 跨年那篇只能出现在 2016-01
    jan = await blog_api.get_archive_by_month(YEAR + 1, 1, _request(), db_session, LANG, 1, 20)
    assert [p["slug"] for p in jan["posts"]] == ["utc-jan-first"]

    # 归档统计的年份分桶与年度页同口径
    stats = await PostRepository(db_session).get_archive_stats()
    assert stats["year_stats"].get(YEAR) == 3
    assert stats["year_stats"].get(YEAR + 1) == 1
    assert stats["total_years"] == len(stats["years"])
    assert stats["years"] == sorted(stats["year_stats"], reverse=True)
