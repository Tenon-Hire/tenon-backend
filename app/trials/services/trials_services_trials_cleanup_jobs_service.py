"""Application module for trials services trials cleanup jobs service workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Job, Trial
from app.shared.jobs.repositories import repository as jobs_repo

TRIAL_CLEANUP_JOB_TYPE = "trial_cleanup"
TRIAL_CLEANUP_MAX_ATTEMPTS = 8


def trial_cleanup_idempotency_key(trial_id: int) -> str:
    """Execute trial cleanup idempotency key."""
    return f"trial_cleanup:{trial_id}"


def build_trial_cleanup_payload(
    trial: Trial,
    *,
    terminated_by_user_id: int,
    reason: str | None,
) -> dict[str, Any]:
    """Build trial cleanup payload."""
    payload: dict[str, Any] = {
        "trialId": trial.id,
        "companyId": trial.company_id,
        "terminatedByUserId": terminated_by_user_id,
    }
    if reason:
        payload["reason"] = reason
    return payload


async def enqueue_trial_cleanup_job(
    db: AsyncSession,
    *,
    trial: Trial,
    terminated_by_user_id: int,
    reason: str | None,
    commit: bool = False,
) -> Job:
    """Enqueue trial cleanup job."""
    payload = build_trial_cleanup_payload(
        trial,
        terminated_by_user_id=terminated_by_user_id,
        reason=reason,
    )
    return await jobs_repo.create_or_get_idempotent(
        db,
        job_type=TRIAL_CLEANUP_JOB_TYPE,
        idempotency_key=trial_cleanup_idempotency_key(trial.id),
        payload_json=payload,
        company_id=trial.company_id,
        max_attempts=TRIAL_CLEANUP_MAX_ATTEMPTS,
        correlation_id=f"trial:{trial.id}:terminate",
        commit=commit,
    )


__all__ = [
    "TRIAL_CLEANUP_JOB_TYPE",
    "build_trial_cleanup_payload",
    "enqueue_trial_cleanup_job",
    "trial_cleanup_idempotency_key",
]
