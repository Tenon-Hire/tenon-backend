from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_unexpected_exception_marks_failed_and_reraises(
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
        use_group=True,
    )

    async def _raise_unexpected(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler,
        "_enforce_collaborator_revocation",
        _raise_unexpected,
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

    with pytest.raises(ValueError, match="boom"):
        await cleanup_handler.handle_workspace_cleanup({"companyId": company_id})

    stored = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    assert stored.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert stored.cleanup_error == "ValueError"
