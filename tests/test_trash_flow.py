"""
回收站闭环回归测试

覆盖口径：
- 单删文章（DELETE /api/blog/posts/{id}）与批删同构——必须落 TrashItem 快照而非物理删除；
- 列表（GET /api/admin/trash）返回裸分页对象并含快照字段；
- 恢复（POST /api/admin/trash/{id}/restore）重建文章并消费记录（一次性）；
- 永久删除（DELETE /api/admin/trash/{id}）只删记录。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Post
from backend.models.user import User


async def _new_post(db_session: AsyncSession, test_user: User, test_category: Category) -> Post:
    post = Post(
        title={"zh": "回收站闭环文章"},
        slug="trash-flow-post",
        content={"zh": "正文内容"},
        excerpt={"zh": "摘要"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="draft",
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


class TestSingleDeleteToTrash:
    """单个删除必须进回收站（与批删口径一致）"""

    @pytest.mark.asyncio
    async def test_delete_post_creates_trash_entry(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
        db_session: AsyncSession,
    ):
        post = await _new_post(db_session, test_user, test_category)

        resp = await client.delete(f"/api/blog/posts/{post.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert "回收站" in resp.json()["message"]

        # 原行已删（expire 后 get() 会对已删实例做 refresh 报错，改用 COUNT 直查表）
        remaining = (
            await db_session.execute(
                select(func.count()).select_from(Post).where(Post.id == post.id)
            )
        ).scalar()
        assert remaining == 0

        listing = await client.get(
            "/api/admin/trash", params={"resource_type": "post"}, headers=admin_headers
        )
        assert listing.status_code == 200
        body = listing.json()
        entry = next(i for i in body["items"] if i["resource_id"] == post.id)
        snap = entry["resource_data"]
        # 快照字段与批删（advanced.py）同构
        assert snap["slug"] == "trash-flow-post"
        assert snap["status"] == "draft"
        assert snap["author_id"] == test_user.id
        for key in ("title", "content", "excerpt", "cover_image", "category_id", "views"):
            assert key in snap
        assert entry["auto_delete_at"] is not None

    @pytest.mark.asyncio
    async def test_restore_single_deleted_post(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
        db_session: AsyncSession,
    ):
        post = await _new_post(db_session, test_user, test_category)
        await client.delete(f"/api/blog/posts/{post.id}", headers=admin_headers)

        listing = await client.get(
            "/api/admin/trash", params={"resource_type": "post"}, headers=admin_headers
        )
        entry = next(i for i in listing.json()["items"] if i["resource_id"] == post.id)

        restore = await client.post(
            f"/api/admin/trash/{entry['id']}/restore", headers=admin_headers
        )
        assert restore.status_code == 200
        assert restore.json()["success"] is True

        # 恢复后同 slug 文章重新存在，快照记录被消费
        revived = (
            await db_session.execute(select(Post).where(Post.slug == "trash-flow-post"))
        ).scalar_one()
        assert revived.status == "draft"
        assert revived.author_id == test_user.id
        await db_session.refresh(revived)

        after = await client.get(
            "/api/admin/trash", params={"resource_type": "post"}, headers=admin_headers
        )
        assert all(i["id"] != entry["id"] for i in after.json()["items"])

    @pytest.mark.asyncio
    async def test_permanent_delete_removes_record(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
        db_session: AsyncSession,
    ):
        post = await _new_post(db_session, test_user, test_category)
        await client.delete(f"/api/blog/posts/{post.id}", headers=admin_headers)

        listing = await client.get(
            "/api/admin/trash", params={"resource_type": "post"}, headers=admin_headers
        )
        entry = next(i for i in listing.json()["items"] if i["resource_id"] == post.id)

        gone = await client.delete(f"/api/admin/trash/{entry['id']}", headers=admin_headers)
        assert gone.status_code == 200

        after = await client.get(
            "/api/admin/trash", params={"resource_type": "post"}, headers=admin_headers
        )
        assert all(i["id"] != entry["id"] for i in after.json()["items"])

        # 永久删除后不可再恢复
        re_restore = await client.post(
            f"/api/admin/trash/{entry['id']}/restore", headers=admin_headers
        )
        assert re_restore.status_code == 404
