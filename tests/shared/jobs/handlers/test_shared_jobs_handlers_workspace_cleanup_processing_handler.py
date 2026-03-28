from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.shared.jobs.handlers import (
    shared_jobs_handlers_workspace_cleanup_processing_handler as processing_handler,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    _WorkspaceCleanupRetryableError,
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
async def test_process_cleanup_target_not_expired_keeps_completed_non_pending_status(
    monkeypatch,
):
    db = _FakeDB()
    logger = _FakeLogger()
    now = datetime(2026, 3, 25, 12, 0, tzinfo=UTC)
    record = SimpleNamespace(
        id="ws-1",
        repo_full_name="org/repo",
        created_at=now,
        cleanup_status=WORKSPACE_CLEANUP_STATUS_ARCHIVED,
        cleanup_error="keep-error",
        cleaned_at=now,
        retention_expires_at=None,
        cleanup_attempted_at=None,
    )
    target = SimpleNamespace(
        record=record,
        candidate_session=SimpleNamespace(id=11, completed_at=now),
        simulation=SimpleNamespace(status="terminated"),
    )
    summary: dict[str, int] = {"processed": 0}
    config = SimpleNamespace(
        retention_days=30, cleanup_mode="archive", delete_enabled=False
    )

    async def _enforce_collaborator_revocation(*_args, **_kwargs):
        return "collaborator_already_removed"

    async def _apply_retention_cleanup(*_args, **_kwargs):
        raise AssertionError("retention cleanup should not run when not expired")

    monkeypatch.setattr(
        processing_handler, "_retention_cleanup_eligible", lambda **_kw: True
    )
    monkeypatch.setattr(processing_handler, "_retention_expired", lambda **_kw: False)

    await processing_handler._process_cleanup_target(
        db=db,
        target=target,
        now=now,
        config=config,
        github_client=object(),
        cutoff_session_ids=set(),
        summary=summary,
        job_id="job-1",
        logger=logger,
        enforce_collaborator_revocation=_enforce_collaborator_revocation,
        apply_retention_cleanup=_apply_retention_cleanup,
    )

    assert record.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert record.cleanup_error == "keep-error"
    assert summary["pending"] == 1
    assert summary["processed"] == 1
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_process_cleanup_target_retryable_error_preserves_existing_cleanup_error(
    monkeypatch,
):
    db = _FakeDB()
    logger = _FakeLogger()
    now = datetime(2026, 3, 25, 12, 0, tzinfo=UTC)
    record = SimpleNamespace(
        id="ws-2",
        repo_full_name="org/repo",
        created_at=now,
        cleanup_status="pending",
        cleanup_error="already-set",
        cleaned_at=None,
        retention_expires_at=None,
        cleanup_attempted_at=None,
    )
    target = SimpleNamespace(
        record=record,
        candidate_session=SimpleNamespace(id=12, completed_at=now),
        simulation=SimpleNamespace(status="terminated"),
    )
    summary: dict[str, int] = {"processed": 0}
    config = SimpleNamespace(
        retention_days=30, cleanup_mode="archive", delete_enabled=False
    )

    async def _enforce_collaborator_revocation(*_args, **_kwargs):
        raise _WorkspaceCleanupRetryableError(
            workspace_id="ws-2",
            repo_full_name="org/repo",
            error_code="github_status_502",
        )

    async def _apply_retention_cleanup(*_args, **_kwargs):
        return "archived"

    monkeypatch.setattr(
        processing_handler, "_retention_cleanup_eligible", lambda **_kw: True
    )
    monkeypatch.setattr(processing_handler, "_retention_expired", lambda **_kw: False)

    with pytest.raises(RuntimeError, match="github_status_502"):
        await processing_handler._process_cleanup_target(
            db=db,
            target=target,
            now=now,
            config=config,
            github_client=object(),
            cutoff_session_ids=set(),
            summary=summary,
            job_id="job-2",
            logger=logger,
            enforce_collaborator_revocation=_enforce_collaborator_revocation,
            apply_retention_cleanup=_apply_retention_cleanup,
        )

    assert record.cleanup_status == WORKSPACE_CLEANUP_STATUS_FAILED
    assert record.cleanup_error == "already-set"
    assert db.commit_calls == 1
    assert logger.warning_calls == 1
