from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_handoff_resubmission_allowed_while_day4_is_current_before_day5_open(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="current-day4-resubmit-before-day5@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    day1_task = _task_for_day(tasks, day_index=1)
    day2_task = _task_for_day(tasks, day_index=2)
    day3_task = _task_for_day(tasks, day_index=3)
    day4_task = _task_for_day(tasks, day_index=4)

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

    first_recording_id = await _complete_handoff_upload(
        async_client=async_client,
        async_session=async_session,
        candidate_session=cs,
        task_id=day4_task.id,
        filename="day4-first-resubmit.mp4",
        size_bytes=2_048,
    )
    second_recording_id = await _complete_handoff_upload(
        async_client=async_client,
        async_session=async_session,
        candidate_session=cs,
        task_id=day4_task.id,
        filename="day4-second-resubmit.mp4",
        size_bytes=2_049,
    )
    assert second_recording_id != first_recording_id

    headers = {
        "Authorization": f"Bearer candidate:{cs.invite_email}",
        "x-candidate-session-id": str(cs.id),
    }
    current_view = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers=headers,
    )
    assert current_view.status_code == 200, current_view.text
    current_body = current_view.json()
    assert current_body["currentTask"]["id"] == day4_task.id
    assert current_body["currentTask"]["dayIndex"] == 4
