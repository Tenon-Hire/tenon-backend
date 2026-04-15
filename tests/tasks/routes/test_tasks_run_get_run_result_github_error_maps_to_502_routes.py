from __future__ import annotations

import pytest

from app.config import settings
from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_get_run_result_github_error_maps_to_502(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="run-fetch-err@sim.com"
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

    class ErrorRunner:
        async def fetch_run_result(self, **_kwargs):
            raise GithubError("nope")

    class StubGithubClient:
        async def generate_repo_from_template(
            self,
            *,
            template_full_name: str,
            new_repo_name: str,
            owner=None,
            private=True,
        ):
            destination_owner = settings.github.GITHUB_ORG
            return {
                "owner": {"login": destination_owner},
                "name": new_repo_name,
                "full_name": f"{destination_owner}/{new_repo_name}",
                "id": 1,
                "default_branch": "main",
            }

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            return {"ok": True}

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "base"}}

        async def get_compare(self, repo_full_name: str, base: str, head: str):
            return {}

    with override_dependencies(
        {
            candidate_submissions.get_actions_runner: lambda: ErrorRunner(),
            candidate_submissions.get_github_client: lambda: StubGithubClient(),
        }
    ):
        headers = candidate_header_factory(cs)
        await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )
        resp = await async_client.get(
            f"/api/tasks/{tasks[1].id}/run/9999",
            headers=headers,
        )

    assert resp.status_code == 502
