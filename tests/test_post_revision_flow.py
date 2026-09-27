"""
文章版本历史（PostRevision）写入与回滚回归

覆盖口径：
- 编辑保存改了 title/content/excerpt 才会自动生成修订版本（快照存的是改动前的内容）；
- 重复保存同一份内容、只改状态，都不得造出字节相同的空版本；
- 恢复（POST /api/admin/posts/{id}/revisions/{rid}/restore）会先把当前内容另存一版，
  再把文章回滚到目标版本。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Post
from backend.models.user import User


async def _new_post(db_session: AsyncSession, test_user: User, test_category: Category) -> Post:
    post = Post(
        title={"zh": "版本历史文章"},
        slug="revision-flow-post",
        content={"zh": "第一版正文"},
        excerpt={"zh": "第一版摘要"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="draft",
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _revision_count(client: AsyncClient, headers: dict, post_id: int) -> dict:
    resp = await client.get(f"/api/admin/posts/{post_id}/revisions", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    return body


class TestRevisionWriter:
    """编辑保存必须真的产出修订记录（此前全仓无写入点，版本列表恒空）"""

    @pytest.mark.asyncio
    async def test_content_edit_creates_revision(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
        db_session: AsyncSession,
    ):
        post = await _new_post(db_session, test_user, test_category)

        resp = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"content": {"zh": "第二版正文"}},
        )
        assert resp.status_code == 200

        body = await _revision_count(client, admin_headers, post.id)
        assert body["total"] == 1
        rev = body["revisions"][0]
        assert rev["revision_number"] == 1
        assert rev["change_summary"] == "编辑保存"
        assert rev["author"]["username"] == "admin"

        # 快照记录的是「改动前」的内容，不是新内容
        detail = await client.get(
            f"/api/admin/posts/{post.id}/revisions/{rev['id']}", headers=admin_headers
        )
        assert detail.status_code == 200
        assert detail.json()["content"] == {"zh": "第一版正文"}

    @pytest.mark.asyncio
    async def test_unchanged_save_creates_nothing(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
        db_session: AsyncSession,
    ):
        post = await _new_post(db_session, test_user, test_category)
        payload = {"title": {"zh": "版本历史文章"}, "content": {"zh": "第一版正文"}}

        for _ in range(2):
            assert (
                await client.put(f"/api/blog/posts/{post.id}", headers=admin_headers, json=payload)
            ).status_code == 200

        # 第一次保存内容与库中相同 → 零版本；第二次同理
        assert (await _revision_count(client, admin_headers, post.id))["total"] == 0

    @pytest.mark.asyncio
    async def test_status_only_change_creates_nothing(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
        db_session: AsyncSession,
    ):
        post = await _new_post(db_session, test_user, test_category)
        assert (
            await client.put(
                f"/api/blog/posts/{post.id}", headers=admin_headers, json={"status": "published"}
            )
        ).status_code == 200

        assert (await _revision_count(client, admin_headers, post.id))["total"] == 0


class TestRevisionRestore:
    """恢复链路：目标版本回滚 + 当前内容留备份"""

    @pytest.mark.asyncio
    async def test_restore_rolls_back_and_keeps_backup(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
        db_session: AsyncSession,
    ):
        post = await _new_post(db_session, test_user, test_category)
        await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"content": {"zh": "第二版正文"}},
        )
        body = await _revision_count(client, admin_headers, post.id)
        first_rev = body["revisions"][0]

        resp = await client.post(
            f"/api/admin/posts/{post.id}/revisions/{first_rev['id']}/restore",
            headers=admin_headers,
        )
        assert resp.status_code == 200

        post_id = post.id
        db_session.expire_all()
        revived = (await db_session.execute(select(Post).where(Post.id == post_id))).scalar_one()
        assert revived.content == {"zh": "第一版正文"}

        after = await _revision_count(client, admin_headers, post.id)
        assert after["total"] == 2
        backup = next(r for r in after["revisions"] if r["revision_number"] == 2)
        assert "恢复到版本 #1 前的备份" in backup["change_summary"]
