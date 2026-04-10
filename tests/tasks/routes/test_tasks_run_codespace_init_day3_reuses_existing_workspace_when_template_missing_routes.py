from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_day3_reuses_existing_workspace_when_template_missing(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    actions_stubber()
    talent_partner = await create_talent_partner(
        async_session, email="missing-template@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    # Create day 2 workspace so day 3 reuses it.
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

    # Day 3 template is unused when reusing unified coding workspace.
    tasks[2].template_repo = None
    await async_session.commit()

    resp = await async_client.post(
        f"/api/tasks/{tasks[2].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )

    assert resp.status_code == 200, resp.text
