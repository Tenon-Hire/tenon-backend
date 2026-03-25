from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_create_invite_success(async_session):
    recruiter = await create_recruiter(async_session, email="invite-success@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    assert sim.active_scenario_version_id is not None
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    cs, created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )
    assert cs.token
    assert cs.status == "not_started"
    assert created is True
