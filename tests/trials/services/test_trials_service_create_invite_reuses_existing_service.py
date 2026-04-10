from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_invite_reuses_existing(async_session, monkeypatch):
    talent_partner = await create_talent_partner(async_session, email="reuse@test.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    first, created = await sim_service.create_invite(
        async_session,
        trial_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    assert created is True
    first_id = first.id
    fail_once = True
    original_commit = async_session.commit

    async def _commit_with_integrity_error():
        nonlocal fail_once
        if fail_once:
            fail_once = False
            raise IntegrityError("", {}, None)
        return await original_commit()

    async def _get_existing(*_args, **_kwargs):
        return type("S", (), {"id": first_id})()

    monkeypatch.setattr(async_session, "commit", _commit_with_integrity_error)
    monkeypatch.setattr(sim_service.cs_repo, "get_by_trial_and_email", _get_existing)
    second, created = await sim_service.create_invite(
        async_session,
        trial_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    assert second.id == first_id
    assert created is False
