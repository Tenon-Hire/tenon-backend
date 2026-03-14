from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.api.dependencies.github_native import get_github_client
from app.core.db import async_session_maker
from app.core.settings import settings
from app.domains import (
    CandidateDayAudit,
    CandidateSession,
    Simulation,
    Workspace,
    WorkspaceGroup,
)
from app.integrations.github import GithubError
from app.repositories.github_native.workspaces.models import (
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    WORKSPACE_CLEANUP_STATUS_DELETED,
    WORKSPACE_CLEANUP_STATUS_FAILED,
    WORKSPACE_CLEANUP_STATUS_PENDING,
    WORKSPACE_CLEANUP_TERMINAL_STATUSES,
)
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED
from app.services.submissions.workspace_cleanup_jobs import WORKSPACE_CLEANUP_JOB_TYPE

logger = logging.getLogger(__name__)

_TRANSIENT_GITHUB_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
_SESSION_TERMINAL_STATUSES = {"completed", "expired"}
_SIMULATION_TERMINAL_STATUSES = {SIMULATION_STATUS_TERMINATED}
_REVOCATION_BLOCKING_FAILURES = {
    "missing_repo",
    "missing_github_username",
    "collaborator_revocation_failed",
}

WorkspaceCleanupRecord = Workspace | WorkspaceGroup


@dataclass(slots=True, frozen=True)
class _WorkspaceCleanupConfig:
    retention_days: int
    cleanup_mode: str
    delete_enabled: bool


@dataclass(slots=True)
class _WorkspaceCleanupTarget:
    record: WorkspaceCleanupRecord
    candidate_session: CandidateSession
    simulation: Simulation


class _WorkspaceCleanupRetryableError(Exception):
    def __init__(
        self,
        *,
        workspace_id: str,
        repo_full_name: str | None,
        error_code: str,
    ) -> None:
        super().__init__(error_code)
        self.workspace_id = workspace_id
        self.repo_full_name = repo_full_name
        self.error_code = error_code


