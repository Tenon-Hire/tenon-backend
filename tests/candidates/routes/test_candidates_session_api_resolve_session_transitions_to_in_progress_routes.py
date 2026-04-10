from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_resolve_session_transitions_to_in_progress(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="resolve@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    assert cs.status == "not_started"
    assert cs.started_at is None

    res = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["status"] == "in_progress"
    assert body["candidateSessionId"] == cs.id
    assert body["claimedAt"] is not None

    await async_session.refresh(cs)
    assert cs.status == "in_progress"
    assert cs.started_at is not None
    assert cs.candidate_auth0_sub == f"candidate-{cs.invite_email}"
