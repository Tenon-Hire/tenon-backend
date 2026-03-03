from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.principal import Principal
from app.domains import CandidateSession, User
from app.repositories.jobs.models import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    Job,
)

MAX_JOB_PAYLOAD_BYTES = 64 * 1024
MAX_JOB_ERROR_CHARS = 2_048


def _runnable_filter(now, *, stale_before):
    return or_(
        and_(
            Job.status == JOB_STATUS_QUEUED,
            or_(Job.next_run_at.is_(None), Job.next_run_at <= now),
        ),
        and_(
            Job.status == JOB_STATUS_RUNNING,
            or_(Job.locked_at.is_(None), Job.locked_at <= stale_before),
        ),
    )


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _validate_payload_size(payload_json: dict[str, Any]) -> None:
    encoded = json.dumps(
        payload_json,
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if len(encoded) > MAX_JOB_PAYLOAD_BYTES:
        raise ValueError(
            f"payload_json exceeds {MAX_JOB_PAYLOAD_BYTES} bytes "
            f"({len(encoded)} bytes)"
        )


def sanitize_error(error_str: str) -> str:
    normalized = " ".join((error_str or "").split())
    return normalized[:MAX_JOB_ERROR_CHARS]


async def get_by_id(db: AsyncSession, job_id: str) -> Job | None:
    return (
        await db.execute(
            select(Job)
            .where(Job.id == job_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()


async def get_by_id_for_principal(
    db: AsyncSession, job_id: str, principal: Principal
) -> Job | None:
    if "recruiter:access" in principal.permissions:
        recruiter = (
            await db.execute(select(User).where(User.email == principal.email))
        ).scalar_one_or_none()
        company_id = getattr(recruiter, "company_id", None)
        if company_id is not None:
            recruiter_job = (
                await db.execute(
                    select(Job).where(Job.id == job_id, Job.company_id == company_id)
                )
            ).scalar_one_or_none()
            if recruiter_job is not None:
                return recruiter_job

    if "candidate:access" in principal.permissions:
        # Keep this strict check aligned with candidate session ownership logic:
        # candidate access requires an explicit `email_verified is True` claim.
        if principal.claims.get("email_verified") is not True:
            return None
        email = _normalize_email(principal.email)
        if not email:
            return None

        candidate_row = (
            await db.execute(
                select(Job, CandidateSession)
                .join(
                    CandidateSession,
                    CandidateSession.id == Job.candidate_session_id,
                )
                .where(Job.id == job_id)
            )
        ).first()
        if candidate_row is None:
            return None

        candidate_job, candidate_session = candidate_row
        if _normalize_email(candidate_session.invite_email) != email:
            return None

        claimed_sub = (candidate_session.candidate_auth0_sub or "").strip()
        if claimed_sub and claimed_sub != principal.sub:
            return None
        return candidate_job

    return None


async def create_or_get_idempotent(
    db: AsyncSession,
    *,
    job_type: str,
    idempotency_key: str,
    payload_json: dict[str, Any],
    company_id: int,
    candidate_session_id: int | None = None,
    max_attempts: int = 5,
    correlation_id: str | None = None,
) -> Job:
    normalized_type = job_type.strip()
    normalized_key = idempotency_key.strip()
    if not normalized_type:
        raise ValueError("job_type is required")
    if not normalized_key:
        raise ValueError("idempotency_key is required")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    _validate_payload_size(payload_json)

    existing = (
        await db.execute(
            select(Job).where(
                Job.company_id == company_id,
                Job.job_type == normalized_type,
                Job.idempotency_key == normalized_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    job = Job(
        job_type=normalized_type,
        status=JOB_STATUS_QUEUED,
        attempt=0,
        max_attempts=max_attempts,
        idempotency_key=normalized_key,
        payload_json=payload_json,
        result_json=None,
        last_error=None,
        next_run_at=datetime.now(UTC),
        locked_at=None,
        locked_by=None,
        correlation_id=correlation_id,
        company_id=company_id,
        candidate_session_id=candidate_session_id,
    )
    db.add(job)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = (
            await db.execute(
                select(Job).where(
                    Job.company_id == company_id,
                    Job.job_type == normalized_type,
                    Job.idempotency_key == normalized_key,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            raise
        return existing
    await db.refresh(job)
    return job


async def claim_next_runnable(
    db: AsyncSession,
    *,
    worker_id: str,
    now,
    lease_seconds: int,
) -> Job | None:
    stale_before = now - timedelta(seconds=lease_seconds)
    order = (
        func.coalesce(Job.next_run_at, Job.created_at).asc(),
        Job.created_at.asc(),
    )

    for _ in range(8):
        candidate_row = (
            await db.execute(
                select(Job.id, Job.attempt)
                .where(_runnable_filter(now, stale_before=stale_before))
                .order_by(*order)
                .limit(1)
            )
        ).first()
        if candidate_row is None:
            return None

        current_attempt = int(candidate_row.attempt)
        claimed = await db.execute(
            update(Job)
            .where(
                Job.id == candidate_row.id,
                Job.attempt == current_attempt,
                _runnable_filter(now, stale_before=stale_before),
            )
            .values(
                status=JOB_STATUS_RUNNING,
                attempt=current_attempt + 1,
                locked_at=now,
                locked_by=worker_id,
                updated_at=now,
            )
        )
        if claimed.rowcount == 1:
            await db.commit()
            return await get_by_id(db, candidate_row.id)
        await db.rollback()
    return None


async def mark_succeeded(
    db: AsyncSession, *, job_id: str, result_json: dict[str, Any] | None, now
) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JOB_STATUS_SUCCEEDED,
            result_json=result_json,
            last_error=None,
            next_run_at=None,
            locked_at=None,
            locked_by=None,
            updated_at=now,
        )
    )
    await db.commit()


async def mark_failed_and_reschedule(
    db: AsyncSession, *, job_id: str, error_str: str, next_run_at, now
) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JOB_STATUS_QUEUED,
            last_error=sanitize_error(error_str),
            next_run_at=next_run_at,
            locked_at=None,
            locked_by=None,
            updated_at=now,
        )
    )
    await db.commit()


async def mark_dead_letter(
    db: AsyncSession, *, job_id: str, error_str: str, now
) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=JOB_STATUS_DEAD_LETTER,
            last_error=sanitize_error(error_str),
            next_run_at=None,
            locked_at=None,
            locked_by=None,
            updated_at=now,
        )
    )
    await db.commit()
