from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_current_task_mismatch_still_ownership_error_before_schedule_gate(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="ownership-order@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="owner@example.com",
        with_default_schedule=False,
    )
    await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=2),
        timezone_name="America/New_York",
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:attacker@example.com",
            "x-candidate-session-id": str(candidate_session.id),
        },
    )
    assert response.status_code == 403, response.text
    assert response.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"
