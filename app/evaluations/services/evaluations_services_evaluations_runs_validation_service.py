"""Application module for evaluations services evaluations runs validation service workflows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    EVALUATION_RUN_STATUS_PENDING: {
        EVALUATION_RUN_STATUS_RUNNING,
        EVALUATION_RUN_STATUS_FAILED,
    },
    EVALUATION_RUN_STATUS_RUNNING: {
        EVALUATION_RUN_STATUS_COMPLETED,
        EVALUATION_RUN_STATUS_FAILED,
    },
    EVALUATION_RUN_STATUS_COMPLETED: set(),
    EVALUATION_RUN_STATUS_FAILED: set(),
}


class EvaluationRunStateError(ValueError):
    """Raised when an evaluation run transition is invalid."""


def normalize_datetime(value: datetime | None, *, field_name: str) -> datetime:
    """Normalize datetime."""
    if value is None:
        return datetime.now(UTC).replace(microsecond=0)
    if not isinstance(value, datetime):
        raise EvaluationRunStateError(f"{field_name} must be a datetime.")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def normalize_stored_datetime(value: datetime, *, field_name: str) -> datetime:
    """Normalize stored datetime."""
    if not isinstance(value, datetime):
        raise EvaluationRunStateError(f"{field_name} must be a datetime.")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def ensure_transition(*, current_status: str, target_status: str) -> None:
    """Ensure transition."""
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise EvaluationRunStateError(
            f"invalid evaluation run transition: {current_status} -> {target_status}"
        )


def linked_job_id(metadata_json: Any) -> str | int | None:
    """Execute linked job id."""
    if not isinstance(metadata_json, Mapping):
        return None
    return metadata_json.get("jobId") or metadata_json.get("job_id")


__all__ = [
    "EvaluationRunStateError",
    "ensure_transition",
    "linked_job_id",
    "normalize_datetime",
    "normalize_stored_datetime",
]
