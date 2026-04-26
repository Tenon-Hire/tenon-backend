from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_invalid_token_maps_to_specific_error(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(async_session, email="token@test.com")
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

    class ErrorGithubClient:
        async def create_empty_repo(self, **_kwargs):
            raise GithubError("bad token", status_code=401)

    with override_dependencies(
        {candidate_submissions.get_github_client: lambda: ErrorGithubClient()}
    ):
        headers = candidate_header_factory(cs)
        resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )

    assert resp.status_code == 502
    assert resp.json()["errorCode"] == "GITHUB_TOKEN_INVALID"
