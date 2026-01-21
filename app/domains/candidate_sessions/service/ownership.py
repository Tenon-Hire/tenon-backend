from __future__ import annotations

from fastapi import HTTPException, status

from app.domains import CandidateSession
from app.domains.candidate_sessions.service.email import normalize_email
from app.infra.security.principal import Principal


def ensure_email_verified(principal: Principal) -> None:
    if principal.claims.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )


def ensure_candidate_ownership(
    candidate_session: CandidateSession, principal: Principal, *, now
) -> bool:
    stored_sub = getattr(candidate_session, "candidate_auth0_sub", None)
    if stored_sub:
        if stored_sub != principal.sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate session not found",
            )
        changed = False
        email = normalize_email(principal.email)
        if email and getattr(candidate_session, "candidate_auth0_email", None) is None:
            candidate_session.candidate_auth0_email = email
            changed = True
        if email and candidate_session.candidate_email != email:
            candidate_session.candidate_email = email
            changed = True
        return changed

    ensure_email_verified(principal)
    email = normalize_email(principal.email)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email claim missing",
        )

    invite_email = normalize_email(candidate_session.invite_email)
    if invite_email != email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate session not found",
        )

    candidate_session.candidate_auth0_sub = principal.sub
    candidate_session.candidate_auth0_email = email
    candidate_session.candidate_email = email
    if getattr(candidate_session, "claimed_at", None) is None:
        candidate_session.claimed_at = now
    return True
