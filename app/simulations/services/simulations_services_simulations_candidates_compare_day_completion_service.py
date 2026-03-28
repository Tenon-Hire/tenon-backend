"""Application module for simulations services simulations candidates compare day completion service workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Submission,
    Task,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_constants import (
    COMPARE_DAYS,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_time_service import (
    default_day_completion,
    max_datetime,
    normalize_datetime,
)


async def load_day_completion(
    db: AsyncSession,
    *,
    simulation_id: int,
    candidate_session_ids: list[int],
) -> tuple[dict[int, dict[str, bool]], dict[int, datetime | None]]:
    """Load day completion."""
    completion_by_session = {
        session_id: default_day_completion() for session_id in candidate_session_ids
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
            Task.day_index.in_(COMPARE_DAYS),
        )
        .group_by(CandidateSession.id, Task.day_index)
    )
    for row in (await db.execute(stmt)).all():
        session_id = int(row.candidate_session_id)
        day_key = str(int(row.day_index))
        if day_key not in completion_by_session[session_id]:
            continue
        task_count = int(row.task_count or 0)
        submitted_count = int(row.submitted_count or 0)
        completion_by_session[session_id][day_key] = (
            task_count > 0 and submitted_count >= task_count
        )
        latest_submission = normalize_datetime(row.latest_submission_at)
        if latest_submission is None:
            continue
        latest_submission_by_session[session_id] = max_datetime(
            latest_submission_by_session.get(session_id),
            latest_submission,
        )
    return completion_by_session, latest_submission_by_session


__all__ = ["load_day_completion"]
