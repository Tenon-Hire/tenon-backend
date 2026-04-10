from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_tests_returns_actions_result(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    talent_partner = await create_talent_partner(
        async_session, email="run-tests@sim.com"
    )
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

    stub_result = ActionsRunResult(
        status="failed",
        run_id=111,
        conclusion="failure",
        passed=2,
        failed=1,
        total=3,
        stdout="out",
        stderr=None,
        head_sha="abc123",
        html_url="https://example.com/run/111",
        raw=None,
    )
    actions_stubber(result=stub_result)

    headers = candidate_header_factory(cs)
    # Init workspace first
    init_resp = await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )
    assert init_resp.status_code == 200, init_resp.text

    resp = await async_client.post(
        f"/api/tasks/{tasks[1].id}/run",
        headers=headers,
        json={},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["passed"] == 2
    assert body["failed"] == 1
    assert body["total"] == 3
    assert body["status"] == "failed"
    assert body["runId"] == 111
    assert body["commitSha"] == "abc123"
    assert body["timeout"] is False
