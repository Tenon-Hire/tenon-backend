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
    await async_session.commit()

    class GithubClientStub:
        async def generate_repo_from_template(self, **_kwargs):
            raise AssertionError("generate_repo_from_template should not be called")

        async def create_empty_repo(self, **_kwargs):
            raise AssertionError("create_empty_repo should not be called")

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")

    with override_dependencies(
        {
            get_email_service: lambda: email_service,
            get_github_client: lambda: GithubClientStub(),
        }
    ):
        res = await async_client.post(
            f"/api/trials/{trial_id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers={"x-dev-user-email": talent_partner_email},
        )
    assert res.status_code == 200, res.text
    assert res.json()["outcome"] == "created"

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
    assert existing[0].github_username is None

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
    assert workspace_groups == []
    assert workspaces == []
