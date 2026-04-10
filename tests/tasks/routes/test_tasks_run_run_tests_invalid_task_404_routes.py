from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_tests_invalid_task_404(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    talent_partner = await create_talent_partner(async_session, email="run-404@sim.com")
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
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
