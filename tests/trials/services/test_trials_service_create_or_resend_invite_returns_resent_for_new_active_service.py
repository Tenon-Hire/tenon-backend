from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_returns_resent_for_new_active(monkeypatch):
    cs = CandidateSession(
        trial_id=1,
        candidate_name="Active",
        invite_email="active@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    async def fake_get_for_update(db, trial_id, invite_email):
        return None

    async def fake_create_invite(db, trial_id, payload, now=None):
        return cs, False

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_trial_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    created, outcome = await sim_service.create_or_resend_invite(
        db=None,
        trial_id=1,
        payload=SimpleNamespace(inviteEmail="active@test.com"),
        now=datetime.now(UTC),
    )
    assert outcome == "resent"
    assert created is cs
