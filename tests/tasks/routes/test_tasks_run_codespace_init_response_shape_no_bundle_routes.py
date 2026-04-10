from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_response_shape_no_bundle(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="init-shape@sim.com"
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

    class StubGithubClient:
        async def generate_repo_from_template(
            self,
            *,
            template_full_name: str,
            new_repo_name: str,
            owner=None,
            private=True,
        ):
            return {
                "full_name": "org/init-shape-repo",
                "id": 909,
                "default_branch": "main",
            }

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            return {"ok": True}

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "base-sha-shape"}}

    with override_dependencies(
        {candidate_submissions.get_github_client: lambda: StubGithubClient()}
    ):
        headers = candidate_header_factory(cs)
        resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "repoFullName": "org/init-shape-repo",
        "codespaceUrl": "https://codespaces.new/org/init-shape-repo?quickstart=1",
        "codespaceState": None,
        "defaultBranch": "main",
        "baseTemplateSha": "base-sha-shape",
        "precommitSha": None,
        "workspaceId": body["workspaceId"],
    }
    assert isinstance(body["workspaceId"], str)
    assert body["workspaceId"]

    workspace = await workspace_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[1].id,
    )
    assert workspace is not None
    assert workspace.precommit_sha is None
    assert json.loads(workspace.precommit_details_json or "{}") == {
        "reason": "bundle_not_found",
        "scenarioVersionId": cs.scenario_version_id,
        "state": "no_bundle",
        "templateKey": sim.template_key,
    }
