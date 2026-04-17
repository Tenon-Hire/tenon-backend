"""Application module for submissions day flow cutoff gate service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as cs_repo,
)
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.utils.shared_utils_errors_utils import (
    TASK_WINDOW_CLOSED,
    ApiError,
)

_DAY_FLOW_INDEXES = {2, 3}


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return (
        value.replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _build_day_flow_cutoff_error(
    *,
    candidate_session_id: int | None,
    task_id: int | None,
    day_index: int | None,
    cutoff_commit_sha: str | None,
    cutoff_at: datetime | None,
    eval_basis_ref: str | None,
    access_revoked_at: datetime | None = None,
) -> ApiError:
    details: dict[str, object | None] = {
        "candidateSessionId": candidate_session_id,
        "taskId": task_id,
        "dayIndex": day_index,
        "cutoffCommitSha": cutoff_commit_sha,
        "cutoffAt": _serialize_optional_datetime(cutoff_at),
        "evalBasisRef": eval_basis_ref,
    }
    if access_revoked_at is not None:
        details["accessRevokedAt"] = _serialize_optional_datetime(access_revoked_at)
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Task is closed after the recorded cutoff.",
        error_code=TASK_WINDOW_CLOSED,
        retryable=False,
        details=details,
    )


async def ensure_day_flow_open(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task,
    workspace=None,
) -> None:
    """Reject active Day 2/3 work once the cutoff is recorded or revoked."""
    day_index = getattr(task, "day_index", None)
    if day_index not in _DAY_FLOW_INDEXES:
        return

    day_audit = await cs_repo.get_day_audit(
        db,
        candidate_session_id=candidate_session.id,
        day_index=day_index,
    )
    if day_audit is not None:
        raise _build_day_flow_cutoff_error(
            candidate_session_id=candidate_session.id,
            task_id=getattr(task, "id", None),
            day_index=day_index,
            cutoff_commit_sha=getattr(day_audit, "cutoff_commit_sha", None),
            cutoff_at=getattr(day_audit, "cutoff_at", None),
            eval_basis_ref=getattr(day_audit, "eval_basis_ref", None),
        )

    if workspace is None:
        return
    access_revoked_at = getattr(workspace, "access_revoked_at", None)
    if access_revoked_at is None:
        return
    raise _build_day_flow_cutoff_error(
        candidate_session_id=candidate_session.id,
        task_id=getattr(task, "id", None),
        day_index=day_index,
        cutoff_commit_sha=None,
        cutoff_at=access_revoked_at,
        eval_basis_ref=None,
        access_revoked_at=access_revoked_at,
    )


__all__ = ["ensure_day_flow_open"]
