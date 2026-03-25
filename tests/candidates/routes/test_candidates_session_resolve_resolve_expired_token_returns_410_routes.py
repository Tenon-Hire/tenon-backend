from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *


@pytest.mark.asyncio
async def test_resolve_expired_token_returns_410(async_client, async_session):
    recruiter_email = "recruiter1@tenon.com"
    await _seed_recruiter(async_session, recruiter_email)

    sim_id = await _create_simulation(async_client, async_session, recruiter_email)
    invite = await _invite_candidate(async_client, sim_id, recruiter_email)

    token = invite["token"]
    cs_id = invite["candidateSessionId"]

    cs = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()
    cs.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": "Bearer candidate:jane@example.com"},
    )
    assert res.status_code == 410
    assert res.json()["detail"] == "Invite token expired"
