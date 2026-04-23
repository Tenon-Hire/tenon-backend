"""Application module for jobs repositories repository lookup repository workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import CandidateSession, User
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import Job
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    normalize_email,
)


async def get_by_id(db: AsyncSession, job_id: str) -> Job | None:
    """Return by id."""
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
    """Return by id for principal."""
    talent_partner_job = await _talent_partner_job(db, job_id, principal)
    if talent_partner_job is not None:
        return talent_partner_job
    return await _candidate_job(db, job_id, principal)


async def _talent_partner_job(
    db: AsyncSession, job_id: str, principal: Principal
) -> Job | None:
    if "talent_partner:access" not in principal.permissions:
        return None
    talent_partner = (
        await db.execute(select(User).where(User.email == principal.email))
    ).scalar_one_or_none()
    company_id = getattr(talent_partner, "company_id", None)
    if company_id is None:
        return None
    return (
        await db.execute(
            select(Job).where(Job.id == job_id, Job.company_id == company_id)
        )
    ).scalar_one_or_none()


async def _candidate_job(
    db: AsyncSession, job_id: str, principal: Principal
) -> Job | None:
    if "candidate:access" not in principal.permissions:
        return None
    email = normalize_email(principal.email)
    if not email:
        return None
    candidate_row = (
        await db.execute(
            select(Job, CandidateSession)
            .join(CandidateSession, CandidateSession.id == Job.candidate_session_id)
            .where(Job.id == job_id)
        )
    ).first()
    if candidate_row is None:
        return None
    candidate_job, candidate_session = candidate_row
    if normalize_email(candidate_session.invite_email) != email:
        return None
    claimed_sub = (candidate_session.candidate_auth0_sub or "").strip()
    if claimed_sub and claimed_sub != principal.sub:
        return None
    return candidate_job
