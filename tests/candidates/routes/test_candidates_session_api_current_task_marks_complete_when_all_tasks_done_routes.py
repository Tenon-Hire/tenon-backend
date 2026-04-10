from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_marks_complete_when_all_tasks_done(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="progress@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        with_default_schedule=True,
    )

    # Seed submissions for all tasks to mimic completion.
    for task in tasks:
        await create_submission(
            async_session,
            candidate_session=cs,
            task=task,
            content_text=f"Answer for day {task.day_index}",
        )

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["isComplete"] is True
    assert body["currentDayIndex"] is None
    assert body["currentTask"] is None
    assert body["progress"]["completed"] == len(tasks)

    await async_session.refresh(cs)
    assert cs.status == "completed"
    assert cs.completed_at is not None
