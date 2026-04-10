from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_unknown_task_type_errors(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(async_session, email="unk@sim.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )

    # Manually insert a task with unsupported type
    res_tasks = await async_session.execute(
        select(Task).where(Task.trial_id == sim.id).order_by(Task.day_index)
    )
    for t in res_tasks.scalars():
        await async_session.delete(t)
    await async_session.commit()

    bad_task = Task(
        trial_id=sim.id,
        day_index=1,
        type="behavioral",
        title="Unknown type",
        description="N/A",
    )
    async_session.add(bad_task)
    await async_session.commit()
    await async_session.refresh(bad_task)

    headers = candidate_header_factory(cs)
    res = await async_client.post(
        f"/api/tasks/{bad_task.id}/submit",
        headers=headers,
        json={"contentText": "unknown"},
    )
    assert res.status_code == 500
