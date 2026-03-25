from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_collaborator_already_removed_is_noop(
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
            raise GithubError("not found", status_code=404)

        async def archive_repo(self, *_args, **_kwargs):
            raise AssertionError(
                "archive_repo should not run for non-expired workspace"
            )

        async def delete_repo(self, *_args, **_kwargs):
            raise AssertionError("delete_repo should not run for non-expired workspace")

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["revoked"] == 1
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.access_revoked_at is not None
    assert stored.access_revocation_error is None
