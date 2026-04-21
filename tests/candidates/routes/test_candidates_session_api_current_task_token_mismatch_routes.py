from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_token_mismatch(async_client, async_session):
    talent_partner = await create_talent_partner(async_session, email="tm@test.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    claim = await async_client.post(
        f"/api/candidate/session/{cs.token}/claim",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert claim.status_code == 200, claim.text

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:other@example.com",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"


@pytest.mark.asyncio
async def test_current_task_cross_session_access_is_rejected(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="cross-session@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    await create_candidate_session(
        async_session, trial=sim, invite_email="candidate-a@example.com"
    )
    candidate_b = await create_candidate_session(
        async_session, trial=sim, invite_email="candidate-b@example.com"
    )

    res = await async_client.get(
        f"/api/candidate/session/{candidate_b.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:candidate-a@example.com",
            "x-candidate-session-id": str(candidate_b.id),
        },
    )
    assert res.status_code == 403, res.text
    assert res.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"
