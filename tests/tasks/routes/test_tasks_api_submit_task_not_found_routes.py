from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_task_not_found(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="missingtask@sim.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    headers = candidate_header_factory(cs)
    res = await async_client.post(
        "/api/tasks/999999/submit",
        headers=headers,
        json={"contentText": "no task"},
    )
    assert res.status_code == 404
