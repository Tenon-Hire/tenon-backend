from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_submit_invalid_schedule_returns_schedule_invalid_window(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="submit-invalid-window@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        with_default_schedule=False,
    )
    candidate_session.scheduled_start_at = datetime.now(UTC) - timedelta(days=1)
    candidate_session.candidate_timezone = "Invalid/Timezone"
    candidate_session.day_windows_json = None
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=candidate_header_factory(candidate_session),
        json={"contentText": "still blocked"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["detail"] == "Schedule window configuration is invalid."
    assert body["errorCode"] == "SCHEDULE_INVALID_WINDOW"
    assert body["retryable"] is False
    assert body["details"] == {
        "candidateSessionId": candidate_session.id,
        "taskId": tasks[0].id,
        "dayIndex": tasks[0].day_index,
        "windowStartAt": None,
        "windowEndAt": None,
    }
