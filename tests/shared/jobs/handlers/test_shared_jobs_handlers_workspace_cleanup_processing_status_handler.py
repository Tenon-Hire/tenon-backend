from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.jobs.handlers import (
    shared_jobs_handlers_workspace_cleanup_processing_status_handler as status_handler,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_workspace_cleanup_status_constants import (
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    WORKSPACE_CLEANUP_STATUS_FAILED,
)


class _FakeDB:
    def __init__(self) -> None:
        self.commit_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1


class _FakeLogger:
    def __init__(self) -> None:
        self.warning_calls = 0

    def warning(self, *_args, **_kwargs) -> None:
        self.warning_calls += 1


@pytest.mark.asyncio
async def test_mark_revocation_blocked_when_cleanup_already_complete_skips_status_mutation():
    db = _FakeDB()
    summary: dict[str, int] = {"processed": 0}
    logger = _FakeLogger()
    record = SimpleNamespace(
        id="ws-1",
        repo_full_name="org/repo",
        cleanup_status=WORKSPACE_CLEANUP_STATUS_ARCHIVED,
        cleaned_at=object(),
        cleanup_error="keep-existing",
        access_revocation_error="revocation-error",
    )

    await status_handler._mark_revocation_blocked(
        db=db,
        summary=summary,
        record=record,
        job_id="job-1",
        logger=logger,
    )

    assert record.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert record.cleanup_error == "keep-existing"
    assert summary["failed"] == 1
    assert summary["processed"] == 1
    assert db.commit_calls == 1
    assert logger.warning_calls == 1


@pytest.mark.asyncio
async def test_mark_revocation_blocked_sets_failed_even_with_blank_revocation_error():
    db = _FakeDB()
    summary: dict[str, int] = {"processed": 0}
    logger = _FakeLogger()
    record = SimpleNamespace(
        id="ws-2",
        repo_full_name="org/repo",
        cleanup_status="pending",
        cleaned_at=None,
        cleanup_error=None,
        access_revocation_error="   ",
    )

    await status_handler._mark_revocation_blocked(
        db=db,
        summary=summary,
        record=record,
        job_id="job-2",
        logger=logger,
    )

    assert record.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert record.cleanup_error is None
    assert summary["failed"] == 1
    assert summary["processed"] == 1
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_mark_pending_active_keeps_non_pending_complete_status_unchanged():
    db = _FakeDB()
    summary: dict[str, int] = {"processed": 0}
    record = SimpleNamespace(
        cleanup_status=WORKSPACE_CLEANUP_STATUS_ARCHIVED,
        cleaned_at=object(),
        cleanup_error="keep-error",
    )

    await status_handler._mark_pending_active(db=db, summary=summary, record=record)

    assert record.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert record.cleanup_error == "keep-error"
    assert summary["pending"] == 1
    assert summary["skippedActive"] == 1
    assert summary["processed"] == 1
    assert db.commit_calls == 1
