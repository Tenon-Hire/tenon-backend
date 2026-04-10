"""Application module for trials routes trials routes trials routes invite render routes workflows."""

from __future__ import annotations

from fastapi import status
from fastapi.responses import JSONResponse

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateInviteErrorResponse,
    CandidateInviteResponse,
)


def render_invite_response(
    candidate_session, invite_url: str, outcome: str
) -> CandidateInviteResponse:
    """Render invite response."""
    return CandidateInviteResponse(
        candidateSessionId=candidate_session.id,
        token=candidate_session.token,
        inviteUrl=invite_url,
        outcome=outcome,
    )


def render_invite_error(exc) -> CandidateInviteErrorResponse:
    """Render invite error."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {"code": exc.code, "message": exc.message, "outcome": exc.outcome}
        },
    )


def render_invite_status(candidate_session) -> dict:
    """Render invite status."""
    return {
        "inviteEmailStatus": getattr(candidate_session, "invite_email_status", None),
        "inviteEmailSentAt": getattr(candidate_session, "invite_email_sent_at", None),
        "inviteEmailError": getattr(candidate_session, "invite_email_error", None),
    }
