from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime

from fastapi import HTTPException

from app.candidates.candidate_sessions import services as cs_service
from app.config import settings
from app.shared.auth.principal import Principal
from app.trials.repositories.trials_repositories_trials_trial_status_constants import (
    TRIAL_STATUS_TERMINATED,
)
from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)


def _principal(email: str, *, email_verified: bool | None = True) -> Principal:
    email_claim = settings.auth.AUTH0_EMAIL_CLAIM
    permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
    claims = {
        "sub": f"auth0|{email}",
        "email": email,
        email_claim: email,
        "permissions": ["candidate:access"],
        permissions_claim: ["candidate:access"],
    }
    if email_verified is not None:
        claims["email_verified"] = email_verified
    return Principal(
        sub=f"auth0|{email}",
        email=email,
        name=email.split("@")[0],
        roles=[],
        permissions=["candidate:access"],
        claims=claims,
    )


class _DummyDB:
    def __init__(self, cs_for_update):
        self.cs_for_update = cs_for_update

    def begin_nested(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed = obj


__all__ = [name for name in globals() if not name.startswith("__")]
