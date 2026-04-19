from __future__ import annotations

import pytest

from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_invite_github_failure_does_not_persist_failed_candidate_session(
    async_client, async_session, auth_header_factory, override_dependencies, monkeypatch
):
    talent_partner = await create_talent_partner(async_session, email="fail@app.com")
    talent_partner_email = talent_partner.email
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    trial_id = sim.id
    day2_task = next(t for t in tasks if t.day_index == 2)
    day3_task = next(t for t in tasks if t.day_index == 3)
    day2_task.type = "code"
    day3_task.type = "code"
    day2_task_id = day2_task.id
    day3_task_id = day3_task.id
    await async_session.commit()

    class FailingGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            raise AssertionError("generate_repo_from_template should not be called")

        async def create_empty_repo(self, **_kw):
            raise GithubError("boom")

        async def get_file_contents(self, *_a, **_k):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, *_a, **_k):
            raise GithubError("missing", status_code=404)

        async def create_tree(self, *_a, **_k):
            return {"sha": "tree-sha"}

        async def create_commit(self, *_a, **_k):
            return {"sha": "commit-sha"}

        async def create_ref(self, *_a, **_k):
            return {"ref": "refs/heads/main", "sha": "commit-sha"}

        async def add_collaborator(self, *_a, **_k):
            return {"ok": True}

    class SuccessGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            raise AssertionError("generate_repo_from_template should not be called")

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "full_name": f"{owner}/{repo_name}",
                "id": 200,
                "default_branch": default_branch,
                "owner": {"login": owner},
                "name": repo_name,
            }

        async def get_file_contents(self, *_a, **_k):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, repo_full_name, branch):
            raise GithubError("missing", status_code=404)

        async def create_tree(self, *_a, **_k):
            return {"sha": "tree-sha"}

        async def create_commit(self, *_a, **_k):
            return {"sha": "commit-sha"}

        async def create_ref(self, *_a, **_k):
            return {"ref": "refs/heads/main", "sha": "commit-sha"}

        async def create_codespace(
            self,
            repo_full_name,
            *,
            ref=None,
            devcontainer_path=None,
            machine=None,
            location=None,
        ):
            return {
                "name": f"codespace-{repo_full_name.split('/', 1)[-1]}",
                "state": "available",
                "web_url": "https://codespace.example",
            }

        async def add_collaborator(self, *_a, **_k):
            return {"ok": True}

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")

    with override_dependencies(
        {
            get_email_service: lambda: email_service,
            get_github_client: lambda: FailingGithubClient(),
        }
    ):
        res = await async_client.post(
            f"/api/trials/{trial_id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers={"x-dev-user-email": talent_partner_email},
        )
    assert res.status_code == 502, res.text

    existing = (
        (
            await async_session.execute(
                select(CandidateSession).where(
                    CandidateSession.invite_email == "jane@example.com"
                )
            )
        )
        .scalars()
        .all()
    )
    assert existing == []

    with override_dependencies(
        {
            get_email_service: lambda: email_service,
            get_github_client: lambda: SuccessGithubClient(),
        }
    ):
        res = await async_client.post(
            f"/api/trials/{trial_id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers={"x-dev-user-email": talent_partner_email},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["outcome"] == "created"

    created = (
        (
            await async_session.execute(
                select(CandidateSession).where(
                    CandidateSession.invite_email == "jane@example.com"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(created) == 1
    assert body["candidateSessionId"] == created[0].id

    workspaces = (
        (
            await async_session.execute(
                select(Workspace).where(Workspace.candidate_session_id == created[0].id)
            )
        )
        .scalars()
        .all()
    )
    workspace_groups = (
        (
            await async_session.execute(
                select(WorkspaceGroup).where(
                    WorkspaceGroup.candidate_session_id == created[0].id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(workspace_groups) == 1
    assert workspace_groups[0].workspace_key == "coding"
    assert len(workspaces) == 1
    assert workspaces[0].task_id in {day2_task_id, day3_task_id}
