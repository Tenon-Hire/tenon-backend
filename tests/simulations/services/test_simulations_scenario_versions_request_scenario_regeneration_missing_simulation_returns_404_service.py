from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_request_scenario_regeneration_missing_simulation_returns_404(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-missing@test.com"
    )
    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.request_scenario_regeneration(
            async_session,
            simulation_id=999999,
            actor_user_id=recruiter.id,
        )
    assert excinfo.value.status_code == 404
