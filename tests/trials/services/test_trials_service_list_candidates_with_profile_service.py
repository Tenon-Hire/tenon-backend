from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_list_candidates_with_profile(async_session):
    talent_partner = await create_talent_partner(async_session, email="list@test.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs, _created = await sim_service.create_invite(
        async_session,
        trial_id=sim.id,
        payload=type("P", (), {"candidateName": "a", "inviteEmail": "b@example.com"}),
        scenario_version_id=sim.active_scenario_version_id,
    )
    rows = await sim_service.list_candidates_with_profile(async_session, sim.id)
    assert rows and rows[0][0].id == cs.id
