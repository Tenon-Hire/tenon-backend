from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_tests_rejects_invalid_branch(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    actions_stubber()
    talent_partner = await create_talent_partner(async_session, email="branch@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    headers = candidate_header_factory(cs)
    await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )

    resp = await async_client.post(
        f"/api/tasks/{tasks[1].id}/run",
        headers=headers,
        json={"branch": "../bad"},
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body["errorCode"] == "INVALID_BRANCH_NAME"
    assert "branch" in body["detail"].lower()
