"""Application module for trials services trials candidates compare queries service workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    WinoeReport,
)
from app.trials.services.trials_services_trials_candidates_compare_subqueries_service import (
    active_job_subquery,
    latest_run_subquery,
)


def _candidate_session_timestamp_columns() -> tuple[Any, Any]:
    created_column = getattr(CandidateSession, "created_at", None)
    updated_column = getattr(CandidateSession, "updated_at", None)
    created_at = (
        created_column.label("candidate_session_created_at")
        if created_column is not None
        else literal(None).label("candidate_session_created_at")
    )
    updated_at = (
        updated_column.label("candidate_session_updated_at")
        if updated_column is not None
        else literal(None).label("candidate_session_updated_at")
    )
    return created_at, updated_at


def candidate_compare_rows_stmt(*, trial_id: int) -> Any:
    """Execute candidate compare rows stmt."""
    latest_run_any = latest_run_subquery(completed_only=False)
    latest_run_success = latest_run_subquery(completed_only=True)
    (
        candidate_session_created_at,
        candidate_session_updated_at,
    ) = _candidate_session_timestamp_columns()
    active_job = active_job_subquery()
    return (
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
            WinoeReport.generated_at.label("winoe_report_generated_at"),
            latest_run_any.c.run_status.label("latest_run_status"),
            latest_run_any.c.run_started_at.label("latest_run_started_at"),
            latest_run_any.c.run_completed_at.label("latest_run_completed_at"),
            latest_run_any.c.run_generated_at.label("latest_run_generated_at"),
            latest_run_success.c.candidate_session_id.label(
                "latest_success_candidate_session_id"
            ),
            latest_run_success.c.overall_winoe_score.label("overall_winoe_score"),
            latest_run_success.c.recommendation.label("recommendation"),
            latest_run_success.c.run_started_at.label("latest_success_started_at"),
            latest_run_success.c.run_completed_at.label("latest_success_completed_at"),
            latest_run_success.c.run_generated_at.label("latest_success_generated_at"),
            active_job.c.active_job_updated_at.label("active_job_updated_at"),
        )
        .outerjoin(WinoeReport, WinoeReport.candidate_session_id == CandidateSession.id)
        .outerjoin(
            latest_run_any, latest_run_any.c.candidate_session_id == CandidateSession.id
        )
        .outerjoin(
            latest_run_success,
            latest_run_success.c.candidate_session_id == CandidateSession.id,
        )
        .outerjoin(active_job, active_job.c.candidate_session_id == CandidateSession.id)
        .where(CandidateSession.trial_id == trial_id)
        .order_by(CandidateSession.id.asc())
    )


async def fetch_candidate_compare_rows(db: AsyncSession, *, trial_id: int) -> list[Any]:
    """Return candidate compare rows."""
    stmt = candidate_compare_rows_stmt(trial_id=trial_id)
    return list((await db.execute(stmt)).all())


__all__ = ["candidate_compare_rows_stmt", "fetch_candidate_compare_rows"]
