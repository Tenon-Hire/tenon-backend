from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_returns_500_when_simulation_missing_tasks(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="notasks@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    # Remove tasks to exercise guard
    await async_session.execute(delete(Task).where(Task.simulation_id == sim.id))
    await async_session.commit()

    headers = candidate_header_factory(cs)
    res = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=headers,
        json={"contentText": "should error"},
    )
    assert res.status_code == 404
