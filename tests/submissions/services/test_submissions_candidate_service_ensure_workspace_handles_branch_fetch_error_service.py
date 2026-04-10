from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_ensure_workspace_handles_branch_fetch_error(async_session):
    talent_partner = await create_talent_partner(async_session, email="branch@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")

    class StubGithub:
        async def generate_repo_from_template(self, **_kw):
            return {"full_name": "org/repo", "default_branch": "main", "id": 1}

        async def get_branch(self, *_a, **_k):
            raise GithubError("no branch")

        async def add_collaborator(self, *_a, **_k):
            return None

    ws = await svc.ensure_workspace(
        async_session,
        candidate_session=cs,
        task=tasks[1],
        github_client=StubGithub(),
        github_username="",
        repo_prefix="pref-",
        template_default_owner="org",
        now=datetime.now(UTC),
    )
    assert ws.base_template_sha is None
