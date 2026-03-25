from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_already_cleaned_is_noop(async_session, monkeypatch):
    now = datetime.now(UTC).replace(microsecond=0)
    created_at = now - timedelta(days=40)
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
    cleanup_record = await _load_cleanup_record(
        async_session,
        workspace_id=workspace_id,
        workspace_group_id=workspace_group_id,
    )
    cleanup_record.cleanup_status = WORKSPACE_CLEANUP_STATUS_ARCHIVED
    cleanup_record.cleaned_at = now - timedelta(days=1)
    await async_session.commit()

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
    assert result["alreadyCleaned"] == 1
    assert calls == {"archive": 0, "delete": 0}
