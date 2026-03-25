from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_task_from_other_simulation(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="cross@sim.com")
    sim_a, tasks_a = await create_simulation(async_session, created_by=recruiter)
    sim_b, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim_b,
        status="in_progress",
        with_default_schedule=True,
    )

    # Use task from sim_a with session from sim_b -> 404
    headers = candidate_header_factory(cs)
    res = await async_client.post(
        f"/api/tasks/{tasks_a[0].id}/submit",
        headers=headers,
        json={"contentText": "wrong sim"},
    )
    assert res.status_code == 404
