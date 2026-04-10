from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_require_owned_trial_with_tasks_success(async_session):
    talent_partner = await create_talent_partner(async_session, email="owned@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    found_sim, found_tasks = await sim_service.require_owned_trial_with_tasks(
        async_session, sim.id, talent_partner.id
    )
    assert found_sim.id == sim.id
    assert [t.id for t in found_tasks] == [t.id for t in tasks]
