from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_require_owned_trial_success(async_session):
    talent_partner = await create_talent_partner(async_session, email="owned@test.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    owned = await sim_service.require_owned_trial(
        async_session, sim.id, talent_partner.id
    )
    assert owned.id == sim.id
