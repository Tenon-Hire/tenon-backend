"""Application module for evaluations services evaluations winoe report api service workflows."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories import repository as evaluation_repo
from app.evaluations.services.evaluations_services_evaluations_winoe_report_access_service import (
    CandidateSessionEvaluationContext,
    get_candidate_session_evaluation_context,
    has_company_access,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_api_helpers_service import (
    build_latest_run_status,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_api_helpers_service import (
    has_active_evaluation_job as _has_active_evaluation_job_impl,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_composer_service import (
    build_ready_payload,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_jobs_service import (
    EVALUATION_RUN_JOB_TYPE,
    enqueue_evaluation_run,
)
from app.shared.database.shared_database_models_model import User


async def _has_active_evaluation_job(
    db: AsyncSession,
    *,
    candidate_session_id: int,
) -> bool:
    return await _has_active_evaluation_job_impl(
        db,
        candidate_session_id=candidate_session_id,
        job_type=EVALUATION_RUN_JOB_TYPE,
    )


async def require_talent_partner_candidate_session_context(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    user: User,
) -> CandidateSessionEvaluationContext:
    """Require Talent Partner candidate session context."""
    context = await get_candidate_session_evaluation_context(
        db,
        candidate_session_id=candidate_session_id,
    )
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found"
        )
    if not has_company_access(
        trial_company_id=context.trial.company_id,
        expected_company_id=getattr(user, "company_id", None),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate session access forbidden",
        )
    return context


async def generate_winoe_report(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    user: User,
) -> dict[str, Any]:
    """Generate winoe report."""
    context = await require_talent_partner_candidate_session_context(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    job = await enqueue_evaluation_run(
        db,
        candidate_session_id=context.candidate_session.id,
        company_id=context.trial.company_id,
        requested_by_user_id=user.id,
        commit=True,
    )
    return {"jobId": job.id, "status": "queued"}


async def fetch_winoe_report(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    user: User,
) -> dict[str, Any]:
    """Return winoe report."""
    context = await require_talent_partner_candidate_session_context(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    session_id = context.candidate_session.id
    latest_success = (
        await evaluation_repo.get_latest_successful_run_for_candidate_session(
            db,
            candidate_session_id=session_id,
        )
    )
    if latest_success is not None:
        return build_ready_payload(latest_success)

    latest_run = await evaluation_repo.get_latest_run_for_candidate_session(
        db,
        candidate_session_id=session_id,
    )
    if latest_run is None:
        if await _has_active_evaluation_job(db, candidate_session_id=session_id):
            return {"status": "running"}
        return {"status": "not_started"}
    return build_latest_run_status(latest_run)


__all__ = [
    "fetch_winoe_report",
    "generate_winoe_report",
    "require_talent_partner_candidate_session_context",
]
