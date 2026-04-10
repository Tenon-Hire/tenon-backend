from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_current_task_includes_current_window_metadata(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="current-window@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="window-owner@example.com",
        with_default_schedule=False,
    )
    await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=-1),
        timezone_name="America/New_York",
    )

    response = await async_client.get(
        f"/api/candidate/session/{candidate_session.id}/current_task",
        headers={
            "Authorization": "Bearer candidate:window-owner@example.com",
            "x-candidate-session-id": str(candidate_session.id),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    current_window = body["currentWindow"]
    assert current_window is not None
    assert current_window["windowStartAt"] is not None
    assert current_window["windowEndAt"] is not None
    assert isinstance(current_window["isOpen"], bool)
    assert current_window["now"] is not None
