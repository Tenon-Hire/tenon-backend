"""Application module for trials services trials candidates compare time service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.trials.services.trials_services_trials_candidates_compare_constants import (
    COMPARE_DAYS,
)


def normalize_datetime(value: datetime | None) -> datetime | None:
    """Normalize datetime."""
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def max_datetime(*values: datetime | None) -> datetime | None:
    """Execute max datetime."""
    normalized = [normalize_datetime(value) for value in values]
    filtered = [value for value in normalized if value is not None]
    return max(filtered) if filtered else None


def default_day_completion() -> dict[str, bool]:
    """Execute default day completion."""
    return {str(day): False for day in COMPARE_DAYS}


def winoe_report_updated_at(row: Any) -> datetime | None:
    """Execute winoe report updated at."""
    return max_datetime(
        row.winoe_report_generated_at,
        row.latest_run_started_at,
        row.latest_run_completed_at,
        row.latest_run_generated_at,
        row.latest_success_started_at,
        row.latest_success_completed_at,
        row.latest_success_generated_at,
        row.active_job_updated_at,
    )


def candidate_session_updated_at(
    row: Any, *, latest_submission_at: datetime | None
) -> datetime | None:
    """Execute candidate session updated at."""
    return max_datetime(
        row.candidate_session_updated_at,
        row.claimed_at,
        row.started_at,
        row.completed_at,
        row.schedule_locked_at,
        row.invite_email_sent_at,
        row.invite_email_last_attempt_at,
        latest_submission_at,
    )


def candidate_session_created_at(row: Any) -> datetime | None:
    """Execute candidate session created at."""
    return normalize_datetime(row.candidate_session_created_at)


__all__ = [
    "candidate_session_created_at",
    "candidate_session_updated_at",
    "default_day_completion",
    "winoe_report_updated_at",
    "max_datetime",
    "normalize_datetime",
]
