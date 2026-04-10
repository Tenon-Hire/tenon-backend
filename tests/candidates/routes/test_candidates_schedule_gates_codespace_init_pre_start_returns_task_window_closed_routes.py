from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_pre_start_returns_task_window_closed(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="init-prestart@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        with_default_schedule=False,
    )
    day_windows = await _set_schedule(
        async_session=async_session,
        candidate_session=candidate_session,
        scheduled_start_at=_local_window_start_utc("America/New_York", days_ahead=2),
        timezone_name="America/New_York",
    )
    day2_window = _window_by_day(day_windows, day_index=2)

    response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=candidate_header_factory(candidate_session),
        json={"githubUsername": "octocat"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["errorCode"] == "TASK_WINDOW_CLOSED"
    assert body["details"]["windowStartAt"] == _window_iso(day2_window, "windowStartAt")
    assert body["details"]["windowEndAt"] == _window_iso(day2_window, "windowEndAt")
    assert body["details"]["nextOpenAt"] == _window_iso(day2_window, "windowStartAt")
