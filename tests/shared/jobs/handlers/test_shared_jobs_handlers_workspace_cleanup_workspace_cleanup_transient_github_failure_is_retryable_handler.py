from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_transient_github_failure_is_retryable(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC)
    (
        company_id,
        _candidate_session_id,
        workspace_id,
        workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        with_cutoff=True,
        use_group=True,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            raise GithubError("temporary failure", status_code=502)

        async def archive_repo(self, *_args, **_kwargs):
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    with pytest.raises(RuntimeError, match="github_status_502"):
        await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_attempted_at is not None
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.access_revocation_error == "github_status_502"
