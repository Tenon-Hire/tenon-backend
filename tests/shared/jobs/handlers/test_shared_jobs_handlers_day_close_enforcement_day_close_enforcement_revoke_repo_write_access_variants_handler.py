from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_day_close_enforcement_revoke_repo_write_access_variants():
    class Client:
        async def remove_collaborator(self, _repo: str, username: str):
            if username == "missing":
                raise GithubError("not found", status_code=404)
            if username == "broken":
                raise GithubError("failure", status_code=500)
            return {}

    client = Client()
    with pytest.raises(
        RuntimeError, match="day_close_enforcement_missing_github_username"
    ):
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username=None,
            candidate_session_id=1,
            day_index=2,
        )
    assert (
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username="missing",
            candidate_session_id=1,
            day_index=2,
        )
        == "collaborator_not_found"
    )
    assert (
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username="octocat",
            candidate_session_id=1,
            day_index=2,
        )
        == "collaborator_removed"
    )
    with pytest.raises(GithubError):
        await enforcement_handler._revoke_repo_write_access(
            client,
            repo_full_name="org/repo",
            github_username="broken",
            candidate_session_id=1,
            day_index=2,
        )
