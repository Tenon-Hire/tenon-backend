"""Application module for jobs handlers workspace cleanup utils workflows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import settings
from app.integrations.github import GithubError
from app.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_types_handler import (
    _SESSION_TERMINAL_STATUSES,
    _SIMULATION_TERMINAL_STATUSES,
    _TRANSIENT_GITHUB_STATUS_CODES,
    WORKSPACE_CLEANUP_TERMINAL_STATUSES,
    WorkspaceCleanupRecord,
    _WorkspaceCleanupConfig,
)
from app.shared.utils.shared_utils_parsing_utils import (
    parse_positive_int as _parse_positive_int_value,
)


def _parse_positive_int(value: Any) -> int | None:
    return _parse_positive_int_value(value)


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


def _retention_anchor(record: WorkspaceCleanupRecord, candidate_session) -> datetime:
    if candidate_session.completed_at is not None:
        return _normalize_datetime(candidate_session.completed_at)
    return _normalize_datetime(record.created_at)


def _retention_expires_at(anchor: datetime, *, retention_days: int) -> datetime:
    return anchor + timedelta(days=retention_days)


def _retention_expired(*, now: datetime, expires_at: datetime) -> bool:
    return now > expires_at


def _retention_cleanup_eligible(*, candidate_session, simulation) -> bool:
    session_status = (candidate_session.status or "").strip().lower()
    simulation_status = (simulation.status or "").strip().lower()
    if candidate_session.completed_at is not None:
        return True
    if session_status in _SESSION_TERMINAL_STATUSES:
        return True
    return simulation_status in _SIMULATION_TERMINAL_STATUSES


def _cleanup_target_repo_key(
    *, candidate_session_id: int, repo_full_name: str | None, fallback_id: str
) -> tuple[int, str]:
    normalized_repo = _normalize_repo_full_name(repo_full_name)
    if normalized_repo is not None:
        return (candidate_session_id, normalized_repo.lower())
    return (candidate_session_id, f"id:{fallback_id}")


def _summarize_result(summary: dict[str, int], *, key: str) -> None:
    summary[key] = summary.get(key, 0) + 1


__all__ = [
    "_cleanup_is_complete",
    "_cleanup_target_repo_key",
    "_is_transient_github_error",
    "_normalize_datetime",
    "_normalize_repo_full_name",
    "_parse_positive_int",
    "_resolve_cleanup_config",
    "_retention_anchor",
    "_retention_cleanup_eligible",
    "_retention_expired",
    "_retention_expires_at",
    "_summarize_result",
    "_workspace_error_code",
]
