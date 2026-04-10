from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_returns_500_when_trial_missing_tasks(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(async_session, email="notasks@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    # Remove tasks to exercise guard
    await async_session.execute(delete(Task).where(Task.trial_id == sim.id))
    await async_session.commit()

    headers = candidate_header_factory(cs)
    res = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=headers,
        json={"contentText": "should error"},
    )
    assert res.status_code == 404
