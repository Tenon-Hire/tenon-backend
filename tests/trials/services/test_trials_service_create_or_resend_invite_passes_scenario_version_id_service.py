from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_passes_scenario_version_id(monkeypatch):
    cs = CandidateSession(
        trial_id=1,
        candidate_name="Scenario",
        invite_email="scenario@test.com",
        token="tok",
        status="not_started",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    captured = {}

    async def fake_get_for_update(db, trial_id, invite_email):
        return None

    async def fake_create_invite(
        db, trial_id, payload, now=None, scenario_version_id=None
    ):
        captured["scenario_version_id"] = scenario_version_id
        return cs, True

    monkeypatch.setattr(
        sim_service.cs_repo,
        "get_by_trial_and_email_for_update",
        fake_get_for_update,
    )
    monkeypatch.setattr(sim_service, "create_invite", fake_create_invite)

    created, outcome = await sim_service.create_or_resend_invite(
        db=None,
        trial_id=1,
        payload=SimpleNamespace(inviteEmail="scenario@test.com"),
        now=datetime.now(UTC),
        scenario_version_id=321,
    )
    assert outcome == "created"
    assert created is cs
    assert captured["scenario_version_id"] == 321
