from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_rejects_expired_session(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(async_session, email="expired@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        expires_in_days=-1,
    )

    task_id = tasks[0].id
    headers = candidate_header_factory(cs)
    res = await async_client.post(
        f"/api/tasks/{task_id}/submit",
        headers=headers,
        json={"contentText": "should fail"},
    )
    assert res.status_code == 410
