"""
Regression: show_results=False must hide votes_count/total_votes from non-privileged viewers.

When a poll has show_results=False, anonymous and regular users should see null votes_count
and 0 total_votes. Staff/superuser always see real counts regardless of show_results setting.

Mutation pitfall: if you remove the can_see_results check, this test turns red —
votes become visible to everyone even when show_results=False.
"""

import pytest
from httpx import AsyncClient


class TestVotingShowResultsEnforcement:
    """Predict red when reverted: show_results gate removed."""

    @pytest.mark.asyncio
    async def test_poll_list_hides_votes_when_show_results_false(
        self, client: AsyncClient, db_session
    ):
        """Anonymous user sees null votes_count + 0 total_votes when show_results=False."""
        from backend.models.voting import Poll, Choice
        
        # Create poll with show_results=False
        poll = Poll(title="Hidden Results Poll", show_results=False, is_active=True)
        db_session.add(poll)
        await db_session.flush()
        
        choice = Choice(poll_id=poll.id, text="Option A", order=0)
        db_session.add(choice)
        await db_session.flush()
        
        # Add a vote
        from backend.models.voting import Vote
        vote = Vote(poll_id=poll.id, choice_id=choice.id, user_id=None)
        db_session.add(vote)
        await db_session.commit()
        
        # Anonymous request
        r = await client.get(f"/api/voting/polls/{poll.id}")
        assert r.status_code == 200, r.text
        data = r.json()
        
        # votes_count should be null, total_votes should be 0
        assert data["choices"][0]["votes_count"] is None, f"Expected null votes_count, got {data['choices'][0]['votes_count']}"
        assert data["total_votes"] == 0, f"Expected 0 total_votes, got {data['total_votes']}"

    @pytest.mark.asyncio
    async def test_poll_list_shows_votes_to_staff_when_show_results_false(
        self, client: AsyncClient, staff_headers: dict, db_session
    ):
        """Staff user sees real votes even when show_results=False."""
        from backend.models.voting import Poll, Choice, Vote
        
        # Create poll with show_results=False
        poll = Poll(title="Hidden Results Poll (Staff)", show_results=False, is_active=True)
        db_session.add(poll)
        await db_session.flush()
        
        choice = Choice(poll_id=poll.id, text="Option B", order=0)
        db_session.add(choice)
        await db_session.flush()
        
        # Add a vote
        vote = Vote(poll_id=poll.id, choice_id=choice.id, user_id=None)
        db_session.add(vote)
        await db_session.commit()
        
        # Staff request
        r = await client.get(f"/api/voting/polls/{poll.id}", headers=staff_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        
        # Staff should see real counts
        assert data["choices"][0]["votes_count"] == 1, f"Expected 1 votes_count for staff, got {data['choices'][0]['votes_count']}"
        assert data["total_votes"] == 1, f"Expected 1 total_votes for staff, got {data['total_votes']}"
