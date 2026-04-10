"""Application module for candidates candidate sessions services candidates candidate sessions fetch owned helpers service workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_email_service import (
    normalize_email,
)
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_status_service import (
    mark_in_progress,
    require_not_expired,
)
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Candidate session not found"
)


def _loaded_trial_status(cs: CandidateSession) -> str | None:
    try:
        state = inspect(cs)
    except NoInspectionAvailable:
        trial = getattr(cs, "trial", None)
        return getattr(trial, "status", None)

    if "trial" in state.unloaded:
        raise _NOT_FOUND

    trial = state.attrs.trial.value
    if trial is None:
        raise _NOT_FOUND
    return getattr(trial, "status", None)


def ensure_can_access(
    cs: CandidateSession | None,
    _principal: Principal,
    *,
    now=None,
    allow_missing=True,
) -> CandidateSession:
    """Ensure can access."""
    if cs is None and allow_missing:
        raise _NOT_FOUND
    if cs is None:
        raise _NOT_FOUND
    if _loaded_trial_status(cs) == TRIAL_STATUS_TERMINATED:
        raise _NOT_FOUND
    require_not_expired(cs, now=now or shared_utcnow())
    return cs


def apply_auth_updates(cs: CandidateSession, principal: Principal, *, now) -> bool:
    """Apply auth updates."""
    changed = False
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
    return changed


__all__ = ["apply_auth_updates", "ensure_can_access"]
