"""Application module for jobs repositories repository workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    Job,
)
from app.shared.utils.shared_utils_normalization_utils import normalize_email

MAX_JOB_PAYLOAD_BYTES = 64 * 1024
MAX_JOB_ERROR_CHARS = 2_048


@dataclass(slots=True)
class IdempotentJobSpec:
    """Represent idempotent job spec data and behavior."""

    job_type: str
    idempotency_key: str
    payload_json: dict[str, Any]
    candidate_session_id: int | None = None
    max_attempts: int = 5
    correlation_id: str | None = None
    next_run_at: datetime | None = None


def validate_payload_size(payload_json: dict[str, Any]) -> None:
    """Validate payload size."""
    encoded = json.dumps(
        payload_json,
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if len(encoded) > MAX_JOB_PAYLOAD_BYTES:
        raise ValueError(
            f"payload_json exceeds {MAX_JOB_PAYLOAD_BYTES} bytes ({len(encoded)} bytes)"
        )


def sanitize_error(error_str: str) -> str:
    """Sanitize error."""
    normalized = " ".join((error_str or "").split())
    return normalized[:MAX_JOB_ERROR_CHARS]


def normalize_idempotent_create_inputs(
    *, job_type: str, idempotency_key: str, max_attempts: int
) -> tuple[str, str]:
    """Normalize idempotent create inputs."""
    normalized_type = job_type.strip()
    normalized_key = idempotency_key.strip()
    if not normalized_type:
        raise ValueError("job_type is required")
    if not normalized_key:
        raise ValueError("idempotency_key is required")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    return normalized_type, normalized_key


async def load_idempotent_job(
    db: AsyncSession, *, company_id: int, job_type: str, idempotency_key: str
) -> Job | None:
    """Load idempotent job."""
    return (
        await db.execute(
            select(Job).where(
                Job.company_id == company_id,
                Job.job_type == job_type,
                Job.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()


def is_mutable_idempotent_job(job: Job) -> bool:
    """Return whether mutable idempotent job."""
    return (
        job.status == JOB_STATUS_QUEUED
        and job.locked_at is None
        and job.locked_by is None
    )


def apply_idempotent_job_updates(
    job: Job,
    *,
    payload_json: dict[str, Any],
    candidate_session_id: int | None,
    max_attempts: int,
    correlation_id: str | None,
    next_run_at: datetime | None,
) -> None:
    """Apply idempotent job updates."""
    job.payload_json = payload_json
    job.candidate_session_id = candidate_session_id
    job.max_attempts = max_attempts
    job.correlation_id = correlation_id
    job.next_run_at = next_run_at or datetime.now(UTC)


__all__ = [
    "IdempotentJobSpec",
    "MAX_JOB_ERROR_CHARS",
    "MAX_JOB_PAYLOAD_BYTES",
    "apply_idempotent_job_updates",
    "is_mutable_idempotent_job",
    "load_idempotent_job",
    "normalize_email",
    "normalize_idempotent_create_inputs",
    "sanitize_error",
    "validate_payload_size",
]
