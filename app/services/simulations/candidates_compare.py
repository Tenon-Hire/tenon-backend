from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.domains import (
    CandidateSession,
    EvaluationRun,
    FitProfile,
    Job,
    Simulation,
    Submission,
    Task,
    User,
)
from app.repositories.evaluations.models import (
    EVALUATION_RECOMMENDATIONS,
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
    EVALUATION_RUN_STATUS_PENDING,
    EVALUATION_RUN_STATUS_RUNNING,
)
from app.repositories.jobs.models import JOB_STATUS_QUEUED, JOB_STATUS_RUNNING
from app.schemas.simulations_compare import (
    CandidateCompareStatus,
    FitProfileCompareStatus,
)
from app.services.evaluations.fit_profile_access import has_company_access
from app.services.evaluations.fit_profile_jobs import EVALUATION_RUN_JOB_TYPE

_COMPARE_DAYS = (1, 2, 3, 4, 5)


@dataclass(slots=True)
class SimulationCompareAccessContext:
    simulation_id: int


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _max_datetime(*values: datetime | None) -> datetime | None:
    normalized = [_normalize_datetime(value) for value in values]
    filtered = [value for value in normalized if value is not None]
    if not filtered:
        return None
    return max(filtered)


def _default_day_completion() -> dict[str, bool]:
    return {str(day): False for day in _COMPARE_DAYS}


def _fit_profile_updated_at(row: Any) -> datetime | None:
    return _max_datetime(
        row.fit_profile_generated_at,
        row.latest_run_started_at,
        row.latest_run_completed_at,
        row.latest_run_generated_at,
        row.latest_success_started_at,
        row.latest_success_completed_at,
        row.latest_success_generated_at,
        row.active_job_updated_at,
    )


def _candidate_session_updated_at(
    row: Any,
    *,
    latest_submission_at: datetime | None,
) -> datetime | None:
    return _max_datetime(
        row.candidate_session_updated_at,
        row.claimed_at,
        row.started_at,
        row.completed_at,
        row.schedule_locked_at,
        row.invite_email_sent_at,
        row.invite_email_last_attempt_at,
        latest_submission_at,
    )


def _candidate_session_created_at(row: Any) -> datetime | None:
    return _normalize_datetime(row.candidate_session_created_at)


def _anonymized_candidate_label(position: int) -> str:
    # 0 -> A, 25 -> Z, 26 -> AA, 27 -> AB
    if position < 0:
        position = 0
    encoded: list[str] = []
    value = position
    while True:
        value, remainder = divmod(value, 26)
        encoded.append(chr(ord("A") + remainder))
        if value == 0:
            break
        value -= 1
    return f"Candidate {''.join(reversed(encoded))}"


def _display_name(candidate_name: Any, *, position: int) -> str:
    if isinstance(candidate_name, str):
        normalized = candidate_name.strip()
        if normalized:
            return normalized
    return _anonymized_candidate_label(position)


