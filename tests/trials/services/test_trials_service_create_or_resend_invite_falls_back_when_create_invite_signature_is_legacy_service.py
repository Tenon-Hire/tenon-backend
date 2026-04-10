from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_falls_back_when_create_invite_signature_is_legacy(
    monkeypatch,
):
    cs = CandidateSession(
        trial_id=1,
        candidate_name="Legacy",
        invite_email="legacy@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    call_count = 0

    async def fake_get_for_update(db, trial_id, invite_email):
        return None

    async def fake_create_invite_legacy(db, trial_id, payload, now=None):
        nonlocal call_count
        call_count += 1
        return cs, True

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_trial_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite_legacy)

    created, outcome = await sim_service.create_or_resend_invite(
        db=None,
        trial_id=1,
        payload=SimpleNamespace(inviteEmail="legacy@test.com"),
        now=datetime.now(UTC),
        scenario_version_id=999,
    )
    assert outcome == "created"
    assert created is cs
    assert call_count == 1
