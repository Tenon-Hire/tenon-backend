from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_not_found(async_session):
    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, simulation_id=999999
        )
    assert excinfo.value.status_code == 404
