"""Application module for jobs handlers workspace cleanup processing handler workflows."""

from __future__ import annotations

from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_processing_status_handler import (
    _mark_pending_active,
    _mark_revocation_blocked,
    _record_cleanup_outcome,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    _REVOCATION_BLOCKING_FAILURES,
    WORKSPACE_CLEANUP_STATUS_FAILED,
    _WorkspaceCleanupRetryableError,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    _cleanup_is_complete,
    _normalize_repo_full_name,
    _retention_anchor,
    _retention_cleanup_eligible,
    _retention_expired,
    _retention_expires_at,
    _summarize_result,
    _workspace_error_code,
)


async def _process_cleanup_target(
    *,
    db,
    target,
    now,
    config,
    github_client,
    cutoff_session_ids: set[int],
    summary: dict[str, int],
    job_id: str | None,
    logger,
    enforce_collaborator_revocation,
    apply_retention_cleanup,
) -> None:
    record = target.record
    candidate_session = target.candidate_session
    simulation = target.simulation
    record.cleanup_attempted_at = now
    record.retention_expires_at = _retention_expires_at(
        _retention_anchor(record, candidate_session),
        retention_days=config.retention_days,
    )
    try:
        revoke_status = await enforce_collaborator_revocation(
            github_client,
            record=record,
            candidate_session=candidate_session,
            should_revoke=candidate_session.id in cutoff_session_ids,
            now=now,
            job_id=job_id,
            logger=logger,
        )
        if revoke_status in {"collaborator_removed", "collaborator_already_removed"}:
            _summarize_result(summary, key="revoked")
        elif revoke_status in _REVOCATION_BLOCKING_FAILURES:
            await _mark_revocation_blocked(
                db=db, summary=summary, record=record, job_id=job_id, logger=logger
            )
            return

        if not _retention_cleanup_eligible(
            candidate_session=candidate_session, simulation=simulation
        ):
            await _mark_pending_active(db=db, summary=summary, record=record)
            return

        if not _retention_expired(now=now, expires_at=record.retention_expires_at):
            if not _cleanup_is_complete(record):
                record.cleanup_status = "pending"
            if record.cleanup_status == "pending":
                record.cleanup_error = None
            _summarize_result(summary, key="pending")
        else:
            cleanup_status = await apply_retention_cleanup(
                github_client,
                record=record,
                now=now,
                cleanup_mode=config.cleanup_mode,
                delete_enabled=config.delete_enabled,
                job_id=job_id,
                logger=logger,
            )
            _record_cleanup_outcome(
                summary=summary,
                cleanup_status=cleanup_status,
                record=record,
                job_id=job_id,
                logger=logger,
            )
    except _WorkspaceCleanupRetryableError as exc:
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
        if record.cleanup_error is None:
            record.cleanup_error = exc.error_code
        await db.commit()
        logger.warning(
            "workspace_cleanup_failed",
            extra={
                "jobId": job_id,
                "repoFullName": exc.repo_full_name,
                "workspaceId": exc.workspace_id,
                "errorCode": exc.error_code,
            },
        )
        raise RuntimeError(exc.error_code) from exc
    except Exception as exc:
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
        record.cleanup_error = _workspace_error_code(exc)
        await db.commit()
        logger.warning(
            "workspace_cleanup_failed",
            extra={
                "jobId": job_id,
                "repoFullName": _normalize_repo_full_name(record.repo_full_name),
                "workspaceId": str(record.id),
                "errorCode": record.cleanup_error,
            },
        )
        raise

    summary["processed"] += 1
    await db.commit()


__all__ = ["_process_cleanup_target"]
