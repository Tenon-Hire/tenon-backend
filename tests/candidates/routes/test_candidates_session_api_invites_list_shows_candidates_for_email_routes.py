from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_invites_list_shows_candidates_for_email(async_client, async_session):
    talent_partner = await create_talent_partner(async_session, email="list@test.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs_match = await create_candidate_session(async_session, trial=sim)
    await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="other@example.com",
        candidate_name="Other",
    )

    res = await async_client.get(
        "/api/candidate/invites",
        headers={"Authorization": f"Bearer candidate:{cs_match.invite_email}"},
    )
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) == 1
    assert items[0]["candidateSessionId"] == cs_match.id
