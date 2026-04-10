"""Application module for trials services trials listing service workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    WinoeReport,
)
from app.trials.repositories import repository as sim_repo


async def list_trials(
    db: AsyncSession, user_id: int, *, include_terminated: bool = False
):
    """List trials with candidate counts for a Talent Partner."""
    return await sim_repo.list_with_candidate_counts(
        db, user_id, include_terminated=include_terminated
    )


async def list_candidates_with_profile(
    db: AsyncSession, trial_id: int
) -> list[tuple[CandidateSession, int | None]]:
    """Return candidates with profile."""
    stmt = (
        select(CandidateSession, WinoeReport.id)
        .options(
            load_only(
                CandidateSession.id,
                CandidateSession.invite_email,
                CandidateSession.candidate_name,
                CandidateSession.token,
                CandidateSession.status,
                CandidateSession.started_at,
                CandidateSession.completed_at,
                CandidateSession.invite_email_status,
                CandidateSession.invite_email_sent_at,
                CandidateSession.invite_email_error,
            )
        )
        .outerjoin(
            WinoeReport,
            WinoeReport.candidate_session_id == CandidateSession.id,
        )
        .where(CandidateSession.trial_id == trial_id)
        .order_by(CandidateSession.id.desc())
    )
    return (await db.execute(stmt)).all()
