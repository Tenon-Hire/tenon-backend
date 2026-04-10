from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_create_invite_success(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="invite-success@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    assert sim.active_scenario_version_id is not None
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    cs, created = await sim_service.create_invite(
        async_session,
        trial_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    assert cs.token
    assert cs.status == "not_started"
    assert created is True
