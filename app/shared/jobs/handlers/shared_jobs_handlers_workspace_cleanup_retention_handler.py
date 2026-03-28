"""Application module for jobs handlers workspace cleanup retention handler workflows."""

from __future__ import annotations

from datetime import datetime

from app.integrations.github import GithubError
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    WORKSPACE_CLEANUP_STATUS_DELETED,
    WORKSPACE_CLEANUP_STATUS_FAILED,
    WorkspaceCleanupRecord,
    _WorkspaceCleanupRetryableError,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    _cleanup_is_complete,
    _is_transient_github_error,
    _normalize_repo_full_name,
    _workspace_error_code,
)


async def _apply_retention_cleanup(
    github_client,
    *,
    record: WorkspaceCleanupRecord,
    now: datetime,
    cleanup_mode: str,
    delete_enabled: bool,
    job_id: str | None,
    logger,
) -> str:
    if _cleanup_is_complete(record):
        return "already_cleaned"

    repo_full_name = _normalize_repo_full_name(record.repo_full_name)
    if repo_full_name is None:
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
        record.cleanup_error = "missing_repo_full_name"
        return "failed_missing_repo"
    template_repo_full_name = _normalize_repo_full_name(record.template_repo_full_name)
    if template_repo_full_name and template_repo_full_name == repo_full_name:
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
        record.cleanup_error = "protected_template_repo_match"
        return "failed_protected_template_repo"

    if cleanup_mode == "delete":
        if not delete_enabled:
            record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
            record.cleanup_error = "delete_mode_disabled"
            return "failed_delete_disabled"
        repo_missing = False
        try:
            await github_client.delete_repo(repo_full_name)
        except GithubError as exc:
            if exc.status_code == 404:
                repo_missing = True
            else:
                record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
                record.cleanup_error = _workspace_error_code(exc)
                if _is_transient_github_error(exc):
                    raise _WorkspaceCleanupRetryableError(
                        workspace_id=str(record.id),
                        repo_full_name=repo_full_name,
                        error_code=record.cleanup_error,
                    ) from exc
                return "failed_delete_permanent"
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_DELETED
        record.cleaned_at = now
        record.cleanup_error = None
        logger.info(
            "workspace_cleanup_repo_deleted",
            extra={
                "jobId": job_id,
                "repoFullName": repo_full_name,
                "workspaceId": str(record.id),
            },
        )
        return "deleted_repo_missing" if repo_missing else "deleted"

    try:
        await github_client.archive_repo(repo_full_name)
    except GithubError as exc:
        if exc.status_code == 404:
            record.cleanup_status = WORKSPACE_CLEANUP_STATUS_DELETED
            record.cleaned_at = now
            record.cleanup_error = None
            logger.info(
                "workspace_cleanup_repo_deleted",
                extra={
                    "jobId": job_id,
                    "repoFullName": repo_full_name,
                    "workspaceId": str(record.id),
                },
            )
            return "deleted_repo_missing"
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
        record.cleanup_error = _workspace_error_code(exc)
        if _is_transient_github_error(exc):
            raise _WorkspaceCleanupRetryableError(
                workspace_id=str(record.id),
                repo_full_name=repo_full_name,
                error_code=record.cleanup_error,
            ) from exc
        return "failed_archive_permanent"

    record.cleanup_status = WORKSPACE_CLEANUP_STATUS_ARCHIVED
    record.cleaned_at = now
    record.cleanup_error = None
    logger.info(
        "workspace_cleanup_repo_archived",
        extra={
            "jobId": job_id,
            "repoFullName": repo_full_name,
            "workspaceId": str(record.id),
        },
    )
    return "archived"


__all__ = ["_apply_retention_cleanup"]
