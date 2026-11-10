"""
列表计数的回归测试（P2-9）。

P2-9 把 list_posts 的 COUNT 从「含 likes/comments 两个 GROUP BY 外连接的整条查询包子查询」
改为「仅含过滤谓词的 base = select(Post)」再 count，避免聚合跑两遍。

本测试锁定：在 category/tag 内连接、author、media(video)、组合过滤下，分页元数据里的
``total`` 既等于实际返回条数，也等于按过滤条件独立核对的预期数量——防止计数子查询因
漏掉/多算 JOIN 而与列表取数不一致。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Post, Tag
from backend.models.user import User


@pytest.mark.asyncio
async def test_list_count_matches_items_across_filters(
    client: AsyncClient, db_session: AsyncSession, test_user: User
):
    # 唯一 slug，避免与种子 / 其它 fixture 数据冲突
    cat = Category(
        name={"zh": "计数分类", "en": "CountCat"},
        slug="count-cat-unique",
        description={"zh": "x", "en": "x"},
    )
    tag = Tag(
        name={"zh": "计数标签", "en": "CountTag"},
        slug="count-tag-unique",
        is_active=True,
    )
    db_session.add_all([cat, tag])
    await db_session.commit()
    await db_session.refresh(cat)
    await db_session.refresh(tag)

    author2 = User(
        username="author_two_unique",
        email="author2@example.com",
        password_hash="x",
        nickname="A2",
        is_active=True,
    )
    db_session.add(author2)
    await db_session.commit()
    await db_session.refresh(author2)

    def _mk(slug: str, author_id: int, with_cat: bool, with_tag: bool, with_video: bool) -> Post:
        p = Post(
            title={"zh": slug, "en": slug},
            slug=slug,
            content={"zh": "c", "en": "c"},
            excerpt={"zh": "e", "en": "e"},
            author_id=author_id,
            category_id=cat.id if with_cat else None,
            status="published",
        )
        if with_video:
            p.video = "v.mp4"
        if with_tag:
            p.tags = [tag]
        db_session.add(p)
        return p

    _mk("count-p1", test_user.id, True, True, True)
    _mk("count-p2", test_user.id, True, False, False)
    _mk("count-p3", test_user.id, False, True, False)
    _mk("count-p4", author2.id, True, False, True)
    _mk("count-p5", author2.id, False, False, False)
    await db_session.commit()

    async def total_and_items(params: dict) -> tuple[int, list]:
        resp = await client.get("/api/blog/posts", params={**params, "page": 1, "page_size": 200})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        return data["total"], data["items"]

    # 无过滤：至少包含我建的 5 篇，且 total == len(items)
    total, items = await total_and_items({})
    slugs = {it["slug"] for it in items}
    assert {"count-p1", "count-p2", "count-p3", "count-p4", "count-p5"} <= slugs
    assert total == len(items)

    # 分类内连接：P1/P2/P4 = 3
    total, items = await total_and_items({"category": "count-cat-unique"})
    assert total == 3 == len(items)

    # 标签内连接：P1/P3 = 2
    total, items = await total_and_items({"tag": "count-tag-unique"})
    assert total == 2 == len(items)

    # 作者过滤（用户名 → author_id）：test_user = P1/P2/P3 = 3
    total, items = await total_and_items({"author": test_user.username})
    assert total == 3 == len(items)

    # 作者过滤：author2 = P4/P5 = 2
    total, items = await total_and_items({"author": "author_two_unique"})
    assert total == 2 == len(items)

    # 分类 + 作者组合：P1/P2 = 2
    total, items = await total_and_items(
        {"category": "count-cat-unique", "author": test_user.username}
    )
    assert total == 2 == len(items)

    # 媒体过滤 media=video：P1/P4 = 2
    total, items = await total_and_items({"media": "video"})
    assert total == 2 == len(items)
