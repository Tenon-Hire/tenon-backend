from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_no_tasks_returns_500(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="notasks@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    # Remove all tasks to trigger guard
    await async_session.execute(select(Task))  # ensure tasks loaded
    for t in tasks:
        await async_session.delete(t)
    await async_session.commit()

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": f"Bearer candidate:{cs.invite_email}",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 500
