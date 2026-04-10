from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_get_run_result_returns_parsed_counts(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    actions_stubber()
    talent_partner = await create_talent_partner(async_session, email="run-get@sim.com")
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

    # fetch_run_result uses the stubbed runner
    resp = await async_client.get(
        f"/api/tasks/{tasks[1].id}/run/123",
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["runId"] == 123
    assert body["passed"] == 1
    assert body["failed"] == 0
    assert body["total"] == 1
