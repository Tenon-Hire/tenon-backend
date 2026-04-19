from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_works_for_day3_implementation_wrap_up(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    actions_stubber()
    talent_partner = await create_talent_partner(
        async_session, email="wrap-up-task@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    # Complete day 1 and initialize day 2 workspace first.
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    headers = candidate_header_factory(cs)
    day2_init = await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )
    assert day2_init.status_code == 200, day2_init.text

    await create_submission(
        async_session, candidate_session=cs, task=tasks[1], content_text="day2"
    )
    await async_session.commit()

    resp = await async_client.post(
        f"/api/tasks/{tasks[2].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["repoFullName"]
    assert body["workspaceId"]
    assert "baseTemplateSha" not in body
    assert "precommitSha" not in body
