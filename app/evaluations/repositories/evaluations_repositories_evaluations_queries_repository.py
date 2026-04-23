"""Application module for evaluations repositories evaluations queries repository workflows."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EvaluationRun,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_validation_scalars_repository import (
    normalize_non_empty_str,
    normalize_status,
)


async def get_run_by_id(
    db: AsyncSession, run_id: int, *, for_update: bool = False
) -> EvaluationRun | None:
    """Return run by id."""
    stmt = (
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.day_scores),
            selectinload(EvaluationRun.reviewer_reports),
        )
        .where(EvaluationRun.id == run_id)
    )
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_run_by_job_id(
    db: AsyncSession,
    *,
    job_id: str,
    candidate_session_id: int | None = None,
    for_update: bool = False,
) -> EvaluationRun | None:
    """Return run by job id."""
    normalized_job_id = normalize_non_empty_str(job_id, field_name="job_id")
    stmt = (
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.day_scores),
            selectinload(EvaluationRun.reviewer_reports),
        )
        .where(EvaluationRun.job_id == normalized_job_id)
        .order_by(EvaluationRun.started_at.desc(), EvaluationRun.id.desc())
        .limit(1)
    )
    if candidate_session_id is not None:
        stmt = stmt.where(
            EvaluationRun.candidate_session_id == int(candidate_session_id)
        )
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_run_for_candidate_session(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    statuses: Sequence[str] | None = None,
    basis_fingerprint: str | None = None,
) -> EvaluationRun | None:
    """Return latest run for candidate session."""
    stmt = (
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.day_scores),
            selectinload(EvaluationRun.reviewer_reports),
        )
        .where(EvaluationRun.candidate_session_id == candidate_session_id)
        .order_by(EvaluationRun.started_at.desc(), EvaluationRun.id.desc())
        .limit(1)
    )
    if basis_fingerprint is not None:
        stmt = stmt.where(EvaluationRun.basis_fingerprint == basis_fingerprint)
    if statuses is not None:
        normalized_statuses = {normalize_status(value) for value in statuses}
        if not normalized_statuses:
            return None
        stmt = stmt.where(EvaluationRun.status.in_(sorted(normalized_statuses)))
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_successful_run_for_candidate_session(
    db: AsyncSession, *, candidate_session_id: int
):
    """Return latest successful run for candidate session."""
    return await get_latest_run_for_candidate_session(
        db,
        candidate_session_id=candidate_session_id,
        statuses=[EVALUATION_RUN_STATUS_COMPLETED],
    )


async def list_runs_for_candidate_session(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    scenario_version_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[EvaluationRun]:
    """Return runs for candidate session."""
    stmt = (
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.day_scores),
            selectinload(EvaluationRun.reviewer_reports),
        )
        .where(EvaluationRun.candidate_session_id == candidate_session_id)
        .order_by(EvaluationRun.started_at.desc(), EvaluationRun.id.desc())
    )
    if scenario_version_id is not None:
        stmt = stmt.where(EvaluationRun.scenario_version_id == scenario_version_id)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def has_runs_for_candidate_session(
    db: AsyncSession, candidate_session_id: int
) -> bool:
    """Execute has runs for candidate session."""
    stmt = (
        select(EvaluationRun.id)
        .where(EvaluationRun.candidate_session_id == candidate_session_id)
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None