def _normalize_score(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    normalized = float(value)
    if normalized < 0 or normalized > 1:
        return None
    return normalized


def _normalize_recommendation(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized or normalized not in EVALUATION_RECOMMENDATIONS:
        return None
    return normalized


def derive_fit_profile_status(
    *,
    has_ready_profile: bool,
    latest_run_status: str | None,
    has_active_job: bool,
) -> FitProfileCompareStatus:
    if has_ready_profile:
        return "ready"
    if latest_run_status in {
        EVALUATION_RUN_STATUS_PENDING,
        EVALUATION_RUN_STATUS_RUNNING,
    }:
        return "generating"
    if latest_run_status == EVALUATION_RUN_STATUS_FAILED:
        return "failed"
    if has_active_job:
        return "generating"
    return "none"


def derive_candidate_compare_status(
    *,
    fit_profile_status: FitProfileCompareStatus,
    day_completion: dict[str, bool],
    candidate_session_status: str | None,
    started_at: datetime | None,
    completed_at: datetime | None,
) -> CandidateCompareStatus:
    if fit_profile_status == "ready":
        return "evaluated"

    all_days_completed = all(
        bool(day_completion.get(str(day), False)) for day in _COMPARE_DAYS
    )
    if (
        all_days_completed
        or candidate_session_status == "completed"
        or completed_at is not None
    ):
        return "completed"

    has_progress = (
        any(bool(day_completion.get(str(day), False)) for day in _COMPARE_DAYS)
        or candidate_session_status in {"in_progress", "completed"}
        or started_at is not None
        or completed_at is not None
    )
    return "in_progress" if has_progress else "scheduled"


async def require_simulation_compare_access(
    db: AsyncSession,
    *,
    simulation_id: int,
    user: User,
) -> SimulationCompareAccessContext:
    simulation = (
        await db.execute(
            select(Simulation)
            .options(
                load_only(
                    Simulation.id,
                    Simulation.company_id,
                    Simulation.created_by,
                )
            )
            .where(Simulation.id == simulation_id)
        )
    ).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    if not has_company_access(
        simulation_company_id=simulation.company_id,
        expected_company_id=getattr(user, "company_id", None),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation access forbidden",
        )
    if simulation.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation access forbidden",
        )
    return SimulationCompareAccessContext(
        simulation_id=simulation.id,
    )


def _latest_run_subquery(*, completed_only: bool) -> Any:
    base_stmt = select(
        EvaluationRun.candidate_session_id.label("candidate_session_id"),
        EvaluationRun.status.label("run_status"),
        EvaluationRun.started_at.label("run_started_at"),
        EvaluationRun.completed_at.label("run_completed_at"),
        EvaluationRun.generated_at.label("run_generated_at"),
        EvaluationRun.overall_fit_score.label("overall_fit_score"),
        EvaluationRun.recommendation.label("recommendation"),
        func.row_number()
        .over(
            partition_by=EvaluationRun.candidate_session_id,
            order_by=(EvaluationRun.started_at.desc(), EvaluationRun.id.desc()),
        )
        .label("rn"),
    )
    if completed_only:
        base_stmt = base_stmt.where(
            EvaluationRun.status == EVALUATION_RUN_STATUS_COMPLETED
        )
    ranked = base_stmt.subquery()
    return (
        select(
            ranked.c.candidate_session_id,
            ranked.c.run_status,
            ranked.c.run_started_at,
            ranked.c.run_completed_at,
            ranked.c.run_generated_at,
            ranked.c.overall_fit_score,
            ranked.c.recommendation,
        )
        .where(ranked.c.rn == 1)
        .subquery()
    )


async def _load_day_completion(
    db: AsyncSession,
    *,
    simulation_id: int,
    candidate_session_ids: list[int],
) -> tuple[dict[int, dict[str, bool]], dict[int, datetime | None]]:
    completion_by_session = {
        session_id: _default_day_completion() for session_id in candidate_session_ids
    }
    latest_submission_by_session: dict[int, datetime | None] = {
        session_id: None for session_id in candidate_session_ids
    }
    if not candidate_session_ids:
        return completion_by_session, latest_submission_by_session

    stmt = (
        select(
            CandidateSession.id.label("candidate_session_id"),
            Task.day_index.label("day_index"),
            func.count(Task.id).label("task_count"),
            func.count(Submission.id).label("submitted_count"),
            func.max(Submission.submitted_at).label("latest_submission_at"),
        )
        .join(Task, Task.simulation_id == CandidateSession.simulation_id)
        .outerjoin(
            Submission,
            and_(
                Submission.candidate_session_id == CandidateSession.id,
                Submission.task_id == Task.id,
            ),
        )
        .where(
            CandidateSession.simulation_id == simulation_id,
            CandidateSession.id.in_(candidate_session_ids),
            Task.day_index.in_(_COMPARE_DAYS),
        )
        .group_by(CandidateSession.id, Task.day_index)
    )
    for row in (await db.execute(stmt)).all():
        session_id = int(row.candidate_session_id)
        day_index = int(row.day_index)
        day_key = str(day_index)
        if day_key not in completion_by_session[session_id]:
            continue
        task_count = int(row.task_count or 0)
        submitted_count = int(row.submitted_count or 0)
        completion_by_session[session_id][day_key] = (
            task_count > 0 and submitted_count >= task_count
        )
        latest_submission = _normalize_datetime(row.latest_submission_at)
        if latest_submission is None:
            continue
        existing_latest = latest_submission_by_session.get(session_id)
        latest_submission_by_session[session_id] = _max_datetime(
            existing_latest,
            latest_submission,
        )

    return completion_by_session, latest_submission_by_session


async def list_candidates_compare_summary(
    db: AsyncSession,
    *,
    simulation_id: int,
    user: User,
) -> dict[str, Any]:
    access = await require_simulation_compare_access(
        db,
        simulation_id=simulation_id,
        user=user,
    )
    latest_run_any = _latest_run_subquery(completed_only=False)
    latest_run_success = _latest_run_subquery(completed_only=True)
    candidate_session_created_column = getattr(CandidateSession, "created_at", None)
    candidate_session_updated_column = getattr(CandidateSession, "updated_at", None)
    candidate_session_created_at = (
        candidate_session_created_column.label("candidate_session_created_at")
        if candidate_session_created_column is not None
        else literal(None).label("candidate_session_created_at")
    )
    candidate_session_updated_at = (
        candidate_session_updated_column.label("candidate_session_updated_at")
        if candidate_session_updated_column is not None
        else literal(None).label("candidate_session_updated_at")
    )
    active_job = (
        select(
            Job.candidate_session_id.label("candidate_session_id"),
            func.max(Job.updated_at).label("active_job_updated_at"),
        )
        .where(
            Job.candidate_session_id.is_not(None),
            Job.job_type == EVALUATION_RUN_JOB_TYPE,
            Job.status.in_((JOB_STATUS_QUEUED, JOB_STATUS_RUNNING)),
        )
        .group_by(Job.candidate_session_id)
        .subquery()
    )

    stmt = (
        select(
            CandidateSession.id.label("candidate_session_id"),
            CandidateSession.candidate_name.label("candidate_name"),
            CandidateSession.status.label("candidate_session_status"),
            CandidateSession.claimed_at.label("claimed_at"),
            CandidateSession.started_at.label("started_at"),
            CandidateSession.completed_at.label("completed_at"),
            candidate_session_created_at,
            candidate_session_updated_at,
            CandidateSession.schedule_locked_at.label("schedule_locked_at"),
            CandidateSession.invite_email_sent_at.label("invite_email_sent_at"),
            CandidateSession.invite_email_last_attempt_at.label(
                "invite_email_last_attempt_at"
            ),
            FitProfile.generated_at.label("fit_profile_generated_at"),
            latest_run_any.c.run_status.label("latest_run_status"),
            latest_run_any.c.run_started_at.label("latest_run_started_at"),
            latest_run_any.c.run_completed_at.label("latest_run_completed_at"),
            latest_run_any.c.run_generated_at.label("latest_run_generated_at"),
            latest_run_success.c.candidate_session_id.label(
                "latest_success_candidate_session_id"
            ),
            latest_run_success.c.overall_fit_score.label("overall_fit_score"),
            latest_run_success.c.recommendation.label("recommendation"),
            latest_run_success.c.run_started_at.label("latest_success_started_at"),
            latest_run_success.c.run_completed_at.label("latest_success_completed_at"),
            latest_run_success.c.run_generated_at.label("latest_success_generated_at"),
            active_job.c.active_job_updated_at.label("active_job_updated_at"),
        )
        .outerjoin(FitProfile, FitProfile.candidate_session_id == CandidateSession.id)
        .outerjoin(
            latest_run_any,
            latest_run_any.c.candidate_session_id == CandidateSession.id,
        )
        .outerjoin(
            latest_run_success,
            latest_run_success.c.candidate_session_id == CandidateSession.id,
        )
        .outerjoin(
            active_job,
            active_job.c.candidate_session_id == CandidateSession.id,
        )
        .where(CandidateSession.simulation_id == simulation_id)
        .order_by(CandidateSession.id.asc())
    )
    rows = (await db.execute(stmt)).all()
    candidate_session_ids = [int(row.candidate_session_id) for row in rows]
    (
        day_completion_by_session,
        latest_submission_by_session,
    ) = await _load_day_completion(
        db,
        simulation_id=simulation_id,
        candidate_session_ids=candidate_session_ids,
    )

    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        session_id = int(row.candidate_session_id)
        day_completion = day_completion_by_session.get(
            session_id, _default_day_completion()
        )

        fit_profile_status = derive_fit_profile_status(
            has_ready_profile=(
                row.latest_success_candidate_session_id is not None
                or row.fit_profile_generated_at is not None
            ),
            latest_run_status=row.latest_run_status,
            has_active_job=row.active_job_updated_at is not None,
        )
        candidate_status = derive_candidate_compare_status(
            fit_profile_status=fit_profile_status,
            day_completion=day_completion,
            candidate_session_status=row.candidate_session_status,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
        display_name = _display_name(row.candidate_name, position=index)
        fit_profile_updated_at = _fit_profile_updated_at(row)
        session_updated_at = _candidate_session_updated_at(
            row,
            latest_submission_at=latest_submission_by_session.get(session_id),
        )
        session_created_at = _candidate_session_created_at(row)
        updated_at = (
            fit_profile_updated_at
            or session_updated_at
            or session_created_at
            or datetime.now(UTC).replace(microsecond=0)
        )

        candidates.append(
            {
                "candidateSessionId": session_id,
                "candidateName": display_name,
                "candidateDisplayName": display_name,
                "status": candidate_status,
                "fitProfileStatus": fit_profile_status,
                "overallFitScore": _normalize_score(row.overall_fit_score),
                "recommendation": _normalize_recommendation(row.recommendation),
                "dayCompletion": day_completion,
                "updatedAt": updated_at,
            }
        )

    return {
        "simulationId": access.simulation_id,
        "candidates": candidates,
    }


__all__ = [
    "derive_candidate_compare_status",
    "derive_fit_profile_status",
    "list_candidates_compare_summary",
    "require_simulation_compare_access",
]
