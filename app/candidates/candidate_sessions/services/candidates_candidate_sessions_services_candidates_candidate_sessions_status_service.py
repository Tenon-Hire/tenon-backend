"""Application module for candidates candidate sessions services candidates candidate sessions status service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.shared.database.shared_database_models_model import CandidateSession


def require_not_expired(
    candidate_session: CandidateSession, *, now: datetime | None = None
) -> None:
    """Require not expired."""
    now = now or datetime.now(UTC)
    expires_at = candidate_session.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at is not None and expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invite token expired",
        )


def mark_in_progress(candidate_session: CandidateSession, *, now: datetime) -> None:
    """Mark in progress."""
    if candidate_session.status == "not_started":
        candidate_session.status = "in_progress"
        if candidate_session.started_at is None:
            candidate_session.started_at = now
