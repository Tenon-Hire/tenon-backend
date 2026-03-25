from __future__ import annotations

import pytest

from tests.simulations.services.simulations_core_service_utils import *


@pytest.mark.asyncio
async def test_create_or_resend_invite_resends_active(async_session):
    recruiter = await create_recruiter(async_session, email="resend@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    payload = type(
        "P", (), {"candidateName": "Jane", "inviteEmail": "jane@example.com"}
    )
    first, _created = await sim_service.create_invite(
        async_session,
        simulation_id=sim.id,
        payload=payload,
        scenario_version_id=sim.active_scenario_version_id,
        now=datetime.now(UTC),
    )

    second, outcome = await sim_service.create_or_resend_invite(
        async_session, simulation_id=sim.id, payload=payload, now=datetime.now(UTC)
    )

    assert second.id == first.id
    assert outcome == "resent"
