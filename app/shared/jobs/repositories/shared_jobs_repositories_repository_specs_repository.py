"""Application module for jobs repositories repository specs repository workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    Job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    IdempotentJobSpec,
    normalize_idempotent_create_inputs,
    validate_payload_size,
)


def normalize_many_specs(specs: list[IdempotentJobSpec]) -> list[IdempotentJobSpec]:
    """Normalize many specs."""
    normalized_specs: list[IdempotentJobSpec] = []
    for spec in specs:
        normalized_type, normalized_key = normalize_idempotent_create_inputs(
            job_type=spec.job_type,
            idempotency_key=spec.idempotency_key,
            max_attempts=spec.max_attempts,
        )
        validate_payload_size(spec.payload_json)
        normalized_specs.append(
            IdempotentJobSpec(
                job_type=normalized_type,
                idempotency_key=normalized_key,
                payload_json=spec.payload_json,
                candidate_session_id=spec.candidate_session_id,
                max_attempts=spec.max_attempts,
                correlation_id=spec.correlation_id,
                next_run_at=spec.next_run_at,
            )
        )
    return normalized_specs


def job_from_spec(*, company_id: int, spec: IdempotentJobSpec) -> Job:
    """Execute job from spec."""
    return Job(
        job_type=spec.job_type,
        status=JOB_STATUS_QUEUED,
        attempt=0,
        max_attempts=spec.max_attempts,
        idempotency_key=spec.idempotency_key,
        payload_json=spec.payload_json,
        result_json=None,
        last_error=None,
        next_run_at=spec.next_run_at or datetime.now(UTC),
        locked_at=None,
        locked_by=None,
        correlation_id=spec.correlation_id,
        company_id=company_id,
        candidate_session_id=spec.candidate_session_id,
    )


def job_insert_row(*, company_id: int, spec: IdempotentJobSpec) -> dict[str, object]:
    """Execute job insert row."""
    job = job_from_spec(company_id=company_id, spec=spec)
    return {
        "job_type": job.job_type,
        "status": job.status,
        "attempt": job.attempt,
        "max_attempts": job.max_attempts,
        "idempotency_key": job.idempotency_key,
        "payload_json": job.payload_json,
        "result_json": job.result_json,
        "last_error": job.last_error,
        "next_run_at": job.next_run_at,
        "locked_at": job.locked_at,
        "locked_by": job.locked_by,
        "correlation_id": job.correlation_id,
        "company_id": job.company_id,
        "candidate_session_id": job.candidate_session_id,
    }


async def load_idempotent_jobs_for_keys(
    db: AsyncSession, *, company_id: int, keys: list[tuple[str, str]]
) -> dict[tuple[str, str], Job]:
    """Load idempotent jobs for keys."""
    if not keys:
        return {}
    rows = (
        await db.execute(
            select(Job).where(
                Job.company_id == company_id,
                tuple_(Job.job_type, Job.idempotency_key).in_(keys),
            )
        )
    ).scalars()
    return {(row.job_type, row.idempotency_key): row for row in rows}
