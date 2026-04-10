from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_current_task_omits_current_window_when_bounds_are_invalid(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="current-window-invalid@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="window-invalid-owner@example.com",
        with_default_schedule=False,
    )
    candidate_session.scheduled_start_at = datetime.now(UTC) - timedelta(days=1)
    candidate_session.candidate_timezone = "Invalid/Timezone"
    candidate_session.day_windows_json = None
    await async_session.commit()

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:window-invalid-owner@example.com",
            "x-candidate-session-id": str(candidate_session.id),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["currentWindow"] is None
