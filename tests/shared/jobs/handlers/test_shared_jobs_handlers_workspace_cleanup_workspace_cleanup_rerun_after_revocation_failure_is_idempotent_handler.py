from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_rerun_after_revocation_failure_is_idempotent(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=60)
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

    class FlakyGithubClient:
        def __init__(self):
            self.remove_calls = 0
            self.archive_calls = 0

        async def remove_collaborator(self, *_args, **_kwargs):
            self.remove_calls += 1
            if self.remove_calls == 1:
                raise GithubError("forbidden", status_code=403)
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            self.archive_calls += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    github_client = FlakyGithubClient()
    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(cleanup_handler, "get_github_client", lambda: github_client)

    first = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})
    second = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert first["failed"] == 1
    assert second["archived"] == 1
    assert github_client.remove_calls == 2
    assert github_client.archive_calls == 1

    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert stored.access_revocation_error is None
    assert stored.cleanup_error is None
