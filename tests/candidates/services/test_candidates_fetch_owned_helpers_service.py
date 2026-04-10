from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_fetch_owned_helpers_service import (
    apply_auth_updates,
    ensure_can_access,
)
from app.config import settings
from app.shared.auth.principal import Principal
from app.shared.database.shared_database_models_model import CandidateSession
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
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
        trial=SimpleNamespace(status="terminated"),
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


@pytest.mark.asyncio
async def test_ensure_can_access_fails_closed_when_trial_unloaded(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="fail-closed@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    session_id = cs.id
    invite_email = cs.invite_email

    sim.status = TRIAL_STATUS_TERMINATED
    await async_session.commit()
    async_session.expunge_all()

    res = await async_session.execute(
        select(CandidateSession).where(CandidateSession.id == session_id)
    )
    unloaded = res.scalar_one()
    assert "trial" in sa_inspect(unloaded).unloaded

    principal = _principal(invite_email)
    with pytest.raises(HTTPException) as excinfo:
        ensure_can_access(unloaded, principal, now=datetime.now(UTC))
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Candidate session not found"
