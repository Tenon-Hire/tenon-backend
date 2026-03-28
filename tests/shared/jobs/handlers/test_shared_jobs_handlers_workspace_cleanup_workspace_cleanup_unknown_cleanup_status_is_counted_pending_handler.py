from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_unknown_cleanup_status_is_counted_pending(
    async_session,
    monkeypatch,
):
    created_at = datetime.now(UTC) - timedelta(days=60)
    (
        company_id,
        _candidate_session_id,
        _workspace_id,
        _workspace_group_id,
    ) = await _prepare_workspace(
        async_session,
        created_at=created_at,
        use_group=False,
    )

    async def _fake_apply_retention_cleanup(*_args, **_kwargs):
        return "unknown_status"

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler,
        "_apply_retention_cleanup",
        _fake_apply_retention_cleanup,
    )

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            return {}

    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})
    assert result["pending"] == 1
