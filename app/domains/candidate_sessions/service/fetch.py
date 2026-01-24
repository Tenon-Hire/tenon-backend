from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import CandidateSession
from app.domains.candidate_sessions import repository as cs_repo
from app.domains.candidate_sessions.service.ownership import ensure_candidate_ownership
from app.domains.candidate_sessions.service.status import (
    mark_in_progress,
    require_not_expired,
)
from app.infra.security.principal import Principal


async def fetch_by_token(db: AsyncSession, token: str, *, now=None) -> CandidateSession:
    cs = await cs_repo.get_by_token(db, token, with_simulation=True)
    if cs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite token")
    require_not_expired(cs, now=now)
    return cs


async def fetch_by_token_for_update(db: AsyncSession, token: str, *, now=None) -> CandidateSession:
    cs = await cs_repo.get_by_token_for_update(db, token)
    if cs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite token")
    require_not_expired(cs, now=now)
    return cs


async def fetch_owned_session(
    db: AsyncSession,
    session_id: int,
    principal: Principal,
    *,
    now=None,
) -> CandidateSession:
    now = now or datetime.now(UTC)
    cs = await cs_repo.get_by_id(db, session_id)
    if cs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found")
    require_not_expired(cs, now=now)
    stored_sub = getattr(cs, "candidate_auth0_sub", None)
    if stored_sub:
        if stored_sub != principal.sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found")
        changed = False
        from app.domains.candidate_sessions.service.email import normalize_email

        email = normalize_email(principal.email)
        if email and getattr(cs, "candidate_auth0_email", None) is None:
            cs.candidate_auth0_email = email
            changed = True
        if email and cs.candidate_email != email:
            cs.candidate_email = email
            changed = True
        if cs.status == "not_started":
            mark_in_progress(cs, now=now)
            changed = True
        if changed:
            await db.commit()
            await db.refresh(cs)
        return cs

    changed = False
    async with db.begin_nested():
        cs = await cs_repo.get_by_id_for_update(db, session_id)
        if cs is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found")
        require_not_expired(cs, now=now)
        if cs.candidate_auth0_sub and cs.candidate_auth0_sub != principal.sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found")
        changed = ensure_candidate_ownership(cs, principal, now=now)
        if cs.status == "not_started":
            mark_in_progress(cs, now=now)
            changed = True
    if changed:
        await db.commit()
        await db.refresh(cs)
    return cs
