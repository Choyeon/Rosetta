"""后台文章列表的状态过滤回归测试。

起因：审计报「GET /blog/posts?status=draft 触发 MissingGreenlet」+
「前端 useAdminManage 会传 status=all，而路由未声明 all」。
这里把两个口径钉住：草稿必须能列出、all 必须是「全部状态」而不是 422。
"""

import pytest

from backend.models.blog import Post


async def _make_draft(db_session, author, category, slug):
    post = Post(
        title={"zh": f"草稿 {slug}", "en": f"Draft {slug}"},
        slug=slug,
        content={"zh": "正文", "en": "body"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        status="draft",
        author_id=author.id,
        category_id=category.id,
    )
    db_session.add(post)
    await db_session.commit()
    return post


@pytest.mark.asyncio
async def test_admin_can_list_draft_posts(
    client, db_session, admin_headers, test_user, test_category
):
    """草稿列表：不得 500，且只返回 draft"""
    await _make_draft(db_session, test_user, test_category, "draft-a")

    resp = await client.get("/api/blog/posts", params={"status": "draft"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert all(item["status"] == "draft" for item in data["items"])
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_admin_status_all_returns_every_status(
    client, db_session, admin_headers, test_user, test_category
):
    """status=all 是后台「全部」标签页的值：不能 422，也不能被当成未知值回落成 draft"""
    await _make_draft(db_session, test_user, test_category, "draft-b")

    resp = await client.get("/api/blog/posts", params={"status": "all"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    statuses = {item["status"] for item in resp.json()["items"]}
    assert "draft" in statuses


@pytest.mark.asyncio
async def test_public_caller_cannot_see_drafts(client, db_session, test_category, test_user):
    """无鉴权请求即使显式传 status=draft 也只能拿到已发布文章"""
    await _make_draft(db_session, test_user, test_category, "draft-c")

    resp = await client.get("/api/blog/posts", params={"status": "draft"})
    assert resp.status_code == 200, resp.text
    assert all(item["status"] == "published" for item in resp.json()["items"])
