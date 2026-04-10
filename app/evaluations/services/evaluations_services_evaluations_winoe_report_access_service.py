"""Application module for evaluations services evaluations winoe report access service workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    ScenarioVersion,
    Trial,
)


@dataclass(slots=True)
class CandidateSessionEvaluationContext:
    """Represent candidate session evaluation context data and behavior."""

    candidate_session: CandidateSession
    trial: Trial
    scenario_version: ScenarioVersion | None


async def get_candidate_session_evaluation_context(
    db: AsyncSession,
    *,
    candidate_session_id: int,
) -> CandidateSessionEvaluationContext | None:
    """Return candidate session evaluation context."""
    row = (
        await db.execute(
            select(CandidateSession, Trial, ScenarioVersion)
            .join(Trial, Trial.id == CandidateSession.trial_id)
            .outerjoin(
                ScenarioVersion,
                ScenarioVersion.id == CandidateSession.scenario_version_id,
            )
            .where(CandidateSession.id == candidate_session_id)
        )
    ).first()
    if row is None:
        return None

    candidate_session, trial, scenario_version = row
    return CandidateSessionEvaluationContext(
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
    )


def has_company_access(
    *,
    trial_company_id: int | None,
    expected_company_id: int | None,
) -> bool:
    """Execute has company access."""
    if expected_company_id is None:
        return True
    return trial_company_id == expected_company_id


__all__ = [
    "CandidateSessionEvaluationContext",
    "get_candidate_session_evaluation_context",
    "has_company_access",
]
