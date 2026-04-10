from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_after_completion_returns_409(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(async_session, email="done@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    # Seed submissions for all tasks to mark sim complete
    for task in tasks:
        await create_submission(
            async_session,
            candidate_session=cs,
            task=task,
            content_text="done",
        )
    await async_session.refresh(cs)

    task_id = tasks[-1].id
    headers = candidate_header_factory(cs)
    res = await async_client.post(
        f"/api/tasks/{task_id}/submit",
        headers=headers,
        json={"contentText": "too late"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] in {
        "Trial already completed",
        "Task already submitted",
    }
