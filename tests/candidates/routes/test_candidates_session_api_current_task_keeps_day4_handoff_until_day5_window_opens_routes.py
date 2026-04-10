from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_keeps_day4_handoff_until_day5_window_opens(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="current-day4-handoff-window@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    day1_task = _task_for_day(tasks, day_index=1)
    day2_task = _task_for_day(tasks, day_index=2)
    day3_task = _task_for_day(tasks, day_index=3)
    day4_task = _task_for_day(tasks, day_index=4)
    day5_task = _task_for_day(tasks, day_index=5)

    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=False,
        consent_version="mvp1",
        ai_notice_version="mvp1",
    )
    _set_day4_day5_transition_windows(cs, day5_open=False)
    await create_submission(async_session, candidate_session=cs, task=day1_task)
    await create_submission(async_session, candidate_session=cs, task=day2_task)
    await create_submission(async_session, candidate_session=cs, task=day3_task)
    await async_session.commit()

    await _complete_handoff_upload(
        async_client=async_client,
        async_session=async_session,
        candidate_session=cs,
        task_id=day4_task.id,
        filename="day4-first.mp4",
        size_bytes=2_048,
    )

    headers = {
        "Authorization": f"Bearer candidate:{cs.invite_email}",
        "x-candidate-session-id": str(cs.id),
    }
    first_view = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert first_view.status_code == 200, first_view.text
    first_body = first_view.json()
    assert first_body["currentTask"]["id"] == day4_task.id
    assert first_body["currentTask"]["dayIndex"] == 4
    assert first_body["currentTask"]["type"] == "handoff"

    revisit_view = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert revisit_view.status_code == 200, revisit_view.text
    revisit_body = revisit_view.json()
    assert revisit_body["currentTask"]["id"] == day4_task.id
    assert revisit_body["currentTask"]["dayIndex"] == 4

    _set_day4_day5_transition_windows(cs, day5_open=True)
    await async_session.commit()

    after_day5_open = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert after_day5_open.status_code == 200, after_day5_open.text
    after_day5_open_body = after_day5_open.json()
    assert after_day5_open_body["currentTask"]["id"] == day5_task.id
    assert after_day5_open_body["currentTask"]["dayIndex"] == 5
