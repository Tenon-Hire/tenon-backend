from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_ensure_workspace_reuses_existing(async_session):
    talent_partner = await create_talent_partner(async_session, email="reuse@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    task = tasks[1]

    existing = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=task.id,
        template_repo_full_name=task.template_repo,
        repo_full_name="owner/repo",
        repo_id=123,
        default_branch="main",
        base_template_sha="abc",
        created_at=datetime.now(UTC),
    )

    calls = []

    class DummyGithub:
        async def add_collaborator(self, repo_full_name, username):
            calls.append((repo_full_name, username))

        async def generate_repo_from_template(self, *a, **k):
            raise AssertionError("should not generate new repo")

    ws = await svc.ensure_workspace(
        async_session,
        candidate_session=cs,
        task=task,
        github_client=DummyGithub(),
        github_username="octocat",
        repo_prefix="pref-",
        template_default_owner="owner",
        now=datetime.now(UTC),
    )

    assert ws.id == existing.id
    assert calls == [("owner/repo", "octocat")]