def _parse_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _normalize_repo_full_name(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _cleanup_is_complete(record: WorkspaceCleanupRecord) -> bool:
    return (
        record.cleanup_status in WORKSPACE_CLEANUP_TERMINAL_STATUSES
        and record.cleaned_at is not None
    )


def _workspace_error_code(exc: Exception) -> str:
    if isinstance(exc, GithubError):
        if exc.status_code is None:
            return "github_request_failed"
        return f"github_status_{exc.status_code}"
    return type(exc).__name__


def _is_transient_github_error(exc: GithubError) -> bool:
    status = exc.status_code
    if status is None:
        return True
    return status in _TRANSIENT_GITHUB_STATUS_CODES or status >= 500


def _resolve_cleanup_config() -> _WorkspaceCleanupConfig:
    cfg = settings.github
    return _WorkspaceCleanupConfig(
        retention_days=int(cfg.WORKSPACE_RETENTION_DAYS),
        cleanup_mode=str(cfg.WORKSPACE_CLEANUP_MODE).strip().lower(),
        delete_enabled=bool(cfg.WORKSPACE_DELETE_ENABLED),
    )


def _retention_anchor(
    record: WorkspaceCleanupRecord,
    candidate_session: CandidateSession,
) -> datetime:
    # Retention anchor: prefer candidate completion (stable business completion),
    # fallback to repo creation when completion is not available.
    if candidate_session.completed_at is not None:
        return _normalize_datetime(candidate_session.completed_at)
    return _normalize_datetime(record.created_at)


def _retention_expires_at(anchor: datetime, *, retention_days: int) -> datetime:
    return anchor + timedelta(days=retention_days)


def _retention_expired(*, now: datetime, expires_at: datetime) -> bool:
    return now > expires_at


def _retention_cleanup_eligible(
    *,
    candidate_session: CandidateSession,
    simulation: Simulation,
) -> bool:
    session_status = (candidate_session.status or "").strip().lower()
    simulation_status = (simulation.status or "").strip().lower()
    if candidate_session.completed_at is not None:
        return True
    if session_status in _SESSION_TERMINAL_STATUSES:
        return True
    return simulation_status in _SIMULATION_TERMINAL_STATUSES


def _cleanup_target_repo_key(
    *,
    candidate_session_id: int,
    repo_full_name: str | None,
    fallback_id: str,
) -> tuple[int, str]:
    normalized_repo = _normalize_repo_full_name(repo_full_name)
    if normalized_repo is not None:
        return (candidate_session_id, normalized_repo.lower())
    return (candidate_session_id, f"id:{fallback_id}")


async def _list_company_cleanup_targets(
    db,
    *,
    company_id: int,
) -> list[_WorkspaceCleanupTarget]:
    grouped_rows = (
        await db.execute(
            select(WorkspaceGroup, CandidateSession, Simulation)
            .join(
                CandidateSession,
                CandidateSession.id == WorkspaceGroup.candidate_session_id,
            )
            .join(Simulation, Simulation.id == CandidateSession.simulation_id)
            .where(Simulation.company_id == company_id)
            .order_by(WorkspaceGroup.created_at.asc(), WorkspaceGroup.id.asc())
        )
    ).all()

    legacy_rows = (
        await db.execute(
            select(Workspace, CandidateSession, Simulation)
            .join(
                CandidateSession,
                CandidateSession.id == Workspace.candidate_session_id,
            )
            .join(Simulation, Simulation.id == CandidateSession.simulation_id)
            .where(
                Simulation.company_id == company_id,
                Workspace.workspace_group_id.is_(None),
            )
            .order_by(Workspace.created_at.asc(), Workspace.id.asc())
        )
    ).all()

    targets: list[_WorkspaceCleanupTarget] = []
    seen_repo_keys: set[tuple[int, str]] = set()

    for group, candidate_session, simulation in grouped_rows:
        repo_key = _cleanup_target_repo_key(
            candidate_session_id=candidate_session.id,
            repo_full_name=group.repo_full_name,
            fallback_id=f"workspace_group:{group.id}",
        )
        if repo_key in seen_repo_keys:
            continue
        seen_repo_keys.add(repo_key)
        targets.append(
            _WorkspaceCleanupTarget(
                record=group,
                candidate_session=candidate_session,
                simulation=simulation,
            )
        )

    for workspace, candidate_session, simulation in legacy_rows:
        repo_key = _cleanup_target_repo_key(
            candidate_session_id=candidate_session.id,
            repo_full_name=workspace.repo_full_name,
            fallback_id=f"workspace:{workspace.id}",
        )
        if repo_key in seen_repo_keys:
            continue
        seen_repo_keys.add(repo_key)
        targets.append(
            _WorkspaceCleanupTarget(
                record=workspace,
                candidate_session=candidate_session,
                simulation=simulation,
            )
        )

    targets.sort(
        key=lambda target: (
            _normalize_datetime(target.record.created_at),
            str(target.record.id),
        )
    )
    return targets


async def _load_sessions_with_cutoff(
    db,
    *,
    candidate_session_ids: list[int],
) -> set[int]:
    if not candidate_session_ids:
        return set()
    rows = (
        await db.execute(
            select(CandidateDayAudit.candidate_session_id)
            .where(CandidateDayAudit.candidate_session_id.in_(candidate_session_ids))
            .distinct()
        )
    ).scalars()
    return {int(value) for value in rows}


async def _enforce_collaborator_revocation(
    github_client,
    *,
    record: WorkspaceCleanupRecord,
    candidate_session: CandidateSession,
    should_revoke: bool,
    now: datetime,
    job_id: str | None,
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


async def _apply_retention_cleanup(
    github_client,
    *,
    record: WorkspaceCleanupRecord,
    now: datetime,
    cleanup_mode: str,
    delete_enabled: bool,
    job_id: str | None,
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
        try:
            await github_client.delete_repo(repo_full_name)
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
            error_code = _workspace_error_code(exc)
            record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
            record.cleanup_error = error_code
            if _is_transient_github_error(exc):
                raise _WorkspaceCleanupRetryableError(
                    workspace_id=str(record.id),
                    repo_full_name=repo_full_name,
                    error_code=error_code,
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
        return "deleted"

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
        error_code = _workspace_error_code(exc)
        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
        record.cleanup_error = error_code
        if _is_transient_github_error(exc):
            raise _WorkspaceCleanupRetryableError(
                workspace_id=str(record.id),
                repo_full_name=repo_full_name,
                error_code=error_code,
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


def _summarize_result(summary: dict[str, int], *, key: str) -> None:
    summary[key] = summary.get(key, 0) + 1


async def handle_workspace_cleanup(payload_json: dict[str, Any]) -> dict[str, Any]:
    company_id = _parse_positive_int(payload_json.get("companyId"))
    if company_id is None:
        return {"status": "skipped_invalid_payload", "companyId": company_id}

    config = _resolve_cleanup_config()
    now = datetime.now(UTC)
    job_id_raw = payload_json.get("jobId")
    job_id = str(job_id_raw).strip() if isinstance(job_id_raw, str) else None
    github_client = get_github_client()

    summary: dict[str, int] = {
        "candidateCount": 0,
        "processed": 0,
        "revoked": 0,
        "archived": 0,
        "deleted": 0,
        "failed": 0,
        "pending": 0,
        "alreadyCleaned": 0,
        "skippedActive": 0,
    }

    async with async_session_maker() as db:
        targets = await _list_company_cleanup_targets(db, company_id=company_id)
        summary["candidateCount"] = len(targets)
        logger.info(
            "workspace_cleanup_started",
            extra={
                "jobId": job_id,
                "companyId": company_id,
                "countCandidates": summary["candidateCount"],
            },
        )
        candidate_session_ids = sorted(
            {target.candidate_session.id for target in targets}
        )
        cutoff_session_ids = await _load_sessions_with_cutoff(
            db,
            candidate_session_ids=candidate_session_ids,
        )

        for target in targets:
            record = target.record
            candidate_session = target.candidate_session
            simulation = target.simulation

            record.cleanup_attempted_at = now
            retention_anchor = _retention_anchor(record, candidate_session)
            retention_expires_at = _retention_expires_at(
                retention_anchor,
                retention_days=config.retention_days,
            )
            record.retention_expires_at = retention_expires_at

            try:
                revocation_required = candidate_session.id in cutoff_session_ids
                revoke_status = await _enforce_collaborator_revocation(
                    github_client,
                    record=record,
                    candidate_session=candidate_session,
                    should_revoke=revocation_required,
                    now=now,
                    job_id=job_id,
                )
                if revoke_status in {
                    "collaborator_removed",
                    "collaborator_already_removed",
                }:
                    _summarize_result(summary, key="revoked")
                elif revoke_status in _REVOCATION_BLOCKING_FAILURES:
                    if not _cleanup_is_complete(record):
                        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
                        if (record.access_revocation_error or "").strip():
                            record.cleanup_error = record.access_revocation_error
                    _summarize_result(summary, key="failed")
                    logger.warning(
                        "workspace_cleanup_failed",
                        extra={
                            "jobId": job_id,
                            "repoFullName": _normalize_repo_full_name(
                                record.repo_full_name
                            ),
                            "workspaceId": str(record.id),
                            "errorCode": record.access_revocation_error,
                        },
                    )
                    summary["processed"] += 1
                    await db.commit()
                    continue

                if not _retention_cleanup_eligible(
                    candidate_session=candidate_session,
                    simulation=simulation,
                ):
                    if not _cleanup_is_complete(record):
                        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_PENDING
                    if record.cleanup_status == WORKSPACE_CLEANUP_STATUS_PENDING:
                        record.cleanup_error = None
                    _summarize_result(summary, key="pending")
                    _summarize_result(summary, key="skippedActive")
                    summary["processed"] += 1
                    await db.commit()
                    continue

                if not _retention_expired(now=now, expires_at=retention_expires_at):
                    if not _cleanup_is_complete(record):
                        record.cleanup_status = WORKSPACE_CLEANUP_STATUS_PENDING
                    if record.cleanup_status == WORKSPACE_CLEANUP_STATUS_PENDING:
                        record.cleanup_error = None
                    _summarize_result(summary, key="pending")
                else:
                    cleanup_status = await _apply_retention_cleanup(
                        github_client,
                        record=record,
                        now=now,
                        cleanup_mode=config.cleanup_mode,
                        delete_enabled=config.delete_enabled,
                        job_id=job_id,
                    )
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
                                "repoFullName": _normalize_repo_full_name(
                                    record.repo_full_name
                                ),
                                "workspaceId": str(record.id),
                                "errorCode": record.cleanup_error,
                            },
                        )
                    else:
                        _summarize_result(summary, key="pending")
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
                error_code = _workspace_error_code(exc)
                record.cleanup_status = WORKSPACE_CLEANUP_STATUS_FAILED
                record.cleanup_error = error_code
                await db.commit()
                logger.warning(
                    "workspace_cleanup_failed",
                    extra={
                        "jobId": job_id,
                        "repoFullName": _normalize_repo_full_name(
                            record.repo_full_name
                        ),
                        "workspaceId": str(record.id),
                        "errorCode": error_code,
                    },
                )
                raise

            summary["processed"] += 1
            await db.commit()

    return {
        "status": "completed",
        "companyId": company_id,
        "cleanupMode": config.cleanup_mode,
        "retentionDays": config.retention_days,
        **summary,
    }


__all__ = ["WORKSPACE_CLEANUP_JOB_TYPE", "handle_workspace_cleanup"]
