from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.auth.principal import Principal
from app.core.settings import settings
from app.services.candidate_sessions.fetch_owned_helpers import (
    apply_auth_updates,
    ensure_can_access,
)


def _principal(email: str) -> Principal:
    email_claim = settings.auth.AUTH0_EMAIL_CLAIM
    permissions_claim = settings.auth.AUTH0_PERMISSIONS_CLAIM
    claims = {
        "sub": f"candidate-{email}",
        "email": email,
        email_claim: email,
        "permissions": ["candidate:access"],
        permissions_claim: ["candidate:access"],
        "email_verified": True,
    }
    return Principal(
        sub=f"candidate-{email}",
        email=email,
        name=email.split("@")[0],
        roles=[],
        permissions=["candidate:access"],
        claims=claims,
    )


def test_ensure_can_access_hides_terminated_sessions():
    principal = _principal("hidden@example.com")
    session = SimpleNamespace(
        status="not_started",
        started_at=None,
        expires_at=None,
        simulation=SimpleNamespace(status="terminated"),
    )
    with pytest.raises(HTTPException) as excinfo:
        ensure_can_access(session, principal, now=datetime.now(UTC))
    assert excinfo.value.status_code == 404


def test_apply_auth_updates_sets_candidate_emails_and_progress():
    principal = _principal("owner@example.com")
    now = datetime.now(UTC)
    session = SimpleNamespace(
        candidate_auth0_email=None,
        candidate_email=None,
        status="not_started",
        started_at=None,
    )
    changed = apply_auth_updates(session, principal, now=now)
    assert changed is True
    assert session.candidate_auth0_email == "owner@example.com"
    assert session.candidate_email == "owner@example.com"
    assert session.status == "in_progress"
    assert session.started_at == now
