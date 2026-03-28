from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Company,
    Job,
)


async def create_job(
    session: AsyncSession,
    *,
    company: Company,
    job_type: str = "test_job",
    status: str = "queued",
    idempotency_key: str | None = None,
    payload_json: dict | None = None,
    result_json: dict | None = None,
    last_error: str | None = None,
    attempt: int = 0,
    max_attempts: int = 5,
    candidate_session: CandidateSession | None = None,
    correlation_id: str | None = None,
    next_run_at: datetime | None = None,
) -> Job:
    job = Job(
        job_type=job_type,
        status=status,
        attempt=attempt,
        max_attempts=max_attempts,
        idempotency_key=idempotency_key or secrets.token_hex(12),
        payload_json=payload_json or {"ok": True},
        result_json=result_json,
        last_error=last_error,
        next_run_at=next_run_at,
        company_id=company.id,
        candidate_session_id=candidate_session.id if candidate_session else None,
        correlation_id=correlation_id,
    )
    session.add(job)
    await session.flush()
    return job
