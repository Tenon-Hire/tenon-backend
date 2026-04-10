from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_list_with_candidate_counts(async_session):
    talent_partner = await create_talent_partner(async_session, email="counts@test.com")
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    rows = await sim_service.list_trials(async_session, talent_partner.id)
    assert rows[0][0].id == sim.id
