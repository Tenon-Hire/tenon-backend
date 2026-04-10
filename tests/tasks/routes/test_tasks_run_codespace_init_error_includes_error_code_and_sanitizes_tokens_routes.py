from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_error_includes_error_code_and_sanitizes_tokens(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(async_session, email="secure@sim.com")
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
        async def generate_repo_from_template(self, **_kwargs):
            raise GithubError(
                "Authorization: Bearer eyJFAKE.JWT.TOKEN ghp_FAKEGITHUBTOKEN123",
                status_code=403,
            )

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
    body = resp.json()
    assert body["errorCode"] == "GITHUB_PERMISSION_DENIED"
    combined = json.dumps(body)
    for forbidden in ["Authorization", "Bearer", "ghp_", "eyJ", "Traceback"]:
        assert forbidden not in combined
