from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_ensure_workspace_creates_repo(async_session):
    talent_partner = await create_talent_partner(async_session, email="ws@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")

    class StubGithubClient:
        async def generate_repo_from_template(self, **_kw):
            return {"full_name": "org/new-repo", "id": 5, "default_branch": "main"}

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            return {"invited": username}

        async def get_branch(self, repo_full_name, branch):
            return {"commit": {"sha": "base-sha"}}

    ws = await svc.ensure_workspace(
        async_session,
        candidate_session=cs,
        task=tasks[1],
        github_client=StubGithubClient(),
        github_username="octocat",
        repo_prefix="prefix-",
        template_default_owner="org",
        now=datetime.now(UTC),
    )
    assert ws.repo_full_name == "org/new-repo"
    assert ws.base_template_sha == "base-sha"
