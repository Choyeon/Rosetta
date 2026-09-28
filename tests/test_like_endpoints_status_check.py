"""
Regression: like endpoints must check content status.

Pending/spam/rejected guestbook entries and comments should NOT be likable —
the like endpoint should return 404 (GUESTBOOK_ENTRY_NOT_FOUND / COMMENT_NOT_FOUND)
instead of incrementing likes_count on invisible content.

Mutation pitfall: if you remove the status == "approved" check from the WHERE clause,
these tests turn red — pending/spam items become likable again.
"""

import pytest
from httpx import AsyncClient


class TestLikeEndpointsCheckStatus:
    """Predict red when reverted: status check removed from like queries."""

    @pytest.mark.asyncio
    async def test_guestbook_like_rejects_pending(
        self, client: AsyncClient, db_session
    ):
        """Pending guestbook entry should not be likable (404)."""
        from backend.models.guestbook import GuestbookEntry
        
        entry = GuestbookEntry(
            author_name="Test User",
            content="Pending entry",
            status="pending",  # Not approved yet
        )
        db_session.add(entry)
        await db_session.commit()
        
        r = await client.post(f"/api/guestbook/{entry.id}/like")
        assert r.status_code == 404, f"Expected 404 for pending entry, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_guestbook_like_rejects_spam(
        self, client: AsyncClient, db_session
    ):
        """Spam guestbook entry should not be likable (404)."""
        from backend.models.guestbook import GuestbookEntry
        
        entry = GuestbookEntry(
            author_name="Spammer",
            content="Spam entry",
            status="spam",
        )
        db_session.add(entry)
        await db_session.commit()
        
        r = await client.post(f"/api/guestbook/{entry.id}/like")
        assert r.status_code == 404, f"Expected 404 for spam entry, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_comment_like_rejects_pending(
        self, client: AsyncClient, db_session, test_post
    ):
        """Pending comment should not be likable (404)."""
        from backend.models.blog import Comment
        
        comment = Comment(
            post_id=test_post.id,
            author_name="Test User",
            content="Pending comment",
            status="pending",
        )
        db_session.add(comment)
        await db_session.commit()
        
        r = await client.post(f"/api/comments/{comment.id}/like")
        assert r.status_code == 404, f"Expected 404 for pending comment, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_comment_like_rejects_spam(
        self, client: AsyncClient, db_session, test_post
    ):
        """Spam comment should not be likable (404)."""
        from backend.models.blog import Comment
        
        comment = Comment(
            post_id=test_post.id,
            author_name="Spammer",
            content="Spam comment",
            status="spam",
        )
        db_session.add(comment)
        await db_session.commit()
        
        r = await client.post(f"/api/comments/{comment.id}/like")
        assert r.status_code == 404, f"Expected 404 for spam comment, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_guestbook_like_allows_approved(
        self, client: AsyncClient, db_session
    ):
        """Approved guestbook entry should still be likable."""
        from backend.models.guestbook import GuestbookEntry
        
        entry = GuestbookEntry(
            author_name="Good User",
            content="Approved entry",
            status="approved",
        )
        db_session.add(entry)
        await db_session.commit()
        
        r = await client.post(f"/api/guestbook/{entry.id}/like")
        assert r.status_code == 200, f"Expected 200 for approved entry, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["likes_count"] == 1

    @pytest.mark.asyncio
    async def test_comment_like_allows_approved(
        self, client: AsyncClient, db_session, test_post
    ):
        """Approved comment should still be likable."""
        from backend.models.blog import Comment
        
        comment = Comment(
            post_id=test_post.id,
            author_name="Good User",
            content="Approved comment",
            status="approved",
        )
        db_session.add(comment)
        await db_session.commit()
        
        r = await client.post(f"/api/comments/{comment.id}/like")
        assert r.status_code == 200, f"Expected 200 for approved comment, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["likes_count"] == 1
