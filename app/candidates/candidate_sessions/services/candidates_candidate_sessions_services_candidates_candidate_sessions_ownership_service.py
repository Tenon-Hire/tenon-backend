"""Application module for candidates candidate sessions services candidates candidate sessions ownership service workflows."""

from __future__ import annotations

from fastapi import status

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_email_service import (
    normalize_email,
)
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.utils.shared_utils_errors_utils import (
    CANDIDATE_AUTH_EMAIL_MISSING,
    CANDIDATE_EMAIL_NOT_VERIFIED,
    CANDIDATE_INVITE_EMAIL_MISMATCH,
    CANDIDATE_SESSION_ALREADY_CLAIMED,
    ApiError,
)


def _forbidden(detail: str, error_code: str) -> None:
    raise ApiError(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
        error_code=error_code,
        retryable=False,
    )


def ensure_email_verified(principal: Principal) -> None:
    """Ensure email verified."""
    if principal.claims.get("email_verified") is not True:
        _forbidden(
            "Authenticated email is not verified.",
            CANDIDATE_EMAIL_NOT_VERIFIED,
        )


def ensure_candidate_ownership(
    candidate_session: CandidateSession, principal: Principal, *, now
) -> bool:
    """Ensure candidate ownership."""
    ensure_email_verified(principal)
    email = normalize_email(principal.email)
    if not email:
        _forbidden(
            "Authenticated email claim is missing.",
            CANDIDATE_AUTH_EMAIL_MISSING,
        )

    invite_email = normalize_email(candidate_session.invite_email)
    if invite_email != email:
        _forbidden(
            "Invite email does not match authenticated user.",
            CANDIDATE_INVITE_EMAIL_MISMATCH,
        )

    stored_sub = getattr(candidate_session, "candidate_auth0_sub", None)
    if stored_sub and stored_sub != principal.sub:
        _forbidden(
            "Candidate session is already claimed by another user.",
            CANDIDATE_SESSION_ALREADY_CLAIMED,
        )
    changed = False
    if not stored_sub:
        candidate_session.candidate_auth0_sub = principal.sub
        changed = True
        if getattr(candidate_session, "claimed_at", None) is None:
            candidate_session.claimed_at = now
            changed = True
    if getattr(candidate_session, "candidate_auth0_email", None) != email:
        candidate_session.candidate_auth0_email = email
        changed = True
    if candidate_session.candidate_email != email:
        candidate_session.candidate_email = email
        changed = True
    return changed
