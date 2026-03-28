from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_archive_permanent_failure_is_terminal(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=40)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=True,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            raise GithubError("forbidden", status_code=403)

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["failed"] == 1
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.cleanup_error == "github_status_403"
