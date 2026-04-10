"""Application module for trials services trials invite create service workflows."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateInviteRequest,
)
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow

from .trials_services_trials_invite_tokens_service import (
    INVITE_TOKEN_TTL_DAYS,
)


async def create_invite(
    db: AsyncSession,
    trial_id: int,
    payload: CandidateInviteRequest,
    *,
    scenario_version_id: int | None = None,
    now: datetime | None = None,
) -> tuple[CandidateSession, bool]:
    """Create invite."""
    now = now or shared_utcnow()
    invite_email = str(payload.inviteEmail).strip().lower()
    expires_at = now + timedelta(days=INVITE_TOKEN_TTL_DAYS)
    for _ in range(3):
        token = secrets.token_urlsafe(32)
        cs = CandidateSession(
            trial_id=trial_id,
            scenario_version_id=scenario_version_id,
            candidate_name=payload.candidateName,
            invite_email=invite_email,
            token=token,
            status="not_started",
            expires_at=expires_at,
        )
        try:
            async with db.begin_nested():
                db.add(cs)
                await db.flush()
            return cs, True
        except IntegrityError:
            existing = await cs_repo.get_by_trial_and_email(
                db, trial_id=trial_id, invite_email=invite_email
            )
            if existing:
                return existing, False
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate invite token",
    )
