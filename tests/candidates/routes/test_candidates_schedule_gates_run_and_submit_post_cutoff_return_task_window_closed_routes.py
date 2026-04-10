from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_run_and_submit_post_cutoff_return_task_window_closed(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="post-cutoff@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        with_default_schedule=False,
    )
    now_utc = datetime.now(UTC).replace(microsecond=0)
    day_windows = []
    for day_index in range(1, 6):
        window_end = now_utc - timedelta(days=6 - day_index)
        window_start = window_end - timedelta(hours=8)
        day_windows.append(
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
        )
    candidate_session.scheduled_start_at = day_windows[0]["windowStartAt"]
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()
    day2_window = _window_by_day(day_windows, day_index=2)

    run_response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/run",
        headers=candidate_header_factory(candidate_session),
        json={},
    )
    assert run_response.status_code == 409, run_response.text
    run_body = run_response.json()
    assert run_body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert run_body["details"]["windowStartAt"] == _window_iso(
        day2_window, "windowStartAt"
    )
    assert run_body["details"]["windowEndAt"] == _window_iso(day2_window, "windowEndAt")

    submit_response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/submit",
        headers=candidate_header_factory(candidate_session),
        json={},
    )
    assert submit_response.status_code == 409, submit_response.text
    submit_body = submit_response.json()
    assert submit_body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert submit_body["details"]["windowStartAt"] == _window_iso(
        day2_window, "windowStartAt"
    )
    assert submit_body["details"]["windowEndAt"] == _window_iso(
        day2_window, "windowEndAt"
    )
