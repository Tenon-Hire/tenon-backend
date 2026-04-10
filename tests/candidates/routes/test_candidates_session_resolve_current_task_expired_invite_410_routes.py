from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *


@pytest.mark.asyncio
async def test_current_task_expired_invite_410(async_client, async_session):
    talent_partner_email = "talent_partner1@winoe.com"
    await _seed_talent_partner(async_session, talent_partner_email)

    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    invite = await _invite_candidate(async_client, sim_id, talent_partner_email)

    await _claim(async_client, invite["token"], "jane@example.com")
    cs_id = invite["candidateSessionId"]
    token = "candidate:jane@example.com"

    cs = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()

    cs.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{cs_id}/current_task",
        headers={
            "Authorization": f"Bearer {token}",
            "x-candidate-session-id": str(cs_id),
        },
    )
    assert res.status_code == 410
