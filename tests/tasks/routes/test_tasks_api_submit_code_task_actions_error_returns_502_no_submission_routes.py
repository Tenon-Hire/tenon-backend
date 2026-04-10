from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_api_submit_utils import *


@pytest.mark.asyncio
async def test_submit_code_task_actions_error_returns_502_no_submission(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    talent_partner = await create_talent_partner(
        async_session, email="actions-err@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    # seed day 1 to reach day 2 code task
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    class Boom(Exception):
        pass

    actions_stubber(error=Boom("boom"))

    headers = candidate_header_factory(cs)
    await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )
    resp = await async_client.post(
        f"/api/tasks/{tasks[1].id}/submit",
        headers=headers,
        json={},
    )

    assert resp.status_code == 502
    result = await async_session.execute(
        select(Submission).where(
            Submission.candidate_session_id == cs.id, Submission.task_id == tasks[1].id
        )
    )
    assert result.scalar_one_or_none() is None
