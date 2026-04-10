from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_code_submission_requires_workspace_without_preprovision(
    async_client, async_session: AsyncSession, actions_stubber
):
    actions_stubber()
    talent_partner = await create_talent_partner(
        async_session, email="no-preprov@test.com"
    )
    sim, tasks = await create_trial_factory(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        content_text="day1",
    )
    await async_session.commit()

    res = await async_client.post(
        f"/api/tasks/{tasks[1].id}/submit",
        headers=candidate_headers(cs.id, f"candidate:{cs.invite_email}"),
        json={},
    )
    assert res.status_code == 400
    assert "Workspace not initialized" in res.json()["detail"]
    assert res.json()["errorCode"] == "WORKSPACE_NOT_INITIALIZED"
