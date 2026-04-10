"""Application module for candidates candidate sessions services candidates candidate sessions fetch owned service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_fetch_owned_helpers_service import (
    apply_auth_updates,
    ensure_can_access,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_ownership_service import (
    ensure_candidate_ownership,
)
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow


async def fetch_owned_session(
    db: AsyncSession, session_id: int, principal: Principal, *, now=None
) -> CandidateSession:
    """Return owned session."""
    now = now or shared_utcnow()
    cs = ensure_can_access(await cs_repo.get_by_id(db, session_id), principal, now=now)
    if cs.candidate_auth0_sub:
        changed = ensure_candidate_ownership(cs, principal, now=now)
        changed = apply_auth_updates(cs, principal, now=now) or changed
        if changed:
            await db.commit()
            await db.refresh(cs, attribute_names=["trial", "scenario_version"])
        return cs

    changed = False
    async with db.begin_nested():
        cs = ensure_can_access(
            await cs_repo.get_by_id_for_update(db, session_id),
            principal,
            now=now,
            allow_missing=False,
        )
        changed = ensure_candidate_ownership(cs, principal, now=now) or changed
        changed = apply_auth_updates(cs, principal, now=now) or changed
    if changed:
        await db.commit()
        await db.refresh(cs, attribute_names=["trial", "scenario_version"])
    return cs


__all__ = ["fetch_owned_session"]
