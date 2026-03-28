"""Application module for evaluations repositories evaluations create run helpers repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_scalars_repository import (
    normalize_datetime,
)


def normalize_run_time_fields(
    *,
    status: str,
    started_at: datetime | None,
    completed_at: datetime | None,
    generated_at: datetime | None,
) -> tuple[datetime, datetime | None, datetime | None]:
    """Normalize run time fields."""
    normalized_started_at = normalize_datetime(
        started_at, field_name="started_at", default_now=True
    )
    assert normalized_started_at is not None
    normalized_completed_at = normalize_datetime(
        completed_at, field_name="completed_at", default_now=False
    )
    if (
        status in {EVALUATION_RUN_STATUS_PENDING, EVALUATION_RUN_STATUS_RUNNING}
        and normalized_completed_at is not None
    ):
        raise ValueError(f"completed_at is not allowed when status is {status}.")
    if status == EVALUATION_RUN_STATUS_COMPLETED and normalized_completed_at is None:
        normalized_completed_at = datetime.now(UTC).replace(microsecond=0)
    if (
        normalized_completed_at is not None
        and normalized_completed_at < normalized_started_at
    ):
        raise ValueError("completed_at must be greater than or equal to started_at.")
    normalized_generated_at = normalize_datetime(
        generated_at, field_name="generated_at", default_now=False
    )
    if (
        status in {EVALUATION_RUN_STATUS_PENDING, EVALUATION_RUN_STATUS_RUNNING}
        and normalized_generated_at is not None
    ):
        raise ValueError(f"generated_at is not allowed when status is {status}.")
    if (
        status == EVALUATION_RUN_STATUS_COMPLETED
        and normalized_generated_at is None
        and normalized_completed_at is not None
    ):
        normalized_generated_at = normalized_completed_at
    if (
        normalized_generated_at is not None
        and normalized_generated_at < normalized_started_at
    ):
        raise ValueError("generated_at must be greater than or equal to started_at.")
    return normalized_started_at, normalized_completed_at, normalized_generated_at
