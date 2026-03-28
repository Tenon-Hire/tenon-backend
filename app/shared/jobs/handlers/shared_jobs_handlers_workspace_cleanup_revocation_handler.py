"""Application module for jobs handlers workspace cleanup revocation handler workflows."""

from __future__ import annotations

from datetime import datetime

from app.integrations.github import GithubError
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    WorkspaceCleanupRecord,
    _WorkspaceCleanupRetryableError,
)
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    _is_transient_github_error,
    _normalize_repo_full_name,
    _workspace_error_code,
)


async def _enforce_collaborator_revocation(
    github_client,
    *,
    record: WorkspaceCleanupRecord,
    candidate_session,
    should_revoke: bool,
    now: datetime,
    job_id: str | None,
    logger,
) -> str:
    if not should_revoke:
        return "not_required"
    if (
        record.access_revoked_at is not None
        and not (record.access_revocation_error or "").strip()
    ):
        return "already_revoked"

    repo_full_name = _normalize_repo_full_name(record.repo_full_name)
    if repo_full_name is None:
        record.access_revocation_error = "missing_repo_full_name"
        return "missing_repo"

    github_username = (candidate_session.github_username or "").strip()
    if not github_username:
        record.access_revocation_error = "missing_github_username"
        return "missing_github_username"

    try:
        await github_client.remove_collaborator(repo_full_name, github_username)
        record.access_revoked_at = now
        record.access_revocation_error = None
        logger.info(
            "workspace_cleanup_collaborator_removed",
            extra={
                "jobId": job_id,
                "repoFullName": repo_full_name,
                "candidateSessionId": candidate_session.id,
            },
        )
        return "collaborator_removed"
    except GithubError as exc:
        if exc.status_code == 404:
            record.access_revoked_at = now
            record.access_revocation_error = None
            return "collaborator_already_removed"
        error_code = _workspace_error_code(exc)
        record.access_revocation_error = error_code
        if _is_transient_github_error(exc):
            raise _WorkspaceCleanupRetryableError(
                workspace_id=str(record.id),
                repo_full_name=repo_full_name,
                error_code=error_code,
            ) from exc
        return "collaborator_revocation_failed"


__all__ = ["_enforce_collaborator_revocation"]
