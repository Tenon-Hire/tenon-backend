from __future__ import annotations

import pytest

from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_invite_github_failure_reuses_candidate_session(
    async_client, async_session, auth_header_factory, override_dependencies, monkeypatch
):
    talent_partner = await create_talent_partner(async_session, email="fail@app.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    day2_task = next(t for t in tasks if t.day_index == 2)
    day3_task = next(t for t in tasks if t.day_index == 3)
    day2_task.type = "code"
    day3_task.type = "debug"
    day2_task_id = day2_task.id
    day3_task_id = day3_task.id
    await async_session.commit()

    class FailingGithubClient:
        async def generate_repo_from_template(self, **_kw):
            raise GithubError("boom")

        async def get_branch(self, *_a, **_k):
            return {"commit": {"sha": "base-sha"}}

        async def add_collaborator(self, *_a, **_k):
            return {"ok": True}

    class SuccessGithubClient:
        async def generate_repo_from_template(
            self, *, template_full_name, new_repo_name, owner=None, private=True
        ):
            return {
                "full_name": f"{owner}/{new_repo_name}",
                "id": 200,
                "default_branch": "main",
            }

        async def get_branch(self, repo_full_name, branch):
            return {"commit": {"sha": "base-sha"}}

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
            f"/api/trials/{sim.id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers=auth_header_factory(talent_partner),
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
    assert len(existing) == 1

    with override_dependencies(
        {
            get_email_service: lambda: email_service,
            get_github_client: lambda: SuccessGithubClient(),
        }
    ):
        res = await async_client.post(
            f"/api/trials/{sim.id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers=auth_header_factory(talent_partner),
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["candidateSessionId"] == existing[0].id
    assert body["outcome"] == "resent"

    workspaces = (
        (
            await async_session.execute(
                select(Workspace).where(
                    Workspace.candidate_session_id == existing[0].id
                )
            )
        )
        .scalars()
        .all()
    )
    workspace_groups = (
        (
            await async_session.execute(
                select(WorkspaceGroup).where(
                    WorkspaceGroup.candidate_session_id == existing[0].id
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
