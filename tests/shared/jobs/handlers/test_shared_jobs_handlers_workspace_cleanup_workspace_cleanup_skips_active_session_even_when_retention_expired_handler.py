from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_skips_active_session_even_when_retention_expired(
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
        session_status="in_progress",
        completed_at=None,
        use_group=True,
    )

    calls = {"archive": 0, "delete": 0}

    class StubGithubClient:
        async def remove_collaborator(self, *_args, **_kwargs):
            return {}

        async def archive_repo(self, *_args, **_kwargs):
            calls["archive"] += 1
            return {"archived": True}

        async def delete_repo(self, *_args, **_kwargs):
            calls["delete"] += 1
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    assert result["status"] == "completed"
    assert result["pending"] == 1
    assert result["skippedActive"] == 1
    assert calls == {"archive": 0, "delete": 0}
    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_PENDING
    assert stored.cleaned_at is None
