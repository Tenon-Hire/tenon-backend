"""Application module for evaluations services evaluations winoe report jobs service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import Job
from app.shared.jobs.repositories import repository as jobs_repo

EVALUATION_RUN_JOB_TYPE = "evaluation_run"
EVALUATION_RUN_JOB_MAX_ATTEMPTS = 7


def build_evaluation_job_payload(
    *,
    candidate_session_id: int,
    company_id: int,
    requested_by_user_id: int,
    basis_fingerprint: str,
) -> dict[str, object]:
    """Build evaluation job payload."""
    requested_at = datetime.now(UTC).replace(microsecond=0)
    return {
        "candidateSessionId": int(candidate_session_id),
        "companyId": int(company_id),
        "requestedByUserId": int(requested_by_user_id),
        "basisFingerprint": str(basis_fingerprint),
        "requestedAt": requested_at.isoformat().replace("+00:00", "Z"),
    }


def build_evaluation_job_idempotency_key(*, basis_fingerprint: str) -> str:
    """Build evaluation job idempotency key."""
    normalized = basis_fingerprint.strip()
    if not normalized:
        raise ValueError("basis_fingerprint is required")
    return f"evaluation_run:{normalized}"


async def enqueue_evaluation_run(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    company_id: int,
    requested_by_user_id: int,
    basis_fingerprint: str,
    commit: bool = True,
) -> Job:
    """Enqueue evaluation run."""
    payload_json = build_evaluation_job_payload(
        candidate_session_id=candidate_session_id,
        company_id=company_id,
        requested_by_user_id=requested_by_user_id,
        basis_fingerprint=basis_fingerprint,
    )
    job = await jobs_repo.create_or_get_idempotent(
        db,
        job_type=EVALUATION_RUN_JOB_TYPE,
        idempotency_key=build_evaluation_job_idempotency_key(
            basis_fingerprint=basis_fingerprint
        ),
        payload_json=payload_json,
        company_id=company_id,
        candidate_session_id=candidate_session_id,
        correlation_id=f"candidate_session:{candidate_session_id}:evaluation_run",
        max_attempts=EVALUATION_RUN_JOB_MAX_ATTEMPTS,
        commit=False,
    )
    payload_with_job_id = dict(job.payload_json or {})
    payload_with_job_id["jobId"] = job.id
    job.payload_json = payload_with_job_id
    if commit:
        await db.commit()
        await db.refresh(job)
    else:
        await db.flush()
    return job


__all__ = [
    "EVALUATION_RUN_JOB_TYPE",
    "EVALUATION_RUN_JOB_MAX_ATTEMPTS",
    "build_evaluation_job_payload",
    "build_evaluation_job_idempotency_key",
    "enqueue_evaluation_run",
]
