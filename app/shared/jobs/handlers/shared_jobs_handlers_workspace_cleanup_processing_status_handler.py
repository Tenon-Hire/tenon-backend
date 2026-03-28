"""Application module for jobs handlers workspace cleanup processing status handler workflows."""

from __future__ import annotations

from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    WORKSPACE_CLEANUP_STATUS_FAILED,
    WORKSPACE_CLEANUP_STATUS_PENDING,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    _cleanup_is_complete,
    _normalize_repo_full_name,
    _summarize_result,
)


async def _mark_revocation_blocked(
    *, db, summary: dict[str, int], record, job_id: str | None, logger
) -> None:
    if not _cleanup_is_complete(record):
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
        if (record.access_revocation_error or "").strip():
            record.cleanup_error = record.access_revocation_error
    _summarize_result(summary, key="failed")
    logger.warning(
        "workspace_cleanup_failed",
        extra={
            "jobId": job_id,
            "repoFullName": _normalize_repo_full_name(record.repo_full_name),
            "workspaceId": str(record.id),
            "errorCode": record.access_revocation_error,
        },
    )
    summary["processed"] += 1
    await db.commit()


async def _mark_pending_active(*, db, summary: dict[str, int], record) -> None:
    if not _cleanup_is_complete(record):
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_PENDING
    if record.cleanup_status == WORKSPACE_CLEANUP_STATUS_PENDING:
        record.cleanup_error = None
    _summarize_result(summary, key="pending")
    _summarize_result(summary, key="skippedActive")
    summary["processed"] += 1
    await db.commit()


def _record_cleanup_outcome(
    *, summary: dict[str, int], cleanup_status: str, record, job_id: str | None, logger
) -> None:
    if cleanup_status == "archived":
        _summarize_result(summary, key="archived")
    elif cleanup_status in {"deleted", "deleted_repo_missing"}:
        _summarize_result(summary, key="deleted")
    elif cleanup_status == "already_cleaned":
        _summarize_result(summary, key="alreadyCleaned")
    elif cleanup_status.startswith("failed_"):
        _summarize_result(summary, key="failed")
        logger.warning(
            "workspace_cleanup_failed",
            extra={
                "jobId": job_id,
                "repoFullName": _normalize_repo_full_name(record.repo_full_name),
                "workspaceId": str(record.id),
                "errorCode": record.cleanup_error,
            },
        )
    else:
        _summarize_result(summary, key="pending")


__all__ = [
    "_mark_pending_active",
    "_mark_revocation_blocked",
    "_record_cleanup_outcome",
]
