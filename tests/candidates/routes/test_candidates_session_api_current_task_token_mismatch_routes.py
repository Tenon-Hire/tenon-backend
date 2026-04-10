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
