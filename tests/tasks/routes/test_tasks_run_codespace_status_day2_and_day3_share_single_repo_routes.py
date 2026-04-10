from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_status_day2_and_day3_share_single_repo(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="status-shared-repo@sim.com"
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

    calls: dict[str, int] = {"generate": 0}

    class StubGithubClient:
        async def generate_repo_from_template(
            self,
            *,
            template_full_name: str,
            new_repo_name: str,
            owner=None,
            private=True,
        ):
            calls["generate"] += 1
            return {
                "full_name": f"{owner}/{new_repo_name}",
                "id": 800 + calls["generate"],
                "default_branch": "main",
            }

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            return {"ok": True}

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "base-sha"}}

    with override_dependencies(
        {candidate_submissions.get_github_client: lambda: StubGithubClient()}
    ):
        headers = candidate_header_factory(cs)
        day2_init = await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )
        assert day2_init.status_code == 200, day2_init.text
        day2_repo = day2_init.json()["repoFullName"]

        await create_submission(
            async_session, candidate_session=cs, task=tasks[1], content_text="day2"
        )
        await async_session.commit()

        day3_status = await async_client.get(
            f"/api/tasks/{tasks[2].id}/codespace/status",
            headers=headers,
        )

    assert day3_status.status_code == 200, day3_status.text
    assert day3_status.json()["repoFullName"] == day2_repo
    assert calls["generate"] == 1
