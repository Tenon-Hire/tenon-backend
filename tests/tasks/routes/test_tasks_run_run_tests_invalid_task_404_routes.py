from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_tests_invalid_task_404(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    recruiter = await create_recruiter(async_session, email="run-404@sim.com")
    sim, _tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await async_session.commit()

    actions_stubber()

    headers = candidate_header_factory(cs)
    resp = await async_client.post(
        "/api/tasks/99999/run",
        headers=headers,
        json={},
    )

    assert resp.status_code == 404
