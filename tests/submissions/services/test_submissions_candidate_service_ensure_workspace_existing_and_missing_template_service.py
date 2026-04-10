from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_ensure_workspace_existing_and_missing_template(
    monkeypatch, async_session
):
    talent_partner = await create_talent_partner(async_session, email="exist@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    now = datetime.now(UTC)
    existing = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[0].id,
        template_repo_full_name=tasks[0].template_repo or "",
        repo_full_name="org/existing",
        repo_id=1,
        default_branch="main",
        base_template_sha=None,
        created_at=now,
    )

    class StubGithub:
        def __init__(self):
            self.invites: list[tuple[str, str]] = []

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            self.invites.append((repo_full_name, username))
            return {"invited": username}

    stub = StubGithub()
    ws = await svc.ensure_workspace(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        github_client=stub,
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="org",
        now=now,
    )
    assert ws.id == existing.id
    assert stub.invites == [("org/existing", "octocat")]

    bad_task = SimpleNamespace(id=99, template_repo=" ", trial_id=sim.id, type="code")
    with pytest.raises(HTTPException):
        await svc.ensure_workspace(
            async_session,
            candidate_session=cs,
            task=bad_task,
            github_client=object(),
            github_username="octocat",
            repo_prefix="pref-",
            template_default_owner="org",
            now=now,
        )
