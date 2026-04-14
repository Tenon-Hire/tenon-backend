from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
async def test_resolve_transitions_to_in_progress(async_client, async_session):
    talent_partner_email = "talent_partner1@winoe.com"
    await _seed_talent_partner(async_session, talent_partner_email)

    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    await _approve_trial(
        async_client,
        sim_id=sim_id,
        headers={"x-dev-user-email": talent_partner_email},
    )
    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        json={"confirm": True},
        headers={"x-dev-user-email": talent_partner_email},
    )
    assert activate.status_code == 200, activate.text
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
