from __future__ import annotations

import pytest

from app.config import settings
from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_invite_preprovisions_day2_day3_workspaces(
    async_client,
    async_session,
    auth_header_factory,
    override_dependencies,
    monkeypatch,
):
    talent_partner = await create_talent_partner(async_session, email="preprov@app.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)

    day2_tasks = [t for t in tasks if t.day_index == 2]
    day3_tasks = [t for t in tasks if t.day_index == 3]
    assert day2_tasks and day3_tasks
    day2_tasks[0].type = "code"
    day3_tasks[0].type = "debug"
    await async_session.commit()
    monkeypatch.setattr(settings.github, "GITHUB_ORG", "winoe-ai-repos")
    monkeypatch.setattr(settings.github, "GITHUB_TEMPLATE_OWNER", "template-source")

    class StubGithubClient:
        def __init__(self):
            self.generated: list[tuple[str, str, str | None]] = []

        async def generate_repo_from_template(
            self, *, template_full_name, new_repo_name, owner=None, private=True
        ):
            self.generated.append((template_full_name, new_repo_name, owner))
            return {
                "owner": {"login": owner},
                "name": new_repo_name,
                "full_name": f"{owner}/{new_repo_name}",
                "id": 100 + len(self.generated),
                "default_branch": "main",
            }

        async def get_branch(self, repo_full_name, branch):
            return {"commit": {"sha": "base-sha"}}

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            return {"ok": True}

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    stub_client = StubGithubClient()

    with override_dependencies(
        {
            get_email_service: lambda: email_service,
            get_github_client: lambda: stub_client,
        }
    ):
        res = await async_client.post(
            f"/api/trials/{sim.id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers=auth_header_factory(talent_partner),
        )

    assert res.status_code == 200, res.text

    cs = (await async_session.execute(select(CandidateSession))).scalar_one()
    workspaces = (
        (
            await async_session.execute(
                select(Workspace).where(Workspace.candidate_session_id == cs.id)
            )
        )
        .scalars()
        .all()
    )
    workspace_groups = (
        (
            await async_session.execute(
                select(WorkspaceGroup).where(
                    WorkspaceGroup.candidate_session_id == cs.id
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(stub_client.generated) == 1
    expected_repo_name = f"winoe-ws-{cs.id}-coding"
    assert stub_client.generated[0] == (
        tasks[1].template_repo,
        expected_repo_name,
        "winoe-ai-repos",
    )
    assert len(workspace_groups) == 1
    assert workspace_groups[0].workspace_key == "coding"
    assert len(workspaces) == 1
    assert workspaces[0].workspace_group_id == workspace_groups[0].id
    assert workspaces[0].repo_full_name == f"winoe-ai-repos/{expected_repo_name}"
    assert workspace_groups[0].repo_full_name == f"winoe-ai-repos/{expected_repo_name}"
    assert all(ws.base_template_sha == "base-sha" for ws in workspaces)
