"""一次性脚本：对 posts 表按 slug 去重，保留最小 ID，删除重复行。
用法：cd d:\WebProjects\Rosetta && uv run python -m backend.scripts.dedup_posts
"""
from __future__ import annotations

import asyncio

from sqlalchemy import delete, func, select

from backend.core.database import async_session_maker, init_db
from backend.models.blog import Post


async def main() -> None:
    await init_db()
    async with async_session_maker() as db:
        total_before = (await db.execute(select(func.count(Post.id)))).scalar_one()
        print(f"[dedup] posts total BEFORE: {total_before}")

        dup_q = (
            select(Post.slug, func.count(Post.id).label("c"))
            .group_by(Post.slug)
            .having(func.count(Post.id) > 1)
            .order_by(func.count(Post.id).desc())
        )
        dup_rows = (await db.execute(dup_q)).all()
        print(f"[dedup] distinct duplicate slugs: {len(dup_rows)}")
        for slug, cnt in dup_rows[:20]:
            print(f"   {cnt}x  {slug!r}")

        removed = 0
        for slug, _ in dup_rows:
            ids_res = await db.execute(select(Post.id).where(Post.slug == slug).order_by(Post.id.asc()))
            ids = [r for (r,) in ids_res.all()]
            if len(ids) < 2:
                continue
            to_del = ids[1:]
            res = await db.execute(delete(Post).where(Post.id.in_(to_del)))
            removed += int(res.rowcount or 0)

        await db.commit()

        total_after = (await db.execute(select(func.count(Post.id)))).scalar_one()
        print(f"[dedup] removed={removed} after={total_after}")


if __name__ == "__main__":
    asyncio.run(main())
