"""Application module for trials services trials candidates compare access service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.evaluations.services.evaluations_services_evaluations_winoe_report_access_service import (
    has_company_access,
)
from app.shared.database.shared_database_models_model import Trial, User
from app.trials.services.trials_services_trials_candidates_compare_model import (
    TrialCompareAccessContext,
)


async def require_trial_compare_access(
    db: AsyncSession,
    *,
    trial_id: int,
    user: User,
) -> TrialCompareAccessContext:
    """Require trial compare access."""
    trial = (
        await db.execute(
            select(Trial)
            .options(load_only(Trial.id, Trial.company_id, Trial.created_by))
            .where(Trial.id == trial_id)
        )
    ).scalar_one_or_none()
    if trial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trial not found",
        )
    if not has_company_access(
        trial_company_id=trial.company_id,
        expected_company_id=getattr(user, "company_id", None),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trial access forbidden",
        )
    if trial.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trial access forbidden",
        )
    return TrialCompareAccessContext(trial_id=trial.id)


__all__ = ["require_trial_compare_access"]
