from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_get_run_result_marks_timeout(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    timed_out = ActionsRunResult(
        status="running",
        run_id=777,
        conclusion="timed_out",
        passed=0,
        failed=0,
        total=0,
        stdout=None,
        stderr=None,
        head_sha="abc123",
        html_url="https://example.com/run/777",
        raw=None,
    )
    actions_stubber(result=timed_out)
    talent_partner = await create_talent_partner(
        async_session, email="run-timeout@sim.com"
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

    headers = candidate_header_factory(cs)
    await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )

    resp = await async_client.get(
        f"/api/tasks/{tasks[1].id}/run/{timed_out.run_id}",
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["timeout"] is True
    assert data["runId"] == timed_out.run_id
