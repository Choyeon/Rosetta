"""文章级"按 id 取值"的公开口不得变成存在性探针。

``POST /api/posts/{id}/decrypt`` 与 ``POST /api/post_crypto/verify_access`` 都是
匿名可访问、直接吃 ``post_id`` 的端点。它们的原始实现只判"这行在不在"：

* 不存在 → 404；存在但未加密 → 400 / ``{"ok": true}``

于是任何人从 id=1 遍历就能区分"存在"与"不存在"，而草稿 / 待审 / 未来定时文章
在详情口与评论口一律是按 404 收口的（services/post_access 的唯一判据）。
更糟的是 ``decrypt`` 完全不看 status：草稿的密文会被任何知道密码的人解出全文。

这里按"草稿必须与不存在同形、已发布照常可用"两侧钉住。
"""

import pytest

from backend.core.auth import get_password_hash
from backend.core.crypto import encrypt_content
from backend.models.blog import Post
from backend.models.user import User

PASSWORD = "Secret@123"


async def _author(db_session) -> User:
    user = User(
        username="oracle_author",
        email="oracle_author@example.com",
        password_hash=get_password_hash("Pass@1234"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _encrypted_post(db_session, author: User, *, status: str) -> Post:
    post = Post(
        title={"zh": "加密文章"},
        slug=f"encrypted-{status}",
        status=status,
        content="密文版的正文",
        excerpt={"zh": "摘要"},
        author_id=author.id,
        encryption_enabled=True,
        password=get_password_hash(PASSWORD),
        encrypted_content={"data": encrypt_content("绝密正文", PASSWORD)},
        encryption_algorithm="AES-256-GCM",
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.mark.asyncio
async def test_decrypt_hides_draft_posts(client, db_session):
    """草稿的密文不能被匿名解出来，且必须与"不存在"同形（都是 404）。"""
    author = await _author(db_session)
    draft = await _encrypted_post(db_session, author, status="draft")

    response = await client.post(f"/api/posts/{draft.id}/decrypt", json={"password": PASSWORD})
    assert response.status_code == 404, (
        f"草稿密文被匿名接口解出或暴露了存在性: {response.status_code} {response.text}"
    )

    missing = await client.post("/api/posts/999999/decrypt", json={"password": PASSWORD})
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_decrypt_still_works_for_published_posts(client, db_session):
    """闸门不能把正常加密文章一起关掉。"""
    author = await _author(db_session)
    published = await _encrypted_post(db_session, author, status="published")

    response = await client.post(f"/api/posts/{published.id}/decrypt", json={"password": PASSWORD})
    assert response.status_code == 200, response.text
    assert response.json()["content"] == "绝密正文"

    wrong = await client.post(f"/api/posts/{published.id}/decrypt", json={"password": "nope"})
    assert wrong.status_code == 403


@pytest.mark.asyncio
async def test_verify_access_hides_draft_posts(client, db_session):
    """verify_access 对草稿必须是 404，而不是 {"ok": true} 式的存在性回执。"""
    author = await _author(db_session)
    draft = await _encrypted_post(db_session, author, status="draft")
    published = await _encrypted_post(db_session, author, status="published")

    hidden = await client.post(
        "/api/post_crypto/verify_access",
        json={"post_id": draft.id, "password": PASSWORD},
    )
    assert hidden.status_code == 404, f"草稿存在性被 verify_access 泄漏: {hidden.text}"

    ok = await client.post(
        "/api/post_crypto/verify_access",
        json={"post_id": published.id, "password": PASSWORD},
    )
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
