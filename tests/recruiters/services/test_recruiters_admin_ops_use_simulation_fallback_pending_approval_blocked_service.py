from __future__ import annotations

import pytest

from tests.recruiters.services.recruiters_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_simulation_fallback_pending_approval_blocked(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-pending-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    scenario_v2 = await _create_scenario_version(
        async_session,
        simulation_id=simulation.id,
        version_index=2,
    )
    simulation.pending_scenario_version_id = scenario_v2.id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="pending approval blocked",
            dry_run=False,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_APPROVAL_PENDING"
