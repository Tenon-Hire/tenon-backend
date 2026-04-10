from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *


@pytest.mark.asyncio
async def test_resolve_transitions_to_in_progress(async_client, async_session):
    talent_partner_email = "talent_partner1@winoe.com"
    await _seed_talent_partner(async_session, talent_partner_email)

    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    invite = await _invite_candidate(async_client, sim_id, talent_partner_email)

    token = invite["token"]
    cs_id = invite["candidateSessionId"]

    await _claim(async_client, token, "jane@example.com")
    access_token = "candidate:jane@example.com"

    res = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "in_progress"
    assert body["startedAt"] is not None
    assert body["candidateSessionId"] == cs_id
    assert body["aiNoticeVersion"] == "mvp1"
    assert isinstance(body["aiNoticeText"], str)
    assert body["aiNoticeText"]
    assert body["evalEnabledByDay"] == {
        "1": True,
        "2": True,
        "3": True,
        "4": True,
        "5": True,
    }

    cs_after = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == cs_id)
        )
    ).scalar_one()
    assert cs_after.status == "in_progress"
    assert cs_after.started_at is not None
